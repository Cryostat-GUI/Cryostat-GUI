
from PyQt5.QtCore import pyqtSlot
from copy import deepcopy
# from importlib import reload
# import time

#
# import LockIn

from pymeasure.instruments.srs import SR830

from util import AbstractLoopThread
from util import ExceptionHandling


class SR830_Updater(AbstractLoopThread):
    """Updater class to update all instrument data of the SR830

    """

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        self.lockin = SR830(InstrumentAddress)

        # self.interval = 0.05

    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the Lock-In, and emit signal, sending the data


        """

        data = dict()
        data['Frequency_Hz'] = self.lockin.frequency

        self.sig_Infodata.emit(deepcopy(data))

    @pyqtSlot()
    @ExceptionHandling
    def setFrequency(self):
        self.lockin.frequency = self.set_Frequency

    @pyqtSlot()
    def gettoset_Frequency(self, value):
        self.set_Frequency = value
