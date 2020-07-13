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
from PyQt5 import QtWidgets
# from copy import deepcopy
# import time
import json
import sys
from datetime import datetime
import numpy as np

#
# import LockIn

from pymeasure.instruments.srs import SR830

from util import AbstractLoopClient
from util import Window_trayService_ui
from util import ExceptionHandling
from util import dummy

from zmqcomms import enc, dec


class SR830_ControlClient(AbstractLoopClient, Window_trayService_ui):
    """Updater class to update all instrument data of the SR830

    """
    data = dict()

    def __init__(self, comLock=None, InstrumentAddress='', log=None, **kwargs):
        """init: get the driver connection to the Lock-In, set up default conf"""
        super().__init__(**kwargs)
        # self.logger = log if log else logging.getLogger(__name__)

        self.__name__ = 'SR830_Updater ' + InstrumentAddress
        self._comLock = dummy() if comLock is None else comLock

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        # self.lockin = SR830(InstrumentAddress)
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        # self.interval = 0.05
        self.ShuntResistance_Ohm = 1e3  # default value in the GUI
        self.ContactResistance_Ohm = 0
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots

        self.spinSetFrequency_Hz.valueChanged.connect(
            lambda value: self.gettoset_Frequency(value))
        self.spinSetFrequency_Hz.editingFinished.connect(self.setFrequency)

        self.spinSetVoltage_V.valueChanged.connect(
            lambda value: self.gettoset_Voltage(value))
        self.spinSetVoltage_V.editingFinished.connect(self.setVoltage)

        self.spinShuntResistance_kOhm.valueChanged.connect(
            lambda value: self.getShuntResistance(value * 1e3))
        self.spinContactResistance_Ohm.valueChanged.connect(
            lambda value: self.getContactResistance(value))

        # -------------------------------------------------------------------------------------------------------------------------

    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the Lock-In, and emit signal, sending the data
        """

        with self._comLock:
            self.data['Frequency_Hz'] = self.lockin.frequency

            self.data['Voltage_V'] = self.lockin.sine_voltage
            self.data['X_V'] = self.lockin.x
            self.data['Y_V'] = self.lockin.y
            self.data['R_V'] = self.lockin.magnitude
            self.data['Theta_Deg'] = self.lockin.theta

            self.data['ShuntResistance_user_Ohm'] = self.ShuntResistance_Ohm
            self.data['ContactResistance_user_Ohm'] = self.ContactResistance_Ohm

        # in mili ampers, 50 ohm is the internal resistance of the lockin
        SampleCurrent_A = self.data['Voltage_V'] / \
            (self.ShuntResistance_Ohm + self.ContactResistance_Ohm + 50)
        self.data['SampleCurrent_mA'] = SampleCurrent_A * 1e3

        try:
            self.data['SampleResistance_Ohm'] = self.data[
                'X_V'] / SampleCurrent_A
        except ZeroDivisionError:
            self.data['SampleResistance_Ohm'] = np.NaN

        self.data['realtime'] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.comms_upstream.send_multipart(
            [self.comms_name, enc(json.dumps(self.data))])

        # self.sig_Infodata.emit(deepcopy(data))

    @ExceptionHandling
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        pass
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        if 'setFrequency' in command:
            self.setFrequency(command['setFrequency'])
        if 'setVoltage' in command:
            self.setVoltage(command['setVoltage'])
        # -------------------------------------------------------------------------------------------------------------------------

    @pyqtSlot()
    @ExceptionHandling
    def setFrequency(self, f_Hz=None):
        """set a frequency"""
        if f_Hz:
            self.set_Frequency_Hz = f_Hz
        with self._comLock:
            self.lockin.frequency = self.set_Frequency_Hz

    @pyqtSlot()
    @ExceptionHandling
    def setVoltage(self, Voltage_V=None):
        """set a voltage"""
        if Voltage_V:
            self.set_Voltage_V = Voltage_V
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = SR830_ControlClient(
        ui_file='LockIn_main.ui', Name='Lockin SR830', identity=b'SR830_1', InstrumentAddress='')
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
