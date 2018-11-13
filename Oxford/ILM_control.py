
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from .Drivers.ilm200 import ilm211
from pyvisa.errors import VisaIOError

from copy import deepcopy
# from util import AbstractThread
from util import AbstractLoopThread
from util import ExceptionHandling


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
    # sig_visaerror = pyqtSignal(str)
    # sig_visatimeout = pyqtSignal()
    # timeouterror = VisaIOError(-1073807339)

    sensors = dict(
        channel_1_level=1,
        channel_2_level=2)
        # channel_3_level=,
        # channel_1_wire_current=6,
        # channel_2_wire_current=7,
        # needle_valve_position=10)

    def __init__(self, InstrumentAddress=''):
        super().__init__()

        # here the class instance of the ITC should be handed
        self.ILM = ilm211(InstrumentAddress=InstrumentAddress)
        self.control_state = 3
        # self.interval = 60*30# every half hour one measurement lHe is not measured more often by the device anyways
        self.interval = 3

        self.setControl()

    def running(self):
        """Try to extract all current data from the ILM, and emit signal, sending the data

            self.delay2 should be at at least 0.4 to ensure relatively error-free communication
            with ITC over serial RS-232 connection. (this worked on Benjamin's PC, to be checked
            with any other PC, so errors which come back are "caught", or communication is set up
            in a way no errors occur)

        """
        data = dict()

        for key in self.sensors:
            try:
                # get key-value pairs of the sensors dict,
                # so I can then transmit one single dict
                # for key, idx_sensor in self.sensors.items():
                data[key] = self.ILM.getValue(self.sensors[key])*0.1
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
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    self.sig_visatimeout.emit()
                    self.read_buffer()
                else:
                    self.sig_visaerror.emit(e_visa.args[0])
        self.sig_Infodata.emit(deepcopy(data))



    def read_buffer(self):
        try:
            return self.ILM.read()
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                pass
    # @pyqtSlot(int)
    # def set_delay_sending(self, delay):
    #     self.delay1 = delay

    @pyqtSlot(int)
    def set_delay_measuring(self, delay):
        self.delay2 = delay

    @pyqtSlot()
    @ExceptionHandling
    def setControl(self):
        """class method to be called to set Control
            this is to be invoked by a signal
        """
        self.ILM.setControl(self.control_state)

    @pyqtSlot(int)
    @ExceptionHandling
    def setProbingSpeed(self, speed, channel=1):
        """
            set probing speed for a specific channel
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
        """class method to receive and store the value to set the Control status
            later on, when the command to enforce the value is sent
        """
        self.control_state = value