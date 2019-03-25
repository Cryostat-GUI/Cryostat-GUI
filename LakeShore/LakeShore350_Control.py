from PyQt5.QtCore import pyqtSlot
from pyvisa.errors import VisaIOError
from copy import deepcopy
from importlib import reload

import LakeShore

from util import AbstractLoopThread
from util import ExceptionHandling


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

    sensors = dict(
        Heater_Output_percentage=None,
        Heater_Output_mW=None,
        Temp_K=None,
        Ramp_Rate_Status=None,
        Ramp_Rate=None,
        Input_Sensor=None,
        Sensor_1_K=None,
        Sensor_2_K=None,
        Sensor_3_K=None,
        Sensor_4_K=None,
        Loop_P_Param=None,
        Loop_I_Param=None,
        Loop_D_Param=None,
        Heater_Range=None,
        Heater_Setup=None,
        Sensor_1_Ohm=None,
        Sensor_2_Ohm=None,
        Sensor_3_Ohm=None,
        Sensor_4_Ohm=None,
        OutputMode=None)

    def __init__(self, InstrumentAddress='', **kwargs):
        super().__init__(**kwargs)

        # here the class instance of the LakeShore should be handed
        self.__name__ = 'LakeShore350_Updater ' + InstrumentAddress
        global LakeShore
        LS = reload(LakeShore.LakeShore350)
        try:
            self.LakeShore350 = LS.LakeShore350(
                InstrumentAddress=InstrumentAddress)
        except VisaIOError as e:
            self.sig_assertion.emit('running in control: {}'.format(e))
            return
            # need to quit the THREAD!!
        self.Temp_K_value = 3
#       self.Heater_mW_value = 0
        self.Ramp_Rate_value = 0

        self.Upper_Bound_value = 330
        self._max_power = None
        """proper P, I, D values needed
        """
        # self.ZoneP_value
        # self.ZoneI_value
        # self.ZoneD_value
        self.Mout_value = 50
        self.Zone_Range_value = 2
        self.Zone_Rate_value = 1

        """sets Heater power to 994,05 mW
        """
        self.configHeater()
        self.configTempLimit()
        self.initiating_PID()

        self.Ramp_status_internal = int(False)

#        self.setControlLoopZone()
#        self.startHeater()

        # self.interval = 0

    @ExceptionHandling
    def initiating_PID(self):
        temp_list0 = self.LakeShore350.ControlLoopPIDValuesQuery(1)
        self.LoopP_value = temp_list0[0]
        self.LoopI_value = temp_list0[1]
        self.LoopD_value = temp_list0[2]

    # @control_checks
    @ExceptionHandling
    def running(self):
        """
        Try to extract all current data from LakeShore350,
        and emit signal, sending the data
        """

        self.sensors['Temp_K'] = self.LakeShore350.ControlSetpointQuery(1)
        self.sensors['Ramp_Rate_Status'] = self.LakeShore350.ControlSetpointRampParameterQuery(1)[
            0]

        self.sensors['Input_Sensor'] = self.LakeShore350.OutputModeQuery(1)[1]
        temp_list = self.LakeShore350.KelvinReadingQuery(0)
        self.sensors['Sensor_1_K'] = temp_list[0]
        self.sensors['Sensor_2_K'] = temp_list[1]
        self.sensors['Sensor_3_K'] = temp_list[2]
        self.sensors['Sensor_4_K'] = temp_list[3]
        ramp_rate = self.LakeShore350.ControlSetpointRampParameterQuery(1)[1]
        self.sensors['Ramp_Rate'] = ramp_rate if self.Temp_K_value > self.sensors[
            'Temp_K'] else - ramp_rate
        temp_list2 = self.LakeShore350.ControlLoopPIDValuesQuery(1)
        self.sensors['Loop_P_Param'] = temp_list2[0]
        self.sensors['Loop_I_Param'] = temp_list2[1]
        self.sensors['Loop_D_Param'] = temp_list2[2]

        self.sensors['Heater_Range'] = self.LakeShore350.HeaterRangeQuery(1)
        self.sensors['Heater_Range_times_10'] = self.sensors[
            'Heater_Range'] * 10
        self.sensors[
            'Heater_Output_percentage'] = self.LakeShore350.HeaterOutputQuery(1)
        self.sensors['Heater_Output_mW'] = self.sensors['Heater_Output_percentage'] / \
            100 * self._max_power * 1e3 * \
            10**(-(5 - self.sensors['Heater_Range']))

        temp_list3 = self.LakeShore350.SensorUnitsInputReadingQuery(0)
        self.sensors['Sensor_1_Ohm'] = temp_list3[0]
        self.sensors['Sensor_2_Ohm'] = temp_list3[1]
        self.sensors['Sensor_3_Ohm'] = temp_list3[2]
        self.sensors['Sensor_4_Ohm'] = temp_list3[3]
        self.sensors['OutputMode'] = self.LakeShore350.OutputModeQuery(1)[1]

        self.sig_Infodata.emit(deepcopy(self.sensors))

    @ExceptionHandling
    def configSensor(self):
        """configures sensor inputs to Cerox
        """
        for i in ['A', 'B', 'C', 'D']:
            self.LakeShore350.InputTypeParameterCommand(i, 3, 1, 0, 1, 1, 0)

    @ExceptionHandling
    def configHeater(self):
        """configures heater output
        HeaterSetupCommand(1,2,0,0.141,2) sets Output 1, Heater_Resistance to 50 Ohm, enables Custom Maximum Heater Output Current of 0.141 and configures the heater output displays to show in power.
        """
        # weak heater
        # self.LakeShore350.HeaterSetupCommand(1, 2, 0, 0.141, 2)
        # strong heater
        # 1A, 50Ohm, display power percentages
        self.LakeShore350.HeaterSetupCommand(1, 2, 2, 1, 2)
        self._max_current = 1  # [A]
        self._heater_resistance = 50  # [Ohm]
        self._max_power = self._heater_resistance * self._max_current**2  # [W]

    @ExceptionHandling
    def configTempLimit(self):
        """sets temperature limit
        """
        for i in ['A', 'B', 'C', 'D']:
            self.LakeShore350.TemperatureLimitCommand(i, 400.)

    @pyqtSlot()
    @ExceptionHandling
    def setTemp_K(self):
        """takes value Temp_K and uses it on function ControlSetpointCommand to set desired temperature.
        """
        self.LakeShore350.ControlSetpointCommand(1, self.Temp_K_value)
        self.LakeShore350.ControlSetpointRampParameterCommand(
            1, self.Ramp_status_internal, self.Ramp_Rate_value)

    @ExceptionHandling
    def read_Temperatures(self):
        sensors = dict()
        sensor_names = ['Sensor_1_K', 'Sensor_2_K', 'Sensor_3_K', 'Sensor_4_K']
        temp_list = self.LakeShore350.KelvinReadingQuery(0)

        for idx, sens in enumerate(sensor_names):
            sensors[sens] = temp_list[idx]
        return sensors

#    @pyqtSlot()
#    def setHeater_mW(self):
#        try:
#            self.LakeShore350.HeaterSetupCommand
#        except AssertionError as e_ass:
#            self.sig_assertion.emit(e_ass.args[0])
#        except VisaIOError as e_visa:
#            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
#                self.sig_visatimeout.emit()
#            else:
#                self.sig_visaerror.emit(e_visa.args[0])
    @pyqtSlot(bool)
    def setStatusRamp(self, bools):
        self.Ramp_status_internal = int(bools)
        self.setRamp_Rate_K()
        self.setTemp_K()

    @pyqtSlot()
    @ExceptionHandling
    def setRamp_Rate_K(self):
        self.LakeShore350.ControlSetpointRampParameterCommand(
            1, self.Ramp_status_internal, self.Ramp_Rate_value)
        # the lone '1' here is the output

    @pyqtSlot()
    @ExceptionHandling
    def setInput(self, Input_value):
        """(1,1,value,1) configure Output 1 for Closed Loop PID, using Input "value" and set powerup enable to On.
        """
        self.LakeShore350.OutputModeCommand(1, 1, Input_value, 1)

    @pyqtSlot()
    @ExceptionHandling
    def setLoopP_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(1, self.LoopP_value, self.sensors[
                                                      'Loop_I_Param'], self.sensors['Loop_D_Param'])

    @pyqtSlot()
    @ExceptionHandling
    def setLoopI_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.sensors['Loop_P_Param'], self.LoopI_value, self.sensors['Loop_D_Param'])

    @pyqtSlot()
    @ExceptionHandling
    def setLoopD_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.sensors['Loop_P_Param'], self.sensors['Loop_I_Param'], self.LoopD_value)

    @pyqtSlot()
    @ExceptionHandling
    def startHeater(self):
        """start up Heater with Output 1 for Closed Loop PID, using Input "value" and set powerup enable to On.
        """
        self.LakeShore.OutputModeCommand(1, 1, self.sensor_values[5], 1)

    @pyqtSlot()
    @ExceptionHandling
    def setHeater_Range(self, range_value = None):
        """set Heater Range for Output 1
        """
        if range_value == None:
	        self.LakeShore350.HeaterRangeCommand(1, self.Heater_Range_value)
	    if not range_value == None:
	    	self.LakeShore350.HeaterRangeCommand(1, range_value)

    @pyqtSlot()
    @ExceptionHandling
    def setControlLoopZone(self):

        self.LakeShore350.ControlLoopZoneTableParameterCommand(
            1, 1, self.Upper_Bound_value, self.ZoneP_value, self.ZoneI_value, self.ZoneD_value, self.Mout_value, self.Zone_Range_value, 1, self.Zone_Rate_value)

    @pyqtSlot()
    def gettoset_Temp_K(self, value):
        """class method to receive and store the value to set the temperature
        later on, when the command to enforce the value is sent
        """
        self.Temp_K_value = value


#    @pyqtSlot()
#    def gettoset_Heater_mW(self,value):
#        """class method to receive and store the value to set the temperature
#        later on, when the command to enforce the value is sent
#        """
#        self.Heater_mW_value = value

    @pyqtSlot()
    def gettoset_LoopP_Param(self, value):
        self.LoopP_value = value

    @pyqtSlot()
    def gettoset_LoopI_Param(self, value):
        self.LoopI_value = value

    @pyqtSlot()
    def gettoset_LoopD_Param(self, value):
        self.LoopD_value = value

    @pyqtSlot()
    def gettoset_Ramp_Rate_K(self, value):
        self.Ramp_Rate_value = value

    @pyqtSlot()
    def gettoset_Upper_Bound(self, value):
        self.Upper_Bound_value = value

    @pyqtSlot()
    def gettoset_ZoneP_Param(self, value):
        self.ZoneP_value = value

    @pyqtSlot()
    def gettoset_ZoneI_Param(self, value):
        self.ZoneI_value = value

    @pyqtSlot()
    def gettoset_ZoneD_Param(self, value):
        self.ZoneD_value = value

    @pyqtSlot()
    def gettoset_ZoneMout(self, value):
        self.Mout_value = value

    @pyqtSlot()
    def gettoset_Zone_Range(self, value):
        self.Zone_Range_value = value

    @pyqtSlot()
    def gettoset_Zone_Rate(self, value):
        self.Zone_Rate_value = value


#    def gettoset_Heater_Range(self,value):
#       self.Heater_Range_value = value
