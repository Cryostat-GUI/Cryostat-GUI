import time

# from labdrivers.oxford.itc503 import itc503
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from .Drivers.itc503 import itc503
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

    sensors = dict(
        set_temperature=0,
        sensor_1_temperature=1,
        sensor_2_temperature=2,
        sensor_3_temperature=3,
        temperature_error=4,
        heater_output_as_percent=5,
        heater_output_as_voltage=6,
        gas_flow_output=7,
        proportional_band=8,
        integral_action_time=9,
        derivative_action_time=10)

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        # here the class instance of the ITC should be handed
        self.ITC = itc503(InstrumentAddress=InstrumentAddress)

        self.control_state = 3
        self.set_temperature = 0
        self.set_prop = 0
        self.set_integral = 0
        self.set_derivative = 0
        self.set_sensor = 1
        self.set_heater_output = 0
        self.set_gas_output = 0
        self.set_auto_manual = 0
        self.sweep_parameters = None

        self.delay1 = 1
        self.delay = 0.0
        self.setControl()
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

            data = dict()
            # get key-value pairs of the sensors dict,
            # so I can then transmit one single dict
            for key, idx_sensor in self.sensors.items():
                data[key] = self.ITC.getValue(idx_sensor)
                time.sleep(self.delay)
            self.sig_Infodata.emit(deepcopy(data))

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


    @pyqtSlot(int)
    def set_delay_sending(self, delay):
        self.ITC.set_delay_measuring(delay)


