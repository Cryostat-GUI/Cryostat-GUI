"""Module containing a class to run a LakeShore 350 Cryogenic Temperature Controller in a pyqt5 application

Classes:
    LakeShore350_ControlClient: a class for interfacing with a LakeShore350 temperature controller
            inherits from AbstractLoopClient
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# to be removed once this is packaged!

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets
import sys
from copy import deepcopy

from util import ExceptionHandling
from util import AbstractLoopThreadClient
from util import Window_trayService_ui
from util import AbstractMainApp

from datetime import datetime
from pyvisa.errors import VisaIOError

from Oxford.ilm211 import ilm211
# import logging


class ILM_ControlClient(AbstractLoopThreadClient):
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
    data = dict()
    sensors = dict(
        channel_1_level=1,
        channel_2_level=2)

    def __init__(self, mainthread=None, comLock=None, InstrumentAddress='', log=None, **kwargs):
        super().__init__(**kwargs)
        # self.logger = log if log else logging.getLogger(__name__)

        # here the class instance of the LakeShore should be handed
        self.__name__ = 'LakeShore350_control ' + InstrumentAddress
        # try:
        # print(self.logger, self.logger.name)

        # -------------------------------------------------------------------------------------------------------------------------
        # Interface with hardware device
        self.ILM = ilm211(InstrumentAddress=InstrumentAddress)

        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # initial configurations for the hardware device
        self.control_state = 3
        self.interval = 3

        self.setControl()
        # -------------------------------------------------------------------------------------------------------------------------

        # -------------------------------------------------------------------------------------------------------------------------
        # GUI: passing GUI interactions to the corresponding slots
        # Examples:

        # mainthread.spinSetLoopP_Param.valueChanged.connect(lambda value: self.gettoset_LoopP_Param(value))
        # mainthread.spinSetLoopP_Param.editingFinished.connect(self.setLoopP_Param)

        # mainthread.spinSetLoopI_Param.valueChanged.connect(lambda value: self.gettoset_LoopI_Param(value))
        # mainthread.spinSetLoopI_Param.editingFinished.connect(self.setLoopI_Param)

        # mainthread.spinSetLoopD_Param.valueChanged.connect(lambda value: self.gettoset_LoopD_Param(value))
        # mainthread.spinSetLoopD_Param.editingFinished.connect(self.setLoopD_Param)

        # -------------------------------------------------------------------------------------------------------------------------

        mainthread.spin_threadinterval.valueChanged.connect(
            lambda value: self.setInterval(value))


    # @control_checks
    @ExceptionHandling
    def running(self):
        """
        Try to extract all current data from LakeShore350,
        and emit signal, sending the data
        """
        # print('run')
        self.run_finished = False
        # -------------------------------------------------------------------------------------------------------------------------

        # data collection for to be exposed on the data upstream
        # to be stored in self.data
        # example:

        for key in self.sensors:
            self.data[key] = self.ILM.getValue(self.sensors[key]) * 0.1


        self.data['realtime'] = datetime.now()
        # -------------------------------------------------------------------------------------------------------------------------
        self.sig_Infodata.emit(deepcopy(self.data))
        self.run_finished = True
        # data is being sent by the zmqClient class automatically

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



class DeviceGUI(AbstractMainApp, Window_trayService_ui):
    """This is the LakeShore GUI Window"""

    sig_arbitrary = pyqtSignal()
    sig_assertion = pyqtSignal(str)

    def __init__(self, **kwargs):
        self.kwargs = deepcopy(kwargs)
        del kwargs['identity']
        del kwargs['InstrumentAddress']
        self._identity = self.kwargs['identity']
        self._InstrumentAddress = self.kwargs['InstrumentAddress']
        # print('GUI pre')
        super().__init__(**kwargs)
        # print('GUI post')
        # loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)

        self.__name__ = 'LakeShore_Window'
        self.controls = [self.groupSettings]

        QTimer.singleShot(0, self.run_Hardware)

    @pyqtSlot()
    def run_Hardware(self):
        """start/stop the LakeShore350 thread"""

        try:
            getInfodata = self.running_thread_control(Template_ControlClient(
                InstrumentAddress=self._InstrumentAddress, mainthread=self, identity=self._identity), 'Hardware', )

            getInfodata.sig_Infodata.connect(self.updateGUI)


        self.combosetProbingRate_chan1.activated['int'].connect(
            lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 1))
# self.ILM_window.combosetProbingRate_chan2.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 2))

        self.spin_threadinterval.valueChanged.connect(
            lambda value: self.threads['control_ILM'][0].setInterval(value))

        except (VisaIOError, NameError) as e:
            # self.show_error_general('running: {}'.format(e))
            self.logger_personal.exception(e)

    @pyqtSlot(dict)
    def updateGUI(self, data):
        """
            Store Device data in self.data, update values in GUI
        """
        self.data.update(data)


        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained


        # -----------------------------------------------------------------------------------------------------------
        # update the GUI
        # Examples:
        chan1 = 100 if self.data['channel_1_level'] > 100 else self.data['channel_1_level']
        chan2 = 100 if self.data['channel_2_level'] > 100 else self.data['channel_2_level']
        self.progressLevelHe.setValue(chan1)
        self.progressLevelN2.setValue(chan2)

        self.lcdLevelHe.display(
            self.data['channel_1_level'])
        self.lcdLevelN2.display(
            self.data['channel_2_level'])
        # -----------------------------------------------------------------------------------------------------------



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = DeviceGUI(
        ui_file='Template_main.ui', Name='Template', identity=b'templ', InstrumentAddress='')
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
