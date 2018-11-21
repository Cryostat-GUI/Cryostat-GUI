
# from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
# from PyQt5.uic import loadUi

from Keithley.Keithley6221 import Keithley6221
from pyvisa.errors import VisaIOError

from copy import deepcopy

# from util import AbstractThread
from util import AbstractEventhandlingThread
from util import ExceptionHandling


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

    sensors = dict(
        Current_A=None,
        #        Start_Current = None,
        #        Step_Current = None,
        #        Stop_Current = None
    )

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        self.Keithley6221 = Keithley6221(InstrumentAddress=InstrumentAddress)

        self.Current_A_value = 0
        self.Current_A_storage = 0  # if power is turned off
        self.OutputOn = self.getstatus()  # 0 == OFF, 1 == ON
#        self.Start_Current_value = 0
#        self.Step_Current_value = 0
#        self.Stop_Current_value = 0

    def getCurrent_A(self):
        return self.Current_A_value

    @pyqtSlot()
    @ExceptionHandling
    def disable(self):
        self.Keithley6221.disable()
        self.Current_A_storage = self.Current_A_value
        # for logging/application running:
        self.Current_A_value = 0
        self.OutputOn = self.Keithley6221.getstatus()[0]

    @pyqtSlot()
    @ExceptionHandling
    def enable(self):
        self.Keithley6221.enable()
        self.Current_A_value = self.Current_A_storage
        self.setCurrent_A()
        self.OutputOn = self.Keithley6221.getstatus()[0]

    @pyqtSlot()
    @ExceptionHandling
    def getstatus(self):
        return int(self.Keithley6221.getstatus()[0])

    @ExceptionHandling
    def toggle_frontpanel(self, bools, text='In sequence...'):
        if bools:
            self.Keithley6221.enable_frontpanel(text)
        else:
            self.Keithley6221.disable_frontpanel()

    @pyqtSlot()
    @ExceptionHandling
    def setCurrent_A(self):
        self.Keithley6221.setCurrent(self.Current_A_value)
        self.sig_Infodata.emit(deepcopy(dict(Current_A=self.Current_A_value)))

    @pyqtSlot()
    @ExceptionHandling
    def setSweep(self):
        self.Keithley6221.SetupSweet(
            self.Start_Current_value, self.Step_Current_value, self.Stop_Current_value)

    @pyqtSlot()
    @ExceptionHandling
    def startSweep(self):
        self.Keithley6221.StartSweep()

    @pyqtSlot(float)
    def gettoset_Current_A(self, value):
        self.Current_A_value = value
        self.Current_A_storage = value

    @pyqtSlot(float)
    def gettoset_Start_Current(self, value):
        self.Start_Current_value = value

    @pyqtSlot(float)
    def gettoset_Step_Current(self, value):
        self.Step_Current_value = value

    @pyqtSlot(float)
    def gettoset_Stop_Current(self, value):
        self.Stop_Current_value = value
