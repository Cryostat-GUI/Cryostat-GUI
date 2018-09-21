from PyQt5 import QtWidgets, QtGui
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

from util import Window_ui

dropstring = re.compile(r'([a-zA-Z0-9])')


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
        if not self.conf['Temp'] and not self.conf['Field']: 
            self.reject()
            return
        self.sig_accept.emit(deepcopy(self.conf))
        self.accept()

    def setValue(self, parameter, value):
        """set any kind of value in the conf dict"""
        self.conf[parameter] = value

    # def accepted(self):
    #     self.sig_accept.emit(self.conf)



from qlistmodel import SequenceListModel

class Sequence_builder(Window_ui):
    """docstring for sequence_builder"""
    def __init__(self, sequence_file=None, parent=None, **kwargs):
        super(Sequence_builder, self).__init__(ui_file='.\\configurations\\sequence.ui', **kwargs)

        # self.listSequence.sig_dropped.connect(lambda value: self.dropreact(value))
        self.data = []
        self.sequence_file = sequence_file

        QTimer.singleShot(0, self.initialize_all_windows)
        QTimer.singleShot(0, lambda: self.initialize_sequence(self.sequence_file))

        self.model = SequenceListModel()
        self.listSequence.setModel(self.model)

        self.treeOptions.itemDoubleClicked['QTreeWidgetItem*', 'int'].connect(lambda value: self.addItem_toSequence(value))
        self.pushSaving.clicked.connect(lambda: self.model.pass_data)
        self.model.sig_send.connect(lambda value: self.printing(value))
        # self.treeOptions.itemDoubleClicked['QTreeWidgetItem*', 'int'].connect(lambda value: self.listSequence.repaint())
        self.show()


    def initialize_sequence(self, sequence_file):
        if sequence_file: 
            def construct_pattern(expressions):
                pat = ''
                for e in exp: 
                    pat = pat + r'|' + e
                return pat[1:]
            exp = [r'TMP TEMP(.*?)$', r'FLD FIELD(.*?)$', r'SCAN(.*?)EOS$', r'WAITFOR(.*?)$']
            self.p = re.compile(construct_pattern(exp), re.DOTALL|re.M) # '(.*?)[^\S]* EOS'
            self.number = re.compile(r'([0-9]+[.]*[0-9]*)') 

            sequence = self.read_sequence(sequence_file)       
            for command in sequence: 
                # print(command)
                self.model.addItem(command)


    def addItem_toSequence(self, text):
        if text.text(0) == 'Wait': 
            # self.window_waiting.show()
            self.window_waiting.exec_()# if self.window_waiting.exec_():
            # print('success')

        if text.text(0) == 'Set Temperature': 
            raise NotImplementedError

        if text.text(0) == 'Set Field': 
            raise NotImplementedError

        if text.text(0) == 'Resistivity vs Temperature': 
            raise NotImplementedError

        if text.text(0) == 'Resistivity vs Field': 
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
    def printing(self, data):
        print(data)

    def initialize_all_windows(self):
        self.initialise_window_waiting()

    def initialise_window_waiting(self):
        self.window_waiting = Window_waiting()
        self.window_waiting.sig_accept.connect(lambda value: self.addWaiting(value))
        # self.window_waiting.sig_accept.connect(lambda value: self.addWaiting(value))


    def read_sequence(self, file): 
        with open('.\\testing\\{}'.format(file), 'r') as myfile:
            data=myfile.read()#.replace('\n', '')

        sequence_raw = self.p.findall(data)
        commands = []
        for part in sequence_raw: 
            # dic = dict()
            # print(part)
            if part[0]: 
                # set temperature
                comm = part[0]
                nums = [float(x) for x in self.number.findall(comm)]
                dic = dict(typ='set_T', Temp=nums[0], rate=nums[1] )

                dic['DisplayText']=self.parse_set_temp(dic)

            elif part[1]: 
                # set field
                comm = part[1]
                nums = [float(x) for x in self.number.findall(comm)]
                dic = dict(typ='set_Field', Field=nums[0], rate=nums[1] )
                dic['DisplayText']=self.parse_set_field(dic)

            elif part[2]: 
                # scan temperature
                comm = part[2]
                if comm[0] == 'T': 
                    templine = comm.splitlines()[0]
                    temps = [float(x) for x in self.number.findall(templine)]
                    dic = dict(typ='scan_T', start=temps[0], 
                                                    stop=temps[1], 
                                                    stepsize=temps[2],
                                                    steps = temps[3])
                measureline = comm.splitlines()[1]
                if measureline[:3] == 'RES': 
                    nums = [float(x) for x in self.number.findall(measureline)]
                dic.update(dict(measuretype='RES', 
                                RES_arbnum1 = nums[0], 
                                RES_arbnum2 = nums[1] ))
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


            commands.append(dic)
        # for x in commands: 
        #     print(x)
        return commands







# class sequence_listwidget(QtWidgets.QListWidget):
#     """docstring for Sequence_ListWidget"""
#     sig_dropped = pyqtSignal()
#     def __init__(self, **kwargs):
#         super(Sequence_ListWidget, self).__init__(**kwargs)

#     def dropEvent(self, event):
#         self.sig_dropped.emit(event)
#         event.accept()


if __name__ == '__main__':


    file = 'Hg1201_UD88_17Aug2018_dn.seq'
    file = 'SEQ_20180914_Tscans.seq'

    app = QtWidgets.QApplication(sys.argv)
    form = Sequence_builder(file)
    form.show()
    sys.exit(app.exec_())
