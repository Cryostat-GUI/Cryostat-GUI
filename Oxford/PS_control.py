import sys
import time


from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from pyvisa.errors import VisaIOError


class PS_Updater(QObject):
	"""docstring for PS_Updater"""

    sig_Infodata = pyqtSignal(dict)
    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)


	def __init__(self, PS):
		super().__init__()
		QThread.__init__(self)

		self.PS = PS


	@pyqtSlot()
    def work(self):
    	"""worker method of the power supply controlling thread"""
    	try:
    		pass




	    except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])
        except AssertionError as assertion: 
            self.sig_assertion.emit(assertion.args[0])




	@pyqtSlot(int)
	def setControl(self, control_state):
		"""method to set the control for local/remote"""
        try:
            self.PS.setControl(control_state)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])
		



	@pyqtSlot()
	def readField(self): 
		'''method to readField - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def readFieldSetpoint(self): 
		'''method to readFieldSetpoint - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def readFieldSweepRate(self): 
		'''method to readFieldSweepRate - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def setActivity(self): 
		'''method to setActivity - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def setHeater(self): 
		'''method to setHeater - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def setFieldSetpoint(self): 
		'''method to setFieldSetpoint - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def setFieldSweepRate(self): 
		'''method to setFieldSweepRate - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def setDisplay(self): 
		'''method to setDisplay - this can be invoked by a signal'''
		pass

	@pyqtSlot()
	def waitForField(self): 
		'''method to waitForField - this can be invoked by a signal'''
		pass