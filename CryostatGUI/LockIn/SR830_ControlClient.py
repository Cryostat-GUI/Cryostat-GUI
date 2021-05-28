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
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# to be removed once this is packaged!

from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer

from copy import deepcopy
from datetime import datetime
import numpy as np
from pyvisa.errors import VisaIOError
import logging

import time

# import LockIn

from pymeasure.instruments.srs import SR830
from drivers import ApplicationExit

from util import AbstractLoopThreadClient
from util import Window_trayService_ui
from util import ExceptionHandling
from util import dummy
from util import AbstractMainApp


# from PyQt5.QtCore import QTimer
# import sys

from pid import PidFile
from pid import PidFileError

# from zmqcomms import enc, dec


class SR830_ControlClient(AbstractLoopThreadClient):
    """Updater class to update all instrument data of the SR830"""

    data = {}

    def __init__(
        self, mainthread=None, comLock=None, InstrumentAddress="", Lockin=None, **kwargs
    ):
        """init: get the driver connection to the Lock-In, set up default conf"""
        super().__init__(**kwargs)

        self.__name__ = "SR830_Updater " + InstrumentAddress
        self._comLock = dummy() if comLock is None else comLock
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        self.lockin = Lockin(InstrumentAddress, read_termination="\n")
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        # self.interval = 0.05
        self.ShuntResistance_Ohm = 1e3  # default value in the GUI
        self.ContactResistance_Ohm = 0
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots
        if mainthread is not None:
            mainthread.spinSetFrequency_Hz.valueChanged.connect(
                lambda value: self.gettoset_Frequency(value)
            )
            mainthread.spinSetFrequency_Hz.editingFinished.connect(self.setFrequency)

            mainthread.spinSetVoltage_V.valueChanged.connect(
                lambda value: self.gettoset_Voltage(value)
            )
            mainthread.spinSetVoltage_V.editingFinished.connect(self.setVoltage)

            mainthread.spinShuntResistance_kOhm.valueChanged.connect(
                lambda value: self.getShuntResistance(value * 1e3)
            )
            mainthread.spinContactResistance_Ohm.valueChanged.connect(
                lambda value: self.getContactResistance(value)
            )

        # -------------------------------------------------------------------------------------------------------------------------

    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the Lock-In, and emit signal, sending the data"""
        self.run_finished = False
        # -------------------------------------------------------------------------------------------------------------------------
        with self._comLock:
            self.data["Frequency_Hz"] = self.lockin.frequency

            self.data["Voltage_V"] = self.lockin.sine_voltage
            self.data["X_V"] = self.lockin.x
            self.data["Y_V"] = self.lockin.y
            self.data["R_V"] = self.lockin.magnitude
            self.data["Theta_Deg"] = self.lockin.theta

            self.data["ShuntResistance_user_Ohm"] = self.ShuntResistance_Ohm
            self.data["ContactResistance_user_Ohm"] = self.ContactResistance_Ohm

        # in mili ampers, 50 ohm is the internal resistance of the lockin
        SampleCurrent_A = self.data["Voltage_V"] / (
            self.ShuntResistance_Ohm + self.ContactResistance_Ohm + 50
        )
        self.data["SampleCurrent_mA"] = SampleCurrent_A * 1e3

        try:
            self.data["SampleResistance_Ohm"] = self.data["X_V"] / SampleCurrent_A
        except ZeroDivisionError:
            self.data["SampleResistance_Ohm"] = np.NaN

        self.data["realtime"] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.sig_Infodata.emit(deepcopy(self.data))
        self.run_finished = True
        # self.comms_upstream.send_multipart(
        #     [self.comms_name, enc(json.dumps(self.data))])

        # self.sig_Infodata.emit(deepcopy(data))

    @ExceptionHandling
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        if "setFrequency" in command:
            self.setFrequency(command["setFrequency"])
        if "setVoltage" in command:
            self.setVoltage(command["setVoltage"])
        if "setShuntResistance" in command:
            self.getShuntResistance(command["setShuntResistance"])
        if "setContactResistance" in command:
            self.getContactResistance(command["setContactResistance"])
        # -------------------------------------------------------------------------------------------------------------------------

    @ExceptionHandling
    def query_on_command(self, command):
        """execute commands sent via tcp"""
        answer_dict = {}
        answer_dict["OK"] = True
        answer_dict["Errors"] = []
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq tcp, and executed here
        # examples:
        if "measure_Resistance" in command:
            with self._comLock:
                Voltage_V = self.lockin.sine_voltage
                X_V = self.lockin.x

            # in mili ampers, 50 ohm is the internal resistance of the lockin
            SampleCurrent_A = Voltage_V / (
                self.ShuntResistance_Ohm + self.ContactResistance_Ohm + 50
            )

            try:
                answer_dict["X_V"] = X_V
                answer_dict["specified_Shunt_Ohm"] = self.ShuntResistance_Ohm
                answer_dict["specified_Contact_Ohm"] = self.ContactResistance_Ohm
                answer_dict["SampleCurrent_A"] = SampleCurrent_A
                answer_dict["SampleResistance_Ohm"] = X_V / SampleCurrent_A
            except ZeroDivisionError:
                answer_dict["SampleResistance_Ohm"] = np.NaN
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        if not answer_dict["OK"]:
            answer_dict["ERROR"] = True
            answer_dict["ERROR_message"] = str(answer_dict["Errors"])
        return answer_dict

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


class SR830GUI(AbstractMainApp, Window_trayService_ui):
    """This is the SR830 GUI WIndow"""

    sig_arbitrary = pyqtSignal()
    sig_assertion = pyqtSignal(str)

    def __init__(
        self,
        Lockin=None,
        identity=None,
        InstrumentAddress=None,
        prometheus_port=None,
        **kwargs,
    ):
        self._identity = identity
        self._InstrumentAddress = InstrumentAddress
        self._prometheus_port = prometheus_port
        self._Lockin = Lockin
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        # loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)

        self.__name__ = "Lockin_Window"
        self.controls = [self.groupSettings]

        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot()
    def run_Hardware(self):
        """start/stop the Lockin thread"""
        try:
            self.getInfodata = self.running_thread_control(
                SR830_ControlClient(
                    InstrumentAddress=self._InstrumentAddress,
                    mainthread=self,
                    identity=self._identity,
                    Lockin=self._Lockin,
                    prometheus_port=self._prometheus_port,
                    prometheus_name=self._identity,
                ),
                "Hardware",
            )
            # getInfodata = self.running_thread_control(SR530_ControlClient(
            # InstrumentAddress=self._InstrumentAddress, mainthread=self,
            # identity=self._identity), 'Hardware', )

            self.getInfodata.sig_Infodata.connect(self.updateGUI)
            # getInfodata.sig_visaerror.connect(self.printing)
            # getInfodata.sig_assertion.connect(self.printing)
            # getInfodata.sig_visaerror.connect(self.show_error_general)
            # getInfodata.sig_assertion.connect(self.show_error_general)

            # getInfodata.sig_visatimeout.connect(
            # lambda: self.show_error_general('SR830: timeout'))
        except (VisaIOError, NameError) as e:
            # self.show_error_general('running: {}'.format(e))
            self._logger.exception(e)
            raise ApplicationExit("Could not connect to Hardware!")

    def closeEvent(self, event):
        while not self.getInfodata.run_finished:
            time.sleep(0.1)
        # with self.getInfodata.lock:
        self.getInfodata.lock.acquire()
        del self.getInfodata.lockin
        super().closeEvent(event)

    @pyqtSlot(dict)
    def updateGUI(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""
        self.data.update(data)
        # data['date'] = convert_time(time.time())
        # self.data['SR830'].update(data)
        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        self.lcdSetFrequency_Hz.display(self.data["Frequency_Hz"])
        self.lcdSetVoltage_V.display(self.data["Voltage_V"])
        self.textX_V.setText("{num:=+13.12f}".format(num=self.data["X_V"]))

        self.textSampleCurrent_mA.setText(
            "{num:=+8.6f}".format(num=self.data["SampleCurrent_mA"])
        )
        self.textSampleResistance_Ohm.setText(
            "{num:=+8.6f}".format(num=self.data["SampleResistance_Ohm"])
        )

        self.textY_V.setText("{num:=+13.12f}".format(num=self.data["Y_V"]))
        self.textR_V.setText("{num:=+13.12f}".format(num=self.data["R_V"]))
        self.textTheta_Deg.setText("{num:=+8.6f}".format(num=self.data["Theta_Deg"]))


if __name__ == "__main__":
    try:
        with PidFile("SR830"):

            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)

            logger_2 = logging.getLogger("pyvisa")
            logger_2.setLevel(logging.INFO)
            logger_3 = logging.getLogger("PyQt5")
            logger_3.setLevel(logging.INFO)

            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
            )
            handler.setFormatter(formatter)

            logger.addHandler(handler)
            logger_2.addHandler(handler)
            logger_3.addHandler(handler)

            Sr830_InstrumentAddress = "GPIB::9::INSTR"
            # Sr860_InstrumentAddress: 'filler'

            app = QtWidgets.QApplication(sys.argv)
            form = SR830GUI(
                ui_file="LockIn_main.ui",
                Name="Lockin SR830",
                identity="SR830_1",
                InstrumentAddress=Sr830_InstrumentAddress,
                Lockin=SR830,
                prometheus_port=8006,
            )
            form.show()
            # print('date: ', dt.datetime.now(),
            #       '\nstartup time: ', time.time() - a)
            sys.exit(app.exec_())
    except PidFileError:
        print("Program already running! \nShutting down now!\n")
        sys.exit()
