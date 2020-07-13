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


class Template_ControlClient(AbstractLoopClient, Window_trayService_ui):
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
        Temp_K=None,)

    def __init__(self, comLock=None, InstrumentAddress='', log=None, **kwargs):
        super().__init__(**kwargs)
        # self.logger = log if log else logging.getLogger(__name__)

        # here the class instance of the LakeShore should be handed
        self.__name__ = 'LakeShore350_control ' + InstrumentAddress
        # try:
        # print(self.logger, self.logger.name)

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        # Example:
        # self.LakeShore350 = LakeShore350(
        #     InstrumentAddress=InstrumentAddress, comLock=comLock)

        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        # Example:
        # self.initiating_PID()
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots
        # Examples:

        # self.spinSetLoopP_Param.valueChanged.connect(lambda value: self.gettoset_LoopP_Param(value))
        # self.spinSetLoopP_Param.editingFinished.connect(self.setLoopP_Param)

        # self.spinSetLoopI_Param.valueChanged.connect(lambda value: self.gettoset_LoopI_Param(value))
        # self.spinSetLoopI_Param.editingFinished.connect(self.setLoopI_Param)

        # self.spinSetLoopD_Param.valueChanged.connect(lambda value: self.gettoset_LoopD_Param(value))
        # self.spinSetLoopD_Param.editingFinished.connect(self.setLoopD_Param)

        # -------------------------------------------------------------------------------------------------------------------------

        self.spin_threadinterval.valueChanged.connect(
            lambda value: self.setInterval(value))


    # @control_checks
    @ExceptionHandling
    def running(self):
        """
        Try to extract all current data from LakeShore350,
        and emit signal, sending the data
        """
        # print('run')
        # -------------------------------------------------------------------------------------------------------------------------

        # data collection for to be exposed on the data upstream
        # to be stored in self.data
        # example:
        # self.data['Temp_K'] = self.LakeShore350.ControlSetpointQuery(1)
        self.data['realtime'] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.comms_upstream.send_multipart(
            [self.comms_name, enc(json.dumps(self.data))])

    @ExceptionHandling
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        pass
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        # examples:
        # if 'setTemp_K' in command:
        #     self.setTemp_K(command['setTemp_K'])
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        # -------------------------------------------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    #  hardware communication functions
    # Examples:

    # @ExceptionHandling
    # def initiating_PID(self):
    #     temp_list0 = self.LakeShore350.ControlLoopPIDValuesQuery(1)
    #     self.LoopP_value = temp_list0[0]
    #     self.LoopI_value = temp_list0[1]
    #     self.LoopD_value = temp_list0[2]

    # @ExceptionHandling
    # def configTempLimit(self, confdict=None):
    #     """sets temperature limit
    #     """
    #     if confdict is None:
    #         confdict = {key: 400 for key in ['A', 'B', 'C', 'D']}
    #     for i in ['A', 'B', 'C', 'D']:
    #         self.LakeShore350.TemperatureLimitCommand(i, 400.)

    # @pyqtSlot()
    # @ExceptionHandling
    # def setTemp_K(self, temp=None):
    #     """takes value Temp_K and uses it on function ControlSetpointCommand to set desired temperature.
    #     """
    #     if temp is not None:
    #         self.Temp_K_value = temp
    #     self.LakeShore350.ControlSetpointCommand(1, self.Temp_K_value)
    #     self.LakeShore350.ControlSetpointRampParameterCommand(
    #         1, self.Ramp_status_internal, self.Ramp_Rate_value)

    # @ExceptionHandling
    # def read_Temperatures(self):
    #     sensors = dict()
    #     sensor_names = ['Sensor_1_K', 'Sensor_2_K', 'Sensor_3_K', 'Sensor_4_K']
    #     temp_list = self.LakeShore350.KelvinReadingQuery(0)

    #     for idx, sens in enumerate(sensor_names):
    #         sensors[sens] = temp_list[idx]
    #     return sensors

    # @pyqtSlot()
    # @ExceptionHandling
    # def setLoopP_Param(self):
    #     self.LakeShore350.ControlLoopPIDValuesCommand(1, self.LoopP_value, self.data[
    #                                                   'Loop_I_Param'], self.data['Loop_D_Param'])

    # @pyqtSlot()
    # @ExceptionHandling
    # def setLoopI_Param(self):
    #     self.LakeShore350.ControlLoopPIDValuesCommand(
    #         1, self.data['Loop_P_Param'], self.LoopI_value, self.data['Loop_D_Param'])

    # @pyqtSlot()
    # @ExceptionHandling
    # def setLoopD_Param(self):
    #     self.LakeShore350.ControlLoopPIDValuesCommand(
    #         1, self.data['Loop_P_Param'], self.data['Loop_I_Param'], self.LoopD_value)


    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    # GUI value acceptance functions
    # Examples:


    # @pyqtSlot()
    # def gettoset_Temp_K(self, value):
    #     self.Temp_K_value = value

    # @pyqtSlot()
    # def gettoset_LoopP_Param(self, value):
    #     self.LoopP_value = value

    # @pyqtSlot()
    # def gettoset_LoopI_Param(self, value):
    #     self.LoopI_value = value

    # @pyqtSlot()
    # def gettoset_LoopD_Param(self, value):
    #     self.LoopD_value = value


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = Template_ControlClient(
        ui_file='LakeShore_main.ui', Name='LakeShore350', identity=b'LS350', InstrumentAddress='')
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
