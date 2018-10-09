import time

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from LakeShore.LakeShore350 import LakeShore350
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

    sensor_names = ['Heater_Output_percentage',
    	'Heater_Output_mW',
    	'Temp_K',
    	'Ramp_Rate_Status',
    	'Ramp_Rate',
    	'Input_Sensor',
    	'Sensor_1_K',
    	'Sensor_2_K',
    	'Sensor_3_K',
    	'Sensor_4_K',
    	'Loop_P_Param',
    	'Loop_I_Param',
    	'Loop_D_Param',
    	'Heater_Range']

    sensor_values = [None] * 20 # 10 of 20 used

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        # here the class instance of the LakeShore should be handed
        # try: 
        self.LakeShore350 = LakeShore350(InstrumentAddress=InstrumentAddress)
        # except VisaIOError as e: 
        #     self.sig_assertion.emit('running in control: {}'.format(e))

		self.Temp_K_value = 3
#		self.Heater_mW_value = 0
		self.Ramp_Rate_value = 0
		self.Input_value = 1
		self.LoopP_value = 0
		self.LoopI_value = 0
		self.LoopD_value = 0

		self.Upper_Bound_value = 300
		"""proper P, I, D values needed
		"""
		self.ZoneP_value
		self.ZoneI_value
		self.ZoneD_value
		self.Mout_value = 50
		self.Zone_Range_value = 2
		self.Zone_Rate_value = 1


        """sets Heater power to 994,05 mW
        """
        self.configHeater()
        self.configTempLimit()
        self.setControlLoopZone()

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
            sensor_values[0] = self.LakeShore350.HeaterOutputQuery(1)[0]
            sensor_values[1] = self.sensor_values[0]*994.5
            sensor_values[2] = self.LakeShore350.ControlSetpointQuery(1)[0]
            sensor_values[3] = self.LakeShore350.ControlSetpointRampParameterQuery(1)[0]
            sensor_values[4] = self.LakeShore350.ControlSetpointRampParameterQuery(1)[1]
            sensor_values[5] = self.LakeShore350.OutputModeQuery(1)[1]
            temp_list = self.LakeShore350.KelvinReadingQuery(0)
            sensor_values[6] = temp_list[0]
            sensor_values[7] = temp_list[1]
            sensor_values[8] = temp_list[2]
            sensor_values[9] = temp_list[3]
            temp_list2 = self.LakeShore350.ControlLoopPIDValuesQuery(1)[0]
            sensor_values[10] = temp_list2[0]
            sensor_values[11] = temp_list2[1]
            sensor_values[12] = temp_list2[2]
            sensor_values[13] = self.HeaterRangeQuery(1)[0]
 

            # print(dict(zip(self.sensor_names,self.sensor_values)))
            self.sig_Infodata.emit(deepcopy(dict(zip(self.sensor_names,self.sensor_values))))

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


    def configSensor(self):
        """configure sensor inputs to Cerox
        """
        for i in ['A','B','C','D']:
            self.LakeShore350.InputTypeParameterCommand(i,3,1,0,1,1,0)

    def configHeater(self):
    	"""configure heater output
    	HeaterSetupCommand(1,2,0,0.141,2) sets Output 1, Heater_Resistance to 50 Ohm, enables Custom Maximum Heater Output Current of 0.141 and configures the heater output displays to show in power.
    	"""
    	self.LakeShore350.HeaterSetupCommand(1,2,0,0.141,2)

    def configTempLimit(self):
        """sets temperature limit
        """
        for i in ['A','B','C','D']:
           self.LakeShore350.TemperatureLimitCommand(i,400.)

    @pyqtSlot()
    def setTemp_K(self):
        """take value Temp_K and uses it on function ControlSetpointCommand to set desired temperature.
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
    def setInput(self, Input_value):
    	"""(1,1,value,1) configure Output 1 for Closed Loop PID, using Input "value" and set powerup enable to On.
    	"""
        try:
            self.LakeShore350.OutputModeCommand(1,1,self.Input_value,1)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])


    @pyqtSlot()
    def setLoopP_Param(self):
    	try:
    		self.LakeShore350.ControlLoopPIDValuesCommand(1, self.LoopP_value, sensor_values[11], sensor_values[12])
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setLoopI_Param(self):
    	try:
    		self.LakeShore350.ControlLoopPIDValuesCommand(1, sensor_values[10], self.LoopI_value, sensor_values[12])
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setLoopD_Param(self):
    	try:
    		self.LakeShore350.ControlLoopPIDValuesCommand(1, sensor_values[10], sensor_values[11], self.LoopD_value)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])


    @pyqtSlot()
    def setHeater_Range(self):
    	"""set Heater Range for Output 1
    	"""
    	try:
    		self.LakeShore350.HeaterRangeCommand(1, self.Heater_Range_value)
    	except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setControlLoopZone(self):

    	try:
    		self.LakeShore350.ControlLoopZoneTableParameterCommand(1, 1, self.Upper_Bound_value, self.ZoneP_value, self.ZoneI_value, self.ZoneD_value, self.Mout_value, self.Zone_Range_value, 1, self.Zone_Rate_value)
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
    def gettoset_LoopP_Param(self,value):
    	self.LoopP_value = value
    @pyqtSlot()
    def gettoset_LoopI_Param(self,value):
    	self.LoopI_value = value
    @pyqtSlot()
    def gettoset_LoopD_Param(self,value):
    	self.LoopD_value = value
    @pyqtSlot()
    def gettoset_Ramp_Rate_K(self,value):
        self.Ramp_Rate_value = value

    @pyqtSlot()
    def gettoset_Upper_Bound(self,value):
    	self.Upper_Bound_value = value
    @pyqtSlot()
    def gettoset_ZoneP_Param(self,value):
    	self.ZoneP_value = value
    @pyqtSlot()
    def gettoset_ZoneI_Param(self,value):
    	self.ZoneI_value = value
    @pyqtSlot()
    def gettoset_ZoneD_Param(self,value):
    	self.ZoneD_value = value
    @pyqtSlot()
    def gettoset_ZoneMout(self,value):
    	self.Mout_value = value
    @pyqtSlot()
    def gettoset_Zone_Range(self,value):
    	self.Zone_Range_value = value
    @pyqtSlot()
    def gettoset_Zone_Rate(self,value):
    	self.Zone_Rate_value = value


#    def gettoset_Heater_Range(self,value):
#    	self.Heater_Range_value = value

