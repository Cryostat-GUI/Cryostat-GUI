
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
	sig_Needle = pyqtSignal(int)

	def __init__(self, ITC):
		QThread.__init__(self)

		# here the class instance of the ITC should be handed
		self.ITC = ITC

		self.__abort = False

	@pyqtSlot() # int
	def run(self):
		app.processEvents()
		while True:
			# time.sleep(1)
			Needle_value = self.ITC.getValue(7)
			self.sig_Needle.emit(Needle_value)
			time.sleep(2)

	def setNeedle(value):
		if (0 <= value <= 100):
			ITC.setGasOutput(value)

	def setControl(unlocked=1, remote=1):
		ITC.setControl(unlocked=unlocked, remote=remote)

	def setTemperature(temperature):
		ITC.setTemperature(temperature)



class NeedleValve_Window(QtWidgets.QMainWindow, needle_ui.Ui_NeedleControl):
	def __init__(self, ITC, **kwargs):
		super().__init__(**kwargs)
		self.setupUi(self)

		self.ITC = ITC
		self.liste = []
		getNeedle = ITC_Updater(ITC)
		thread = QThread()
		self.liste.append((getNeedle, thread))
		getNeedle.moveToThread(thread)

		getNeedle.sig_step.connect(self.setNeedleIndicator)

		thread.started.connect(getNeedle.run)
		thread.start()

		self.Slider_Needle.valueChanged['int'].connect(self.setNeedle)
	
	def setNeedle(self, value):
		if (0 <= value <= 100): 
			ITC.setGasOutput(value)

	@pyqtSlot(int)
	def setNeedleIndicator(self, value):
		self.NeedleValve_bar.setValue(value)







