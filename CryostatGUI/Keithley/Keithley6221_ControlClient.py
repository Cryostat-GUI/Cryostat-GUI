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


from drivers import ApplicationExit

from util import ExceptionHandling
from util import AbstractLoopThreadClient
from util import Window_trayService_ui
from util import AbstractMainApp

from datetime import datetime
from pyvisa.errors import VisaIOError
import logging

from Keithley.Keithley6221 import Keithley6221


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

    def __init__(self, mainthread=None, comLock=None, InstrumentAddress="", **kwargs):
        super().__init__(**kwargs)
        self.__name__ = "DeviceName_control " + InstrumentAddress
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        self.Keithley6221 = Keithley6221(
            InstrumentAddress=InstrumentAddress,
        )
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        # Example:
        # self.initiating_PID()
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots
        # Examples:
        # if mainthread is not None:
        #     pass

        #     mainthread.spinSetLoopP_Param.valueChanged.connect(lambda value: self.gettoset_LoopP_Param(value))
        #     mainthread.spinSetLoopP_Param.editingFinished.connect(self.setLoopP_Param)

        #     mainthread.spinSetLoopI_Param.valueChanged.connect(lambda value: self.gettoset_LoopI_Param(value))
        #     mainthread.spinSetLoopI_Param.editingFinished.connect(self.setLoopI_Param)

        #     mainthread.spinSetLoopD_Param.valueChanged.connect(lambda value: self.gettoset_LoopD_Param(value))
        #     mainthread.spinSetLoopD_Param.editingFinished.connect(self.setLoopD_Param)

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
        # self.data['Temp_K'] = self.LakeShore350.ControlSetpointQuery(1)
        self.data["realtime"] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.sig_Infodata.emit(deepcopy(self.data))
        self.run_finished = True
        # data is being sent by the zmqClient class automatically

    @ExceptionHandling
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        pass
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        # examples:
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
        # if "measure_Voltage" in command:
        #     answer_dict["Voltage_V"] = self.Keithley2182.measureVoltage()
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        answer_dict["OK"] = True
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
        self.Keithley6221.disable()
        self.Current_A_storage = self.Current_A_value
        # for logging/application running:
        self.Current_A_value = 0
        self.OutputOn = self.Keithley6221.getstatus()[0]

    @pyqtSlot()
    @ExceptionHandling
    def enable(self):
        """enable the output current"""
        self.Keithley6221.enable()
        self.Current_A_value = self.Current_A_storage
        self.setCurrent_A()
        self.OutputOn = self.Keithley6221.getstatus()[0]

    @pyqtSlot()
    @ExceptionHandling
    def getstatus(self):
        """retrieve output current status"""
        return int(self.Keithley6221.getstatus()[0])

    @ExceptionHandling
    def toggle_frontpanel(self, bools, text="In sequence..."):
        """toggle frontpanel display text"""
        if bools:
            self.Keithley6221.enable_frontpanel()
        else:
            self.Keithley6221.disable_frontpanel(text)

    @pyqtSlot()
    @ExceptionHandling
    def setCurrent_A(self):
        """set a previously stored value for the current"""
        self.Keithley6221.setCurrent(self.Current_A_value)
        self.sig_Infodata.emit(deepcopy(dict(Current_A=self.Current_A_value)))

    @pyqtSlot()
    @ExceptionHandling
    def setCurrent(self, current: float):
        """set a pass value for the current"""
        self.Current_A_value = current
        self.Current_A_storage = current
        self.Keithley6221.setCurrent(current)
        self.sig_Infodata.emit(deepcopy(dict(Current_A=self.Current_A_value)))

    @pyqtSlot()
    @ExceptionHandling
    def setSweep(self):
        """set a current sweep"""
        self.Keithley6221.SetupSweet(
            self.Start_Current_value, self.Step_Current_value, self.Stop_Current_value
        )

    @pyqtSlot()
    @ExceptionHandling
    def startSweep(self):
        """start a current sweep"""
        self.Keithley6221.StartSweep()

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    # GUI value acceptance functions
    # Examples:

    @pyqtSlot(float)
    def gettoset_Current_A(self, value):
        """store a current value for later usage"""
        self.Current_A_value = value
        self.Current_A_storage = value

    @pyqtSlot(float)
    def gettoset_Start_Current(self, value):
        """store a start current for a sweep"""
        self.Start_Current_value = value

    @pyqtSlot(float)
    def gettoset_Step_Current(self, value):
        """store a step current for a sweep"""
        self.Step_Current_value = value

    @pyqtSlot(float)
    def gettoset_Stop_Current(self, value):
        """store a stop current for a sweep"""
        self.Stop_Current_value = value


class DeviceGUI(AbstractMainApp, Window_trayService_ui):
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
        # print('GUI post')
        # loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)

        self.__name__ = "Template_Window"
        self.controls = [self.groupSettings]

        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot()
    def run_Hardware(self):
        """start/stop the LakeShore350 thread"""

        try:
            getInfodata = self.running_thread_control(
                Template_ControlClient(
                    InstrumentAddress=self._InstrumentAddress,
                    mainthread=self,
                    identity=self._identity,
                    prometheus_port=self._prometheus_port,
                    prometheus_name=self._identity,
                ),
                "Hardware",
            )

            getInfodata.sig_Infodata.connect(self.updateGUI)

        except (VisaIOError, NameError) as e:
            # self.show_error_general('running: {}'.format(e))
            self.logger_personal.exception(e)
            raise ApplicationExit("Could not connect to Hardware!")

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
        "please use the program 'start_XXX.py' to start communicating with this device!"
    )

    # from pid import PidFile
    # from pid import PidFileError

    # try:
    #     with PidFile("Template"):
    #         logger = logging.getLogger()
    #         logger.setLevel(logging.DEBUG)

    #         logger_2 = logging.getLogger("pyvisa")
    #         logger_2.setLevel(logging.INFO)
    #         logger_3 = logging.getLogger("PyQt5")
    #         logger_3.setLevel(logging.INFO)

    #         handler = logging.StreamHandler(sys.stdout)
    #         handler.setLevel(logging.DEBUG)
    #         formatter = logging.Formatter(
    #             "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    #         )
    #         handler.setFormatter(formatter)

    #         logger.addHandler(handler)
    #         logger_2.addHandler(handler)
    #         logger_3.addHandler(handler)

    #         app = QtWidgets.QApplication(sys.argv)
    #         form = DeviceGUI(
    #             ui_file="Template_main.ui",
    #             Name="Template",
    #             identity=b"templ",
    #             InstrumentAddress="",
    #             prometheus_port=None,
    #         )
    #         form.show()
    #         # print('date: ', dt.datetime.now(),
    #         #       '\nstartup time: ', time.time() - a)
    #         sys.exit(app.exec_())
    # except PidFileError:
    #     print("Program already running! \nShutting down now!\n")
    #     sys.exit()
