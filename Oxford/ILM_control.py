import time

# from labdrivers.oxford.itc503 import itc503 
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from .Drivers.ilm200 import ilm211
from pyvisa.errors import VisaIOError

from copy import deepcopy
# from util import AbstractThread
from util import AbstractLoopThread

class ILM_Updater(AbstractLoopThread):

    """This is the worker thread, which updates all instrument data of the ILM 211.

        For each ILM211 function (except collecting data), there is a wrapping method,
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
        channel_1_level=1,
        channel_2_level=2,
        channel_3_level=3)
        # channel_1_wire_current=6,
        # channel_2_wire_current=7,
        # needle_valve_position=10)


    def __init__(self, InstrumentAddress='COM7'):
        super().__init__()

        # here the class instance of the ITC should be handed
        self.ILM = ilm211(InstrumentAddress=InstrumentAddress)
        self.control_state = 3
        self.setControl()

    def running(self):
        """Try to extract all current data from the ILM, and emit signal, sending the data
        
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
                data[key] = self.ILM.getValue(idx_sensor)*0.1
                # time.sleep(self.delay2)
            # status = self.ILM.getStatus()
            # data.update(dict(   cryogen_channel_1=status[0],
            #                     cryogen_channel_2=status[1],
            #                     status_channel_1=status[2],
            #                     status_channel_2=status[3],
            #                     status_channel_3=status[4]))
            self.sig_Infodata.emit(deepcopy(data))
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])


    # @pyqtSlot(int)
    # def set_delay_sending(self, delay):
    #     self.delay1 = delay

    @pyqtSlot(int)
    def set_delay_measuring(self, delay):
        self.delay2 = delay

    @pyqtSlot()
    def setControl(self):
        """class method to be called to set Control
            this is to be invoked by a signal
        """
        try:
            self.ILM.setControl(self.control_state)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot(int)
    def setProbingSpeed(self, speed, channel):
        """set probing speed for a specific channel"""
        try: 
            if speed == 0: 
                self.ILM.setFast(1)
            elif speed == 1: 
                self.ILM.setSlow(1)

        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot(int)
    def gettoset_Control(self, value):
        """class method to receive and store the value to set the Control status
            later on, when the command to enforce the value is sent
        """
        self.control_state = value                