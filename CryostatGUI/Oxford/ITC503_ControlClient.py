"""Module containing a class to run a (Oxford Instruments) ITC 503 Intelligent Temperature Controller in a pyqt5 application

Classes:
    ITC_Updater: a class for interfacing with a ITC 503 Temperature Controller
            inherits from AbstractLoopThread
                there, the looping behaviour of this thread is defined
Author(s):
    bklebel (Benjamin Klebel)
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# to be removed once this is packaged!

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QSettings
from PyQt5 import QtWidgets

# import json
# import sys
from threading import Lock
from threading import Thread
import time
import numpy as np
from copy import deepcopy
import logging


from util import ExceptionHandling
from util import AbstractLoopThreadClient
from util import Window_trayService_ui
from util import readPID_fromFile
from util import AbstractMainApp

# from zmqcomms import dec, enc

from datetime import datetime
from Oxford import itc503
from pyvisa.errors import VisaIOError


class ITC503_ControlClient(AbstractLoopThreadClient):
    """Control class to update all instrument data of the Intelligent Temperature Controller (ITC) 503.

    For each ITC503 function (except collecting data), there is a wrapping method,
    which we can call by a signal, from the main thread. This wrapper sends
    the corresponding value to the device.

    There is a second method for all wrappers, which accepts
    the corresponding value, and stores it, so it can be sent upon acknowledgment

    The information from the device is collected in regular intervals (method "running"),
    and subsequently sent to the main thread. It is packed in a dict,
    the keys of which are displayed in the "sensors" dict in this class.
    """

    # exposable data dictionary
    data = {}
    sensors = dict(
        set_temperature=0,
        Sensor_1_K=1,
        Sensor_2_K=2,
        Sensor_3_K=3,
        temperature_error=4,
        heater_output_as_percent=5,
        heater_output_as_voltage=6,
        gas_flow_output=7,
        proportional_band=8,
        integral_action_time=9,
        derivative_action_time=10,
    )

    def __init__(self, mainthread=None, InstrumentAddress="", **kwargs):
        super().__init__(**kwargs)
        # self.logger = log if log else logging.getLogger(__name__)

        # here the class instance of the LakeShore should be handed
        self.__name__ = "ITC_control " + InstrumentAddress
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        self.ITC = itc503(InstrumentAddress=InstrumentAddress)

        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        self.control_state = 3
        self.set_temperature = 0
        self.set_prop = 0
        self.set_integral = 0
        self.set_derivative = 0
        self.set_sensor = 1
        self.set_heater_output = 0
        self.set_gas_output = 0
        self.set_auto_manual = 0
        self.sweep_parameters = None
        self.sweep_running = False
        self.sweep_running_device = False
        self.checksweep(stop=False)
        self.sweep_ramp = 0
        self.sweep_first = False

        self.setControl()
        self.interval = 1

        self.setPIDFile(".\\..\\configurations\\PID_conf\\P1C1.conf")
        self.useAutoPID = True
        if mainthread is not None:
            mainthread.sig_useAutocheck.connect(self.setCheckAutoPID)
            mainthread.sig_newFilePID.connect(self.setPIDFile)
            mainthread.sig_sendConfTemp.connect(self.setTemperature)
            mainthread.sig_stopSweep.connect(self.stopSweep)
        self.data_last = {}

        self.lock_newthread = Lock()

        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------

        # def change_gas(self):
        #     """to be worked in a separate worker thread (separate
        #         time.sleep() from GUI)
        #         change the opening percentage of the needle valve in a
        #         repeatable fashion (go to zero, go to new value)
        #         disable the GUI element during the operation

        #         should be changed, to use signals to change GUI,
        #         and possibly timers instead of time.sleep()
        #         (QTimer not usefil in the second case)
        #     """
        #     if self.ITC_window.checkGas_gothroughzero.isChecked():
        #         gas_new = self.threads['control_ITC'][0].set_gas_output
        #         with self.dataLock:
        #             gas_old = int(self.data['ITC']['gas_flow_output'])
        #         if gas_new == 0:
        #             time_wait = 60 / 1e2 * gas_old + 5
        #             self.threads['control_ITC'][0].setGasOutput()

        #             self.ITC_window.spinsetGasOutput.setEnabled(False)
        #             time.sleep(time_wait)
        #             self.ITC_window.spinsetGasOutput.setEnabled(True)
        #         else:
        #             time1 = 60 / 1e2 * gas_old + 5
        #             time2 = 60 / 1e2 * gas_new + 5
        #             self.threads['control_ITC'][
        #                 0].gettoset_GasOutput(0)
        #             self.threads['control_ITC'][0].setGasOutput()
        #             self.ITC_window.spinsetGasOutput.setEnabled(False)
        #             time.sleep(time1)
        #             self.threads['control_ITC'][
        #                 0].gettoset_GasOutput(gas_new)
        #             self.threads['control_ITC'][0].setGasOutput()
        #             time.sleep(time2)
        #             self.ITC_window.spinsetGasOutput.setEnabled(True)
        #     else:
        #         self.threads['control_ITC'][0].setGasOutput()

        mainthread.spinsetGasOutput.valueChanged.connect(self.gettoset_GasOutput)
        mainthread.spinsetGasOutput.editingFinished.connect(self.setGasOutput)

        mainthread.spinsetHeaterPercent.valueChanged.connect(self.gettoset_HeaterOutput)
        mainthread.spinsetHeaterPercent.editingFinished.connect(self.setHeaterOutput)

        mainthread.spinsetProportionalID.valueChanged.connect(
            self.gettoset_Proportional
        )
        mainthread.spinsetProportionalID.editingFinished.connect(self.setProportional)

        mainthread.spinsetPIntegrationD.valueChanged.connect(self.gettoset_Integral)
        mainthread.spinsetPIntegrationD.editingFinished.connect(self.setIntegral)

        mainthread.spinsetPIDerivative.valueChanged.connect(self.gettoset_Derivative)
        mainthread.spinsetPIDerivative.editingFinished.connect(self.setDerivative)

        mainthread.combosetHeatersens.activated["int"].connect(
            lambda value: self.setHeaterSensor(value + 1)
        )

        mainthread.combosetAutocontrol.activated["int"].connect(self.setAutoControl)

        mainthread.spin_threadinterval.valueChanged.connect(self.setInterval)

        # -------------------------------------------------------------------------------------------------------------------------

        mainthread.spin_threadinterval.valueChanged.connect(
            lambda value: self.setInterval(value)
        )

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

        # self.data['status'] = self.read_status()
        self.data["temperature_error"] = self.ITC.getValue(
            self.sensors["temperature_error"]
        )
        self.data["set_temperature"] = self.ITC.getValue(
            self.sensors["set_temperature"]
        )

        for key in self.sensors:
            try:

                value = self.ITC.getValue(self.sensors[key])
                self.data[key] = value
                self.data_last[key] = value

            except AssertionError as e_ass:
                self.sig_assertion.emit(e_ass.args[0])
                self._logger.exception(e_ass)
                self.data[key] = None
            except VisaIOError as e_visa:
                if (
                    isinstance(e_visa, type(self.timeouterror))
                    and e_visa.args == self.timeouterror.args
                ):
                    self.sig_visatimeout.emit()
                    self.ITC.clear_buffers()
                    self.data[key] = None
                else:
                    # raise e_visa
                    self._logger.exception(e_visa)
                    self.sig_visaerror.emit(e_visa.args[0])
        # print('retrieving', time.time()-starttime, self.data['Sensor_1_K'])
        # with "calc" in name it would not enter calculations!

        self.data["Sensor_1_calerr_K"] = (
            self.data["set_temperature"] - self.data["temperature_error"]
        )
        self.data_last["status"] = self.read_status()
        self.data_last["sweep"] = self.checksweep(stop=False)
        self.data["autocontrol"] = int(self.data_last["status"]["auto_int"])

        if self.useAutoPID:
            self.set_PID(temperature=self.data["Sensor_1_K"])
        self.data["realtime"] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.sig_Infodata.emit(deepcopy(self.data))
        self.run_finished = True

    @ExceptionHandling
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        pass
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        # examples:
        if "setTemp_K" in command:
            self.setTemperature(command["setTemp_K"])
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        # -------------------------------------------------------------------------------------------------------------------------

    @ExceptionHandling
    def setCheckAutoPID(self, boolean):
        """reaction to signal: set AutoPID behaviour"""
        self.useAutoPID = boolean

    @ExceptionHandling
    def setPIDFile(self, file):
        """reaction to signal: set AutoPID lookup file"""
        self.PIDFile = file
        self.PID_configuration = readPID_fromFile(self.PIDFile)

    @ExceptionHandling
    def read_status(self, run=True):
        """read the device status"""
        self.device_status = self.ITC.getStatus(run)
        return self.device_status

    # @pyqtSlot(int)
    # def set_delay_sending(self, delay):
    #     self.ITC.set_delay_measuring(delay)

    @ExceptionHandling
    def set_PID(self, temperature):
        """set the PID values acorrding to the configuration
        configuration should be stored in self.PID_configuration:
        a tuple, with
            the first entry being a list of temperatures
            the second entry being a list of dicts with p, i, d values"""
        try:
            PID_id = np.where(self.PID_configuration[0] > temperature)[0][0]
        except IndexError:
            PID_id = -1
        PID_conf = self.PID_configuration[1][PID_id]
        self.set_prop = PID_conf["p"]
        self.set_integral = PID_conf["i"]
        self.set_derivative = PID_conf["d"]
        self.setProportional()
        self.setIntegral()
        self.setDerivative()

    # def startSweep(self, d):
    #     with self.lock:
    #         self.setSweep(setpoint_temp=d['end'],
    #                       rate=d['SweepRate'],
    #                       start=d['start'])
    #         self.ITC.SweepStart()
    #         self.ITC.getValue(0)  # whatever this is needed for

    @ExceptionHandling
    def stopSweep(self):
        # with self.lock:
        self.setSweep(setpoint_temp=self.ITC.getValue(0), rate=50, start=False)
        time.sleep(0.1)
        self.ITC.SweepJumpToLast()
        time.sleep(0.1)

    @pyqtSlot()
    @ExceptionHandling
    def setSweep(self, setpoint_temp, rate, start=False):
        # with self.lock:
        if start:
            setpoint_now = start
        else:
            setpoint_now = self.ITC.getValue(0)
        # print('setpoint now = ', setpoint_now)
        if rate == 0:
            n_sweeps = 0
            sweep_times = [0.1]
            sweep_temps = [setpoint_temp]
            # print('rate was zero!')
        else:
            delta_Temperature = setpoint_temp - setpoint_now
            sweep_time = abs(delta_Temperature) / rate
            if sweep_time < 0.1:
                # print('sweeptime below 0.1: ', sweep_time)
                sweep_time = 0.1
            if sweep_time > 20e3:
                raise AssertionError(
                    "A sweep can be maximal 15 * 23h long (about 20 000 minutes, about 205K at 0.01 K/min)!"
                )
            if sweep_time > 23.5 * 60:
                # not only one step suffices, as the maximum time for one step
                # is 24 hours (using 23.5 for safety)

                # calculate number of full steps
                n_sweeps = int(sweep_time / (23 * 60))
                # calculate remaining time in minutes
                remaining_min = sweep_time - n_sweeps * 23 * 60
                # make list with full sweep times
                sweep_times = [23 * 60 for n in range(n_sweeps)]

                # make list with full sweep temps
                sweep_temps = [
                    setpoint_now + delta_Temperature * 23 * 60 / sweep_time * (n + 1)
                    for n in range(n_sweeps)
                ]
                if not np.isclose(0, remaining_min):
                    # append remaining times and temps in case the user
                    # did not hit a mark
                    sweep_times += [remaining_min]
                    sweep_temps += [setpoint_temp]
            else:
                n_sweeps = 0
                sweep_times = [sweep_time]
                sweep_temps = [setpoint_temp]

        sp = {
            str(z): dict(set_point=setpoint_temp, hold_time=0, sweep_time=0)
            for z in range(1, 17)
        }
        sp.update(
            {
                str(1): dict(set_point=setpoint_now, hold_time=0, sweep_time=0),
                # str(2): dict(set_point=setpoint_temp,
                #              hold_time=0,
                #              sweep_time=sweep_time),
                # str(15): dict(set_point=setpoint_temp,
                #               hold_time=0,
                #               sweep_time=0),
                str(16): dict(set_point=setpoint_temp, hold_time=0, sweep_time=0.1),
            }
        )
        # fill up the steps
        sp.update(
            {
                str(z + 2): dict(
                    set_point=sweep_temps[z], hold_time=0, sweep_time=sweep_times[z]
                )
                for z in range(n_sweeps + 1)
            }
        )

        self.sweep_parameters = sp
        # print('setting sweep to', self.sweep_parameters)
        self.ITC.setSweeps(self.sweep_parameters)
        # self.ITC.getValue(0)
        # print('sweep table read from device:')
        # for x in self.ITC.readSweepTable():
        # print(x)

    # @pyqtSlot(bool)
    # @ExceptionHandling
    # def setSweepStatus(self, bools):
    #     self.sweep_running = bools
    #     # print('set sweep status to', bools)
    #     with self.lock:
    #         # print('sweepstatus: I locked the thread!')
    #         if not bools:
    #             # print('sweepstatus: stopping the sweep')
    #             self.checksweep()
    #             self.ITC.setTemperature(self.set_temperature)
    #     # print('sweepstatus: I unlocked the device')
    #     # if bools:
    #         # print('set the sweep status: ', bools)
    #     #     print('sweepstatus: set the temperature')
    #     #     self.setTemperature()

    # @pyqtSlot(float)
    # @ExceptionHandling
    # def gettoset_sweepRamp(self, value):
    #     self.sweep_ramp = value
    #     # print('set sweep ramp to', value)

    @ExceptionHandling
    def checksweep(self, stop=True):
        # print('checking sweep')
        status = self.read_status(run=False)
        # print(status)
        try:
            int(status["sweep"])
            status["sweep"] = bool(int(status["sweep"]))
        except ValueError:
            status["sweep"] = True
        # print('sweep status: ', status['sweep'])
        self.sweep_running_device = status["sweep"]
        if stop and status["sweep"]:
            # print('setTemp: sweep running, stopping sweep')
            self.stopSweep()

        return self.sweep_running_device
        # else:
        # print('I did not see a running sweep!',
        # self.device_status['sweep'])
        # print('sweep was/is running: ', self.device_status['sweep'])

    @pyqtSlot(dict)
    @ExceptionHandling
    def setTemperature(self, values):
        """set Temperature of the instrument

        dict(isSweep=isSweep,
             isSweepStartCurrent=isSweepStartCurrent,
             setTemp=setTemp,
             start=start,
             end=end,
             SweepRate=SweepRate)

        """
        values["self"] = self

        def settingtheTemp(values):
            instance = values["self"]
            # stop sweep if it runs
            if "start" in values:
                starting = values["start"]
            else:
                starting = instance.ITC.getValue(0)
            start = (
                instance.ITC.getValue(0) if values["isSweepStartCurrent"] else starting
            )
            instance.checksweep(stop=True)
            autocontrol = instance.data_last["status"]["auto_int"]
            instance.ITC.setAutoControl(0)
            while instance.data_last["sweep"]:
                time.sleep(0.01)
            time.sleep(0.1)

            # print('sleeping')
            with instance.lock:
                if values["isSweep"]:
                    # set up sweep

                    instance.setSweep(
                        setpoint_temp=values["end"],
                        rate=values["SweepRate"],
                        start=start,
                    )
                    instance.ITC.SweepStart()
                    instance.ITC.getValue(0)  # whatever this is needed fo
                else:
                    instance.ITC.setTemperature(values["setTemp"])
                instance.ITC.setAutoControl(autocontrol)

        with self.lock_newthread:
            t1 = Thread(target=settingtheTemp, args=(values,))
            t1.start()
        # with self.lock:
        #     self.checksweep()
        #     if not self.sweep_running:
        #         self.ITC.setTemperature(value)
        #         # print(f'setting ITC temperature: {value}')
        #         # self.set_temperature = temp
        #     else:
        #         # print('setTemp: setting sweep.')
        #         self.setSweep(value, self.sweep_ramp)
        #         # print('starting sweep!')
        #         # print(f'setting ITC sweep: {value}')
        #         self.ITC.SweepStart()
        #         self.ITC.getValue(0)

    # @pyqtSlot(float)
    # @ExceptionHandling
    # def setSweepRamp(self):
    #     with self.lock:
    #         if self.sweep_running:
    #             self.checksweep()
    #             self.setSweep(self.set_temperature, self.sweep_ramp)
    #             self.ITC.SweepStart()
    #             self.ITC.getValue(0)

    @pyqtSlot()
    @ExceptionHandling
    def setControl(self):
        """set Control of the instrument"""
        self.ITC.setControl(self.control_state)

    @pyqtSlot()
    @ExceptionHandling
    def setProportional(self):
        """set Proportional of the instrument

        prop: Proportional band, in steps of 0.0001K.
        """
        self.ITC.setProportional(self.set_prop)

    @pyqtSlot()
    @ExceptionHandling
    def setIntegral(self):
        """set Integral of the instrument

        integral: Integral action time, in steps of 0.1 minute.
                    Ranges from 0 to 140 minutes.
        """
        self.ITC.setIntegral(self.set_integral)

    @pyqtSlot()
    @ExceptionHandling
    def setDerivative(self):
        """set Derivative of the instrument

        derivative: Derivative action time.
        Ranges from 0 to 273 minutes.
        """
        self.ITC.setDerivative(self.set_derivative)

    @pyqtSlot()
    @ExceptionHandling
    def setHeaterSensor(self, value):
        """set HeaterSensor of the instrument

        sensor: Should be 1, 2, or 3, corresponding to
        the heater on the front panel.
        """
        self.set_sensor = value
        self.ITC.setHeaterSensor(self.set_sensor)

    @pyqtSlot()
    @ExceptionHandling
    def setHeaterOutput(self):
        """set HeaterOutput of the instrument

        heater_output: Sets the percent of the maximum
                    heater output in units of 0.1%.
                    Min: 0. Max: 999.
        """
        self.ITC.setHeaterOutput(self.set_heater_output)

    @pyqtSlot()
    @ExceptionHandling
    def setGasOutput(self):
        """set GasOutput of the instrument

        gas_output: Sets the percent of the maximum gas
                output in units of 1%.
                Min: 0. Max: 99.
        """
        self.ITC.setGasOutput(self.set_gas_output)

    @pyqtSlot(int)
    @ExceptionHandling
    def setAutoControl(self, value):
        """set AutoControl of the instrument

        Value:Status map
            0: heater manual, gas manual
            1: heater auto  , gas manual
            2: heater manual, gas auto
            3: heater auto  , gas auto

        """
        self.set_auto_manual = value
        self.ITC.setAutoControl(self.set_auto_manual)

    @pyqtSlot(int)
    def gettoset_Control(self, value):
        """receive and store the value to set the Control status"""
        self.control_state = value

    # @pyqtSlot(float)
    # def gettoset_Temperature(self, value):
    #     """receive and store the value to set the temperature"""
    #     self.set_temperature = value
    #     # print('got a new temp:', value)

    @pyqtSlot(float)
    def gettoset_Proportional(self, value):
        """receive and store the value to set the proportional (PID)"""
        self.set_prop = value

    @pyqtSlot(float)
    def gettoset_Integral(self, value):
        """receive and store the value to set the integral (PID)"""
        self.set_integral = value

    @pyqtSlot(float)
    def gettoset_Derivative(self, value):
        """receive and store the value to set the derivative (PID)"""
        self.set_derivative = value

    @pyqtSlot(float)
    def gettoset_HeaterOutput(self, value):
        """receive and store the value to set the heater_output"""
        self.set_heater_output = value

    @pyqtSlot(float)
    def gettoset_GasOutput(self, value):
        """receive and store the value to set the gas_output"""
        self.set_gas_output = value


class ITCGUI(AbstractMainApp, Window_trayService_ui):

    """docstring for ITCGUI"""

    sig_sendConfTemp = pyqtSignal(dict)
    sig_useAutocheck = pyqtSignal(bool)
    sig_newFilePID = pyqtSignal(str)
    sig_stopSweep = pyqtSignal()

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

        self.__name__ = "ITC_Window"
        self.ITC_values = dict(setTemperature=4, SweepRate=2)
        self.controls = [self.groupSettings]
        self._useAutoPID = True
        self._PIDFile = ".\\..\\configurations\\PID_conf\\P1C1.conf"

        self.checkUseAuto.toggled["bool"].connect(self.fun_useAutoPID)
        # self.lineConfFile.textEdited.connect(
        #     self.ITC_PIDFile_store)
        self.pushConfLoad.clicked.connect(self.fun_PIDFile_send)
        self.pushConfBrowse.clicked.connect(self.window_FileDialogOpen)
        # self.lineConfFile.returnPressed.connect(
        #     self.fun_PIDFile_send)

        QTimer.singleShot(0, self.load_settings)
        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setTemp_valcha(self, value):
        # self.threads['control_ITC'][0].gettoset_Temperature(value)
        self.ITC_values["setTemperature"] = value

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setRamp_valcha(self, value):
        self.ITC_values["SweepRate"] = value
        # self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot(bool)
    @ExceptionHandling
    def fun_checkSweep_toggled(self, boolean):
        self.ITC_values["Sweep_status_software"] = boolean

    @pyqtSlot()
    @ExceptionHandling
    def fun_sendConfTemp(self):
        self.fun_startTemp(
            isSweep=self.ITC_values["Sweep_status_software"],
            isSweepStartCurrent=True,
            setTemp=self.ITC_values["setTemperature"],
            end=self.ITC_values["setTemperature"],
            SweepRate=self.ITC_values["SweepRate"],
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
        """method to start/stop the thread which controls the Oxford ITC"""

        try:
            getInfodata = self.running_thread_control(
                ITC503_ControlClient(
                    InstrumentAddress=self._InstrumentAddress,
                    mainthread=self,
                    identity=self._identity,
                    prometheus_port=self._prometheus_port,
                    prometheus_name=self._identity,
                ),
                "Hardware",
            )

            self.ITC_values["setTemperature"] = getInfodata.ITC.getValue(0)
            with getInfodata.lock:
                sweepstatus = getInfodata.checksweep(stop=False)
            self.ITC_values["Sweep_status_software"] = sweepstatus
            self.checkSweep.setChecked(sweepstatus)

            getInfodata.sig_Infodata.connect(self.updateGUI)
            # getInfodata.sig_visaerror.connect(self.printing)
            # getInfodata.sig_visaerror.connect(self.show_error_general)
            # # getInfodata.sig_assertion.connect(self.printing)
            # getInfodata.sig_assertion.connect(self.show_error_general)
            # getInfodata.sig_visatimeout.connect(
            #     lambda: self.show_error_general('ITC: timeout'))

            # setting ITC values by GUI
            self.spinsetTemp.valueChanged.connect(self.fun_setTemp_valcha)
            self.checkSweep.toggled["bool"].connect(self.fun_checkSweep_toggled)
            self.dspinSetRamp.valueChanged.connect(self.fun_setRamp_valcha)
            self.commandSendConfTemp.clicked.connect(self.fun_sendConfTemp)

            # self.sig_useAutocheck.emit(self.window_settings.temp_ITC_useAutoPID)
            # self.sig_newFilePID.emit(self.window_settings.temp_ITC_PIDFile)
        except (VisaIOError, NameError) as e:
            self._logger.exception(e)

    @pyqtSlot(dict)
    def updateGUI(self, data):
        """
        Calculate the rate of change of Temperature on the sensors [K/min]
        Store ITC data in self.data['ITC'], update ITC_window
        """
        # with self.dataLock:
        # print('storing: ', self.time_itc[-1]-time.time(), data['Sensor_1_K'])
        # self.time_itc.append(time.time())
        self.data.update(data)

        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        for key in self.data:
            if self.data[key] is None:
                self.data[key] = np.nan
        # if not self.data['Sensor_1_K'] is None:
        self.lcdTemp_sens1_K.display(self.data["Sensor_1_K"])
        # if not self.data['Sensor_2_K'] is None:
        self.lcdTemp_sens2_K.display(self.data["Sensor_2_K"])
        # if not self.data['Sensor_3_K'] is None:
        self.lcdTemp_sens3_K.display(self.data["Sensor_3_K"])

        # if not self.data['set_temperature'] is None:
        self.lcdTemp_set.display(self.data["set_temperature"])
        # if not self.data['temperature_error'] is None:
        self.lcdTemp_err.display(self.data["temperature_error"])
        # if not self.data['heater_output_as_percent'] is None:
        try:
            self.progressHeaterPercent.setValue(
                int(self.data["heater_output_as_percent"])
            )
            # if not self.data['gas_flow_output'] is None:
            self.progressNeedleValve.setValue(int(self.data["gas_flow_output"]))
        except ValueError:
            pass
        # if not self.data['heater_output_as_voltage'] is None:
        self.lcdHeaterVoltage.display(self.data["heater_output_as_voltage"])
        # if not self.data['gas_flow_output'] is None:
        self.lcdNeedleValve_percent.display(self.data["gas_flow_output"])
        # if not self.data['proportional_band'] is None:
        self.lcdProportionalID.display(self.data["proportional_band"])
        # if not self.data['integral_action_time'] is None:
        self.lcdPIntegrationD.display(self.data["integral_action_time"])
        # if not self.data['derivative_action_time'] is None:
        self.lcdPIDerivative.display(self.data["derivative_action_time"])

        self.lcdTemp_sens1_calcerr_K.display(self.data["Sensor_1_calerr_K"])

        self.combosetAutocontrol.setCurrentIndex(self.data["autocontrol"])

    def load_settings(self):
        """load all settings store in the QSettings
        set corresponding values in the 'Global Settings' window"""
        settings = QSettings("TUW", "CryostatGUI")
        try:
            self._useAutoPID = bool(settings.value("ITC_useAutoPID", int))
            self._PIDFile = settings.value("ITC_PIDFile", str)
        except KeyError as e:
            QTimer.singleShot(20 * 1e3, self.load_settings)
            # self.show_error_general(f'could not find a key: {e}')
            self._logger.warning(f"key {e} was not found in the settings")
        del settings

        self.checkUseAuto.setChecked(self._useAutoPID)
        if isinstance(self._PIDFile, str):
            text = self._PIDFile
        else:
            text = ""
        self.lineConfFile.setText(text)
        self.fun_PIDFile_read()

    def fun_useAutoPID(self, boolean):
        """set the variable for the softwareAutoPID
        emit signal to notify Thread
        store it in settings"""
        self._useAutoPID = boolean
        self.sig_useAutocheck.emit(boolean)
        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue("ITC_useAutoPID", int(boolean))
        del settings

    @ExceptionHandling
    def fun_PIDFile_send(self, dummy):
        """reaction to signal: ITC PID file: send and store permanently"""
        if isinstance(self._PIDFile, str):
            text = self._PIDFile
        else:
            text = ""
        self.sig_newFilePID.emit(text)

        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue("ITC_PIDFile", self._PIDFile)
        del settings
        self.fun_PIDFile_read()

    @ExceptionHandling
    def fun_PIDFile_read(self):
        try:
            with open(self._PIDFile) as f:
                self.textConfShow_current.setText(f.read())
        except OSError as e:
            self._logger.exception(e)
        except TypeError as e:
            self._logger.error(f" missing Filename! (TypeError: {e})")

    @ExceptionHandling
    def window_FileDialogOpen(self, test):
        # print(test)
        fname, __ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose PID configuration file", "c:\\", ".conf(*.conf)"
        )
        self.lineConfFile.setText(fname)
        self._PIDFile = fname
        # self.setValue('general', 'logfile_location', fname)

        try:
            with open(fname) as f:
                self.textConfShow.setText(f.read())
        except OSError as e:
            self._logger.exception(e)
        except TypeError as e:
            self._logger.error(f"missing Filename! (TypeError: {e})")


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
    # ITC_Instrumentadress = "ASRL6::INSTR"
    # form = ITCGUI(
    #     ui_file="itc503_main.ui",
    #     Name="ITC 503",
    #     identity="ITC",
    #     InstrumentAddress=ITC_Instrumentadress,
    #     prometheus_port=8001,
    # )
    # form.show()
    # # print('date: ', dt.datetime.now(),
    # #       '\nstartup time: ', time.time() - a)
    # sys.exit(app.exec_())
