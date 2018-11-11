from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QAbstractListModel, QFile, QIODevice, QModelIndex, Qt
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
        self.lineFileLocation.textChanged.connect(lambda value: self.setValue('new_file_data', value))
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
               'c:\\',"Datafiles (*.dat)")
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
        self.check_Temp.toggled.connect(lambda value: self.setValue('Temp', value))
        self.check_Field.toggled.connect(lambda value: self.setValue('Field', value))
        self.spin_delayseconds.valueChanged.connect(lambda value: self.setValue('Delay', value))
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
                                start = 0,
                                end = 0,
                                Nsteps = None,
                                SizeSteps = None)
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
        self.spinSetTstart.editingFinished.connect(lambda: self.update_list(None, None))

        self.spinSetTend.valueChanged.connect(self.setTend)
        self.spinSetTend.editingFinished.connect(lambda: self.update_list(None, None))

        # self.spinSetNsteps.valueChanged.connect(lambda value: self.printing('spinSetNsteps: valueChanged: {}'.format(value)))
        # self.spinSetNsteps.editingFinished.connect(lambda: self.printing('spinSetNsteps: editingFinished'))
        # self.model.sig_Nsteps.connect(lambda value: self.printing('model: sig_Nsteps: {}'.format(value)))

        self.spinSetNsteps.valueChanged.connect(self.setN)
        self.spinSetNsteps.editingFinished.connect(lambda: self.setLCDNsteps(self.__scanconf['Nsteps']))
        self.spinSetNsteps.editingFinished.connect(lambda: self.update_list(1, 0))
        self.model.sig_Nsteps.connect(lambda value: self.setLCDNsteps(value))
        # self.model.sig_Nsteps.connect(self.spinSetNsteps.setValue)


        # self.spinSetSizeSteps.valueChanged.connect(lambda value: self.printing('spinSetSizeSteps: valueChanged: {}'.format(value)))
        # self.model.sig_stepsize.connect(lambda value: self.printing('model: sig_stepsize: {}'.format(value)))
        # self.spinSetSizeSteps.editingFinished.connect(lambda: self.printing('spinSetSizeSteps: editingFinished'))

        self.spinSetSizeSteps.valueChanged.connect(self.setSizeSteps)
        self.spinSetSizeSteps.editingFinished.connect(lambda: self.setLCDstepsize(self.__scanconf['SizeSteps']))
        self.spinSetSizeSteps.editingFinished.connect(lambda: self.update_list(0, 1))
        self.model.sig_stepsize.connect(lambda value: self.setLCDstepsize(value))
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
        super(Sequence_builder, self).__init__(ui_file='.\\configurations\\sequence.ui', **kwargs)

        # self.listSequence.sig_dropped.connect(lambda value: self.dropreact(value))
        self.sequence_file = sequence_file

        QTimer.singleShot(0, self.initialize_all_windows)
        QTimer.singleShot(0, lambda: self.initialize_sequence(self.sequence_file))

        self.model = SequenceListModel()
        self.listSequence.setModel(self.model)

        self.treeOptions.itemDoubleClicked['QTreeWidgetItem*', 'int'].connect(lambda value: self.addItem_toSequence(value))
        self.pushSaving.clicked.connect(lambda: self.model.pass_data())
        self.pushBrowse.clicked.connect(self.window_FileDialogSave)
        self.pushOpen.clicked.connect(self.window_FileDialogOpen)
        self.lineFileLocation.setText(self.sequence_file)
        self.lineFileLocation.textChanged.connect(lambda value: self.change_file_location(value))
        self.pushClear.clicked.connect(lambda: self.model.clear_all())

        self.Button_RunSequence.clicked.connect(self.running_sequence)
        self.Button_AbortSequence.clicked.connect(lambda: self.sig_abortSequence.emit())
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
            self.window_waiting.exec_()# if self.window_waiting.exec_():
            # print('success')

        if text.text(0) == 'Resistivity vs Temperature':
            # here the Tscan comes
            self.window_Tscan.exec_()

        if text.text(0) == 'Chain Sequence':
            new_file_seq, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Sequence',
               'c:\\',"Sequence files (*.seq)")
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

    def parse_waiting(self, data):
        string = 'Wait for '
        separator = ', ' if data['Temp'] and data['Field'] else ''
        sep_taken = False

        if data['Temp']:
            string += 'Temperature' + separator
            sep_taken = True
        if data['Field']:
            string = string + 'Field' if sep_taken else  string + 'Field' + separator
            sep_taken = True
        string += ' & {} seconds more'.format(data['Delay'])
        return string

    def parse_Tscan(self, data):
        return 'Scan Temperature from {start} to {end} in {Nsteps} steps, {SweepRate}K/min'.format(**data)

    def parse_set_temp(self, data):
        return 'Set Temperature to {Temp} at {rate}K/min (rate is only a wish...)'.format(**data)

    def parse_set_field(self, data):
        return 'Set Field to {Field} at {rate}T/min (rate is only a wish...)'.format(**data)

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
                    f.write('LPT SCANT {start} {end} {SweepRate} {Nsteps} {RampCondition} 0\n'.format(**entry))# TODO: make sure Rampcondition is actually where it is!
                    f.write('{measuretype} 00 00 00 11 11 00\n'.format(**entry))
                    f.write('ENT EOS\n')
                if entry['typ'] == 'Wait':
                    Temp = 1 if entry['Temp'] else 0
                    Field = 1 if entry['Field'] else 0
                    f.write('WAI WAITFOR {Delay} {Temp} {Field}\n'.format(Delay=entry['Delay'], Temp=Temp, Field=Field ))

    def initialize_all_windows(self):
        self.initialise_window_waiting()
        self.initialise_window_Tscan()
        self.initialise_window_ChangeDataFile()

    def initialise_window_waiting(self):
        self.window_waiting = Window_waiting()
        self.window_waiting.sig_accept.connect(lambda value: self.addWaiting(value))

    def initialise_window_Tscan(self):
        self.window_Tscan = Window_Tscan()
        self.window_Tscan.sig_accept.connect(lambda value: self.addTscan(value))

    def initialise_window_ChangeDataFile(self):
        self.Window_ChangeDataFile = Window_ChangeDataFile()
        self.Window_ChangeDataFile.sig_accept.connect(lambda value: self.addChangeDataFile(value))

    def window_FileDialogSave(self):
        self.sequence_file, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save As',
           'c:\\',"Sequence files (*.seq)")
        self.lineFileLocation.setText(self.sequence_file)

    def window_FileDialogOpen(self):
        self.sequence_file, __ = QtWidgets.QFileDialog.getOpenFileName(self, 'Save As',
           'c:\\',"Sequence files (*.seq)")
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
        if sequence_file:
            self.change_file_location(sequence_file)
            def construct_pattern(expressions):
                pat = ''
                for e in exp:
                    pat = pat + r'|' + e
                return pat[1:]
                # set temp,            set field,       scan Something,  Wait for something, chain sequence, change data file
            exp = [r'TMP TEMP(.*?)$', r'FLD FIELD(.*?)$', r'SCAN(.*?)EOS$', r'WAITFOR(.*?)$', r'CHN(.*?)$', r'CDF(.*?)$']
            self.p = re.compile(construct_pattern(exp), re.DOTALL|re.M) # '(.*?)[^\S]* EOS'
            self.number = re.compile(r'([0-9]+[.]*[0-9]*)')

            sequence = self.read_sequence(sequence_file)
            for command in sequence:
                # print(command)
                self.model.addItem(command)
        else:
            self.sequence_file = ['']

    def read_sequence(self, file):
        with open(file, 'r') as myfile:
            data=myfile.read()#.replace('\n', '')

        exp_datafile = re.compile(r'''["'](.*?)["']''')

        sequence_raw = self.p.findall(data)
        commands = []
        for part in sequence_raw:
            # dic = dict()
            # print(part)
            if part[0]:
                # set temperature
                comm = part[0]
                nums = [float(x) for x in self.number.findall(comm)]
                dic = dict(typ='set_T', Temp=nums[0], SweepRate=nums[1] )

                dic['DisplayText']=self.parse_set_temp(dic)

            elif part[1]:
                # set field
                comm = part[1]
                nums = [float(x) for x in self.number.findall(comm)]
                dic = dict(typ='set_Field', Field=nums[0], SweepRate=nums[1] )
                dic['DisplayText']=self.parse_set_field(dic)

            elif part[2]:
                # scan temperature
                comm = part[2]
                if comm[0] == 'T':
                    templine = comm.splitlines()[0]
                    temps = [float(x) for x in self.number.findall(templine)]
                    dic = dict(typ='scan_T', start=temps[0],
                                                    end=temps[1],
                                                    SweepRate=temps[2],
                                                    Nsteps = temps[3],
                                                    RampCondition=temps[4])
                measureline = comm.splitlines()[1]
                if measureline[:3] == 'RES':
                    nums = [float(x) for x in self.number.findall(measureline)]
                dic.update(dict(measuretype='RES',
                                RES_arbnum1 = nums[0],
                                RES_arbnum2 = nums[1],
                                DisplayText = self.parse_Tscan(dic)))
            elif part[3]:
                # waiting
                comm = part[3]
                nums = [float(x) for x in self.number.findall(comm)]
                seconds = nums[0]
                Field = True if int(nums[2]) == 1 else False
                Temp = True if int(nums[1]) == 1 else False

                dic = dict(typ='Wait', Temp=Temp, Field=Field, Delay=seconds)
                dic['DisplayText']=self.parse_waiting(dic)
                # dic.update(local_dic.update(dict(DisplayText=self.parse_waiting(local_dic))))
            elif part[4]:
                # chain sequence
                comm = part[4]
                dic = dict(typ='chain sequence', new_file_seq=comm,
                            DisplayText='Chain sequence: {}'.format(comm))
                print('CHN', comm)
            elif part[5]:
                # change data file
                comm = part[5]
                file = exp_datafile.findall(comm)[0]
                dic = dict(typ='change datafile', new_file_data=file,
                            mode='a' if comm[-1]=='1' else 'w',
                            # a - appending, w - writing, can be inserted directly into opening statement
                            DisplayText='Change data file: {}'.format(file))
                print('CDF', comm)

            commands.append(dic)
        # for x in commands:
        #     print(x)
        return commands


if __name__ == '__main__':


    file = 'Hg1201_UD88_17Aug2018_dn.seq'
    file = 'SEQ_20180914_Tscans.seq'
    file = None
    # file = 't.seq'

    app = QtWidgets.QApplication(sys.argv)
    form = Sequence_builder(file)
    form.show()
    sys.exit(app.exec_())
