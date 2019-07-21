"""Module containing a class to run a (Standford Research) SR 830 Lock-In Amplifier in a pyqt5 application

Classes:
    SR830_Updater: a class for interfacing with a SR 830 Lock-In Amplifier
            inherits from AbstractLoopThread
                there, the looping behaviour of this thread is defined
            uses the pymeasure SR830 command set
Author(s):
    bklebel (Benjamin Klebel)
    Wojtek
"""
from PyQt5.QtCore import pyqtSlot
from copy import deepcopy
# from importlib import reload
# import time

#
# import LockIn

from pymeasure.instruments.srs import SR830

from util import AbstractLoopThread
from util import ExceptionHandling

from datetime import datetime
import logging


class SR830_Updater(AbstractLoopThread):
    """Updater class to update all instrument data of the SR830

    """

    def __init__(self, comLock, InstrumentAddress='', log=None, **kwargs):
        """init: get the driver connection to the Lock-In, set up default conf"""
        super().__init__(**kwargs)
        self.logger = log if log else logging.getLogger(__name__)

        self.lockin = SR830(InstrumentAddress)
        self.__name__ = 'SR830_Updater ' + InstrumentAddress
        self._comLock = comLock

        # self.interval = 0.05
        self.ShuntResistance_Ohm = 0
        self.ContactResistance_Ohm = 0

    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the Lock-In, and emit signal, sending the data
        """

        data = dict()
        with self._comLock:
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

        data['realtime'] = datetime.now()

        self.sig_Infodata.emit(deepcopy(data))

    @pyqtSlot()
    @ExceptionHandling
    def setFrequency(self):
        """set a frequency"""
        with self._comLock:
            self.lockin.frequency = self.set_Frequency_Hz

    @pyqtSlot()
    @ExceptionHandling
    def setVoltage(self):
        """set a voltage"""
        with self._comLock:
            self.lockin.sine_voltage = self.set_Voltage_V

    @pyqtSlot()
    def gettoset_Frequency(self, value):
        """receive and store the value to set the frequency"""
        self.set_Frequency_Hz = value

    @pyqtSlot()
    def gettoset_Voltage(self, value):
        """receive and store the value to set the voltage"""
        self.set_Voltage_V = value

    @pyqtSlot()
    def getShuntResistance(self, value):
        """receive and store the value of the shunt resistance"""
        self.ShuntResistance_Ohm = value

    @pyqtSlot()
    def getContactResistance(self, value):
        """receive and store the value of the samples' contact resistance"""
        self.ContactResistance_Ohm = value
