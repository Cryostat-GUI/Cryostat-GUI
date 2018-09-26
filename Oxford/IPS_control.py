import sys
import time


from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from .Drivers.ips120 import ips120
from pyvisa.errors import VisaIOError


class IPS_Updater(AbstractLoopThread):
    """docstring for PS_Updater"""

    sig_Infodata = pyqtSignal(dict)
    # sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)

    sensors= dict(
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
    statusdict = dict(magnetstatus= {'0': 'normal', 
                                     '1': 'quenched', 
                                     '2': 'over heated', 
                                     '3': 'warming up'}, 
                    currentstatus = {'0': 'normal', 
                                     '1': 'on positive voltage limit', 
                                     '2': 'on negative voltage limit', 
                                     '4': 'outside negative current limit', 
                                     '8': 'outside positive current limit'}, 
                    activitystatus= {'0': 'Hold',
                                     '1': 'To set point',
                                     '2': 'To zero',
                                     '3': 'Clamped'}, 
                    loc_remstatus = {'0': 'local & locked',
                                     '1': 'remote & locked',
                                     '2': 'local & unlocked',
                                     '3': 'remote & unlocked',
                                     '4': 'AUTO RUN DOWN',
                                     '5': 'AUTO RUN DOWN',
                                     '6': 'AUTO RUN DOWN',
                                     '7': 'AUTO RUN DOWN'}, 
                    switchHeaterstat={'0': 'Off (closed) magnet at zero',
                                      '1': 'On (open)',
                                      '2': 'Off (closed) magnet at field',
                                      '8': 'no switch fitted'})


    def __init__(self, InstrumentAddress):
        super(PS_Updater, self).__init__()
        # QThread.__init__(self)

        self.PS = ips120(InstrumentAddress)
        self.delay = 0.0
        self.field_setpoint = 0


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
            data.update(self.getStatus())
            self.sig_Infodata.emit(deepcopy(data))
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot(int)
    def set_delay_sending(self, delay):
        self.PS.set_delay_measuring(delay)

    def getStatus(self):
        status = self.PS.getStatus()
        return dict(status_magnet = self.statusdict['magnetstatus'][status[1]], 
                    status_current = self.statusdict['currentstatus'][status[2]], 
                    status_activity= self.statusdict['activitystatus'][status[4]], 
                    status_locrem = self.statusdict['loc_remstatus'][status[6]], 
                    status_switchheater= self.statusdict['switchHeaterstat'][status[8]])

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
        try:
            self.PS.readField()
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def readFieldSetpoint(self): 
        '''method to readFieldSetpoint - this can be invoked by a signal'''
        try:
            self.PS.readFieldSetpoint()
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def readFieldSweepRate(self): 
        '''method to readFieldSweepRate - this can be invoked by a signal'''
        try:
            self.PS.readFieldSweepRate()
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def setActivity(self, state): 
        '''method to setActivity - this can be invoked by a signal'''
        try:
            self.PS.setActivity( state)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def setSwitchHeater(self, state): 
        '''method to setHeater - this can be invoked by a signal'''
        try:
            self.PS.setSwitchHeater(state)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def setFieldSetpoint(self): 
        '''method to setFieldSetpoint - this can be invoked by a signal'''
        try:
            self.PS.setFieldSetpoint(self.field_setpoint)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 
    @pyqtSlot(float)
    def gettoset_FieldSetpoint(self, value):
            """class method to receive and store the value, to set the Field Setpoint
                later on, when the command to enforce the value is sent
                TODO: adjust for units! 
            """
        self.field_setpoint = value

    @pyqtSlot()
    def setFieldSweepRate(self): 
        '''method to setFieldSweepRate - this can be invoked by a signal'''
        try:
            self.PS.setFieldSweepRate(self.field_rate)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 
    @pyqtSlot(int)
    def gettoset_FieldSweepRate(self, value):
            """class method to receive and store the value to set the Field sweep rate
                later on, when the command to enforce the value is sent
            """
        self.field_setpoint = value

    @pyqtSlot()
    def setDisplay(self, display): 
        '''method to setDisplay - this can be invoked by a signal'''
        try:
            self.PS.setDisplay(display)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 

    @pyqtSlot()
    def waitForField(self, timeout, error_margin): 
        '''method to waitForField - this can be invoked by a signal'''
        try:
            self.PS.waitForField()
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0]) 