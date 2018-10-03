import time

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

import LakeShore350
from pyvisa.errors import VisaIOError

from copy import deepcopy

# from util import AbstractThread
from util import AbstractLoopThread


class LakeShore350_Updater(AbstractLoopThread):
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


#    sensors = dict(
#        Heater_Output_mW=0,
#        Temp_K=1,
#        Heater_mW=2,
#        Sensor_1_K=3,
#        Sensor_2_K=4,
#        Sensor_3_K=5,
#        Sensor_4_K=6)

    sensor_names = ['Heater_Output_percentage', 'Heater_Output_mW' 'Temp_K', 'Ramp_Rate', 'Sensor_1_K', 'Sensor_2_K', 'Sensor_3_K', 'Sensor_4_K']
    
    sensor_values = [None] * 8

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        # here the class instance of the LakeShore should be handed
        self.LakeShore350 = LakeShore350(InstrumentAddress=InstrumentAddress)

		self.Temp_K_value = 3
		self.Heater_mW_value = 0
		self.Ramp_Rate_value = 0
		self.Input_value = 1
        
        """sets Heater power to 994,05 mW
        """
		configHeater()
		configTempLimit

        self.delay1 = 1
        self.delay = 0.0
        # self.setControl()
        # self.__isRunning = True

    # @control_checks
    def running(self):
        """Try to extract all current data from the ITC, and emit signal, sending the data

            self.delay2 should be at at least 0.4 to ensure relatively error-free communication
            with ITC over serial RS-232 connection. (this worked on Benjamin's PC, to be checked 
            with any other PC, so errors which come back are "caught", or communication is set up 
            in a way no errors occur)

        """
        try:
            sensor_values[0] = self.LakeShore350.HeaterOutputQuery(1)
            sensor_values[1] = sensor_values[0]*994.5
            sensor_values[2] = self.lakeShore350.ControlSetpointQuery(1)
            sensor_values[3] = self.LakeShore350.ControlSetpointRampParameterQuery(1)
            temp_list = self.LakeShore350.KelvinReadingQuery(0)
            sensor_values[4] = temp_list[0]
            sensor_values[5] = temp_list[1]
            sensor_values[6] = temp_list[2]
            sensor_values[7] = temp_list[3]
            
            self.sig_Infodata.emit(deepcopy(dict(zip(sensor_names,sensor_values))))

            # time.sleep(self.delay1)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    # def control_checks(func):
    #     @functools.wraps(func)
    #     def wrapper_control_checks(*args, **kwargs):
    #         pass


    def configSensor():
        """configures sensor inputs to Cerox
        """
        for i in ['A','B','C','D']:
            self.LakeShore350.InputTypeParameterCommand(i,3,1,0,1,1,0)


    def configHeater():
    	"""configures heater output
    	HeaterSetupCommand(1,2,0,0.141,2) sets Output 1, Heater_Resistance to 50 Ohm, enables Custom Maximum Heater Output Current of 0.141 and configures the heater output displays to show in power.
    	"""
    	self.LakeShore350.HeaterSetupCommand(1,2,0,0.141,2)

    def configTempLimit():
        """sets temperature limit
        """
        for i in ['A','B','C','D']:
           self.LakeShore350.TemperatureLimitCommand(i,400.)


    @pyqtSlot()
    def setTemp_K(self):
        """takes value Temp_K and uses it on function ControlSetpointCommand to set desired temperature.
        """
        try:
            self.LakeShore350.ControlSetpointCommand(1,self.Temp_K_value)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])


#    @pyqtSlot()
#    def setHeater_mW(self):
#        try:
#            self.LakeShore350.HeaterSetupCommand
#        except AssertionError as e_ass:
#            self.sig_assertion.emit(e_ass.args[0])
#        except VisaIOError as e_visa:
#            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
#                self.sig_visatimeout.emit()
#            else: 
#                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setRamp_Rate_K(self):
    	try:
    		self.LakeShore350.ControlSetpointRampParameterCommand(1,1,self.Ramp_Rate_value)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setInput(self):
    	    	try:
    		self.LakeShore350.OutputModeCommand(1,1,Self.Input_value,1)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])





    @pyqtSlot()
    def gettoset_Temp_K(self,value):
        """class method to receive and store the value to set the temperature
        later on, when the command to enforce the value is sent
        """
        self.Temp_K_value = value


#    @pyqtSlot()
#    def gettoset_Heater_mW(self,value):
#        """class method to receive and store the value to set the temperature
#        later on, when the command to enforce the value is sent
#        """
#        self.Heater_mW_value = value


    @pyqtSlot()
    def gettoset_Ramp_Rate_K(self,value):
    	self.Ramp_Rate_value = value

    @pyqtSlot()
    def gettoset_Input(self,value)
    	self.Input_value = value
