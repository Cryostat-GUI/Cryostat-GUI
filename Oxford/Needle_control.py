

import sys
import time


from labdrivers.oxford.itc503 import itc503 
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

import needle_ui 


ITC = itc503('COM6')
ITC.setControl(unlocked=1, remote=1)
time.sleep(1)


class Needle_Updater(QObject):

	sig_step = pyqtSignal(int)

	def __init__(self, ITC):
		QThread.__init__(self)
		self.ITC = ITC

	@pyqtSlot() # int
	def run(self):
		app.processEvents()
		while True:
			# time.sleep(1)
			Needle_value = self.ITC.getValue(7)
			self.sig_step.emit(Needle_value)	
			time.sleep(2)




class NeedleValve_Window(QtWidgets.QMainWindow, needle_ui.Ui_NeedleControl):
	def __init__(self, ITC, **kwargs):
		super().__init__(**kwargs)
		self.setupUi(self)

		self.ITC = ITC
		self.liste = []
		getNeedle = Needle_Updater(ITC)
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



if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	form = NeedleValve_Window(ITC)
	form.show()
	sys.exit(app.exec_())
