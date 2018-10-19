
import time

# from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
# from PyQt5.uic import loadUi

from .Drivers.itc503 import itc503
from pyvisa.errors import VisaIOError

from copy import deepcopy

# from util import AbstractThread
from util import AbstractLoopThread


class ITC_Updater(AbstractLoopThread):

    """This is the worker thread, which updates all instrument data of the self.ITC 503.

        For each self.ITC503 function (except collecting data), there is a wrapping method,
        which we can call by a signal, from the main thread. This wrapper sends
        the corresponding value to the device.

        There is a second method for all wrappers, which accepts
        the corresponding value, and stores it, so it can be sent upon acknowledgment

        The information from the device is collected in regular intervals (method "running"),
        and subsequently sent to the main thread. It is packed in a dict,
        the keys of which are displayed in the "sensors" dict in this class.
    """

    sig_Infodata = pyqtSignal(dict)
    # sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)


    sensors = dict(
            set_temperature = 0,
            Sensor_1_K = 1,
            Sensor_2_K = 2,
            Sensor_3_K = 3,
            temperature_error = 4,
            heater_output_as_percent = 5,
            heater_output_as_voltage = 6,
            gas_flow_output = 7,
            proportional_band = 8,
            integral_action_time = 9,
            derivative_action_time = 10)

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        # here the class instance of the ITC should be handed
        self.ITC = itc503(InstrumentAddress=InstrumentAddress)


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

        self.setControl()
        self.interval = 0.05
        # self.__isRunning = True


    # @control_checks
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
        for key in self.sensors.keys():
            try:

                value = self.ITC.getValue(self.sensors[key])
                data[key] = value
            except AssertionError as e_ass:
                self.sig_assertion.emit(e_ass.args[0])
                data[key] = None
            except VisaIOError as e_visa:
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    self.sig_visatimeout.emit()
                    self.read_buffer()
                    data[key] = None
                else: 

                    self.sig_visaerror.emit(e_visa.args[0])
        self.sig_Infodata.emit(deepcopy(data))


    # def control_checks(func):
    #     @functools.wraps(func)
    #     def wrapper_control_checks(*args, **kwargs):
    #         pass

    def read_buffer(self):
        try:
            return self.ITC.read()
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                pass

    @pyqtSlot(int)
    def set_delay_sending(self, delay):
        self.ITC.set_delay_measuring(delay)



    @pyqtSlot()
    def setNeedle(self):
        """class method to be called to set Needle
            this is necessary, so it can be invoked by a signal
            self.gasoutput between 0 and 100 %
        """
        value = self.set_GasOutput
        try:
            if 0 <= value <= 100:
                self.ITC.setGasOutput(value)
            else:
                raise AssertionError('ITC_control: setNeedle: Gas output setting must be between 0 and 100%!')
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setControl(self):
        """class method to be called to set Control
            this is to be invoked by a signal
        """
        try:
            self.ITC.setControl(self.control_state)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setTemperature(self):
        """class method to be called to set Temperature
            this is to be invoked by a signal
        """
        try:
            self.ITC.setTemperature(self.set_temperature)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setProportional(self):
        """class method to be called to set Proportional
            this is to be invoked by a signal

            prop: Proportional band, in steps of 0.0001K.
        """
        try:
            self.ITC.setProportional(self.set_prop)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setIntegral(self):
        """class method to be called to set Integral
            this is to be invoked by a signal

            integral: Integral action time, in steps of 0.1 minute.
                        Ranges from 0 to 140 minutes.
        """
        try:
            self.ITC.setIntegral(self.set_integral)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setDerivative(self):
        """class method to be called to set Derivative
            this is to be invoked by a signal

            derivative: Derivative action time.
            Ranges from 0 to 273 minutes.
        """
        try:
            self.ITC.setDerivative(self.set_derivative)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setHeaterSensor(self, value):
        """class method to be called to set HeaterSensor
            this is to be invoked by a signal

            sensor: Should be 1, 2, or 3, corresponding to
            the heater on the front panel.
        """
        self.set_sensor = value
        try:
            self.ITC.setHeaterSensor(self.set_sensor)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setHeaterOutput(self):
        """class method to be called to set HeaterOutput
            this is to be invoked by a signal

            heater_output: Sets the percent of the maximum
                        heater output in units of 0.1%.
                        Min: 0. Max: 999.
        """
        try:
            self.ITC.setHeaterOutput(self.set_heater_output)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setGasOutput(self):
        """class method to be called to set GasOutput
            this is to be invoked by a signal

            gas_output: Sets the percent of the maximum gas
                    output in units of 1%.
                    Min: 0. Max: 99.
        """
        try:
            self.ITC.setGasOutput(self.set_gas_output)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setAutoControl(self, value):
        """class method to be called to set AutoControl
            this is to be invoked by a signal

        Value:Status map
            0: heater manual, gas manual
            1: heater auto  , gas manual
            2: heater manual, gas auto
            3: heater auto  , gas auto

        """
        self.set_auto_manual = value
        try:
            self.ITC.setAutoControl(self.set_auto_manual)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setSweeps(self):
        """class method to be called to set Sweeps
            this is to be invoked by a signal
        """
        try:
            self.ITC.setSweeps(self.sweep_parameters)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])


    @pyqtSlot(int)
    def gettoset_Control(self, value):
        """class method to receive and store the value to set the Control status
            later on, when the command to enforce the value is sent
        """
        self.control_state = value

    @pyqtSlot(float)
    def gettoset_Temperature(self, value):
        """class method to receive and store the value to set the temperature
            later on, when the command to enforce the value is sent
        """
        self.set_temperature = value

    @pyqtSlot()
    def gettoset_Proportional(self, value):
        """class method to receive and store the value to set the proportional (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_prop = value

    @pyqtSlot()
    def gettoset_Integral(self, value):
        """class method to receive and store the value to set the integral (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_integral = value

    @pyqtSlot()
    def gettoset_Derivative(self, value):
        """class method to receive and store the value to set the derivative (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_derivative = value

    @pyqtSlot()
    def gettoset_HeaterOutput(self, value):
        """class method to receive and store the value to set the heater_output
            later on, when the command to enforce the value is sent
        """
        self.set_heater_output = value

    @pyqtSlot()
    def gettoset_GasOutput(self, value):
        """class method to receive and store the value to set the gas_output
            later on, when the command to enforce the value is sent
        """
        self.set_gas_output = value

    @pyqtSlot()
    def gettoset_Sweeps(self, value):
        """class method to receive and store the value to for the sweep_parameters
            to set them later on, when the command to enforce the value is sent
        """
        self.sweep_parameters = value


    # @pyqtSlot()
    # def gettoset_HeaterSensor(self, value):
    #     """class method to receive and store the value to set the sensor
    #         later on, when the command to enforce the value is sent
    #     """
    #     self.set_sensor = value

    # @pyqtSlot()
    # def gettoset_AutoControl(self, value):
    #     """class method to receive and store the value to set the auto_manual
    #         later on, when the command to enforce the value is sent
    #     """
    #     self.set_auto_manual = value


