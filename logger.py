

from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

import sys
import time
import datetime


class main_Logger(QObject):

    """This is a worker thread
    """

    sig_dict = pyqtSignal(dict)
    sig_str = pyqtSignal(str)
    sig_str = pyqtSignal(str)
    sig_ = pyqtSignal()


    def __init__(self, mainthread):
        QThread.__init__(self)
        self.mainthread = mainthread
        self.__isRunning = True

        self.interval = 2 # 60s interval for logging as initialisation

        self.mainthread.sig_saving.connect(self.store_data)

    def f():
        try:
            # Do things
            pass
        finally:
            QTimer.singleShot(self.interval*1e3, f)


    @pyqtSlot()
    def work(self):
        # app.processEvents()
        pass

        # while self.__isRunning:
        #     pass
        #     print(self.mainthread.data)
        #     time.sleep(self.interval)
        #     # log all meaningful arguments of the mainthread

    def printing(self,b):
        """arbitrary exmple function"""
        print('a', b)
        time.sleep(2)
        print('b', b)

    @pyqtSlot()
    def stop(self):
        self.__isRunning = False

    @pyqtSlot(int)
    def set_Interval(self, interval):
        """set the interval between logging events in seconds"""
        self.interval = interval

    def store_data(self):
        pass