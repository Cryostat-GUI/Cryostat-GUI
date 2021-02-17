"""Module containing a class to run a Keithley 6221 Current Source in a pyqt5 application

Classes:
    Keithley6221_ControlClient: a class for interfacing with a Keithley 6221 Current Source
            inherits from AbstractLoopThreadClient
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# to be removed once this is packaged!

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer

# from PyQt5 import QtWidgets
from copy import deepcopy
import time

from drivers import ApplicationExit

from util import ExceptionHandling
from util import AbstractLoopThreadClient
from util import Window_trayService_ui
from util import AbstractMainApp

from datetime import datetime
from pyvisa.errors import VisaIOError
import logging

# from Keithley.Keithley6221 import Keithley6221_ethernet
from pymeasure.instruments.keithley import Keithley6221


class Keithley6221_ControlClient(AbstractLoopThreadClient):
    """Updater class for a hardware device

    For each device function there is a wrapping method,
    which we can call by a signal/by zmq comms. This wrapper sends
    the corresponding value to the device.

    There is a second method for all wrappers, which accepts
    the corresponding value, and stores it, so it can be sent upon acknowledgment

    The information from the device is collected in regular intervals (method "running"),
    and subsequently published on the data upstream. It is packed in a dict,
    the keys of which are displayed in the "data" dict in this class.
    """

    # exposable data dictionary
    data = {}

    def __init__(
        self, mainthread=None, comLock=None, identity="", InstrumentAddress="", **kwargs
    ):
        super().__init__(identity=identity, **kwargs)
        self.__name__ = "Keithley6221_control " + InstrumentAddress
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        self.Keithley6221 = Keithley6221(
            InstrumentAddress,
            read_termination="\n",
        )
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        self.Current_A_storage = self.Keithley6221.source_current
        self.OutputOn = self.getstatus()  # 0 == OFF, 1 == ON
        if self.OutputOn:
            self.Current_A_value = self.Current_A_storage
        else:
            self.Current_A_value = 0
        # if self.OutputOn:
        #     self.disable()
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots
        # Examples:
        if mainthread is not None:
            self.mainthread = mainthread

            mainthread.hardware_IP.setText(InstrumentAddress)
            mainthread.hardware_id.setText(identity)

            mainthread.spinSetCurrent_mA.valueChanged.connect(
                lambda value: self.gettoset_Current_A(value * 1e-3)
            )
            mainthread.spinSetCurrent_mA.editingFinished.connect(self.setCurrent_A)

            mainthread.pushToggleOut.clicked.connect(self.toggleCurrent)

        #     -------------------------------------------------------------------------------------------------------------------------

        #     mainthread.spin_threadinterval.valueChanged.connect(
        #         lambda value: self.setInterval(value)
        #     )

    # @control_checks
    @ExceptionHandling
    def running(self):
        """
        Try to extract all current data from LakeShore350,
        and emit signal, sending the data
        """
        # print('run')
        self.run_finished = False
        # -------------------------------------------------------------------------------------------------------------------------

        # data collection for to be exposed on the data upstream
        # to be stored in self.data
        # example:
        self.data["OutputOn"] = self.getstatus()
        self.Current_A_value = self.Keithley6221.source_current
        self.data["Current_A"] = self.Current_A_value

        # for error in self.Keithley6221.error_gen():
        #     if error[0] != "0":
        #         self._logger.error("code:%s, message:%s", error[0], error[1].strip('"'))
        self.Keithley6221.check_errors()  # pymeasure writing errors to pymeasure log
        self.data["realtime"] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.sig_Infodata.emit(deepcopy(self.data))
        self.run_finished = True
        # data is being sent by the zmqClient class automatically

    @ExceptionHandling
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        # examples:
        if "set_Current_A" in command:
            self._logger.debug("setting the current to %.5f A", command["set_Current_A"])
            self.setCurrent(command["set_Current_A"])
        if "set_Output" in command:
            if int(command["set_Output"]) == 1:
                self._logger.debug("enabling current")
                self.enable()
            elif int(command["set_Output"]) == 0:
                self._logger.debug("disabling current")
                self.disable()
            else:
                self._logger.warning(
                    "output must be 0 or 1, I received '%s'", str(command["set_Output"])
                )
        # if 'setTemp_K' in command:
        #     self.setTemp_K(command['setTemp_K'])
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        # -------------------------------------------------------------------------------------------------------------------------

    @ExceptionHandling
    def query_on_command(self, command):
        """execute commands sent via tcp"""
        answer_dict = {}
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq tcp, and executed here
        # examples:
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        try:
            self.act_on_command(command)
            answer_dict.update(
                dict(
                    Current_A=self.Keithley6221.source_current,
                    OutputOn=self.getstatus(),
                )
            )
            answer_dict["OK"] = True
        finally:
            return answer_dict
        # -------------------------------------------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    #  hardware communication functions
    # Examples:

    def getCurrent_A(self):
        """return currently operated current value"""
        return self.Current_A_value

    @pyqtSlot()
    @ExceptionHandling
    def disable(self):
        """disable the output current"""
        self.Keithley6221.source_enabled = False
        self.Current_A_storage = self.Current_A_value
        # for logging/application running:
        self.Current_A_value = 0
        self.OutputOn = self.Keithley6221.source_enabled

    @pyqtSlot()
    @ExceptionHandling
    def enable(self):
        """enable the output current"""
        self.Keithley6221.source_enabled = True
        self.Current_A_value = self.Keithley6221.source_current
        self.setCurrent_A()
        self.OutputOn = self.Keithley6221.source_enabled

    @pyqtSlot()
    @ExceptionHandling
    def getstatus(self):
        """retrieve output current status"""
        return int(self.Keithley6221.source_enabled)

    @ExceptionHandling
    def toggle_frontpanel(self, bools, text=None):
        """toggle frontpanel display text"""
        self.Keithley6221.display_enabled = bools

    @pyqtSlot()
    @ExceptionHandling
    def setCurrent_A(self):
        """set a previously stored value for the current"""
        self.Keithley6221.source_current = self.Current_A_value
        send_dict = dict(Current_A=self.Current_A_value, OutputOn=self.getstatus())
        self.sig_Infodata.emit(deepcopy(send_dict))

    @pyqtSlot(float)
    @ExceptionHandling
    def setCurrent(self, current: float):
        """set a pass value for the current"""
        if self.getstatus():
            self.Current_A_value = current
        self.Current_A_storage = current
        self.Keithley6221.source_current = current
        send_dict = dict(Current_A=self.Current_A_value, OutputOn=self.getstatus())
        self.sig_Infodata.emit(deepcopy(send_dict))

    # @pyqtSlot()
    # @ExceptionHandling
    # def setSweep(self):
    #     """set a current sweep"""
    #     self.Keithley6221.SetupSweet(
    #         self.Start_Current_value, self.Step_Current_value, self.Stop_Current_value
    #     )

    # @pyqtSlot()
    # @ExceptionHandling
    # def startSweep(self):
    #     """start a current sweep"""
    #     self.Keithley6221.StartSweep()

    @pyqtSlot()
    @ExceptionHandling
    def toggleCurrent(self):
        self.OutputOn = self.getstatus()
        if self.OutputOn:
            self.disable()
            self.mainthread.pushToggleOut.setText("output is OFF")
        else:
            self.enable()
            self.mainthread.pushToggleOut.setText("output is ON")

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    # GUI value acceptance functions
    # Examples:

    @pyqtSlot(float)
    def gettoset_Current_A(self, value):
        """store a current value for later usage"""
        self.Current_A_value = value
        self.Current_A_storage = value

    # @pyqtSlot(float)
    # def gettoset_Start_Current(self, value):
    #     """store a start current for a sweep"""
    #     self.Start_Current_value = value

    # @pyqtSlot(float)
    # def gettoset_Step_Current(self, value):
    #     """store a step current for a sweep"""
    #     self.Step_Current_value = value

    # @pyqtSlot(float)
    # def gettoset_Stop_Current(self, value):
    #     """store a stop current for a sweep"""
    #     self.Stop_Current_value = value


class Keithley6221GUI(AbstractMainApp, Window_trayService_ui):
    """This is the LakeShore GUI Window"""

    sig_arbitrary = pyqtSignal()
    sig_assertion = pyqtSignal(str)

    def __init__(
        self, identity=None, InstrumentAddress=None, prometheus_port=None, **kwargs
    ):
        self._identity = identity
        self._InstrumentAddress = InstrumentAddress
        self._prometheus_port = prometheus_port
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        self.__name__ = "Keithley6221_Window"
        self.controls = [self.groupSettings]

        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot()
    def run_Hardware(self):
        """start/stop the LakeShore350 thread"""

        try:
            self.getInfodata = self.running_thread_control(
                Keithley6221_ControlClient(
                    InstrumentAddress=self._InstrumentAddress,
                    mainthread=self,
                    identity=self._identity,
                    prometheus_port=self._prometheus_port,
                    prometheus_name=self._identity,
                ),
                "Hardware",
            )

            self.getInfodata.sig_Infodata.connect(self.updateGUI)

        except (VisaIOError, NameError) as e:
            # self.show_error_general('running: {}'.format(e))
            self._logger.exception(e)
            raise ApplicationExit("Could not connect to Hardware!")

    def closeEvent(self, event):
        while not self.getInfodata.run_finished:
            time.sleep(0.1)
        with self.getInfodata.lock:
            del self.getInfodata.Keithley6221
            super().closeEvent(event)

    @pyqtSlot(dict)
    def updateGUI(self, data):
        """
        Store Device data in self.data, update values in GUI
        """
        self.data.update(data)
        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        # -----------------------------------------------------------------------------------------------------------
        # update the GUI
        # Examples:

        # self.progressHeaterOutput_percentage.setValue(
        #     self.data['Heater_Output_percentage'])
        # self.lcdHeaterOutput_mW.display(
        #     self.data['Heater_Output_mW'])
        # self.lcdSetTemp_K.display(
        #     self.data['Temp_K'])
        # # self.lcdRampeRate_Status.display(self.data['RampRate_Status'])
        # self.lcdSetRampRate_Kpmin.display(
        #     self.data['Ramp_Rate'])

        # self.comboSetInput_Sensor.setCurrentIndex(
        #     int(self.data['Input_Sensor']) - 1)
        # self.lcdSensor1_K.display(
        #     self.data['Sensor_1_K'])
        # self.lcdSensor2_K.display(
        #     self.data['Sensor_2_K'])
        # self.lcdSensor3_K.display(
        #     self.data['Sensor_3_K'])
        # self.lcdSensor4_K.display(
        #     self.data['Sensor_4_K'])
        # -----------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    print(
        "please use the program 'start_Keithley6221.py' to start communicating with this device!"
    )
