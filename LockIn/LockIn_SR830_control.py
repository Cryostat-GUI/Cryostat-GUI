
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
        self.__name__ = 'SR830_Updater ' + InstrumentAddress

        # self.interval = 0.05
        self.ShuntResistance_Ohm = 0
        self.ContactResistance_Ohm = 0

    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the Lock-In, and emit signal, sending the data


        """

        data = dict()
        data['Frequency_Hz'] = self.lockin.frequency

        data['Voltage_V'] = self.lockin.sine_voltage
        data['X_V'] = self.lockin.x
        data['Y_V'] = self.lockin.y
        data['R_V'] = self.lockin.magnitude
        data['Theta_Deg'] = self.lockin.theta

        # in mili ampers, 50 ohm is the internal resistance of the lockin
        SampleCurrent_A = data['Voltage_V'] / \
            (self.ShuntResistance_Ohm + self.ContactResistance_Ohm + 50)
        data['SampleCurrent_mA'] = SampleCurrent_A * 1e3

        data['SampleResistance_Ohm'] = data['X_V'] / SampleCurrent_A

        self.sig_Infodata.emit(deepcopy(data))

    @pyqtSlot()
    @ExceptionHandling
    def setFrequency(self):
        self.lockin.frequency = self.set_Frequency_Hz

    @pyqtSlot()
    @ExceptionHandling
    def setVoltage(self):
        self.lockin.sine_voltage = self.set_Voltage_V

    @pyqtSlot()
    def gettoset_Frequency(self, value):
        self.set_Frequency_Hz = value

    @pyqtSlot()
    def gettoset_Voltage(self, value):
        self.set_Voltage_V = value

    @pyqtSlot()
    def getShuntResistance(self, value):
        self.ShuntResistance_Ohm = value

    @pyqtSlot()
    def getContactResistance(self, value):
        self.ContactResistance_Ohm = value
