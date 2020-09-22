"""Module containing a class to run a LakeShore 350 Cryogenic Temperature Controller in a pyqt5 application

Classes:
    LakeShore350_ControlClient: a class for interfacing with a LakeShore350 temperature controller
            inherits from AbstractLoopThreadClient
    
    LakeShoreGUI : class to run the ControlClient interface and display its measured values
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# to be removed once this is packaged!

from LakeShore import LakeShore350_ethernet
from drivers import ApplicationExit

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer

# from PyQt5 import QtWidgets

# import json

from util import ExceptionHandling

# from util import AbstractLoopClient
from util import AbstractMainApp
from util import AbstractLoopThreadClient
from util import Window_trayService_ui

from datetime import datetime


# from PyQt5.QtWidgets import QtAlignRight

# import datetime as dt
# from threading import Lock
from copy import deepcopy
# from logging.handlers import RotatingFileHandler
from pyvisa.errors import VisaIOError
import logging


class LakeShore350_ControlClient(AbstractLoopThreadClient):
    """Updater class for the LakeShore350 Temperature controller

    For each Lakeshore350 function there is a wrapping method,
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
        Heater_Output_percentage=None,
        Heater_Output_mW=None,
        Temp_K=None,
        Ramp_Rate_Status=None,
        Ramp_Rate=None,
        Input_Sensor=None,
        Sensor_1_K=None,
        Sensor_2_K=None,
        Sensor_3_K=None,
        Sensor_4_K=None,
        Loop_P_Param=None,
        Loop_I_Param=None,
        Loop_D_Param=None,
        Heater_Range=None,
        Heater_Setup=None,
        Sensor_1_Ohm=None,
        Sensor_2_Ohm=None,
        Sensor_3_Ohm=None,
        Sensor_4_Ohm=None,
        OutputMode=None,
    )

    def __init__(self, mainthread=None, comLock=None, InstrumentAddress="", **kwargs):
        super().__init__(**kwargs)
        self.interval = 0.5
        self.t = datetime.now()

        # here the class instance of the LakeShore should be handed
        self.__name__ = "LakeShore350_control " + InstrumentAddress
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        self.LakeShore350 = LakeShore350_ethernet(InstrumentAddress=InstrumentAddress)

        self.Temp_K_value = 3
        # self.Heater_mW_value = 0
        self.Ramp_Rate_value = 0

        self.Upper_Bound_value = 330
        self._max_power = None
        """proper P, I, D values needed
        """
        # self.ZoneP_value
        # self.ZoneI_value
        # self.ZoneD_value
        self.Mout_value = 50
        self.Zone_Range_value = 2
        self.Zone_Rate_value = 1

        """sets Heater power to 994,05 mW
        """
        self.configHeater()
        self.configTempLimit()
        self.initiating_PID()

        self.Ramp_status_internal = int(False)
        self._SensorInput = 1

        # self.setControlLoopZone()
        # self.startHeater()

        if mainthread is not None:
            mainthread.sig_sendConfTemp.connect(self.setTemp_K)
            # setting LakeShore values by GUI LakeShore window
            # mainthread.spinSetTemp_K.valueChanged.connect(
            #     lambda value: self.gettoset_Temp_K(value)
            # )
            # mainthread.spinSetTemp_K.editingFinished.connect(self.setTemp_K)

            # mainthread.spinSetRampRate_Kpmin.valueChanged.connect(
            #     self.gettoset_Ramp_Rate_K
            # )
            # mainthread.spinSetRampRate_Kpmin.editingFinished.connect(
            #     self.setRamp_Rate_K
            # )

            # turns off heater output
            mainthread.pushButtonHeaterOut.clicked.connect(
                lambda: self.setHeater_Range(0)
            )

            # allows to choose from different inputs to connect to output 1
            # control loop. default is input 1.

            mainthread.comboSetInput_Sensor.activated["int"].connect(
                lambda value: self.setInput(value + 1)
            )
            # mainthread.spinSetInput_Sensor.editingFinished.(lambda
            # value: self.threads['control_LakeShore350'][0].setInput())

            # mainthread.checkRamp_Status.toggled["bool"].connect(self.setStatusRamp)

            # """ NEW GUI controls P, I and D values for Control Loop PID Values Command
            # """
            mainthread.spinSetLoopP_Param.valueChanged.connect(
                self.gettoset_LoopP_Param
            )
            mainthread.spinSetLoopP_Param.editingFinished.connect(self.setLoopP_Param)

            mainthread.spinSetLoopI_Param.valueChanged.connect(
                self.gettoset_LoopI_Param
            )
            mainthread.spinSetLoopI_Param.editingFinished.connect(self.setLoopI_Param)

            mainthread.spinSetLoopD_Param.valueChanged.connect(
                self.gettoset_LoopD_Param
            )
            mainthread.spinSetLoopD_Param.editingFinished.connect(self.setLoopD_Param)

            """ NEW GUI Heater Range and Ouput Zone
            """
            # mainthread.comboSetHeater_Range.activated['int'].connect(self.setHeater_Range(value))
            # mainthread.spinSetHeater_Range.valueChanged.connect(self.gettoset_Heater_Range(value))#mainthread.spinSetHeater_Range.Finished.connect(self.setHeater_Range())
            # mainthread.spinSetUpper_Bound.valueChanged.connect(self.gettoset_Upper_Bound(value))#
            # mainthread.spinSetZoneP_Param.valueChanged.connect(self.gettoset_ZoneP_Param(value))#
            # mainthread.spinSetZoneI_Param.valueChanged.connect(self.gettoset_ZoneI_Param(value))#
            # mainthread.spinSetZoneD_Param.valueChanged.connect(self.gettoset_ZoneD_Param(value))#
            # mainthread.spinSetZoneMout.valueChanged.connect(self.gettoset_ZoneMout(value))#
            # mainthread.spinSetZone_Range.valueChanged.connect(self.gettoset_Zone_Range(value))#
            # mainthread.spinSetZone_Rate.valueChanged.connect(self.gettoset_Zone_Rate(value))

            mainthread.spin_threadinterval.valueChanged.connect(
                lambda value: self.setInterval(value)
            )
            # print('thread done with init')

    @ExceptionHandling
    def initiating_PID(self):
        temp_list0 = self.LakeShore350.ControlLoopPIDValuesQuery(1)
        self.LoopP_value = temp_list0[0]
        self.LoopI_value = temp_list0[1]
        self.LoopD_value = temp_list0[2]

    # @control_checks
    @ExceptionHandling
    def running(self):
        """
        Try to extract all current data from LakeShore350,
        and emit signal, sending the data
        """
        # print('run')
        # self.t1 = datetime.now()
        # print(self.t1 - self.t)
        # self.t = self.t1
        self.run_finished = False
        # -------------------------------------------------------------------------------------------------------------------------
        self.data["Temp_K"] = self.LakeShore350.ControlSetpointQuery(1)
        self.data[
            "Ramp_Rate_Status"
        ] = self.LakeShore350.ControlSetpointRampParameterQuery(1)[0]

        temp_list = self.LakeShore350.KelvinReadingQuery(0)
        self.data["Sensor_1_K"] = temp_list[0]
        self.data["Sensor_2_K"] = temp_list[1]
        self.data["Sensor_3_K"] = temp_list[2]
        self.data["Sensor_4_K"] = temp_list[3]
        ramp_rate = self.LakeShore350.ControlSetpointRampParameterQuery(1)[1]
        self.data["Ramp_Rate"] = (
            ramp_rate if self.Temp_K_value > self.data["Temp_K"] else -ramp_rate
        )

        temp_list3 = self.LakeShore350.SensorUnitsInputReadingQuery(0)
        self.data["Sensor_1_Ohm"] = temp_list3[0]
        self.data["Sensor_2_Ohm"] = temp_list3[1]
        self.data["Sensor_3_Ohm"] = temp_list3[2]
        self.data["Sensor_4_Ohm"] = temp_list3[3]

        self.data["Heater_Range"] = self.LakeShore350.HeaterRangeQuery(1)
        self.data["Heater_Output_percentage"] = self.LakeShore350.HeaterOutputQuery(1)
        self.data["Heater_Output_mW"] = (
            self.data["Heater_Output_percentage"]
            / 100
            * self._max_power
            * 1e3
            * 10 ** (-(5 - self.data["Heater_Range"]))
        )

        self.data["Heater_Range_times_10"] = self.data["Heater_Range"] * 10
        temp_list2 = self.LakeShore350.ControlLoopPIDValuesQuery(1)
        self.data["Loop_P_Param"] = temp_list2[0]
        self.data["Loop_I_Param"] = temp_list2[1]
        self.data["Loop_D_Param"] = temp_list2[2]
        self.data["OutputMode"] = self.LakeShore350.OutputModeQuery(1)[1]
        self.data["Input_Sensor"] = self.LakeShore350.OutputModeQuery(1)[1]

        self.data["realtime"] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.sig_Infodata.emit(deepcopy(self.data))
        self.run_finished = True
        # self.comms_upstream.send_multipart(
        #     [self.comms_name, enc(json.dumps(self.data))])

    @ExceptionHandling
    def act_on_command(self, command):
        if "setTemp_K" in command:
            self.setTemp_K(command["setTemp_K"])
        if "configTempLimit" in command:
            self.configTempLimit(command["configTempLimit"])
        # TODO: implement more commands

    @ExceptionHandling
    def configSensor(self):
        """configures sensor inputs to Cernox"""
        for i in ["A", "B", "C", "D"]:
            self.LakeShore350.InputTypeParameterCommand(i, 3, 1, 0, 1, 1, 0)

    @ExceptionHandling
    def configHeater(self):
        """configures heater output
        HeaterSetupCommand(1,2,0,0.141,2) sets Output 1, Heater_Resistance to 50 Ohm, enables Custom Maximum Heater Output Current of 0.141 and configures the heater output displays to show in power.
        """
        # weak heater
        # self.LakeShore350.HeaterSetupCommand(1, 2, 0, 0.141, 2)
        # strong heater
        # 1A, 50Ohm, display power percentages
        self.LakeShore350.HeaterSetupCommand(1, 2, 2, 1, 2)
        self._max_current = 1  # [A]
        self._heater_resistance = 50  # [Ohm]
        self._max_power = self._heater_resistance * self._max_current ** 2  # [W]

    @ExceptionHandling
    def configTempLimit(self, confdict=None):
        """sets temperature limit"""
        if confdict is None:
            confdict = {key: 400 for key in ["A", "B", "C", "D"]}
        for i in ["A", "B", "C", "D"]:
            self.LakeShore350.TemperatureLimitCommand(i, 400.0)

    @pyqtSlot(dict)
    @ExceptionHandling
    def setTemp_K(self, tempdict: dict):
        """takes value Temp_K and uses it on function ControlSetpointCommand to set desired temperature.
            dict(isSweep=isSweep,
                 isSweepStartCurrent=isSweepStartCurrent,
                 setTemp=setTemp,
                 start=start,
                 end=end,
                 SweepRate=SweepRate)

        """
        self.Temp_K_value = tempdict['setTemp']
        self.Ramp_status_internal = int(tempdict["isSweep"])
        self.Ramp_Rate_value = tempdict["SweepRate"]

        if tempdict["isSweep"]:
            setpoint_now = self.LakeShore350.ControlSetpointQuery(1)
            if "start" in tempdict:
                starting = tempdict["start"]
            else:
                starting = setpoint_now
            start = setpoint_now if tempdict["isSweepStartCurrent"] else starting
            self.LakeShore350.ControlSetpointCommand(1, start)
            self.LakeShore350.ControlSetpointRampParameterCommand(
                1, self.Ramp_status_internal, self.Ramp_Rate_value
            )
            self.LakeShore350.ControlSetpointCommand(1, tempdict["end"])

        else:
            self.LakeShore350.ControlSetpointCommand(1, self.Temp_K_value)
            self.LakeShore350.ControlSetpointRampParameterCommand(
                1, self.Ramp_status_internal, self.Ramp_Rate_value
            )

        # if Temp_K is not None:
        #     self.Temp_K_value = Temp_K
        self.LakeShore350.ControlSetpointCommand(1, self.Temp_K_value)
        self.LakeShore350.ControlSetpointRampParameterCommand(
            1, self.Ramp_status_internal, self.Ramp_Rate_value
        )

    @ExceptionHandling
    def read_Temperatures(self):
        sensors = {}
        sensor_names = ["Sensor_1_K", "Sensor_2_K", "Sensor_3_K", "Sensor_4_K"]
        temp_list = self.LakeShore350.KelvinReadingQuery(0)

        for idx, sens in enumerate(sensor_names):
            sensors[sens] = temp_list[idx]
        return sensors

    # @pyqtSlot()
    # def setHeater_mW(self):
    #    try:
    #        self.LakeShore350.HeaterSetupCommand
    #    except AssertionError as e_ass:
    #        self.sig_assertion.emit(e_ass.args[0])
    #    except VisaIOError as e_visa:
    #        if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
    #            self.sig_visatimeout.emit()
    #        else:
    #            self.sig_visaerror.emit(e_visa.args[0])

    # @pyqtSlot(bool)
    # def setStatusRamp(self, bools):
    #     self.Ramp_status_internal = int(bools)
    #     self.setRamp_Rate_K()
    #     self.setTemp_K()

    # @pyqtSlot()
    # @ExceptionHandling
    # def setRamp_Rate_K(self):
    #     self.LakeShore350.ControlSetpointRampParameterCommand(
    #         1, self.Ramp_status_internal, self.Ramp_Rate_value
    #     )
    #     # the lone '1' here is the output

    @pyqtSlot(int)
    @ExceptionHandling
    def setInput(self, Input_value):
        """(1,1,value,1) configure Output 1 for Closed Loop PID, using Input "value" and set powerup enable to On."""
        # self._SensorInput = Input_value
        self.LakeShore350.OutputModeCommand(1, 1, Input_value, 1)

    @pyqtSlot()
    @ExceptionHandling
    def setLoopP_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.LoopP_value, self.data["Loop_I_Param"], self.data["Loop_D_Param"]
        )

    @pyqtSlot()
    @ExceptionHandling
    def setLoopI_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.data["Loop_P_Param"], self.LoopI_value, self.data["Loop_D_Param"]
        )

    @pyqtSlot()
    @ExceptionHandling
    def setLoopD_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.data["Loop_P_Param"], self.data["Loop_I_Param"], self.LoopD_value
        )

    @pyqtSlot()
    @ExceptionHandling
    def startHeater(self):
        """start up Heater with Output 1 for Closed Loop PID, using Input "value" and set powerup enable to On."""
        self.LakeShore.OutputModeCommand(1, 1, self.sensor_values[5], 1)

    @pyqtSlot(float)
    @ExceptionHandling
    def setHeater_Range(self, range_value=None):
        """set Heater Range for Output 1 (and only 1, using Heater 1, not 2)"""
        if range_value is None:
            self.LakeShore350.HeaterRangeCommand(1, self.Heater_Range_value)
        elif range_value is not None:
            self.LakeShore350.HeaterRangeCommand(1, range_value)

    @pyqtSlot()
    @ExceptionHandling
    def setControlLoopZone(self):

        self.LakeShore350.ControlLoopZoneTableParameterCommand(
            1,
            1,
            self.Upper_Bound_value,
            self.ZoneP_value,
            self.ZoneI_value,
            self.ZoneD_value,
            self.Mout_value,
            self.Zone_Range_value,
            1,
            self.Zone_Rate_value,
        )

    @pyqtSlot(float)
    def gettoset_Temp_K(self, value):
        """class method to receive and store the value to set the temperature
        later on, when the command to enforce the value is sent
        """
        self.Temp_K_value = value

    # @pyqtSlot()
    # def gettoset_Heater_mW(self,value):
    #     """class method to receive and store the value to set the temperature
    #     later on, when the command to enforce the value is sent
    #     """
    #     self.Heater_mW_value = value

    @pyqtSlot(int)
    def gettoset_LoopP_Param(self, value):
        self.LoopP_value = value

    @pyqtSlot(int)
    def gettoset_LoopI_Param(self, value):
        self.LoopI_value = value

    @pyqtSlot(int)
    def gettoset_LoopD_Param(self, value):
        self.LoopD_value = value

    @pyqtSlot(float)
    def gettoset_Ramp_Rate_K(self, value):
        self.Ramp_Rate_value = value

    @pyqtSlot(float)
    def gettoset_Upper_Bound(self, value):
        self.Upper_Bound_value = value

    @pyqtSlot(int)
    def gettoset_ZoneP_Param(self, value):
        self.ZoneP_value = value

    @pyqtSlot(int)
    def gettoset_ZoneI_Param(self, value):
        self.ZoneI_value = value

    @pyqtSlot(int)
    def gettoset_ZoneD_Param(self, value):
        self.ZoneD_value = value

    @pyqtSlot(int)
    def gettoset_ZoneMout(self, value):
        self.Mout_value = value

    @pyqtSlot(float)
    def gettoset_Zone_Range(self, value):
        self.Zone_Range_value = value

    @pyqtSlot(float)
    def gettoset_Zone_Rate(self, value):
        self.Zone_Rate_value = value


#    def gettoset_Heater_Range(self,value):
#       self.Heater_Range_value = value


# errorfile = 'Errors\\' + dt.datetime.now().strftime('%Y%m%d') + '.error'

# directory = os.path.dirname(errorfile)
# os.makedirs(directory, exist_ok=True)

# logger.addHandler(handler)


class LakeShoreGUI(AbstractMainApp, Window_trayService_ui):
    """This is the LakeShore GUI Window"""

    sig_arbitrary = pyqtSignal()
    sig_assertion = pyqtSignal(str)
    sig_sendConfTemp = pyqtSignal(dict)

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
        # print('GUI post')
        # loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)

        self.__name__ = "LakeShore_Window"
        self.controls = [self.groupSettings]

        self.tempcontrol_values = dict(setTemperature=4, SweepRate=2, isSweep=False)

        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setTemp_valcha(self, value):
        # self.threads['control_ITC'][0].gettoset_Temperature(value)
        self.tempcontrol_values["setTemperature"] = value

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setRamp_valcha(self, value):
        self.tempcontrol_values["SweepRate"] = value
        # self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot(bool)
    @ExceptionHandling
    def fun_checkSweep_toggled(self, boolean):
        self.tempcontrol_values["Sweep_status_software"] = boolean

    @pyqtSlot()
    @ExceptionHandling
    def fun_sendConfTemp(self):
        self.fun_startTemp(
            isSweep=self.tempcontrol_values["Sweep_status_software"],
            isSweepStartCurrent=True,
            setTemp=self.tempcontrol_values["setTemperature"],
            end=self.tempcontrol_values["setTemperature"],
            SweepRate=self.tempcontrol_values["SweepRate"],
        )

    # @pyqtSlot(dict)
    # @ExceptionHandling
    # def ITC_fun_routeSignalTemps(self, d: dict) -> None:
    #     self.ITC_fun_startTemp(isSweep=d['Sweep_status_software'],
    #                            isSweepStartCurrent=d['isSweepStartCurrent'],
    #                            setTemp=d['setTemperature'],
    #                            end=d['setTemperature'],
    #                            SweepRate=d['SweepRate'])

    @pyqtSlot(dict)
    def fun_startTemp(
        self,
        isSweep=False,
        isSweepStartCurrent=True,
        setTemp=4,
        start=None,
        end=5,
        SweepRate=2,
    ):
        self.sig_sendConfTemp.emit(
            dict(
                isSweep=isSweep,
                isSweepStartCurrent=isSweepStartCurrent,
                setTemp=setTemp,
                start=start,
                end=end,
                SweepRate=SweepRate,
            )
        )

    @pyqtSlot()
    def run_Hardware(self):
        """start/stop the LakeShore350 thread"""

        try:
            getInfodata = self.running_thread_control(
                LakeShore350_ControlClient(
                    InstrumentAddress=self._InstrumentAddress,
                    mainthread=self,
                    identity=self._identity,
                    prometheus_port=self._prometheus_port,
                    prometheus_name=self._identity,
                ),
                "Hardware",
            )
            with getInfodata.lock:
                temp = getInfodata.LakeShore350.ControlSetpointQuery(output=1)
                self.tempcontrol_values['setTemperature'] = temp
                rampstatus = getInfodata.LakeShore350.ControlSetpointRampParameterQuery(output=1)
                self.tempcontrol_values["Sweep_status_software"] = bool(rampstatus[0])
                self.tempcontrol_values["SweepRate"] = rampstatus[1]

            getInfodata.sig_Infodata.connect(self.updateGUI)
            # getInfodata.sig_visaerror.connect(self.printing)
            # getInfodata.sig_visaerror.connect(self.show_error_general)
            # getInfodata.sig_assertion.connect(self.printing)
            # getInfodata.sig_assertion.connect(self.show_error_general)
            self.spinSetTemp_K.valueChanged.connect(self.fun_setTemp_valcha)
            self.checkRamp_Status.toggled["bool"].connect(self.fun_checkSweep_toggled)
            self.spinSetRamp_Kpmin.valueChanged.connect(self.fun_setRamp_valcha)
            self.commandSendConfTemp.clicked.connect(self.fun_sendConfTemp)

            # getInfodata.sig_visatimeout.connect(
            #     lambda: self.show_error_general('LakeShore350: timeout'))

        except (VisaIOError, NameError) as e:
            # self.show_error_general('running: {}'.format(e))
            self._logger.exception(e)
            raise ApplicationExit("Could not connect to Hardware!")

    # def calculate_Kpmin(self, data):
    # """calculate the rate of change of Temperature"""
    # coeffs = []
    # for sensordata in self.LakeShore350_Kpmin['Sensors'].values():
    #     coeffs.append(np.polynomial.polynomial.polyfit(
    #         self.LakeShore350_Kpmin['newtime'], sensordata, deg=1))

    # integrated_diff = dict(Sensor_1_Kpmin=coeffs[0][1] * 60,
    #                        Sensor_2_Kpmin=coeffs[1][1] * 60,
    #                        Sensor_3_Kpmin=coeffs[2][1] * 60,
    #                        Sensor_4_Kpmin=coeffs[3][1] * 60)

    # data.update(integrated_diff)

    # # advancing entries to the next slot
    # for i, entry in enumerate(self.LakeShore350_Kpmin['newtime'][:-1]):
    #     self.LakeShore350_Kpmin['newtime'][i + 1] = entry
    #     self.LakeShore350_Kpmin['newtime'][0] = time.time()
    #     for key in self.LakeShore350_Kpmin['Sensors'].keys():
    #         self.LakeShore350_Kpmin['Sensors'][key][
    #             i + 1] = self.LakeShore350_Kpmin['Sensors'][key][i]
    #         self.LakeShore350_Kpmin['Sensors'][
    #             key][0] = deepcopy(data[key])

    # self.LakeShore350_Kpmin['Sensors']['Sensor_2_K'][i+1] = self.LakeShore350_Kpmin['Sensors']['Sensor_2_K'][i]
    # self.LakeShore350_Kpmin['Sensors']['Sensor_3_K'][i+1] = self.LakeShore350_Kpmin['Sensors']['Sensor_3_K'][i]
    # self.LakeShore350_Kpmin['Sensors']['Sensor_4_K'][i+1] = self.LakeShore350_Kpmin['Sensors']['Sensor_4_K'][i]

    # including the new values
    # self.LakeShore350_Kpmin['Sensors']['Sensor_2_K'][0] = deepcopy(data['Sensor_2_K'])
    # self.LakeShore350_Kpmin['Sensors']['Sensor_3_K'][0] = deepcopy(data['Sensor_3_K'])
    # self.LakeShore350_Kpmin['Sensors']['Sensor_4_K'][0] = deepcopy(data['Sensor_4_K'])

    # data.update(dict(Sensor_1_Kpmin=integrated_diff['Sensor_1_Kpmin'],
    #                     Sensor_2_Kpmin=integrated_diff['Sensor_2_Kpmin'],
    #                     Sensor_3_Kpmin=integrated_diff['Sensor_3_Kpmin'],
    #                     Sensor_4_Kpmin=integrated_diff['Sensor_4_Kpmin']))

    # return integrated_diff, data

    @pyqtSlot(dict)
    def updateGUI(self, data):
        """
        Calculate the rate of change of Temperature on the sensors [K/min]
        Store LakeShore350 data in self.data['LakeShore350'], update LakeShore350_window
        """
        self.data.update(data)
        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # self.data['LakeShore350'].update(data)
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        self.progressHeaterOutput_percentage.setValue(
            self.data["Heater_Output_percentage"]
        )
        self.lcdHeaterOutput_mW.display(self.data["Heater_Output_mW"])
        self.lcdSetTemp_K.display(self.data["Temp_K"])
        # self.lcdRampeRate_Status.display(self.data['RampRate_Status'])
        self.lcdSetRampRate_Kpmin.display(self.data["Ramp_Rate"])

        self.comboSetInput_Sensor.setCurrentIndex(int(self.data["Input_Sensor"]) - 1)
        self.lcdSensor1_K.display(self.data["Sensor_1_K"])
        self.lcdSensor2_K.display(self.data["Sensor_2_K"])
        self.lcdSensor3_K.display(self.data["Sensor_3_K"])
        self.lcdSensor4_K.display(self.data["Sensor_4_K"])

        """NEW GUI to display P,I and D Parameters
        """
        self.lcdLoopP_Param.display(self.data["Loop_P_Param"])
        self.lcdLoopI_Param.display(self.data["Loop_I_Param"])
        self.lcdLoopD_Param.display(self.data["Loop_D_Param"])

        # self.lcdHeater_Range.display(self.date['LakeShore350']['Heater_Range'])


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

    # LakeShore_InstrumentAddress = "TCPIP::192.168.2.105::7777::SOCKET"
    # app = QtWidgets.QApplication(sys.argv)
    # form = LakeShoreGUI(
    #     ui_file="LakeShore_main.ui",
    #     Name="LakeShore350",
    #     identity="LakeShore350",
    #     InstrumentAddress=LakeShore_InstrumentAddress,
    #     prometheus_port=8004,
    # )
    # form.show()
    # # print('date: ', dt.datetime.now(),
    # #       '\nstartup time: ', time.time() - a)
    # sys.exit(app.exec_())
