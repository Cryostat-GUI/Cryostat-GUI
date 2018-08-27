
import sys
import time


from labdrivers.oxford.itc503 import itc503 
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


ITC = itc503()


class ITC_Updater(QObject):

	"""This is the worker thread, which updates all instrument data of the ITC 503.

		for each itc503 function, we need a wrapping method,
		which we can call by a signal, from the main thread
	"""
	sig_Infodata = pyqtSignal(int)
	sensors = dict(
			SET_TEMPERATURE = 0,
	        SENSOR_1_TEMPERATURE = 1,
	        SENSOR_2_TEMPERATURE = 2,
	        SENSOR_3_TEMPERATURE = 3,
	        TEMPERATURE = 4,
	        HEATER_output_as_percent = 5,
	        HEATER_output_as_voltage = 6,
			GAS_FLOW_output = 7,
			PROPORTIONAL_BAND = 8,
			INTEGRAL_ACTION_TIME = 9,
			DERIVATIVE_ACTION_TIME = 10)

	def __init__(self, ITC):
		QThread.__init__(self)

		# here the class instance of the ITC should be handed
		self.ITC = ITC
		self.__abort = False

		# TODO need initialisation for all the parameters! 

	@pyqtSlot() # int
	def work(self):
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
			except AssertionError as assertion:
				pass

			# except Timeout error from visa as timeout: - check the error!  
			# 	pass 



	def setNeedle(self):
		"""class method to be called to set Needle
			this is necessary, so it can be invoked by a signal"""
		value = self.set_GasOutput
		if (0 <= value <= 100):
			ITC.setGasOutput(value)

	def setControl(self):
		"""class method to be called to set Control
			this is necessary, so it can be invoked by a signal"""
		ITC.setControl(unlocked=self.control_unlocked, remote=self.control_remote)

	def setTemperature(self):
		"""class method to be called to set Temperature
			this is necessary, so it can be invoked by a signal"""
		ITC.setTemperature(self.set_temperature)

	def setProportional(self):
		"""class method to be called to set Proportional
			this is necessary, so it can be invoked by a signal"""
		ITC.setProportional(self.set_prop)

    def setIntegral(self):
    	"""class method to be called to set Integral
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setIntegral(self.set_integral)

    def setDerivative(self):
    	"""class method to be called to set Derivative
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setDerivative(self.set_derivative)

    def setHeaterSensor(self):
    	"""class method to be called to set HeaterSensor
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setHeaterSensor(self.set_sensor)

    def setHeaterOutput(self):
    	"""class method to be called to set HeaterOutput
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setHeaterOutput(self.set_heater_output)

    def setGasOutput(self):
    	"""class method to be called to set GasOutput
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setGasOutput(self.set_gas_output)

    def setAutoControl(self):
    	"""class method to be called to set AutoControl
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setAutoControl(self.set_auto_manual)

    def setSweeps(self):
    	"""class method to be called to set Sweeps
	    	this is necessary, so it can be invoked by a signal"""
	    ITC.setSweeps(self.sweep_parameters)


	def gettoset_Temperature(self, value):
		"""class method to receive and store the value to set the temperature
			later on, when the command to enforce the value is sent
		"""
		self.set_temperature = value

	def gettoset_Proportional(self, value):
		"""class method to receive and store the value to set the prop
			later on, when the command to enforce the value is sent
		"""
		self.set_prop = value

	def gettoset_Integral(self, value):
		"""class method to receive and store the value to set the integral
			later on, when the command to enforce the value is sent
		"""
		self.set_integral = value

	def gettoset_Derivative(self, value):
		"""class method to receive and store the value to set the derivative
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

	def send_data(self, data:int):
		self.sig_arbitrary.connect(self.getInfodata.gettoset_Temperature)
		self.sig_arbitrary.emit(data)

		

	# def setNeedle(self, value):
	# 	if (0 <= value <= 100):
	# 		ITC.setGasOutput(value)

	# @pyqtSlot(int)
	# def setNeedleIndicator(self, value):
	# 	self.NeedleValve_bar.setValue(value)


	# move these methods







