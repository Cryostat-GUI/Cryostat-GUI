"""Module containing a class to run a LakeShore 350 Cryogenic Temperature Controller in a pyqt5 application

Classes:
    LakeShore350_ControlClient: a class for interfacing with a LakeShore350 temperature controller
            inherits from AbstractLoopClient
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# to be removed once this is packaged!

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets
from copy import deepcopy


from drivers import ApplicationExit

from util import ExceptionHandling
from util import AbstractLoopThreadClient

# from util import Timerthread_Clients
from util import Window_trayService_ui
from util import AbstractMainApp

from datetime import datetime as dt
from pyvisa.errors import VisaIOError
import logging


from Keithley.Keithley2182 import Keithley2182


class Keithley2182_ControlClient(AbstractLoopThreadClient):
    """Updater class for the LakeShore350 Temperature controller

    For each Device function there is a wrapping method,
    which we can call by a signal/by zmq comms. This wrapper sends
    the corresponding value to the device.

    There is a second method for all wrappers, which accepts
    the corresponding value, and stores it, so it can be sent upon acknowledgment

    The information from the device is collected in regular intervals (method "running"),
    and subsequently published on the data upstream. It is packed in a dict,
    the keys of which are displayed in the "data" dict in this class.
    """

    # exposable data dictionary
    data = dict(
        Voltage_V=None,
        TemperatureInternal_K=None,
        TemperaturePresent_K=None,
        realtime=None,
    )

    def __init__(self, mainthread=None, InstrumentAddress="", **kwargs):
        super().__init__(**kwargs)
        # self.logger = log if log else logging.getLogger(__name__)

        # here the class instance of the LakeShore should be handed
        self.__name__ = "Keithley2182_control " + InstrumentAddress
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.interval = 0.1 * 1e3
        # try:
        # print(self.logger, self.logger.name)

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        # Example:
        self.Keithley2182 = Keithley2182(InstrumentAddress=InstrumentAddress)
        self._startingtime = dt.now()
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        # Example:
        # self.initiating_PID()
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots
        # Examples:
        if mainthread is not None:
            pass
            # mainthread.spinSetLoopP_Param.valueChanged.connect(lambda value: self.gettoset_LoopP_Param(value))
            # mainthread.spinSetLoopP_Param.editingFinished.connect(self.setLoopP_Param)

            # mainthread.spinSetLoopI_Param.valueChanged.connect(lambda value: self.gettoset_LoopI_Param(value))
            # mainthread.spinSetLoopI_Param.editingFinished.connect(self.setLoopI_Param)

            # mainthread.spinSetLoopD_Param.valueChanged.connect(lambda value: self.gettoset_LoopD_Param(value))
            # mainthread.spinSetLoopD_Param.editingFinished.connect(self.setLoopD_Param)

            # mainthread.spin_threadinterval.valueChanged.connect(
            #     lambda value: self.setInterval(value)
            # )
            # -------------------------------------------------------------------------------------------------------------------------

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

        self.data["Voltage_V"] = self.Keithley2182.measureVoltage()
        if (dt.now() - self._startingtime).seconds > 60:
            self._startingtime = dt.now()
            self.data[
                "TemperatureInternal_K"
            ] = self.Keithley2182.measureInternalTemperature()
            self.data[
                "TemperaturePresent_K"
            ] = self.Keithley2182.measurePresentTemperature()

            for error in self.Keithley2182.error_gen():
                if error[0] != "0":
                    self._logger.error(
                        "code:%s, message:%s", error[0], error[1].strip('"')
                    )
                    if error[0] == "-213":
                        self.Keithley2182 = Keithley2182(
                            InstrumentAddress=self.save_InstrumentAddress,
                        )
                        self._logger.warning(
                            "found error -213, re-establishing connection"
                        )
        self.data["realtime"] = dt.now()
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
        if "measure_Voltage" in command:
            # self.setTemp_K(command['setTemp_K'])
            self.data["Voltage_V"] = self.Keithley2182.measureVoltage()
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
        if "measure_Voltage" in command:
            # self.setTemp_K(command['setTemp_K'])
            answer_dict["Voltage_V"] = self.Keithley2182.measureVoltage()
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        answer_dict["OK"] = True
        return answer_dict
        # -------------------------------------------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    #  hardware communication functions
    # Examples:

    @pyqtSlot()
    @ExceptionHandling
    def read_Voltage(self):
        """read a Voltage from instrument. return value should be float"""
        return self.Keithley2182.measureVoltage()

    @pyqtSlot()
    @ExceptionHandling
    def speed_up(self):
        """increase measurement speed"""
        self.Keithley2182.setRate("FAS")

    @pyqtSlot()
    @ExceptionHandling
    def ToggleDisplay(self, bools):
        if bools:
            self.Keithley2182.DisplayOn()
        else:
            self.Keithley2182.DisplayOff()

    @pyqtSlot()
    @ExceptionHandling
    def ToggleFrontAutozero(self, bools):
        if bools:
            self.Keithley2182.FrontAutozeroOn()
        else:
            self.Keithley2182.FrontAutozeroOff()

    @pyqtSlot()
    @ExceptionHandling
    def ToggleAutozero(self, bools):
        if bools:
            self.Keithley2182.AutozeroOn()
        else:
            self.Keithley2182.AutozeroOff()

    @pyqtSlot()
    @ExceptionHandling
    def ToggleAutorange(self, bools):
        if bools:
            self.Keithley2182.AutorangeOn()
        else:
            self.Keithley2182.AutorangeOff()

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    # GUI value acceptance functions
    # Examples:

    # @pyqtSlot()
    # def gettoset_Temp_K(self, value):
    #     self.Temp_K_value = value

    # @pyqtSlot()
    # def gettoset_LoopP_Param(self, value):
    #     self.LoopP_value = value

    # @pyqtSlot()
    # def gettoset_LoopI_Param(self, value):
    #     self.LoopI_value = value

    # @pyqtSlot()
    # def gettoset_LoopD_Param(self, value):
    #     self.LoopD_value = value


class Keithley2182GUI(AbstractMainApp, Window_trayService_ui):
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

        self.__name__ = "Keithley2182_Window"
        self.controls = [self.groupSettings]

        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot()
    def run_Hardware(self):
        """start/stop the LakeShore350 thread"""

        try:
            getInfodata = self.running_thread_control(
                Keithley2182_ControlClient(
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
            self._logger.exception(e)
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
        gui_elements = [
            self.textVoltage_V,
            self.textTempInternal_K,
            self.textTempPresent_K,
        ]
        formats = ["{num:=+13.12f}"] + ["{num:=06.3f}"] * 2
        keys = ("Voltage_V", "TemperatureInternal_K", "TemperaturePresent_K")
        for g, f, k in zip(gui_elements, formats, keys):
            try:
                g.setText(f.format(num=self.data[k]))
            except KeyError:
                pass

        # self.textVoltage_V.setText("{num:=+13.12f}".format(num=self.data["Voltage_V"]))
        # self.textTempInternal_K.setText(
        #     "{num:=06.3f}".format(num=self.data["TemperatureInternal_K"])
        # )
        # self.textTempPresent_K.setText(
        #     "{num:=06.3f}".format(num=self.data["TemperaturePresent_K"])
        # )
        # -----------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    print(
        "please use the program 'start_XXX.py' to start communicating with this device!"
    )
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)

    # logger_2 = logging.getLogger("pyvisa")
    # logger_2.setLevel(logging.INFO)
    # logger_3 = logging.getLogger("PyQt5")
    # logger_3.setLevel(logging.INFO)

    # handler = logging.StreamHandler(sys.stdout)
    # handler.setLevel(logging.DEBUG)
    # formatter = logging.Formatter(
    #     "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    # )
    # handler.setFormatter(formatter)

    # logger.addHandler(handler)
    # logger_2.addHandler(handler)
    # logger_3.addHandler(handler)

    # app = QtWidgets.QApplication(sys.argv)
    # Keithley2182_1_adress = "GPIB0::2::INSTR"
    # form = Keithley2182GUI(
    #     ui_file="Nanovolt_main.ui",
    #     Name="Keithley2182_1",
    #     identity="Keithley2182_1",
    #     InstrumentAddress=Keithley2182_1_adress,
    #     prometheus_port=None,
    # )
    # form.show()
    # # print('date: ', dt.datetime.now(),
    # #       '\nstartup time: ', time.time() - a)
    # sys.exit(app.exec_())
