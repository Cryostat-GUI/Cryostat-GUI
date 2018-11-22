from PyQt5.QtCore import pyqtSlot

from Keithley.Keithley2182 import Keithley2182

from copy import deepcopy

# from util import AbstractThread
from util import AbstractLoopThread
from util import ExceptionHandling


class Keithley2182_Updater(AbstractLoopThread):
    """This is the worker thread, which updates all instrument data of one Keithley 2182 device.

        For each device function, there is a wrapping method,
        which we can call by a signal, from the main thread. This wrapper sends
        the corresponding value to the device.

        The information from the device is collected in regular intervals (method "running"),
        and subsequently sent to the main thread. It is packed in a dict,
        the keys of which are displayed in the "sensors" dict in this class.
    """

    sensors = dict(Voltage_V=None)

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)
        self.instr = InstrumentAddress
        self.Keithley2182 = Keithley2182(InstrumentAddress=InstrumentAddress)

    # @control_checks
    @ExceptionHandling
    def running(self):
        """Measure Voltage, send the data"""
        self.sensors['Voltage_V'] = self.Keithley2182.measureVoltage()

        self.sig_Infodata.emit(deepcopy(self.sensors))


    @pyqtSlot()
    @ExceptionHandling
    def read_Voltage(self):
        """read a Voltage from instrument. return value should be float"""
        return self.Keithley2182.measureVoltage()

    @pyqtSlot()
    @ExceptionHandling
    def speed_up(self):
        """increase measurement speed
        """
        self.Keithley2182.setRate('FAS')

    @pyqtSlot()
    @ExceptionHandling
    def TurnOnDisplay(self):
        return self.Keithley2182.DisplayOn()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOffDisplay(self):
        return self.Keithley2182.DisplayOff()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOnFrontAutozero(self):
        return self.Keithley2182.FrontAutozeroOn()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOffFrontAutozero(self):
        return self.Keithley2182.FrontAutozeroOff()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOnAutozero(self):
        return self.Keithley2182.AutozeroOn()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOffAutozero(self):
        return self.Keithley2182.AutozeroOff()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOffAutorange(self):
        return self.Keithley2182.AutorangeOff()

    @pyqtSlot()
    @ExceptionHandling
    def TurnOnAutorange(self):
        return self.Keithley2182.AutorangeOn()

