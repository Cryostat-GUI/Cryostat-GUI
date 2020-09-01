"""Module containing a class to run a (Oxford Instruments) ILM 211 Intelligent Level Meter in a pyqt5 application

Classes:
    ILM_Updater: a class for interfacing with an ILM 211 Level Meter
            inherits from AbstractLoopThread
                there, the looping behaviour of this thread is defined
Author(s):
    bklebel (Benjamin Klebel)
"""
from PyQt5.QtCore import pyqtSlot

from pyvisa.errors import VisaIOError

from copy import deepcopy
from importlib import reload

from datetime import datetime

from util import AbstractLoopThread
from util import ExceptionHandling
# import Oxford
import logging
from Oxford.ilm211 import ilm211


class ILM_Updater(AbstractLoopThread):

    """Updater class to update all instrument data of the Intelligent Level Meter (ILM) 211.

    For each ILM211 function (except collecting data), there is a wrapping method,
    which we can call by a signal, from the main thread. This wrapper sends
    the corresponding value to the device.

    There is a second method for all wrappers, which accepts
    the corresponding value, and stores it, so it can be sent upon acknowledgement

    The information from the device is collected in regular intervals (method "running"),
    and subsequently sent to the main thread. It is packed in a dict,
    the keys of which are displayed in the "sensors" dict in this class.
    """

    sensors = dict(channel_1_level=1, channel_2_level=2)
    # channel_3_level=,
    # channel_1_wire_current=6,
    # channel_2_wire_current=7,
    # needle_valve_position=10)

    def __init__(self, InstrumentAddress="", log=None, **kwargs):
        super().__init__(**kwargs)
        # global Oxford
        # ilm211 = reload(Oxford.ilm211).ilm211
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)
        self.ILM = ilm211(InstrumentAddress=InstrumentAddress)
        self.__name__ = "ILM_Updater " + InstrumentAddress
        self.control_state = 3
        # self.interval = 60*30# every half hour one measurement lHe is not
        # measured more often by the device anyways
        self.interval = 3

        self.setControl()

    @ExceptionHandling
    def running(self):
        """Try to extract all current data from the ILM, and emit signal, sending the data"""
        data = dict()

        for key in self.sensors:
            try:
                # get key-value pairs of the sensors dict,
                # so I can then transmit one single dict
                # for key, idx_sensor in self.sensors.items():
                data[key] = self.ILM.getValue(self.sensors[key]) * 0.1
                # data['channel_2_level'] = self.ILM.getValue(2)*0.1
                # if data[key] > 100:
                #     data[key] = 100
                # if data['channel_1_level'] > 100
                #     data['channel_1_level'] = 100
                # status = self.ILM.getStatus()
                # data.update(dict(   cryogen_channel_1=status[0],
                #                     cryogen_channel_2=status[1],
                #                     status_channel_1=status[2],
                #                     status_channel_2=status[3],
                #                     status_channel_3=status[4]))
            except AssertionError as e_ass:
                self.sig_assertion.emit(e_ass.args[0])
            except VisaIOError as e_visa:
                if (
                    isinstance(e_visa, type(self.timeouterror))
                    and e_visa.args == self.timeouterror.args
                ):
                    self.sig_visatimeout.emit()
                    self.ILM.clear_buffers()
                else:
                    self.sig_visaerror.emit(e_visa.args[0])
        data['realtime'] = datetime.now()
        self.sig_Infodata.emit(deepcopy(data))

    # def read_buffer(self):
    #     """read all the possibly full buffer of the instrument"""
    #     try:
    #         return self.ILM.read()
    #     except VisaIOError as e_visa:
    #         if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
    #             pass
    # @pyqtSlot(int)
    # def set_delay_sending(self, delay):
    #     self.delay1 = delay

    # @pyqtSlot(int)
    # def set_delay_measuring(self, delay):
    #     """set the """
    #     self.delay2 = delay

    @pyqtSlot()
    @ExceptionHandling
    def setControl(self):
        """set Control status of the instrument"""
        self.ILM.setControl(self.control_state)

    @pyqtSlot(int)
    @ExceptionHandling
    def setProbingSpeed(self, speed, channel=1):
        """set probing speed for a specific channel

            for fast probing, speed = 1
            for slow probing, speed = 0
            this comes from the order in the comboBox in the GUI
        """
        if speed == 1:
            self.ILM.setFast(channel)
        elif speed == 0:
            self.ILM.setSlow(channel)

    @pyqtSlot(int)
    def gettoset_Control(self, value):
        """receive and store the value to set the Control status"""
        self.control_state = value

    @pyqtSlot()
    @ExceptionHandling
    def measure_once(self):
        """measure the helium level once:
        put the probing speed to 'fast'
            this will immediately trigger the device to measure it once
        put the probing speed to 'slow' again
        measure the helium level and return it
        """
        self.ILM.setFast(1)
        self.ILM.setSlow(1)
        return self.ILM.getValue(1) * 0.1
