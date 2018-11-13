import time

# from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
# from PyQt5.uic import loadUi

from Keithley.Keithley6221 import Keithley6221
from pyvisa.errors import VisaIOError

from copy import deepcopy

# from util import AbstractThread
from util import AbstractEventhandlingThread


class Keithley6221_Updater(AbstractEventhandlingThread):
    """This is the worker thread, which updates all instrument data of a Keithely 6221

        For each method of the device class (except collecting data), there is a wrapping method,
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

    sensors =  dict(
    	Current_A = None,
#        Start_Current = None,
#        Step_Current = None,
#        Stop_Current = None
        )


    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        self.Keithley6221 = Keithley6221(InstrumentAddress=InstrumentAddress)

        self.Current_A_value = 0
        self.OutputOn = self.getstatus()  # 0 == OFF, 1 == ON
#        self.Start_Current_value = 0
#        self.Step_Current_value = 0
#        self.Stop_Current_value = 0


#        self.delay1 = 1
#        self.delay = 0.0
      # self.setControl()
      # self.__isRunning = True

#        self.Keithley6221.ConfigSourceFunctions()

    # @control_checks
#     def running(self):
#         """Try to extract all current data from the ITC, and emit signal, sending the data

#             self.delay2 should be at at least 0.4 to ensure relatively error-free communication
#             with ITC over serial RS-232 connection. (this worked on Benjamin's PC, to be checked
#             with any other PC, so errors which come back are "caught", or communication is set up
#             in a way no errors occur)

#         """
#         try:
#             self.sensors['Current_A'] = self.Keithley6221.measureVoltage()
# #            self.sensors['Start_Current'] = self.Start_Current_value
# #            self.sensors['Step_Current'] = self.Step_Current_value
# #            self.sensors['Stop_Current'] = self.Stop_Current_value

#             self.sig_Infodata.emit(deepcopy(sensors))

#             # time.sleep(self.delay1)
#         except AssertionError as e_ass:
#             self.sig_assertion.emit(e_ass.args[0])
#         except VisaIOError as e_visa:
#             if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
#                 self.sig_visatimeout.emit()
#             else:
#                 self.sig_visaerror.emit(e_visa.args[0])


#    def setCurrent(self):
#        """Utilizes @property to set the value for the voltage and send the command to the device.
#        """
#        try:
#            self.Keithley6221.voltage = self.Current_A_value
#        except AssertionError as e_ass:
#            self.sig_assertion.emit(e_ass.args[0])
#        except VisaIOError as e_visa:
#            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
#                self.sig_visatimeout.emit()
#            else:
#                self.sig_visaerror.emit(e_visa.args[0])

    def getCurrent_A(self):
        return self.Current_A_value

    @pyqtSlot()
    def disable(self):
        try:
            self.Keithley6221.disable()
            self.OutputOn = self.Keithley6221.getstatus()[0]
        except TypeError as e_type:
            self.sig_assertion.emit(e_type.args[0])
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def enable(self):
        try:
            self.Keithley6221.enable()
            self.OutputOn = self.Keithley6221.getstatus()[0]
        except TypeError as e_type:
            self.sig_assertion.emit(e_type.args[0])
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def getstatus(self):
        try:
            return int(self.Keithley6221.getstatus()[0])
        except TypeError as e_type:
            self.sig_assertion.emit(e_type.args[0])
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setCurrent_A(self):
        try:
            self.Keithley6221.setCurrent(self.Current_A_value)
        except TypeError as e_type:
            self.sig_assertion.emit(e_type.args[0])            
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setSweep(self):
        try:
            self.Keithley6221.SetupSweet(self.Start_Current_value, self.Step_Current_value, self.Stop_Current_value)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def startSweep(self):
        try:
            self.Keithley6221.StartSweep()
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot(float)
    def gettoset_Current_A(self, value):
        self.Current_A_value = value

    @pyqtSlot(float)
    def gettoset_Start_Current(self, value):
        self.Start_Current_value = value

    @pyqtSlot(float)
    def gettoset_Step_Current(self, value):
        self.Step_Current_value = value

    @pyqtSlot(float)
    def gettoset_Stop_Current(self, value):
        self.Stop_Current_value = value

