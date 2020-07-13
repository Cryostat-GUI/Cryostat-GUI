"""Module containing a class to run a LakeShore 350 Cryogenic Temperature Controller in a pyqt5 application

Classes:
    LakeShore350_ControlClient: a class for interfacing with a LakeShore350 temperature controller
            inherits from AbstractLoopClient
"""
from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtWidgets
import json
import sys

from util import ExceptionHandling
from util import AbstractLoopClient
from util import Window_trayService_ui

from zmqcomms import dec, enc

from datetime import datetime
# import logging


class LakeShore350_ControlClient(AbstractLoopClient, Window_trayService_ui):
    """Updater class for the LakeShore350 Temperature controller

        For each Lakeshore350 function there is a wrapping method,
        which we can call by a signal/by zmq comms. This wrapper sends
        the corresponding value to the device.

        There is a second method for all wrappers, which accepts
        the corresponding value, and stores it, so it can be sent upon acknowledgment

        The information from the device is collected in regular intervals (method "running"),
        and subsequently published on the data upstream. It is packed in a dict,
        the keys of which are displayed in the "data" dict in this class.
    """

    # exposable data dictionary
    data = dict(
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

    def __init__(self, comLock=None, InstrumentAddress='', log=None, **kwargs):
        super().__init__(**kwargs)
        # self.logger = log if log else logging.getLogger(__name__)
        # print(self.logger, self.logger.name)

        # here the class instance of the LakeShore should be handed
        self.__name__ = 'LakeShore350_control ' + InstrumentAddress
        # global LakeShore
        # LS = reload(LakeShore.LakeShore350)
        # try:

        # self.LakeShore350 = LakeShore350(
        #     InstrumentAddress=InstrumentAddress, comLock=comLock)

        # except VisaIOError as e:
        #     self.sig_assertion.emit('running in control: {}'.format(e))
        #     return
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

        # setting LakeShore values by GUI LakeShore window
        self.spinSetTemp_K.valueChanged.connect(lambda value: self.gettoset_Temp_K(value))
        self.spinSetTemp_K.editingFinished.connect(self.setTemp_K)

        self.spinSetRampRate_Kpmin.valueChanged.connect(
            self.gettoset_Ramp_Rate_K)
        self.spinSetRampRate_Kpmin.editingFinished.connect(self.setRamp_Rate_K)

        # turns off heater output
        self.pushButtonHeaterOut.clicked.connect(
            lambda: self.setHeater_Range(0))

        # allows to choose from different inputs to connect to output 1
        # control loop. default is input 1.

        self.comboSetInput_Sensor.activated['int'].connect(
            lambda value: self.setInput(value + 1))
        # self.spinSetInput_Sensor.editingFinished.(lambda
        # value: self.threads['control_LakeShore350'][0].setInput())

        self.checkRamp_Status.toggled['bool'].connect(self.setStatusRamp)

        #""" NEW GUI controls P, I and D values for Control Loop PID Values Command
        # """
        self.spinSetLoopP_Param.valueChanged.connect(lambda value: self.gettoset_LoopP_Param(value))
        self.spinSetLoopP_Param.editingFinished.connect(self.setLoopP_Param)

        self.spinSetLoopI_Param.valueChanged.connect(lambda value: self.gettoset_LoopI_Param(value))
        self.spinSetLoopI_Param.editingFinished.connect(self.setLoopI_Param)

        self.spinSetLoopD_Param.valueChanged.connect(lambda value: self.gettoset_LoopD_Param(value))
        self.spinSetLoopD_Param.editingFinished.connect(self.setLoopD_Param)

        """ NEW GUI Heater Range and Ouput Zone
        """
    # self.comboSetHeater_Range.activated['int'].connect(self.setHeater_Range(value))
    # self.spinSetHeater_Range.valueChanged.connect(self.gettoset_Heater_Range(value))#self.spinSetHeater_Range.Finished.connect(self.setHeater_Range())
    # self.spinSetUpper_Bound.valueChanged.connect(self.gettoset_Upper_Bound(value))#
    # self.spinSetZoneP_Param.valueChanged.connect(self.gettoset_ZoneP_Param(value))#
    # self.spinSetZoneI_Param.valueChanged.connect(self.gettoset_ZoneI_Param(value))#
    # self.spinSetZoneD_Param.valueChanged.connect(self.gettoset_ZoneD_Param(value))#
    # self.spinSetZoneMout.valueChanged.connect(self.gettoset_ZoneMout(value))#
    # self.spinSetZone_Range.valueChanged.connect(self.gettoset_Zone_Range(value))#
    # self.spinSetZone_Rate.valueChanged.connect(self.gettoset_Zone_Rate(value))

        self.spin_threadinterval.valueChanged.connect(
            lambda value: self.setInterval(value))

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
        # print('run')
        # -------------------------------------------------------------------------------------------------------------------------
        self.data['Temp_K'] = self.LakeShore350.ControlSetpointQuery(1)
        self.data['Ramp_Rate_Status'] = self.LakeShore350.ControlSetpointRampParameterQuery(1)[
            0]

        self.data['Input_Sensor'] = self.LakeShore350.OutputModeQuery(1)[1]
        temp_list = self.LakeShore350.KelvinReadingQuery(0)
        self.data['Sensor_1_K'] = temp_list[0]
        self.data['Sensor_2_K'] = temp_list[1]
        self.data['Sensor_3_K'] = temp_list[2]
        self.data['Sensor_4_K'] = temp_list[3]
        ramp_rate = self.LakeShore350.ControlSetpointRampParameterQuery(1)[1]
        self.data['Ramp_Rate'] = ramp_rate if self.Temp_K_value > self.data[
            'Temp_K'] else - ramp_rate
        temp_list2 = self.LakeShore350.ControlLoopPIDValuesQuery(1)
        self.data['Loop_P_Param'] = temp_list2[0]
        self.data['Loop_I_Param'] = temp_list2[1]
        self.data['Loop_D_Param'] = temp_list2[2]

        self.data['Heater_Range'] = self.LakeShore350.HeaterRangeQuery(1)
        self.data['Heater_Range_times_10'] = self.data[
            'Heater_Range'] * 10
        self.data[
            'Heater_Output_percentage'] = self.LakeShore350.HeaterOutputQuery(1)
        self.data['Heater_Output_mW'] = self.data['Heater_Output_percentage'] / \
            100 * self._max_power * 1e3 * \
            10**(-(5 - self.data['Heater_Range']))

        temp_list3 = self.LakeShore350.SensorUnitsInputReadingQuery(0)
        self.data['Sensor_1_Ohm'] = temp_list3[0]
        self.data['Sensor_2_Ohm'] = temp_list3[1]
        self.data['Sensor_3_Ohm'] = temp_list3[2]
        self.data['Sensor_4_Ohm'] = temp_list3[3]
        self.data['OutputMode'] = self.LakeShore350.OutputModeQuery(1)[1]

        self.data['realtime'] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        # self.sig_Infodata.emit(deepcopy(self.data))
        self.comms_upstream.send_multipart(
            [self.comms_name, enc(json.dumps(self.data))])

    @ExceptionHandling
    def act_on_command(self, command):
        if 'setTemp_K' in command:
            self.setTemp_K(command['setTemp_K'])
        if 'configTempLimit' in command:
            self.configTempLimit(command['configTempLimit'])
        # TODO: implement more commands

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
    def configTempLimit(self, confdict=None):
        """sets temperature limit
        """
        if confdict is None:
            confdict = {key: 400 for key in ['A', 'B', 'C', 'D']}
        for i in ['A', 'B', 'C', 'D']:
            self.LakeShore350.TemperatureLimitCommand(i, 400.)

    @pyqtSlot()
    @ExceptionHandling
    def setTemp_K(self, temp=None):
        """takes value Temp_K and uses it on function ControlSetpointCommand to set desired temperature.
        """
        if temp is not None:
            self.Temp_K_value = temp
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
        self.LakeShore350.ControlLoopPIDValuesCommand(1, self.LoopP_value, self.data[
                                                      'Loop_I_Param'], self.data['Loop_D_Param'])

    @pyqtSlot()
    @ExceptionHandling
    def setLoopI_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.data['Loop_P_Param'], self.LoopI_value, self.data['Loop_D_Param'])

    @pyqtSlot()
    @ExceptionHandling
    def setLoopD_Param(self):
        self.LakeShore350.ControlLoopPIDValuesCommand(
            1, self.data['Loop_P_Param'], self.data['Loop_I_Param'], self.LoopD_value)

    @pyqtSlot()
    @ExceptionHandling
    def startHeater(self):
        """start up Heater with Output 1 for Closed Loop PID, using Input "value" and set powerup enable to On.
        """
        self.LakeShore.OutputModeCommand(1, 1, self.sensor_values[5], 1)

    @pyqtSlot()
    @ExceptionHandling
    def setHeater_Range(self, range_value=None):
        """set Heater Range for Output 1
        """
        if range_value is None:
            self.LakeShore350.HeaterRangeCommand(1, self.Heater_Range_value)
        elif range_value is not None:
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = LakeShore350_ControlClient(
        ui_file='LakeShore_main.ui', Name='LakeShore350', identity=b'LS350')
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
