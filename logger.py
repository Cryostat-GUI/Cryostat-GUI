

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

import sys
import datetime

from util import AbstractEventhandlingThread
from util import Window_ui


class Logger_configuration(Window_ui):
    """docstring for Logger_configuration"""

    sig_send_conf = pyqtSignal(dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.conf = dict()
        self.conf['ITC'] = dict()
        self.conf['ILM'] = dict()
        self.conf['PS'] = dict()
        self.conf['Lakeshore350'] = dict()

        self.general_threads_ITC.toggled.connect(lambda value: self.setValue('ITC', 'thread', value))
        self.general_threads_ITC.toggled.connect(lambda: self.ITC_thread_running.setChecked)
        # self.general_threads_ILM.toggled.connect(lambda value: self.conf['ILM']['thread'] = value)
        self.general_threads_ILM.toggled.connect(lambda: self.ILM_thread_running.setChecked)
        # self.general_threads_PS.toggled.connect(lambda value: self.conf['PS']['thread'] = value)
        self.general_threads_PS.toggled.connect(lambda: self.PS_thread_running.setChecked)
        # self.general_threads_Lakeshore350.toggled.connect(lambda value: self.conf['Lakeshore350']['thread'] = value)
        self.general_threads_Lakeshore350.toggled.connect(lambda: self.Lakeshore350_thread_running.setChecked)
        # self.general_threads_Current1.toggled.connect(lambda value: self.conf['Current1']['thread'] = value)
        # self.general_threads_Current1.toggled.connect(lambda: self.Current1_thread_running.setChecked)
        # self.general_threads_Current2.toggled.connect(lambda value: self.conf['Current2']['thread'] = value)
        # self.general_threads_Current2.toggled.connect(lambda: self.Current2_thread_running.setChecked)
        # self.general_threads_Nano1.toggled.connect(lambda value: self.conf['Nano1']['thread'] = value)
        # self.general_threads_Nano1.toggled.connect(lambda: self.Nano1_thread_running.setChecked)
        # self.general_threads_Nano2.toggled.connect(lambda value: self.conf['Nano2']['thread'] = value)
        # self.general_threads_Nano2.toggled.connect(lambda: self.Nano2_thread_running.setChecked)
        # self.general_threads_Nano3.toggled.connect(lambda value: self.conf['Nano3']['thread'] = value)
        # self.general_threads_Nano3.toggled.connect(lambda: self.Nano3_thread_running.setChecked)
        

        self.buttonBox_finish.accepted.connect(lambda: self.sig_send_conf.emit(self.conf))
        self.buttonBox_finish.accepted.connect(self.close)
        self.buttonBox_finish.rejected.connect(self.close)


    def setValue(self, instrument, value, bools):
        self.conf[instrument][value] = bools



class main_Logger(AbstractEventhandlingThread):

    """This is a worker thread
    """

    sig_dict = pyqtSignal(dict)
    sig_str = pyqtSignal(str)
    sig_log = pyqtSignal()


    def __init__(self, mainthread):
        super().__init__()
        self.mainthread = mainthread

        self.interval = 2 # 60s interval for logging as initialisation

        self.mainthread.sig_logging.connect(self.store_data)
        self.mainthread.sig_logging_newconf.connect(self.update_conf)

        conf = self.logging_read_configuration()


    def running(self):
        try:
            # Do things
            self.sig_log.emit()
            print('emitted signal')
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])            
        finally:
            QTimer.singleShot(self.interval*1e3, self.running)

    # @pyqtSlot()
    # def stop(self):
    #     self.__isRunning = False

    def update_conf(self):
        print('updated conf for logging')

    @pyqtSlot(int)
    def set_Interval(self, interval):
        """set the interval between logging events in seconds"""
        self.interval = interval

    @pyqtSlot(dict)
    def store_data(self, data):
        """storing logging data
            into database or logfile - to be decided!

        """
        print(data)
        
        # saving data

    def logging_read_configuration(self):
        """method to read the last configuration of 
            what shall be logged from a respective file

            Return: dictionary holding bools
        """
        pass        