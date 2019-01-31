"""Module containing a class to run a (Oxford Instruments) ITC 503 Intelligent Temperature Controller in a pyqt5 application

Classes:
    ITC_Updater: a class for interfacing with a ITC 503 Temperature Controller
            inherits from AbstractLoopThread
                there, the looping behaviour of this thread is defined
Author(s):
    bklebel (Benjamin Klebel)
"""
from PyQt5.QtCore import pyqtSlot

import Oxford
from pyvisa.errors import VisaIOError

from copy import deepcopy
from importlib import reload
# import time

from util import AbstractLoopThread
from util import ExceptionHandling


class ITC_Updater(AbstractLoopThread):
    """Updater class to update all instrument data of the Intelligent Temperature Controller (ITC) 503.

    For each ITC503 function (except collecting data), there is a wrapping method,
    which we can call by a signal, from the main thread. This wrapper sends
    the corresponding value to the device.

    There is a second method for all wrappers, which accepts
    the corresponding value, and stores it, so it can be sent upon acknowledgment

    The information from the device is collected in regular intervals (method "running"),
    and subsequently sent to the main thread. It is packed in a dict,
    the keys of which are displayed in the "sensors" dict in this class.
    """

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
        derivative_action_time=10)

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)
        global Oxford
        itc503 = reload(Oxford.itc503).itc503
        # here the class instance of the ITC should be handed
        self.ITC = itc503(InstrumentAddress=InstrumentAddress)
        self.__name__ = 'ITC_Updater ' + InstrumentAddress

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
        self.sweep_ramp = 0
        self.sweep_first = False

        self.setControl()
        # self.ITC.SweepStop()
        self.interval = 0.05
        # self.__isRunning = True

    # @control_checks
    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the ITC, and emit signal, sending the data

            self.delay2 should be at at least 0.4 to ensure relatively error-free communication
            with ITC over serial RS-232 connection. (this worked on Benjamin's PC, to be checked
            with any other PC, so errors which come back are "caught", or communication is set up
            in a way no errors occur)

        """

        data = dict()
        # get key-value pairs of the sensors dict,
        # so I can then transmit one single dict
        # starttime = time.time()
        # data['status'] = self.read_status()
        for key in self.sensors.keys():
            try:

                value = self.ITC.getValue(self.sensors[key])
                data[key] = value
            except AssertionError as e_ass:
                self.sig_assertion.emit(e_ass.args[0])
                data[key] = None
            except VisaIOError as e_visa:
                if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
                    self.sig_visatimeout.emit()
                    self.ITC.clear_buffers()
                    data[key] = None
                else:

                    self.sig_visaerror.emit(e_visa.args[0])
        # print('retrieving', time.time()-starttime, data['Sensor_1_K'])
        self.sig_Infodata.emit(deepcopy(data))

    # def control_checks(func):
    #     @functools.wraps(func)
    #     def wrapper_control_checks(*args, **kwargs):
    #         pass

    # def read_buffer(self):
    #     """read all the possibly full buffer of the instrument"""
    #     try:
    #         return self.ITC.read()
    #     except VisaIOError as e_visa:
    #         if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
    #             pass

    @ExceptionHandling
    def read_status(self, run=True):
        """read the device status"""
        self.device_status = self.ITC.getStatus(run)
        return self.device_status

    # @pyqtSlot(int)
    # def set_delay_sending(self, delay):
    #     self.ITC.set_delay_measuring(delay)

    @pyqtSlot(bool)
    @ExceptionHandling
    def setSweep(self, setpoint_temp, rate):
        # with self.lock:
        setpoint_now = self.ITC.getValue(0)
        # print('setpoint now = ', setpoint_now)
        if rate == 0:
            sweep_time = 0.1
            # print('rate was zero!')
        else:
            sweep_time = abs(setpoint_now - setpoint_temp) / rate
            if sweep_time < 0.1:
                # print('sweeptime below 0.1: ', sweep_time)
                sweep_time = 0.1
        sp = {str(z): dict(set_point=setpoint_temp,
                           hold_time=0,
                           sweep_time=0) for z in range(1, 17)}
        sp.update({str(1): dict(set_point=setpoint_now,
                                hold_time=0,
                                sweep_time=0),
                   str(2): dict(set_point=setpoint_temp,
                                hold_time=0,
                                sweep_time=sweep_time),
                   str(15): dict(set_point=setpoint_temp,
                                 hold_time=0,
                                 sweep_time=0),
                   str(16): dict(set_point=setpoint_temp,
                                 hold_time=0,
                                 sweep_time=0.1)})
        self.sweep_parameters = sp
        # print('setting sweep to', self.sweep_parameters)
        self.ITC.setSweeps(self.sweep_parameters)
        # self.ITC.getValue(0)
        # print('sweep table read from device:')
        # for x in self.ITC.readSweepTable():
            # print(x)

    @pyqtSlot(float)
    @ExceptionHandling
    def setSweepStatus(self, bools):
        self.sweep_running = bools
        # print('set sweep status to', bools)
        with self.lock:
            # print('sweepstatus: I locked the thread!')
            if not bools:
                # print('sweepstatus: stopping the sweep')
                self.checksweep()
                self.ITC.setTemperature(self.set_temperature)
        # print('sweepstatus: I unlocked the device')
        # if bools:
            # print('set the sweep status: ', bools)
        #     print('sweepstatus: set the temperature')
        #     self.setTemperature()

    @pyqtSlot(float)
    @ExceptionHandling
    def gettoset_sweepRamp(self, value):
        self.sweep_ramp = value
        # print('set sweep ramp to', value)

    @ExceptionHandling
    def checksweep(self):
        # print('checking sweep')
        status = self.read_status(run=False)
        # print(status)
        try:
            int(status['sweep'])
            status['sweep'] = bool(int(status['sweep']))
        except ValueError:
            status['sweep'] = True
        # print('sweep status: ', status['sweep'])
        if status['sweep'] or self.sweep_first:
            # print('setTemp: sweep running, stopping sweep')
            self.ITC.SweepStop()
            self.sweep_first = False
        # else:
            # print('I did not see a running sweep!',
                  # self.device_status['sweep'])
        # print('sweep was/is running: ', self.device_status['sweep'])

    @pyqtSlot()
    @ExceptionHandling
    def setTemperature(self):
        """set Temperature of the instrument

        """
        with self.lock:
            self.checksweep()
            if not self.sweep_running:
                self.ITC.setTemperature(self.set_temperature)
                # self.set_temperature = temp
            else:
                # print('setTemp: setting sweep.')
                self.setSweep(self.set_temperature, self.sweep_ramp)
                # print('starting sweep!')
                self.ITC.SweepStart()
                self.ITC.getValue(0)

    @pyqtSlot(float)
    @ExceptionHandling
    def setSweepRamp(self):
        with self.lock:
            if self.sweep_running:
                self.checksweep()
                self.setSweep(self.set_temperature, self.sweep_ramp)
                self.ITC.SweepStart()
                self.ITC.getValue(0)

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

    @pyqtSlot()
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

    @pyqtSlot(float)
    def gettoset_Temperature(self, value):
        """receive and store the value to set the temperature"""
        self.set_temperature = value
        # print('got a new temp:', value)

    @pyqtSlot()
    def gettoset_Proportional(self, value):
        """receive and store the value to set the proportional (PID)"""
        self.set_prop = value

    @pyqtSlot()
    def gettoset_Integral(self, value):
        """receive and store the value to set the integral (PID)"""
        self.set_integral = value

    @pyqtSlot()
    def gettoset_Derivative(self, value):
        """receive and store the value to set the derivative (PID)"""
        self.set_derivative = value

    @pyqtSlot()
    def gettoset_HeaterOutput(self, value):
        """receive and store the value to set the heater_output"""
        self.set_heater_output = value

    @pyqtSlot()
    def gettoset_GasOutput(self, value):
        """receive and store the value to set the gas_output"""
        self.set_gas_output = value
