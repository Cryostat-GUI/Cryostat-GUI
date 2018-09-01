

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

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

    @pyqtSlot()
    def work(self):
        # app.processEvents()
        while self.__isRunning:
            pass
            print(self.mainthread.data)
            time.sleep(self.interval)
            # log all meaningful arguments of the mainthread

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
        self.interval = interval

    def store_data(self):
        pass