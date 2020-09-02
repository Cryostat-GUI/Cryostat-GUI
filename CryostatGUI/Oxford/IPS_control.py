"""Module containing a class to run a (Oxford Instruments) IPS 120-10 Intelligent Power Source in a pyqt5 application

Classes:
    IPS_Updater: a class for interfacing with a IPS 120-10 Power Supply
            inherits from AbstractLoopThread
                there, the looping behaviour of this thread is defined
Author(s):
    bklebel (Benjamin Klebel)
"""
import time
from copy import deepcopy

from PyQt5.QtCore import pyqtSlot

from pyvisa.errors import VisaIOError

from Oxford.ips120 import ips120
import logging

from util import AbstractLoopThread
from util import ExceptionHandling

from datetime import datetime


class IPS_Updater(AbstractLoopThread):
    """Updater class for the Intelligent Power Supply (IPS) 120-10

    For each IPS function (except collecting data), there is a wrapping method,
    which we can call by a signal, from the main thread. This wrapper sends
    the corresponding value to the device.

    There is a second method for all wrappers, which accepts
    the corresponding value, and stores it, so it can be sent upon acknowledgment

    The information from the device is collected in regular intervals (method "running"),
    and subsequently sent to the main thread. It is packed in a dict,
    the keys of which are displayed in the "sensors" dict in this class.
    """

    sensors = dict(
        # demand_current_to_psu_= 0,#     output_current
        measured_power_supply_voltage=1,
        measured_magnet_current=2,
        # unused=3,
        CURRENT_output=4,  # CURRENT output current (duplicate of R0)
        CURRENT_set_point=5,  # CURRENT Target [A]
        CURRENT_sweep_rate=6,  # CURRENT        [A/min]
        FIELD_output=7,  # FIELD   Output_Field
        FIELD_set_point=8,  # FIELD   Target [T]
        FIELD_sweep_rate=9,  # FIELD          [T/min]
        lead_resistance=10,  # RESISTANCE     [milli_Ohm]
        # channel_1_Freq4=11,
        # channel_2_Freq4=12,
        # channel_3_Freq4=13,
        # DACZ=14,    # PSU_zero_correction_as_a_hexadecimal_number
        software_voltage_limit=15,
        persistent_magnet_current=16,
        trip_current=17,
        persistent_magnet_field=18,
        trip_field=19,
        # IDAC=20,  # demand_current_as_a_hexadecimal_number
        safe_current_limit_most_negative=21,
        safe_current_limit_most_positive=22,
    )

    statusdict = dict(
        magnetstatus={
            "0": "normal",
            "1": "quenched",
            "2": "over heated",
            "4": "warming up",
        },
        currentstatus={
            "0": "normal",
            "1": "on positive voltage limit",
            "2": "on negative voltage limit",
            "4": "outside negative current limit",
            "8": "outside positive current limit",
        },
        activitystatus={
            "0": "Hold",
            "1": "To set point",
            "2": "To zero",
            "4": "Clamped",
        },
        loc_remstatus={
            "0": "local & locked",
            "1": "remote & locked",
            "2": "local & unlocked",
            "3": "remote & unlocked",
            "4": "AUTO RUN DOWN",
            "5": "AUTO RUN DOWN",
            "6": "AUTO RUN DOWN",
            "7": "AUTO RUN DOWN",
        },
        switchHeaterstat={
            "0": "Off (closed) magnet at zero",
            "1": "On (open)",
            "2": "Off (closed) magnet at field",
            "8": "no switch fitted",
        },
        modestatus1={
            "0": "display: Amps,  mode: immediate, sweepmode: Fast",
            "1": "display: Tesla, mode: immediate, sweepmode: Fast",
            "2": "display: Amps,  mode: sweep,     sweepmode: Fast",
            "3": "display: Tesla, mode: sweep,     sweepmode: Fast",
            "4": "display: Amps,  mode: immediate, sweepmode: Train",
            "5": "display: Tesla, mode: immediate, sweepmode: Train",
            "6": "display: Amps,  mode: sweep,     sweepmode: Train",
            "7": "display: Tesla, mode: sweep,     sweepmode: Train",
        },
        modestatus2={
            "0": "at rest (output constant)",
            "1": "sweeping (output changing)",
            "2": "rate limiting (output changing)",
            "3": "sweeping & rate limiting (output changing)",
        },
        polarity1={
            "0": "desired: Forward, magnet: Forward, commanded: Forward",
            "1": "desired: Forward, magnet: Forward, commanded: Reverse",
            "2": "desired: Forward, magnet: Reverse, commanded: Forward",
            "3": "desired: Forward, magnet: Reverse, commanded: Reverse",
            "4": "desired: Reverse, magnet: Forward, commanded: Forward",
            "5": "desired: Reverse, magnet: Forward, commanded: Reverse",
            "6": "desired: Reverse, magnet: Reverse, commanded: Forward",
            "7": "desired: Reverse, magnet: Reverse, commanded: Reverse",
        },
        polarity2={
            "0": "output clamped (transition)",
            "1": "forward (verification)",
            "2": "reverse (verification)",
            "4": "output clamped (requested)",
        },
    )

    def __init__(self, InstrumentAddress, log=None, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        # QThread.__init__(self)
        # global Oxford
        # ips120 = reload(Oxford.ips120).ips120
        self.PS = ips120(InstrumentAddress=InstrumentAddress)
        self.__name__ = "IPS_Updater " + InstrumentAddress
        self.field_setpoint = 0
        self.first = True

    @pyqtSlot()
    def running(self):
        """worker method of the power supply controlling thread"""
        if self.first:
            time.sleep(1)
            self.first = False
        try:
            data = dict()
            # get key-value pairs of the sensors dict,
            # so I can then transmit one single dict
            for key, idx_sensor in self.sensors.items():
                # key_f_timeout = key
                data[key] = self.PS.getValue(idx_sensor)
            data.update(self.getStatus())

            data["realtime"] = datetime.now()

            self.sig_Infodata.emit(deepcopy(data))
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if (
                isinstance(e_visa, type(self.timeouterror))
                and e_visa.args == self.timeouterror.args
            ):
                self.sig_visatimeout.emit()
                # self.readField(nosend=True)
                self.PS.clear_buffers()
                # data[key_f_timeout] = self.read_buffer()
            else:
                self.sig_visaerror.emit(e_visa.args[0])

    # def read_buffer(self):
    #     """read the instrument buffers"""
    #     try:
    #         return self.PS.read_buffer()
    #     except VisaIOError as e_visa:
    #         if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
    #             pass

    def getStatus(self):
        """read the status of the instrument, return it partially parsed"""
        status = self.PS.getStatus()
        return dict(
            status_magnet=self.statusdict["magnetstatus"][status[1]],
            status_current=self.statusdict["currentstatus"][status[2]],
            status_activity=self.statusdict["activitystatus"][status[4]],
            status_locrem=self.statusdict["loc_remstatus"][status[6]],
            status_switchheater=self.statusdict["switchHeaterstat"][status[8]],
            status_mode1=self.statusdict["modestatus1"][status[10]],
            status_mode2=self.statusdict["modestatus2"][status[11]],
            status_polarity1=self.statusdict["polarity1"][status[13]],
            status_polarity3=self.statusdict["polarity2"][status[14]],
        )

    @pyqtSlot(int)
    @ExceptionHandling
    def setControl(self, control_state=3):
        """set the control for local/remote"""
        self.PS.setControl(control_state)

    @pyqtSlot()
    @ExceptionHandling
    def readField(self, nosend=False):
        """read the Field"""
        try:
            return self.PS.readField()
        except AssertionError as e_ass:
            if not nosend:
                self.sig_assertion.emit(e_ass.args[0])

    @pyqtSlot()
    @ExceptionHandling
    def readFieldSetpoint(self):
        """read the Field Setpoint"""
        return self.PS.readFieldSetpoint()

    @pyqtSlot()
    @ExceptionHandling
    def readFieldSweepRate(self):
        """read the Field SweepRate"""
        return self.PS.readFieldSweepRate()

    @pyqtSlot()
    @ExceptionHandling
    def setActivity(self, state):
        """set the Activity"""
        self.PS.setActivity(state)

    @pyqtSlot()
    @ExceptionHandling
    def setSwitchHeater(self, state):
        """set the Switchheater state"""
        self.PS.setSwitchHeater(state)

    @pyqtSlot()
    @ExceptionHandling
    def setFieldSetpoint(self):
        """setthe Field Setpoint"""
        self.PS.setFieldSetpoint(self.field_setpoint)

    @pyqtSlot(float)
    def gettoset_FieldSetpoint(self, value):
        """receive and store the value, to set the Field Setpoint
            TODO: adjust for units!
        """
        self.field_setpoint = value

    @pyqtSlot()
    @ExceptionHandling
    def setFieldSweepRate(self):
        """set the Field SweepRate"""
        self.PS.setFieldSweepRate(self.field_rate)

    @pyqtSlot(int)
    @ExceptionHandling
    def gettoset_FieldSweepRate(self, value):
        """receive and store the value to set the Field sweep rate"""
        self.field_setpoint = value

    @pyqtSlot()
    @ExceptionHandling
    def setDisplay(self, display):
        """set the Display"""
        self.PS.setDisplay(display)

    @pyqtSlot()
    @ExceptionHandling
    def waitForField(self, timeout, error_margin):
        """wait For the Field"""
        return self.PS.waitForField()
