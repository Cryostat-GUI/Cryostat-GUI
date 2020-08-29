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

        mainthread.combosetProbingRate_chan1.activated['int'].connect(
            lambda value: self.setProbingSpeed(value, 1))

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
    def act_on_command(self, command: dict):
        """execute commands sent on downstream"""
        pass
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        # examples:
        if 'setInterval' in command:
            self.setInterval(command['setInterval'])
        if 'setProbingSpeed' in command:
            self.setProbingSpeed(command['setProbingSpeed'], 1)
        # if 'configTempLimit' in command:
        #     self.configTempLimit(command['configTempLimit'])
        # -------------------------------------------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------
    #  hardware communication functions
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
            getInfodata = self.running_thread_control(ILM_ControlClient(
                InstrumentAddress=self._InstrumentAddress, mainthread=self, identity=self._identity), 'Hardware', )

            getInfodata.sig_Infodata.connect(self.updateGUI)

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
        chan1 = 100 if self.data[
            'channel_1_level'] > 100 else self.data['channel_1_level']
        chan2 = 100 if self.data[
            'channel_2_level'] > 100 else self.data['channel_2_level']
        self.progressLevelHe.setValue(chan1)
        self.progressLevelN2.setValue(chan2)

        tooltip = u'ILM\nHe: {:.1f}\nN2: {:.1f}'.format(chan1, chan2)
        self.pyqt_sysTray.setToolTip(tooltip)

        self.lcdLevelHe.display(
            self.data['channel_1_level'])
        self.lcdLevelN2.display(
            self.data['channel_2_level'])
        # -----------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = DeviceGUI(
        ui_file='ILM_main.ui', Name='ILM 211', identity='ILM', InstrumentAddress='ASRL5::INSTR')
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
