import sys
import time


from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from .Drivers.ips120 import ips120
from pyvisa.errors import VisaIOError


class PS_Updater(AbstractLoopThread):
    """docstring for PS_Updater"""

    sig_Infodata = pyqtSignal(dict)
    # sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)

    sensors_= dict(
                    # demand_current_to_psu_= 0,#           output_current
                    measured_power_supply_voltage = 1,
                    measured_magnet_current = 2,
                    # unused = 3,
                    CURRENT_output = 4,#                  CURRENT output current (duplicate of R0)
                    CURRENT_set_point= 5,#                CURRENT Target [A] 
                    CURRENT_sweep_rate = 6,#              CURRENT        [A/min]
                    FIELD_output = 7,#                    FIELD   Output_Field
                    FIELD_set_point = 8,#                 FIELD   Target [T]
                    FIELD_sweep_rate = 9,#                FIELD          [T/min]
                    lead_resistance = 10,#                RESISTANCE     [milli_Ohm]
                    # channel_1_Freq4 = 11,
                    # channel_2_Freq4 = 12,
                    # channel_3_Freq4 = 13,
                    # DACZ = 14,#                           PSU_zero_correction_as_a_hexadecimal_number
                    software_voltage_limit = 15,
                    persistent_magnet_current = 16,
                    trip_current = 17,
                    persistent_magnet_field = 18,
                    trip_field = 19,
                    # IDAC = 20,#                           demand_current_as_a_hexadecimal_number
                    safe_current_limit_most_negative = 21,
                    safe_current_limit_most_positive = 22)


    def __init__(self, InstrumentAddress):
        super(PS_Updater, self).__init__()
        # QThread.__init__(self)

        self.PS = ips120(InstrumentAddress)
        self.delay = 0.0


    @pyqtSlot()
    def running(self):
        """worker method of the power supply controlling thread"""
        try:
            data = dict()
            # get key-value pairs of the sensors dict,
            # so I can then transmit one single dict
            for key, idx_sensor in self.sensors.items():
                data[key] = self.PS.getValue(idx_sensor)
                time.sleep(self.delay)
            self.sig_Infodata.emit(deepcopy(data))

        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot(float)
    def set_delay_measuring(self, delay):
        self.delay = delay

    @pyqtSlot(int)
    def setControl(self, control_state=3):
        """method to set the control for local/remote"""
        try:
            self.PS.setControl(control_state)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def readField(self): 
        '''method to readField - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def readFieldSetpoint(self): 
        '''method to readFieldSetpoint - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def readFieldSweepRate(self): 
        '''method to readFieldSweepRate - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def setActivity(self): 
        '''method to setActivity - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def setHeater(self): 
        '''method to setHeater - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def setFieldSetpoint(self): 
        '''method to setFieldSetpoint - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def setFieldSweepRate(self): 
        '''method to setFieldSweepRate - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def setDisplay(self): 
        '''method to setDisplay - this can be invoked by a signal'''
        pass

    @pyqtSlot()
    def waitForField(self): 
        '''method to waitForField - this can be invoked by a signal'''
        pass