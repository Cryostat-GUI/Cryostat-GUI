from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
# from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
# from PyQt5.QtCore import QAbstractListModel, QFile, QIODevice, QModelIndex, Qt
from PyQt5.uic import loadUi


from copy import deepcopy

import sys
# import datetime
# import pickle
# import os
import re
import threading

from util import Window_ui


from qlistmodel import SequenceListModel
from qlistmodel import ScanListModel


dropstring = re.compile(r'([a-zA-Z0-9])')
searchf_number = re.compile(r'([0-9]+[.]*[0-9]*)')
searchf_string = re.compile(r'''["']{2}(.*?)["']{2}''')
textnesting = '   '


class EOSException(Exception):
    """Exception to raise if an EOS was encountered"""
    pass


def read_nums(comm):
    """convert a string of numbers into a list of floats"""
    return [float(x) for x in searchf_number.findall(comm)]


def parse_binary(number):
    """parse an integer number which represents a sum of bits
        returns a list with True and False, from back to front
    """
    nums = list(reversed('{:b}'.format(number)))
    print(nums)
    for ct, num in enumerate(nums):
        nums[ct] = True if int(num) else False
    return nums


def parse_binary_dataflags(number):
    """parse flags what to store"""
    nums = parse_binary(number)
    names = ['General Status', 'Temperature',
             'Magnetic Field', 'Sample Position',
             'Chan 1 Resistivity', 'Chan 1 Excitation',
             'Chan 2 Resistivity', 'Chan 2 Excitation',
             'Chan 3 Resistivity', 'Chan 3 Excitation',
             'Chan 4 Resistivity', 'Chan 4 Excitation']
    empty = [False for x in names]
    bare = dict(zip(names, empty))
    bare.update(dict(zip(names, nums)))
    return bare


def displaytext_waiting(data):
    """generate the displaytext for the wait function"""
    string = 'Wait for '
    separator = ', ' if data['Temp'] and data['Field'] else ''
    sep_taken = False

    if data['Temp']:
        string += 'Temperature' + separator
        sep_taken = True
    if data['Field']:
        string = string + 'Field' if sep_taken else string + 'Field' + separator
        sep_taken = True
    string += ' & {} seconds more'.format(data['Delay'])
    return string


def displaytext_scan_T(data):
    """generate the displaytext for the temperature scan"""
    # if data['ApproachMode'] == 0:
    #     mode = 'Fast Settle (single Set Temperature)'
    # if data['ApproachMode'] == 1:
    #     mode = "No o'shoot (slow - not yet implemented!)"
    #     raise NotImplementedError('There is no "No o\'shoot" mode yet!')
    # if data['ApproachMode'] == 2:
    #     mode = 'Sweep'

    return 'Scan Temperature from {start} to {end} in {Nsteps} steps, {SweepRate}K/min, {ApproachMode}, {SpacingCode}'.format(**data)


def displaytext_set_temp(data):
    """generate the displaytext for a set temperature"""
    return 'Set Temperature to {Temp} at {SweepRate}K/min (rate is only a wish...)'.format(**data)


def displatext_res_scan_exc(data):
    """generate the displaytext for an excitation scan"""
    # TODO - finish this up
    return 'Scanning RES Excitation'


def displaytext_res(data):
    """generate the displaytext for the resistivity measurement"""
    # TODO - finish this up
    return 'Measuring Resistance'


def displaytext_set_field(data):
    """generate the displaytext for a set field"""
    return 'Set Field to {Field} at {SweepRate}T/min (rate is only a wish...)'.format(**data)


def parse_set_temp(comm, nesting_level):
    """parse a command to set a single temperature"""
    # TODO: Fast settle
    nums = read_nums(comm)
    dic = dict(typ='set_T', Temp=nums[0], SweepRate=nums[1])
    dic['DisplayText'] = textnesting * \
        nesting_level + displaytext_set_temp(dic)
    return dic


def parse_set_field(comm, nesting_level):
    """parse a command to set a single field"""
    nums = read_nums(comm)
    dic = dict(typ='set_Field', Field=nums[0], SweepRate=nums[1])
    dic['DisplayText'] = textnesting * \
        nesting_level + displaytext_set_field(dic)
    return dic


def parse_waiting(comm, nesting_level):
    """parse a command to wait for certain values"""
    nums = read_nums(comm)
    dic = dict(typ='Wait',
               Temp=bool(int(nums[1])),
               Field=bool(int(nums[2])),
               Position=bool(int(nums[3])),
               Chamber=bool(int(nums[4])),
               Delay=nums[0])
    dic['DisplayText'] = textnesting * nesting_level + displaytext_waiting(dic)
    return dic
    # dic.update(local_dic.update(dict(DisplayText=self.parse_waiting(local_dic))))


def parse_chain_sequence(comm, nesting_level):
    """parse a command to chain a sequence file"""
    file = comm[4:]
    return dict(typ='chain sequence', new_file_seq=file,
                DisplayText=textnesting * nesting_level + 'Chain sequence: {}'.format(comm))
    # print('CHN', comm, dic)
    # return dic


def parse_res_change_datafile(comm, nesting_level):
    """parse a command to change the datafile"""
    file = searchf_string.findall(comm)
    return dict(typ='change datafile', new_file_data=file,
                mode='a' if comm[-1] == '1' else 'w',
                # a - appending, w - writing, can be inserted
                # directly into opening statement
                DisplayText=textnesting * nesting_level + 'Change data file: {}'.format(file))
    # print('CDF', comm, dic)
    # return dic


def parse_res_datafilecomment(comm, nesting_level):
    """parse a command to write a comment to the datafile"""
    comment = searchf_string.findall(comm)[0]
    dic = dict(typ='datafilecomment',
               comment=comment,
               DisplayText=textnesting * nesting_level +
               'Datafile Comment: {}'.format(comment))
    return dic


def parse_res_bridge_setup(nums):
    """parse the res bridge setup for an excitation scan"""
    bridge_setup = []
    bridge_setup.append(nums[:5])
    bridge_setup.append(nums[5:10])
    bridge_setup.append(nums[10:15])
    bridge_setup.append(nums[15:20])
    for ct, channel in enumerate(bridge_setup):
        bridge_setup[ct] = dict(limit_power_uW=channel[
                                1], limit_voltage_mV=channel[4])
        bridge_setup[ct]['ac_dc'] = 'AC' if channel[2] == 0 else 'DC'
        bridge_setup[ct]['on_off'] = True if channel[0] == 2 else False
        bridge_setup[ct]['calibration_mode'] = 'Standard' if channel[
            3] == 0 else 'Fast'
    return bridge_setup


def parse_res(comm, nesting_level):
    """parse a command to measure resistivity"""
    nums = read_nums(comm)
    dataflags = parse_binary_dataflags(nums[0])
    reading_count = nums[1]
    nums = nums[2:]
    bridge_conf = []
    bridge_conf.append(nums[:6])
    bridge_conf.append(nums[6:12])
    bridge_conf.append(nums[12:18])
    bridge_conf.append(nums[18:24])
    for ct, channel in enumerate(bridge_conf):
        bridge_conf[ct] = dict(limit_power_uW=channel[2], limit_current_uA=channel[
                               1], limit_voltage_mV=channel[5])
        bridge_conf[ct]['on_off'] = True if channel[0] == 2 else False
        bridge_conf[ct]['ac_dc'] = 'AC' if channel[3] == 0 else 'DC'
        bridge_conf[ct]['calibration_mode'] = 'Standard' if channel[
            4] == 0 else 'Fast'
    data = dict(dataflags=dataflags, reading_count=reading_count,
                bridge_conf=bridge_conf)
    data['DisplayText'] = textnesting * nesting_level + displaytext_res(data)
    return data


def parse_res_scan_excitation(comm, nesting_level):
    """parse a command to do an excitation scan"""
    nums = read_nums(comm)
    scan_setup = []
    scan_setup.append(nums[:3])  # 1
    scan_setup.append(nums[3:6])  # 2
    scan_setup.append(nums[6:9])  # 3
    scan_setup.append(nums[9:12])  # 4
    for ct, channel in enumerate(scan_setup):
        scan_setup[ct] = dict(start=channel[0], end=[channel[1]])
        if channel[-1] == 0:
            scan_setup[ct]['Spacing'] = 'linear'
        if channel[-1] == 1:
            scan_setup[ct]['Spacing'] = 'log'
        if channel[-1] == 2:
            scan_setup[ct]['Spacing'] = 'power'

    dataflags = parse_binary_dataflags(nums[14])
    n_steps = nums[12]
    reading_count = nums[13]
    bridge_setup = parse_res_bridge_setup(nums[15:35])
    data = dict(scan_setup=scan_setup, bridge_setup=bridge_setup,
                dataflags=dataflags, n_steps=n_steps,
                reading_count=reading_count)
    data['DisplayText'] = textnesting * \
        nesting_level + displatext_res_scan_exc(data)
    return data


def parse_scan_T(comm, nesting_level):
    """parse a command to do a temperature scan"""
    temps = read_nums(comm)
    # temps are floats!
    if len(temps) < 6:
        raise AssertionError(
            'not enough specifying numbers for T-scan!')

    dic = dict(typ='scan_T', start=temps[0],
               end=temps[1],
               SweepRate=temps[2],
               Nsteps=temps[3],
               SpacingCode=temps[4],
               ApproachMode=temps[5])
    if int(temps[4]) == 0:
        dic['SpacingCode'] = 'uniform'
    elif int(temps[4]) == 1:
        dic['SpacingCode'] = '1/T'
    elif int(temps[4]) == 2:
        dic['SpacingCode'] = 'logT'

    if int(temps[5]) == 0:
        dic['ApproachMode'] = 'Fast'
    elif int(temps[5]) == 1:
        dic['ApproachMode'] = 'No O\'Shoot'
    elif int(temps[5]) == 2:
        dic['ApproachMode'] = 'Sweep'
    dic['DisplayText'] = textnesting * nesting_level + displaytext_scan_T(dic)
    return dic


class Window_ChangeDataFile(QtWidgets.QDialog):
    """docstring for Window_waiting"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()

    def __init__(self, ui_file='.\\configurations\\Sequence_change_datafile.ui'):
        """build ui, build dict, connect to signals"""
        super(Window_ChangeDataFile, self).__init__()
        loadUi(ui_file, self)

        self.conf = dict(typ='change datafile', new_file_data='',
                         mode='',
                         DisplayText='')
        self.lineFileLocation.setText(self.conf['new_file_data'])
        self.lineFileLocation.textChanged.connect(
            lambda value: self.setValue('new_file_data', value))
        self.pushBrowse.clicked.connect(self.Browse)
        self.comboMode.activated['int'].connect(self.setMode)

        self.buttonDialog.accepted.connect(self.acc)
        self.buttonDialog.rejected.connect(self.close)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""
        # if not self.conf['Temp'] and not self.conf['Field']:
        #     self.reject()
        #     return
        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()

    def setValue(self, parameter, value):
        """set any kind of value in the conf dict"""
        self.conf[parameter] = value

    def Browse(self):
        """open File Saving Dialog, to choose the datafile, set datafile in conf dict"""
        new_file_data, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose Datafile',
                                                                  'c:\\', "Datafiles (*.dat)")
        self.setValue('new_file_data', new_file_data)
        self.lineFileLocation.setText(self.conf['new_file_data'])

    def setMode(self, modeint):
        pass


class Window_waiting(QtWidgets.QDialog):
    """docstring for Window_waiting"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()

    def __init__(self, ui_file='.\\configurations\\sequence_waiting.ui'):
        """build ui, build dict, connect to signals"""
        super(Window_waiting, self).__init__()
        loadUi(ui_file, self)

        self.conf = dict(typ='Wait', Temp=False, Field=False, Delay=0)
        self.check_Temp.toggled.connect(
            lambda value: self.setValue('Temp', value))
        self.check_Field.toggled.connect(
            lambda value: self.setValue('Field', value))
        self.spin_delayseconds.valueChanged.connect(
            lambda value: self.setValue('Delay', value))
        self.buttonDialog.accepted.connect(self.acc)
        self.buttonDialog.rejected.connect(self.close)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""
        # if not self.conf['Temp'] and not self.conf['Field']:
        #     self.reject()
        #     return
        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()

    def setValue(self, parameter, value):
        """set any kind of value in the conf dict"""
        self.conf[parameter] = value

    # def accepted(self):
    #     self.sig_accept.emit(self.conf)


class Window_Tscan(QtWidgets.QDialog):
    """docstring for Window_Tscan"""

    sig_accept = pyqtSignal(dict)
    sig_reject = pyqtSignal()
    sig_updateScanListModel = pyqtSignal(dict)

    def __init__(self, ui_file='.\\configurations\\sequence_scan_temperature.ui', **kwargs):
        super(Window_Tscan, self).__init__(**kwargs)
        loadUi(ui_file, self)

        QTimer.singleShot(0, self.initialisations)
        self.dictlock = threading.Lock()

    def initialisations(self):

        # BUGS BUGS BUGS

        self.conf = dict(typ='scan_T', measuretype='RES')
        self.__scanconf = dict(
            start=0,
            end=0,
            Nsteps=None,
            SizeSteps=None)
        self.putin_start = False
        self.putin_end = False
        self.putin_N = False
        self.putin_Size = False
        self.model = ScanListModel(self, 0, 0, 0, 0)
        self.listTemperatures.setModel(self.model)

        self._LCD_stepsize = 0
        self._LCD_Nsteps = 0
        self.update_lcds()

        self.buttonOK.clicked.connect(self.acc)
        self.buttonCANCEL.clicked.connect(self.close)

        self.comboSetTempramp.activated['int'].connect(self.setRampCondition)
        self.spinSetRate.valueChanged.connect(self.setSweepRate)

        self.spinSetTstart.valueChanged.connect(self.setTstart)
        self.spinSetTstart.editingFinished.connect(
            lambda: self.update_list(None, None))

        self.spinSetTend.valueChanged.connect(self.setTend)
        self.spinSetTend.editingFinished.connect(
            lambda: self.update_list(None, None))

        # self.spinSetNsteps.valueChanged.connect(lambda value: self.printing('spinSetNsteps: valueChanged: {}'.format(value)))
        # self.spinSetNsteps.editingFinished.connect(lambda: self.printing('spinSetNsteps: editingFinished'))
        # self.model.sig_Nsteps.connect(lambda value: self.printing('model: sig_Nsteps: {}'.format(value)))

        self.spinSetNsteps.valueChanged.connect(self.setN)
        self.spinSetNsteps.editingFinished.connect(
            lambda: self.setLCDNsteps(self.__scanconf['Nsteps']))
        self.spinSetNsteps.editingFinished.connect(
            lambda: self.update_list(1, 0))
        self.model.sig_Nsteps.connect(lambda value: self.setLCDNsteps(value))
        # self.model.sig_Nsteps.connect(self.spinSetNsteps.setValue)

        # self.spinSetSizeSteps.valueChanged.connect(lambda value: self.printing('spinSetSizeSteps: valueChanged: {}'.format(value)))
        # self.model.sig_stepsize.connect(lambda value: self.printing('model: sig_stepsize: {}'.format(value)))
        # self.spinSetSizeSteps.editingFinished.connect(lambda: self.printing('spinSetSizeSteps: editingFinished'))

        self.spinSetSizeSteps.valueChanged.connect(self.setSizeSteps)
        self.spinSetSizeSteps.editingFinished.connect(
            lambda: self.setLCDstepsize(self.__scanconf['SizeSteps']))
        self.spinSetSizeSteps.editingFinished.connect(
            lambda: self.update_list(0, 1))
        self.model.sig_stepsize.connect(
            lambda value: self.setLCDstepsize(value))
        # self.model.sig_stepsize.connect(self.spinSetSizeSteps.setValue)

    def update_list(self, Nsteps, SizeSteps):
        if not (self.putin_start and self.putin_end):
            return
        # if not (self.putin_Size or self.putin_N):
        #     return
        if Nsteps:
            # self.__scanconf['Nsteps'] = Nsteps
            with self.dictlock:
                self.__scanconf['SizeSteps'] = None

        if SizeSteps:
            with self.dictlock:
                self.__scanconf['Nsteps'] = None
            # self.__scanconf['SizeSteps'] = None
        # print(self.__scanconf)
        self.sig_updateScanListModel.emit(deepcopy(self.__scanconf))

    def setTstart(self, Tstart):
        with self.dictlock:
            self.__scanconf['start'] = Tstart
        self.putin_start = True
        self.conf.update(self.__scanconf)

    def setTend(self, Tend):
        with self.dictlock:
            self.__scanconf['end'] = Tend
        self.putin_end = True
        self.conf.update(self.__scanconf)

    def setN(self, N):
        with self.dictlock:
            self.__scanconf['Nsteps'] = N
        # self.putin_N = True
        self.conf.update(self.__scanconf)

    def setSizeSteps(self, stepsize):
        with self.dictlock:
            self.__scanconf['SizeSteps'] = stepsize
        # self.putin_Size = True
        self.conf.update(self.__scanconf)

    def setLCDstepsize(self, value):
        self._LCD_stepsize = value
        self.__scanconf['SizeSteps'] = value

    def setLCDNsteps(self, value):
        self._LCD_Nsteps = value
        self.__scanconf['Nsteps'] = value

    def printing(self, message):
        print(message)

    def setRampCondition(self, value):
        with self.dictlock:
            self.conf['RampCondition'] = value
            # 0 == Stabilize
            # 1 == Sweep
            # CHECK THIS

            # if value == 0:
            #     self.conf['RampCondition'] = 'Stabilize'
            # elif value == 1:
            #     self.conf['RampCondition'] = 'Sweep'

    def setSweepRate(self, value):
        with self.dictlock:
            self.conf['SweepRate'] = value

    def update_lcds(self):
        try:
            self.lcdStepsize.display(self._LCD_stepsize)
            self.lcdNsteps.display(self._LCD_Nsteps)
            # self.listTemperatures.repaint()
        finally:
            QTimer.singleShot(0, self.update_lcds)

    def acc(self):
        """if not rejected, emit signal with configuration and accept"""

        self.conf['sequence_temperature'] = self.model.pass_data()

        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()


class Sequence_builder(Window_ui):
    """docstring for sequence_builder"""

    sig_runSequence = pyqtSignal(list)
    sig_abortSequence = pyqtSignal()

    def __init__(self, sequence_file=None, parent=None, **kwargs):
        super(Sequence_builder, self).__init__(
            ui_file='.\\configurations\\sequence.ui', **kwargs)

        # self.listSequence.sig_dropped.connect(lambda value: self.dropreact(value))
        self.sequence_file = sequence_file

        QTimer.singleShot(0, self.initialize_all_windows)
        QTimer.singleShot(
            0, lambda: self.initialize_sequence(self.sequence_file))

        self.model = SequenceListModel()
        self.listSequence.setModel(self.model)

        self.treeOptions.itemDoubleClicked[
            'QTreeWidgetItem*', 'int'].connect(lambda value: self.addItem_toSequence(value))
        self.pushSaving.clicked.connect(lambda: self.model.pass_data())
        self.pushBrowse.clicked.connect(self.window_FileDialogSave)
        self.pushOpen.clicked.connect(self.window_FileDialogOpen)
        self.lineFileLocation.setText(self.sequence_file)
        self.lineFileLocation.textChanged.connect(
            lambda value: self.change_file_location(value))
        self.pushClear.clicked.connect(lambda: self.model.clear_all())

        self.Button_RunSequence.clicked.connect(self.running_sequence)
        self.Button_AbortSequence.clicked.connect(
            lambda: self.sig_abortSequence.emit())
        # self.model.sig_send.connect(lambda value: self.printing(value))
        self.model.sig_send.connect(self.saving)
        # self.treeOptions.itemDoubleClicked['QTreeWidgetItem*', 'int'].connect(lambda value: self.listSequence.repaint())
        self.show()

    def running_sequence(self):
        self.data = self.model.pass_data()
        self.sig_runSequence.emit(deepcopy(self.data))

    def addItem_toSequence(self, text):
        """
            depending on the Item clicked, add the correct Item to the model,
            which may involve executing a certain window
        """
        if text.text(0) == 'Wait':
            # self.window_waiting.show()
            self.window_waiting.exec_()  # if self.window_waiting.exec_():
            # print('success')

        if text.text(0) == 'Resistivity vs Temperature':
            # here the Tscan comes
            self.window_Tscan.exec_()

        if text.text(0) == 'Chain Sequence':
            new_file_seq, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Sequence',
                                                                     'c:\\', "Sequence files (*.seq)")
            data = dict(typ='chain sequence', new_file_seq=new_file_seq,
                            DisplayText='Chain sequence: {}'.format(new_file_seq))
            self.model.addItem(data)
            QTimer.singleShot(1, lambda: self.listSequence.repaint())

        if text.text(0) == 'Change Data File':
            raise NotImplementedError
        if text.text(0) == 'Set Temperature':
            raise NotImplementedError
        if text.text(0) == 'Set Field':
            raise NotImplementedError
        if text.text(0) == 'Resistivity vs Field':
            raise NotImplementedError
        if text.text(0) == 'Shutdown Temperature Control':
            raise NotImplementedError

    def addWaiting(self, data):
        string = self.parse_waiting(data)
        data.update(dict(DisplayText=string))
        # self.listSequence.addItem(string)
        self.model.addItem(data)
        QTimer.singleShot(1, lambda: self.listSequence.repaint())
        # QTimer.singleShot(10, self.model.)

    def addTscan(self, data):
        string = self.parse_Tscan(data)
        data.update(dict(DisplayText=string))
        self.model.addItem(data)
        QTimer.singleShot(1, lambda: self.listSequence.repaint())

    def addChangeDataFile(self, data):
        pass

    def printing(self, data):
        print(data)

    def saving(self, data):
        with open(self.sequence_file, 'w') as f:
            for entry in data:
                print(entry)
                if entry['typ'] == 'scan_T':
                    f.write('LPT SCANT {start} {end} {SweepRate} {Nsteps} {SpacingCode} {ApproachMode}\n'.format(
                        **entry))  # TODO: make sure Rampcondition is actually where it is!
                    for command in entry['commands']:
                        f.write(
                            '{measuretype} 00 00 00 11 11 00\n'.format(**command))
                    f.write('ENT EOS\n')
                if entry['typ'] == 'Wait':
                    Temp = 1 if entry['Temp'] else 0
                    Field = 1 if entry['Field'] else 0
                    f.write('WAI WAITFOR {Delay} {Temp} {Field}\n'.format(
                        Delay=entry['Delay'], Temp=Temp, Field=Field))

    def initialize_all_windows(self):
        self.initialise_window_waiting()
        self.initialise_window_Tscan()
        self.initialise_window_ChangeDataFile()

    def initialise_window_waiting(self):
        self.window_waiting = Window_waiting()
        self.window_waiting.sig_accept.connect(
            lambda value: self.addWaiting(value))

    def initialise_window_Tscan(self):
        self.window_Tscan = Window_Tscan()
        self.window_Tscan.sig_accept.connect(
            lambda value: self.addTscan(value))

    def initialise_window_ChangeDataFile(self):
        self.Window_ChangeDataFile = Window_ChangeDataFile()
        self.Window_ChangeDataFile.sig_accept.connect(
            lambda value: self.addChangeDataFile(value))

    def window_FileDialogSave(self):
        self.sequence_file, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As',
                                                                       'c:\\', "Sequence files (*.seq)")
        self.lineFileLocation.setText(self.sequence_file)

    def window_FileDialogOpen(self):
        self.sequence_file, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Save As',
                                                                       'c:\\', "Sequence files (*.seq)")
        self.lineFileLocation.setText(self.sequence_file)
        self.initialize_sequence(self.sequence_file)

    def change_file_location(self, fname):
        self.sequence_file = fname

    # def update_filelocation(self):
    #     try:
    #         self.lineFileLocation.setText(self.sequence_file)
    #     finally:
        # QTimer.singleShot(0, update_filelocation)

    def initialize_sequence(self, sequence_file):
        """parse a complete file of instructions"""
        if sequence_file:
            self.change_file_location(sequence_file)

            def construct_pattern(expressions):
                pat = ''
                for e in expressions:
                    pat = pat + r'|' + e
                return pat[1:]
                # set temp,            set field,       scan Something,  Wait
                # for something, chain sequence, change data file
            # exp = [r'TMP TEMP(.*?)$', r'FLD FIELD(.*?)$', r'SCAN(.*?)EOS$',
            #        r'WAITFOR(.*?)$', r'CHN(.*?)$', r'CDF(.*?)$']
            exp = [r'TMP TEMP(.*?)$', r'FLD FIELD(.*?)$', r'SCAN(.*?)$',
                   r'WAITFOR(.*?)$', r'CHN(.*?)$', r'CDF(.*?)$', r'DFC(.*?)$',
                   r'LPI(.*?)$', r'SHT(.*?)DOWN', r'EN(.*?)EOS$', r'RES(.*?)$']
            self.p = re.compile(construct_pattern(
                exp), re.DOTALL | re.M)  # '(.*?)[^\S]* EOS'

            sequence, textsequence = self.read_sequence(sequence_file)
            for command in textsequence:
                # print(command)
                self.model.addItem(command)
            print(
                'done -----------------------------------------------------------------')
        else:
            self.sequence_file = ['']

    def read_sequence(self, file):
        """read the whole sequence from a file"""
        with open(file, 'r') as myfile:
            data = myfile.readlines()  # .replace('\n', '')
        # print(data)
        self.jumping_count = [0, 0]
        self.nesting_level = 0
        commands, textsequence = self.parse_nesting(data, -1)
        print(commands)
        return commands, textsequence

    def parse_nesting(self, lines_file, lines_index):

        commands = []
        if lines_index == -1:
            textsequence = []
        else:
            textsequence = None
        # print(lines_file[lines_index+1:])
        for ct, line_further in enumerate(lines_file[lines_index + 1:]):
            # print(lines_index, ct, leave)
            if self.jumping_count[self.nesting_level + 1] > 0:
                self.jumping_count[self.nesting_level + 1] -= 1
                # print('just reduced the jumpting count', self.jumping_count)
                # print(self.jumping_count, self.nesting_level, self.jumping_count[self.nesting_level + 1] )
                continue
            for count, jump in enumerate(self.jumping_count[:-1]):
                self.jumping_count[count] += 1
            # print(self.jumping_count)
            try:

                dic_loop = self.parse_line(
                    lines_file, line_further, lines_index + 1 + ct)
            except EOSException:
                self.nesting_level -= 1
                dic_loop = dict(
                    typ="EOS", DisplayText=textnesting * (self.nesting_level) + 'EOS')
                commands.append(dic_loop)
                break
            commands.append(dic_loop)
            if lines_index == -1:
                textsequence.append(dic_loop)
                self.add_text(textsequence, dic_loop)
        del self.jumping_count[-1]
        print("done with this nesting level: ", self.nesting_level)
        return commands, textsequence

    # def parsing_list_of_lines(self, lines):
    #     """parse a list of lines in a sequence file"""
    #     commands = []
    #     textsequence = []

    #     return commands, textsequence

    def add_text(self, text_list, dic):
        # pass
        if 'commands' in dic:
            for c in dic['commands']:

                try:
                    text_list.append(dict(DisplayText=c['DisplayText']))
                except KeyError:
                    print(c)
                self.add_text(text_list, c)

    def parse_line(self, lines_file, line, line_index):
        """parse one line of a sequence file, possibly more if it is a scan"""
        line_found = self.p.findall(line)[0]
        print('parsing a line: ', line_found)
        dic = dict(typ=None)
        if line_found[0]:
            # set temperature
            print('I found set_temp')
            dic = parse_set_temp(line, self.nesting_level)
        elif line_found[1]:
            # set field
            print('I found set_field')
            dic = parse_set_field(line, self.nesting_level)
        elif line_found[2]:
            # scan something
            print('I found a scan ')
            # self.jumping_count[self.nesting_level] += 1
            self.jumping_count.append(0)
            dic = self.parse_scan_arb(lines_file, line, line_index)
            # much stuff to do!
        elif line_found[3]:
            # waitfor
            print('I found waiting')
            dic = parse_waiting(line, self.nesting_level)
        elif line_found[4]:
            # chain sequence
            print('I found chain_sequence')
            dic = parse_chain_sequence(line, self.nesting_level)
        elif line_found[5]:
            # resistivity change datafile
            print('I found res_change_datafile')
            dic = parse_res_change_datafile(line, self.nesting_level)
        elif line_found[6]:
            # resistivity datafile comment
            print('I found res_datafilecomment')
            dic = parse_res_datafilecomment(line, self.nesting_level)
        elif line_found[7]:
            # resistivity scan excitation
            print('I found res_scan_excitation')
            dic = parse_res_scan_excitation(line, self.nesting_level)
        elif line_found[8]:
            dic = dict(typ='Shutdown')
        elif line_found[9]:
            # end of a scan
            # break or raise exception
            # dic = dict(typ='EOS', DisplayText='EOS')
            print('I found EOS')
            raise EOSException()
        elif line_found[10]:
            # resistivity - measure
            print('I found res meausrement')
            dic = parse_res(line, self.nesting_level)
        return dic

    def parse_scan_arb(self, lines_file, line, lines_index):
        """parse a line in which a scan was defined"""
        # parse this scan instructions
        line_found = self.p.findall(line)[0]
        # print('parsing a scan: ', line_found)
        dic = dict(typ=None)
        if line_found[2][0] == 'H':
            # Field
            pass
            dic = dict(typ='scan_H', DisplayText=textnesting*self.nesting_level+'Scan Field....')

        if line_found[2][0] == 'T':
            # temperature
            dic = parse_scan_T(line, self.nesting_level)

        if line_found[2][0] == 'P':
            # position
            pass
        if line_found[2][0] == 'C':
            # time
            pass
        self.nesting_level += 1

        commands, nothing = self.parse_nesting(lines_file, lines_index)

        dic.update(dict(commands=commands))
        return dic



    # def read_sequence_old(self, file):
    #     with open(file, 'r') as myfile:
    #         data = myfile.read()  # .replace('\n', '')

    #     exp_datafile = re.compile(r'''["'](.*?)["']''')

    #     sequence_raw = self.p.findall(data)
    #     print(sequence_raw)
    #     commands = []
    #     for part in sequence_raw:
    #         # dic = dict()
    #         # print(part)
    #         if part[0]:
    #             # set temperature
    #             dic = parse_set_temp(part[0])

    #         elif part[1]:
    #             # set field
    #             dic = parse_set_field(part[1])

    #         elif part[2]:
    #             # scan temperature
    #             comm = part[2]
    #             if comm[0] == 'T':
    #                 templine = comm.splitlines()[0]
    #                 temps = [float(x)
    #                          for x in searchf_number.findall(templine)]
    #                 # temps are floats!
    #                 if len(temps) < 6:
    #                     raise AssertionError(
    #                         'not enough specifying numbers for T-scan!')
    #                 dic = dict(typ='scan_T', start=temps[0],
    #                            end=temps[1],
    #                            SweepRate=temps[2],
    #                            Nsteps=temps[3],
    #                            SpacingCode=temps[4],
    #                            ApproachMode=temps[5])
    #                 dic['DisplayText'] = parse_Tscan(dic)
    #             dic['commands'] = []
    #             for commandline in comm.splitlines()[1:]:
    #                 if commandline[:3] == 'RES':
    #                     nums = [float(x)
    #                             for x in searchf_number.findall(commandline)]
    #                     dic['commands'].append(dict(measuretype='RES',
    #                                                 RES_arbnum1=nums[0],
    #                                                 RES_arbnum2=nums[1]))
    #         elif part[3]:
    #             # waiting
    #             comm = part[3]
    #             nums = [float(x) for x in searchf_number.findall(comm)]
    #             seconds = nums[0]
    #             Field = True if int(nums[2]) == 1 else False
    #             Temp = True if int(nums[1]) == 1 else False

    #             dic = dict(typ='Wait', Temp=Temp, Field=Field, Delay=seconds)
    #             dic['DisplayText'] = parse_waiting(dic)
    #             # dic.update(local_dic.update(dict(DisplayText=self.parse_waiting(local_dic))))
    #         elif part[4]:
    #             # chain sequence
    #             comm = part[4]
    #             dic = dict(typ='chain sequence', new_file_seq=comm,
    #                        DisplayText='Chain sequence: {}'.format(comm))
    #             print('CHN', comm)
    #         elif part[5]:
    #             # change data file
    #             comm = part[5]
    #             file = exp_datafile.findall(comm)[0]
    #             dic = dict(typ='change datafile', new_file_data=file,
    #                        mode='a' if comm[-1] == '1' else 'w',
    #                        # a - appending, w - writing, can be inserted
    #                        # directly into opening statement
    #                        DisplayText='Change data file: {}'.format(file))
    #             print('CDF', comm)
    #         elif part[6]:
    #             pass

    #         commands.append(dic)
    #     # for x in commands:
    #     #     print(x)
    #     return commands


if __name__ == '__main__':

    file = 'Hg1201_UD88_17Aug2018_dn.seq'
    file = 'SEQ_20180914_Tscans.seq'
    file = 'Tempscan.seq'
    file = None
    # file = 't.seq'

    app = QtWidgets.QApplication(sys.argv)
    form = Sequence_builder(file)
    form.show()
    sys.exit(app.exec_())
l
