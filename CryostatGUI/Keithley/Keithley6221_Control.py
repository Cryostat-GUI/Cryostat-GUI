
# from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSlot
# from PyQt5.uic import loadUi

from Keithley.Keithley6221 import Keithley6221
# from pyvisa.errors import VisaIOError

from copy import deepcopy
import logging

# from util import AbstractThread
from util import AbstractEventhandlingThread
from util import ExceptionHandling

# from datetime import datetime


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

    def __init__(self, comLock, InstrumentAddress='', log=None, **kwargs):
        super().__init__(**kwargs)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)

        self.Keithley6221 = Keithley6221(InstrumentAddress=InstrumentAddress, comLock=comLock)
        self.__name__ = 'Keithley6221_Updater ' + InstrumentAddress
        self.Current_A_value = 0
        self.Current_A_storage = 0  # if power is turned off
        self.OutputOn = self.getstatus()  # 0 == OFF, 1 == ON
#        self.Start_Current_value = 0
#        self.Step_Current_value = 0
#        self.Stop_Current_value = 0

    def running(self):
        """only needed for debugging
        self.interval in parent class is definde as 500.
        self.interval here is redefined for higher rate of queries.
        """
        self.interval = 0.5  # seconds
        self.error = self.Keithley6221.query_error()
        if self.error[0] != '0':
            self.logger.error('code:{}, message:{}'.format(self.error[0], self.error[1].strip('"')))

    def getCurrent_A(self):
        """return currently operated current value"""
        return self.Current_A_value

    @pyqtSlot()
    @ExceptionHandling
    def disable(self):
        """disable the output current"""
        self.Keithley6221.disable()
        self.Current_A_storage = self.Current_A_value
        # for logging/application running:
        self.Current_A_value = 0
        self.OutputOn = self.Keithley6221.getstatus()[0]

    @pyqtSlot()
    @ExceptionHandling
    def enable(self):
        """enable the output current"""
        self.Keithley6221.enable()
        self.Current_A_value = self.Current_A_storage
        self.setCurrent_A()
        self.OutputOn = self.Keithley6221.getstatus()[0]

    @pyqtSlot()
    @ExceptionHandling
    def getstatus(self):
        """retrieve output current status"""
        return int(self.Keithley6221.getstatus()[0])

    @ExceptionHandling
    def toggle_frontpanel(self, bools, text='In sequence...'):
        """toggle frontpanel display text"""
        if bools:
            self.Keithley6221.enable_frontpanel(text)
        else:
            self.Keithley6221.disable_frontpanel()

    @pyqtSlot()
    @ExceptionHandling
    def setCurrent_A(self):
        """set a previously stored value for the current"""
        self.Keithley6221.setCurrent(self.Current_A_value)
        self.sig_Infodata.emit(deepcopy(dict(Current_A=self.Current_A_value)))

    @pyqtSlot()
    @ExceptionHandling
    def setCurrent(self, current: float):
        """set a pass value for the current"""
        self.Current_A_value = current
        self.Current_A_storage = current
        self.Keithley6221.setCurrent(current)
        self.sig_Infodata.emit(deepcopy(dict(Current_A=self.Current_A_value)))

    @pyqtSlot()
    @ExceptionHandling
    def setSweep(self):
        """set a current sweep"""
        self.Keithley6221.SetupSweet(
            self.Start_Current_value, self.Step_Current_value, self.Stop_Current_value)

    @pyqtSlot()
    @ExceptionHandling
    def startSweep(self):
        """start a current sweep"""
        self.Keithley6221.StartSweep()

    @pyqtSlot(float)
    def gettoset_Current_A(self, value):
        """store a current value for later usage"""
        self.Current_A_value = value
        self.Current_A_storage = value

    @pyqtSlot(float)
    def gettoset_Start_Current(self, value):
        """store a start current for a sweep"""
        self.Start_Current_value = value

    @pyqtSlot(float)
    def gettoset_Step_Current(self, value):
        """store a step current for a sweep"""
        self.Step_Current_value = value

    @pyqtSlot(float)
    def gettoset_Stop_Current(self, value):
        """store a stop current for a sweep"""
        self.Stop_Current_value = value
