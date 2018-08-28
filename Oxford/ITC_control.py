
import sys
import time


from labdrivers.oxford.itc503 import itc503 
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from pyvisa.errors import VisaIOError

ITC = itc503()


class ITC_Updater(QObject):

    """This is the worker thread, which updates all instrument data of the ITC 503.

        For each itc503 function (except collecting data), there is a wrapping method,
        which we can call by a signal, from the main thread. This wrapper sends
        the corresponding value to the device. 

        There is a second method for all wrappers, which accepts
        the corresponding value, and stores it, so it can be sent upon acknowledgment 

        The information from the device is collected in regular intervals (method "work"),
        and subsequently sent to the main thread. It is packed in a dict,
        the keys of which are displayed in the "sensors" dict in this class. 
    """

    sig_Infodata = pyqtSignal(dict)
    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)

    sensors = dict(
            set_temperature = 0,
            sensor_1_temperature = 1,
            sensor_2_temperature = 2,
            sensor_3_temperature = 3,
            temperature = 4,
            heater_output_as_percent = 5,
            heater_output_as_voltage = 6,
            gas_flow_output = 7,
            proportional_band = 8,
            integral_action_time = 9,
            derivative_action_time = 10)

    def __init__(self, ITC):
        QThread.__init__(self)

        # here the class instance of the ITC should be handed
        self.ITC = ITC
        self.__abort = False

        # TODO need initialisation for all the parameters! 

    @pyqtSlot() # int
    def work(self):
        """class method which is working all the time while the thread is running
            
        """
        app.processEvents()
        while True:
            # time.sleep(1)
            try: 
                data = dict()
                # get key-value pairs of the sensors dict, 
                # so I can then transmit one single dict
                for key, idx_sensor in sensors.items(): 
                    data[key] = self.ITC.getValue(idx_sensor)
                    time.sleep(0.1)
                self.sig_Infodata.emit(data)
                time.sleep(1)

            except VisaIOError as e_vsia:   
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                    self.sig_visatimeout.emit()
                else: 
                    self.sig_visaerror.emit(e.args[0])



    def setNeedle(self):
        """class method to be called to set Needle
            this is necessary, so it can be invoked by a signal
        """
        value = self.set_GasOutput
        try:
            if (0 <= value <= 100):
                ITC.setGasOutput(value)
            else:
                raise AssertionError('Gas output setting must be between 0 and 100%!')
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setControl(self):
        """class method to be called to set Control
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setControl(unlocked=self.control_unlocked, remote=self.control_remote)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setTemperature(self):
        """class method to be called to set Temperature
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setTemperature(self.set_temperature)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setProportional(self):
        """class method to be called to set Proportional
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setProportional(self.set_prop)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setIntegral(self):
        """class method to be called to set Integral
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setIntegral(self.set_integral)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setDerivative(self):
        """class method to be called to set Derivative
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setDerivative(self.set_derivative)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setHeaterSensor(self):
        """class method to be called to set HeaterSensor
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setHeaterSensor(self.set_sensor)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setHeaterOutput(self):
        """class method to be called to set HeaterOutput
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setHeaterOutput(self.set_heater_output)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setGasOutput(self):
        """class method to be called to set GasOutput
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setGasOutput(self.set_gas_output)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setAutoControl(self):
        """class method to be called to set AutoControl
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setAutoControl(self.set_auto_manual)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    def setSweeps(self):
        """class method to be called to set Sweeps
            this is necessary, so it can be invoked by a signal
        """
        try:
            ITC.setSweeps(self.sweep_parameters)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])


    def gettoset_Temperature(self, value):
        """class method to receive and store the value to set the temperature
            later on, when the command to enforce the value is sent
        """
        self.set_temperature = value

    def gettoset_Proportional(self, value):
        """class method to receive and store the value to set the proportional (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_prop = value

    def gettoset_Integral(self, value):
        """class method to receive and store the value to set the integral (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_integral = value

    def gettoset_Derivative(self, value):
        """class method to receive and store the value to set the derivative (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_derivative = value

    def gettoset_HeaterSensor(self, value):
        """class method to receive and store the value to set the sensor
            later on, when the command to enforce the value is sent
        """
        self.set_sensor = value

    def gettoset_HeaterOutput(self, value):
        """class method to receive and store the value to set the heater_output
            later on, when the command to enforce the value is sent
        """
        self.set_heater_output = value

    def gettoset_GasOutput(self, value):
        """class method to receive and store the value to set the gas_output
            later on, when the command to enforce the value is sent
        """
        self.set_gas_output = value

    def gettoset_AutoControl(self, value):
        """class method to receive and store the value to set the auto_manual
            later on, when the command to enforce the value is sent
        """
        self.set_auto_manual = value

    def gettoset_Sweeps(self, value):
        """class method to receive and store the value to for the sweep_parameters
            to set them later on, when the command to enforce the value is sent
        """
        self.sweep_parameters = value





class NeedleValve_Window(QtWidgets.QMainWindow, needle_ui.Ui_NeedleControl):
    
    sig_arbitrary = pyqtSignal()

    def __init__(self, ITC, **kwargs):
        super().__init__(**kwargs)
        self.setupUi(self)

        self.ITC = ITC
        self.liste = []
        self.getInfodata = ITC_Updater(ITC)
        self.thread = QThread()
        self.liste.append((self.getInfodata, self.thread))
        self.getInfodata.moveToThread(self.thread)

        self.getInfodata.sig_GasOutput.connect(self.setNeedleIndicator)

        self.thread.started.connect(self.getInfodata.work)
        self.thread.start()

        self.Slider_Needle.valueChanged['int'].connect(self.setNeedle)
    
        self.Something_temperature.valueChanged['int'].connect(self.send_data)

    # this is meant as an example, which should be tested, and then possibly followed! 
    def send_data(self, data:int):
        self.sig_arbitrary.connect(self.getInfodata.gettoset_Temperature)
        self.sig_arbitrary.emit(data)

        

    # def setNeedle(self, value):
    #   if (0 <= value <= 100):
    #       ITC.setGasOutput(value)

    # @pyqtSlot(int)
    # def setNeedleIndicator(self, value):
    #   self.NeedleValve_bar.setValue(value)


