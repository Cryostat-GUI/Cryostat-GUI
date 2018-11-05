import time

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from Keithley.Keithley2182 import Keithley2182
from pyvisa.errors import VisaIOError

from copy import deepcopy

# from util import AbstractThread
from util import AbstractLoopThread


class Keithley2182_Updater(AbstractLoopThread):
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

    sensors =  dict(
    	Voltage_DC = None)


    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        self.Keithley2182 = Keithley2182(InstrumentAddress=InstrumentAddress)

#        self.delay1 = 1
#        self.delay = 0.0
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
            self.sensors['Voltage_DC'] = self.Keithley2182.measureVoltage()

            self.sig_Infodata.emit(deepcopy(sensors))

            # time.sleep(self.delay1)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else:
                self.sig_visaerror.emit(e_visa.args[0])
