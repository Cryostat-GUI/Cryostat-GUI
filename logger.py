

from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

import sys
import time
import datetime

from util import AbstractEventhandlingThread

class main_Logger(AbstractEventhandlingThread):

    """This is a worker thread
    """

    sig_dict = pyqtSignal(dict)
    sig_str = pyqtSignal(str)
    sig_log = pyqtSignal()


    def __init__(self, mainthread):
        super().__init__()
        # QThread.__init__(self)

        self.interval = 2 # 60s interval for logging as initialisation

        self.mainthread.sig_logging.connect(self.store_data)

    def running(self):
        try:
            # Do things
            self.sig_log.emit('log')
        finally:
            QTimer.singleShot(self.interval*1e3, self.running)


    # def printing(self,b):
    #     """arbitrary exmple function"""
    #     print('a', b)
    #     time.sleep(2)
    #     print('b', b)

    @pyqtSlot()
    def stop(self):
        self.__isRunning = False

    @pyqtSlot(int)
    def set_Interval(self, interval):
        """set the interval between logging events in seconds"""
        self.interval = interval

    @pyqtSlot()
    def store_data(self, data):
        pass
        # saving data