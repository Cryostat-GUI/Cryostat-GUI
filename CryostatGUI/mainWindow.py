"""  -----------------------------------------------------------------------------------
    Main Module of the Cryostat-GUI built for a custom setup PPMS at TU Wien, Austria
    (Technical University of Vienna, Austria)
     The cryostat is an Oxford Spectromag, controlled by:
        - Oxford:
            - Intelligent Temperature Controller (ITC) 503
            - Intelligent Level Meter (ILM) 211
            - Intelligent Power Supply (IPS) 120-10
        - LakeShore 350 Temperature Controller
     Measurements will be performed with:
    - Keithley:
        - 2182A Nanovoltmeter (x3)
        - 6221 Current Source (AC and DC)
        - DMM7510 7 1/2 Digital Multimeter
        - 2700 Multimeter / Data Acquisition System
        - SR830 Lock-In Amplifier
        - SR860 Lock-In Amplifier

    Classes:
    mainWindow:
        The main GUI class for the PyQt application
    Author(s):
        bklebel (Benjamin Klebel)
        adtera (Armin Tezer)
        Acronis
----------------------------------------------------------------------------------------
"""

import time

a = time.time()

from PyQt5 import QtWidgets, QtGui

# from PyQt5.QtCore import QObject
# from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QSettings

# from PyQt5.QtWidgets import QtAlignRight
from PyQt5.uic import loadUi

import os
import sys
import datetime as dt
from threading import Lock
import numpy as np
from copy import deepcopy
# from importlib import reload
import sqlite3
import logging
# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
import json

# from logging.handlers import RotatingFileHandler

from pyvisa.errors import VisaIOError
import visa

import measureSequences as mS

# import Oxford
from Oxford.ITC_control import ITC_Updater
from Oxford.ILM_control import ILM_Updater
from Oxford.IPS_control import IPS_Updater
from LakeShore.LakeShore350_Control import LakeShore350_Updater
from Keithley.Keithley2182_Control import Keithley2182_Updater
from Keithley.Keithley6221_Control import Keithley6221_Updater

from LockIn.LockIn_SR830_control import SR830_Updater

# from Sequence import OneShot_Thread
from Sequence import OneShot_Thread_multichannel
from Sequence import Sequence_Thread

from loggingFunctionality.logger import main_Logger
from loggingFunctionality.logger import live_Logger
from loggingFunctionality.logger import measurement_Logger
from loggingFunctionality.logger import Logger_configuration

from loggingFunctionality.sqlBaseFunctions import SQLiteHandler

from settings import windowSettings

from util import Window_ui
from util import convert_time
from util import convert_time_searchable
from util import Workerclass
from util import running_thread
# from util import noKeyError
from util import Window_plotting_specification
from util import ExceptionHandling

import zmq
from zmqcomms import zmqquery_handle
from zmqcomms import zmqquery
from zmqcomms import genericAnswer

ITC_Instrumentadress = "ASRL6::INSTR"
ILM_Instrumentadress = "ASRL5::INSTR"
IPS_Instrumentadress = "ASRL4::INSTR"
LakeShore_InstrumentAddress = "GPIB0::1::INSTR"
Keithley2182_1_InstrumentAddress = "GPIB0::2::INSTR"
Keithley2182_2_InstrumentAddress = "GPIB0::3::INSTR"
Keithley2182_3_InstrumentAddress = "GPIB0::4::INSTR"
Keithley6221_1_InstrumentAddress = "GPIB0::5::INSTR"
Keithley6221_2_InstrumentAddress = "GPIB0::6::INSTR"
SR830_InstrumentAddress = "GPIB::9"

errorfile = "Errors\\" + dt.datetime.now().strftime("%Y%m%d") + ".error"
directory = os.path.dirname(errorfile)
os.makedirs(directory, exist_ok=True)


class mainWindow(QtWidgets.QMainWindow):
    """This is the main GUI Window, where other windows will be spawned from"""

    sig_arbitrary = pyqtSignal()
    sig_assertion = pyqtSignal(str)

    sig_logging = pyqtSignal(dict)
    sig_logging_newconf = pyqtSignal(dict)
    sig_running_new_thread = pyqtSignal()

    sig_log_measurement = pyqtSignal(dict)
    sig_measure_oneshot = pyqtSignal()
    sig_measure_oneshot_start = pyqtSignal()
    sig_measure_oneshot_stop = pyqtSignal()
    # sig_softwarecontrols = pyqtSignal(dict)

    sig_ITC_useAutoPID = pyqtSignal(bool)
    sig_ITC_newFilePID = pyqtSignal(str)
    sig_ITC_setTemperature = pyqtSignal(dict)
    sig_ITC_stopSweep = pyqtSignal()

    sig_Sequence_sendingData = pyqtSignal(dict)
    sig_Sequence_sendingDataLive = pyqtSignal(dict)
    sig_Sequence_newconf = pyqtSignal(dict)
    sig_acal_active = pyqtSignal()
    sig_acal_needed = pyqtSignal()

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        loadUi(".\\configurations\\Cryostat GUI.ui", self)
        # self.setupUi(self)

        self.__name__ = 'MainWindow'
        self._logger = logging.getLogger('CryoGUI.' + __name__ + '.' + self.__class__.__name__)
        self.threads = dict(Lock=Lock())
        # self.threads = dict()
        self.threads_tiny = list()
        self.data = dict()
        self.logging_bools = dict()

        self.logging_running_ITC = False
        self.logging_running_logger = False

        self.dataLock = Lock()
        self.dataLock_live = Lock()
        self.GPIB_comLock = Lock()
        self.app = app
        with open(errorfile, "a") as f:
            f.write("{} - {}\n".format(convert_time(time.time()), "STARTUP PROGRAM"))

        QTimer.singleShot(0, self.initialize_all_windows)
        self.setWindowIcon(QtGui.QIcon("TU-Signet.png"))
        QTimer.singleShot(0, self.load_settings)

        self.sig_assertion.connect(self.show_error_general)

    def closeEvent(self, event):
        """check for a running measurement
        give the user a chance to contemplate his wish to quit the application,
        in case a measurement is currently running"""
        reply = QtWidgets.QMessageBox.Yes
        if self.OneShot_running:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Cryostat-GUI",
                "A measurement is running! \nAre you sure to quit?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )

        if reply == QtWidgets.QMessageBox.Yes:
            super().closeEvent(event)
            self.app.quit()
        else:
            event.ignore()

    def initialize_all_windows(self):
        """window and GUI initialisatoins"""

        self.setup_logging_base()
        # self.setup_logging()

        self.window_SystemsOnline = Window_ui(
            ui_file=".\\configurations\\Systems_online.ui"
        )
        self.actionSystems_Online.triggered.connect(
            lambda: self.window_SystemsOnline.show()
        )

        self.initialize_zmq()
        self.initialize_settings()

        self.initialize_window_ITC()
        self.initialize_window_ILM()
        self.initialize_window_IPS()
        self.initialize_window_Log_conf()
        self.initialize_window_LakeShore350()
        self.initialize_window_Keithley()
        self.initialize_window_LockIn()
        self.initialize_window_Errors()
        self.show_data()
        self.window_SystemsOnline.checkactionLogging_LIVE.toggled["bool"].connect(
            self.run_logger_live
        )

        self.initialize_window_OneShot()
        self.controls = [
            self.ITC_window.groupSettings,
            self.ILM_window.groupSettings,
            self.IPS_window.groupSettings,
            self.LakeShore350_window.groupSettings,
        ]
        self.controls_Lock = Lock()

        self.initialize_window_Sequences()
        self.initialize_mdiArea()

        self.softwarecontrol_check()
        self.softwarecontrol_timer = QTimer()
        self.softwarecontrol_timer.timeout.connect(self.softwarecontrol_check)
        self.softwarecontrol_timer.start(100)

        # start logging only after GUI initialisations
        QTimer.singleShot(1e2, self.setup_logging)

    def initialize_zmq(self):
        '''set up zmq communications'''
        self._logger.debug('initializing zmq communications')
        self.zmq_context = zmq.Context()
        self.zmq_smain_inproc = self.zmq_context.socket(zmq.REP)
        self.zmq_smain_inproc.bind("inproc://main_line")

        self.zmq_smain_tcp = self.zmq_context.socket(zmq.REP)
        self.zmq_smain_tcp.bind(f"tcp://*:{5556}")

        self.timer_zmqhandling = QTimer()
        self.timer_zmqhandling.timeout.connect(self.zmq_handling)
        self.timer_zmqhandling.start(1e2)
        # QTimer.singleShot(1e2, self.zmq_handling)

    # @pyqtSlot()
    def zmq_handling(self):
        '''handle any messages which might have arrived'''
        # self._logger.debug('handling zmq requests')
        zmqquery_handle(self.zmq_smain_inproc, self.zmq_handlefunction)
        zmqquery_handle(self.zmq_smain_tcp, self.zmq_handlefunction)
        # self._logger.debug('handled zmq requests')
        # QTimer.singleShot(1e2, self.zmq_handling)

    def zmq_handlefunction(self, socket, message):
        '''handle incoming zmq requests'''
        self._logger.debug(
            f'handling message: {message} for socket: {socket}')
        if message == b'data':
            # with self.dataLock:
            #     jdata = json.dumps(self.data)
            # socket.send(jdata.encode('utf-8'))
            socket.send_json(self.data)
        elif message == b'dataLive':
            # with self.dataLock_live:
            #     jdata = json.dumps(self.data_live)
            # socket.send(jdata.encode('utf-8'))
            socket.send_json(self.data_live)

        else:
            dic1 = '{'
            dic2 = b'{'
            d_bool = False
            for d in [dic1, dic2]:
                try:
                    d_bool = message.startswith(d)
                except TypeError:
                    pass
            if d_bool:
                mes_dict = json.loads(message)
                # TODO: handle received data
                raise genericAnswer(f'I do not know how to reply to that: {mes_dict}')
            else:
                # the genericAnswer Exception is caught in zmqquery_handle()
                raise genericAnswer(f'I do not know how to reply to that: {message}')

    def setup_logging_base(self):
        pass
        # self.logger_all = logging.getLogger()
        # self._logger = logging.getLogger('CryostatGUI.main')

        # self.Log_DBhandler = SQLiteHandler(
        #     db='Errors\\' + dt.datetime.now().strftime('%Y%m%d') + '_dblog.db')
        # self.Log_DBhandler.setLevel(logging.DEBUG)

        # self._logger.setLevel(logging.DEBUG)
        # self.logger_all.setLevel(logging.ERROR)
        # # self._logger.addHandler(self.Log_DBhandler)

        # handler = logging.StreamHandler(sys.stdout)
        # handler.setLevel(logging.ERROR)
        # formatter = logging.Formatter(
        #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # handler.setFormatter(formatter)
        # self._logger.addHandler(handler)
        # self.logger_all.addHandler(handler)

    def setup_logging(self):
        """set up the logger, handler, for now in DEBUG
        TODO: connect logging levels with GUI preferences"""
        pass
        # self.logger_all.setLevel(logging.INFO)

        # self.logger_all.addHandler(self.Log_DBhandler)

    def load_settings(self):
        """load all settings store in the QSettings
        set corresponding values in the 'Global Settings' window"""
        settings = QSettings("TUW", "CryostatGUI")
        try:
            self.window_settings.temp_ITC_useAutoPID = bool(
                settings.value("ITC_useAutoPID", int)
            )
            self.window_settings.temp_ITC_PIDFile = settings.value(
                "ITC_PIDFile", str)
        except KeyError as e:
            QTimer.singleShot(20 * 1e3, self.load_settings)
            self.show_error_general(f"could not find a key: {e}")
            self._logger.warning(f"key {e} was not found in the settings")
        del settings

        self.window_settings.checkUseAuto.setChecked(
            self.window_settings.temp_ITC_useAutoPID
        )
        if isinstance(self.window_settings.temp_ITC_PIDFile, str):
            text = self.window_settings.temp_ITC_PIDFile
        else:
            text = ""
        self.window_settings.lineConfFile.setText(text)

    def softwarecontrol_toggle_locking(self, value):
        """acquire/release the controls Lock
        this is used to control the disabling/enabling of GUI elements,
        in case of a running sequence/measurement"""
        if value:
            self.controls_Lock.acquire()
        else:
            self.controls_Lock.release()

    def softwarecontrol_check(self):
        """disable all respective GUI elements in case
            the controls_lock is locked
            thus prevent interference of the user
                with a running sequence/measurement
        """
        # try:
        if self.controls_Lock.locked():
            for c in self.controls:
                c.setEnabled(False)
        else:
            for c in self.controls:
                c.setEnabled(True)

    def running_thread_control(self, worker, dataname, threadname, info=None, **kwargs):
        """
            run a specified worker class in a thread
                this should be a device controlling thread
            add a corresponding entry in the data dictionary
            add the thread and worker-class instances to the threads dictionary

            return: the worker-class instance
        """
        worker, thread = running_thread(worker)

        if dataname in self.data or dataname is None:
            pass
        else:
            with self.dataLock:
                self.data[dataname] = dict()
        with self.threads["Lock"]:
            # this needs to be locked when a new thread is added, as otherwise
            # the thread locking context manager would try to unlock the new thread
            # before it was ever locked, resulting in a crash
            self.threads[threadname] = (worker, thread)
        self.sig_running_new_thread.emit()

        return worker

    def running_thread_tiny(self, worker):
        """
            run a specified worker class in a thread
                this is a small worker which performs one single task
                intended to be used in conjuction with util.Workerclass

            return: None
        """
        worker, thread = running_thread(worker)
        self.threads_tiny.append((worker, thread))
        # TODO there should be another worker, who regularly checks which of these
        # are still alive, and removes the dead ones from the list, in order
        # to prevent a memory leak

    def stopping_thread(self, threadname):
        """Stop the thread specified by the argument threadname, delete its entry in self.threads"""

        # self.threads[threadname][0].stop()
        self.threads[threadname][1].quit()
        self.threads[threadname][1].wait()
        with self.threads["Lock"]:
            del self.threads[threadname]

    def show_error_general(self, text):
        """generic method to show errors

        error handling and showing different types of errors differently could
        be handled here. For now, it just shows all errors in the repsective
        window
        """
        with open(errorfile, "a") as f:
            f.write("{} - {}\n".format(convert_time(time.time()), text))
        self.show_error_textBrowser(text)

    def show_error_textBrowser(self, text):
        """ append error to Error window"""
        self.Errors_window.textErrors.append(
            "{} - {}".format(dt.datetime.now().strftime("%Y-%m-%d  %H:%M:%S.%f"), text)
        )
        if not self.Errors_window.checkSilence.isChecked():
            self.Errors_window.show()
            self.Errors_window.raise_()
        # self.Errors_window.activateWindow()

    def show_window(self, window, boolean=None):
        """show or close a window"""
        if boolean is not None:
            if boolean:
                window.show()
                window.raise_()
                # window.activateWindow()
                # print('showing:', window)
            else:
                window.close()
        else:
            window.show()
            window.raise_()

    def initialize_settings(self):
        """initialise the settings window"""

        # store signals in ordered fashion for easy retrieval
        self.sigs = dict(ITC=dict(useAutocheck=self.sig_ITC_useAutoPID,
                                  newFilePID=self.sig_ITC_newFilePID,
                                  setTemp=self.sig_ITC_setTemperature,
                                  stopSweep=self.sig_ITC_stopSweep
                                  ),
                         Sequence=dict(data=self.sig_Sequence_sendingData,
                                       dataLive=self.sig_Sequence_sendingDataLive,
                                       newconf=self.sig_Sequence_newconf),
                         )

        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue('Sequence_PresetsPath',
                          './configurations/presets_sequences/')

        del settings

        self.window_settings = windowSettings(signals=self.sigs, zmqcontext=self.zmq_context, data=dict(
            data=self.data, dataLock=self.dataLock))
        self.actionSettings.triggered.connect(
            lambda: self.show_window(self.window_settings, True))

    # ------ Sequences -----------

    def initialize_window_Sequences(self):
        """initialize Sequence running functionalitys"""
        self.SequenceRunningLock = Lock()
        self.timerSequenceWindowsActive = QTimer()
        self.timerSequenceWindowsActive.timeout.connect(
            self.Sequence_SetActiveSequenceName)
        self.timerSequenceWindowsActive.start(100)

        self.SequencePaused = False

    def initialize_mdiArea(self):
        """initialise all commands for the mdiArea and subwindows"""
        self.actionNew_Sequence.triggered.connect(self.Sequence_newWindow)
        self.mdiArea_windows = dict()
        self.mdiArea_SequenceCount = 0
        self.pushSequenceRun.clicked.connect(self.Sequence_running)
        self.pushSequenceAbort.clicked.connect(self.Sequence_abort)
        self.pushSequencePause.clicked.connect(self.Sequence_pause)

    def Sequence_newWindow(self):
        SB = mS.Sequence_builder(display_only=True)
        SB.window_FileDialogOpen()
        self.mdiArea_SequenceCount += 1
        name = f'Sequence_subwindow_{self.mdiArea_SequenceCount}'
        self._logger.debug(
            'new Sequence window, sequence_file: {}'.format(SB.sequence_file))
        self.mdiArea_newWindow(SB, name)

    def Sequence_SetActiveSequenceName(self):
        try:
            SB = self.mdiArea.activeSubWindow().widget()
            file = SB.sequence_file
            self.labelSequenceSelected.setText(os.path.basename(file))
        except AttributeError:
            pass

    @pyqtSlot()
    def mdiArea_newWindow(self, window, name):

        # window = mS.Sequence_builder()

        sub = QtWidgets.QMdiSubWindow()

        sub.setWidget(window)
        # sub.setWindowTitle("subwindow"+str(MainWindow.count))
        self.mdiArea.addSubWindow(sub)
        sub.show()
        self.mdiArea_windows[name] = [window, sub]

        window.sig_closing.connect(lambda: self.mdiArea_removeWindow(name))

    def mdiArea_removeWindow(self, name):
        self.mdiArea.activateNextSubWindow()
        del self.mdiArea_windows[name]
        if 'Sequence' in name:
            self.mdiArea_SequenceCount -= 1

    @pyqtSlot()
    def Sequence_running(self) -> None:
        """acquire Lock for running sequences,
        get the data from the active window
        start the sequence,
        change pushButton parameters
        """
        self.SequenceRunningLock.acquire()
        try:
            SB = self.mdiArea.activeSubWindow().widget()
        except AttributeError:
            self._logger.warning(
                'Tried to run a sequence without active Sequence!')
            self.SequenceRunningLock.release()
            return
        self._logger.debug(str(SB.data))
        self.pushSequenceAbort.setEnabled(True)
        self.pushSequenceRun.setEnabled(False)
        self.labelSequenceStatus.setText(
            'Running: \n' + os.path.basename(SB.sequence_file))
        if 'control_Logging_live' not in self.threads:
            # self.run_logger_live(True)
            self.window_SystemsOnline.checkactionLogging_LIVE.setChecked(True)

        self.Sequence_run(SB.data)

    @pyqtSlot(str)
    def Sequence_finished(self, exitcode: str) -> None:
        """release Lock for running sequences, change pushButton parameters,
        report exitcode"""
        self.SequenceRunningLock.release()
        self.pushSequenceAbort.setEnabled(False)
        self.pushSequenceRun.setEnabled(True)
        self.labelSequenceStatus.setText('Idle')
        self.show_error_general('Sequence finished with exitcode: ' + exitcode)

    def Sequence_sendingData(self):
        """sending data to the sequence thread"""
        self.sigs['Sequence']['data'].emit(self.data)
        self.sigs['Sequence']['dataLive'].emit(self.data_live)

    def Sequence_run(self, sequence: list) -> None:
        """"""

        self.Sequencedata_timer = QTimer()
        self.Sequencedata_timer.timeout.connect(self.Sequence_sendingData)
        # self.Sequencedata_timer.start(1e3)

        thresholds = dict(
            threshold_T_K=260,
            threshold_Tmean_K=260,
            threshold_stderr_rel=100,
            threshold_relslope_Kpmin=100,
            threshold_slope_residuals=100)
        tempdefinition = ['LakeShore350', 'Sensor_1_K']
        tempdefinition = ['ITC', 'Sensor_1_K']
        try:
            if 'Sequence' in self.threads:
                self.stopping_thread('Sequence')
            sThread = self.running_thread_control(
                Sequence_Thread(sequence=sequence,
                                # data=self.data,
                                # dataLive=self.data_live,
                                # datalock=self.dataLock,
                                # data_LiveLock=self.dataLock_live,
                                device_signals=self.sigs,
                                thresholdsconf=thresholds,
                                tempdefinition=tempdefinition,
                                controlsLock=self.controls_Lock,
                                zmqcontext=self.zmq_context,
                                ), None, 'Sequence')

            sThread.sig_message.connect(self.show_error_general)
            sThread.sig_assertion.connect(self.show_error_general)
            sThread.sig_finished.connect(self.Sequence_finished)

        except AttributeError as e:
            self._logger.exception(e)
            self.Sequence_finished('AttributeError')

    def Sequence_abort(self):
        try:
            self.threads['Sequence'][0].stop()
            self.stopping_thread('Sequence')
            self.Sequencedata_timer.stop()
        except KeyError:
            pass
            self.show_error_general('Sequence: no sequence running!')

    def Sequence_pause(self):
        if self.SequencePaused:
            self.threads['Sequence'][0].continue_()
            self.SequencePaused = False
            self.pushSequencePause.setText('Pause')
            self.Sequencedata_timer.start(1e3)
        else:
            self.SequencePaused = True
            self.threads['Sequence'][0].pause()
            self.pushSequencePause.setText('Continue')
            self.Sequencedata_timer.stop()

    # ------- plotting
    def show_data(self):  # a lot of work to do
        """connect GUI signals for plotting, setting up some of the needs of plotting"""
        # self.action_plotDatabase.triggered.connect(
        #     self.show_dataplotdb_configuration)
        self.action_plotLiveMultiple.triggered.connect(
            self.show_dataplotlive_configuration_new
        )
        # self.action_plotLive.triggered.connect(
        #     self.show_dataplotlive_configuration)
        self.windows_plotting = []
        self.plotting_window_count = 0

    def show_dataplotlive_configuration_new(self):
        """new plotting specification procedure"""
        self.window_configuration = Window_plotting_specification(self)
        self.window_configuration.sig_error.connect(self.show_error_general)

    def plotting_deleting_window(self, window, number):
        """delete the window entry in the list of windows
            was planned to fix the memory leak, not sure if it really works
            this is operated from Window_plotting_specification in util.py!
        """
        for ct, w in enumerate(self.windows_plotting):
            if w.number == number:
                del self.windows_plotting[ct]

    def store_data(self, data: dict, device: str) -> None:
        """store the timed data in the system list"""

        timedict = {
            "timeseconds": time.time(),
            "ReadableTime": convert_time(time.time()),
            "SearchableTime": convert_time_searchable(time.time()),
        }
        data.update(timedict)
        with self.dataLock:
            self.data[device].update(data)

    # ------- Oxford Instruments
    # ------- ------- ITC
    def initialize_window_ITC(self):
        """initialize ITC Window"""
        self.ITC_window = Window_ui(ui_file=".\\Oxford\\ITC_control.ui")
        self.ITC_window.sig_closing.connect(
            lambda: self.action_show_ITC.setChecked(False)
        )

        self.window_SystemsOnline.checkaction_run_ITC.clicked["bool"].connect(
            self.run_ITC
        )
        self.action_show_ITC.triggered["bool"].connect(
            lambda value: self.show_window(self.ITC_window, value)
        )
        # self.mdiArea.addSubWindow(self.ITC_window)

        self.ITC_values = dict(setTemperature=4, SweepRate=2)

    @pyqtSlot(float)
    @ExceptionHandling
    def ITC_fun_setTemp_valcha(self, value):
        # self.threads['control_ITC'][0].gettoset_Temperature(value)
        self.ITC_values["setTemperature"] = value

    @pyqtSlot(float)
    @ExceptionHandling
    def ITC_fun_setRamp_valcha(self, value):
        self.ITC_values["SweepRate"] = value
        # self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot(bool)
    @ExceptionHandling
    def ITC_fun_checkSweep_toggled(self, boolean):
        self.ITC_values["Sweep_status_software"] = boolean
        # if boolean:
        #     self.ITC_fun_setSweep()
        # else:
        #     with self.dataLock:
        #         settempdevice = self.data['ITC']['set_temperature']
        #     self.sigs['ITC']['stopSweep'].emit()
        #     self.sigs['ITC']['setTemp'].emit(settempdevice)

    @pyqtSlot()
    @ExceptionHandling
    def ITC_fun_sendConfTemp(self):
        self.ITC_fun_startTemp(isSweep=self.ITC_values['Sweep_status_software'],
                               isSweepStartCurrent=True,
                               setTemp=self.ITC_values['setTemperature'],
                               end=self.ITC_values['setTemperature'],
                               SweepRate=self.ITC_values['SweepRate'])

    @pyqtSlot(dict)
    @ExceptionHandling
    def ITC_fun_routeSignalTemps(self, d: dict) -> None:
        self.ITC_fun_startTemp(isSweep=d['Sweep_status_software'],
                               isSweepStartCurrent=d['isSweepStartCurrent'],
                               setTemp=d['setTemperature'],
                               end=d['setTemperature'],
                               SweepRate=d['SweepRate'])

    @pyqtSlot(dict)
    def ITC_fun_startTemp(self, isSweep=False, isSweepStartCurrent=True, setTemp=4, start=None, end=5, SweepRate=2):
        self.sigs['ITC']['setTemp'].emit(dict(isSweep=isSweep,
                                              isSweepStartCurrent=isSweepStartCurrent,
                                              setTemp=setTemp,
                                              start=start,
                                              end=end,
                                              SweepRate=SweepRate))

    @pyqtSlot(bool)
    def run_ITC(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""

        if boolean:
            try:
                getInfodata = self.running_thread_control(
                    ITC_Updater(
                        InstrumentAddress=ITC_Instrumentadress,
                        mainthreadSignals=self.sigs["ITC"],
                    ),
                    "ITC",
                    "control_ITC",
                )

                self.ITC_values["setTemperature"] = getInfodata.ITC.getValue(0)
                with getInfodata.lock:
                    sweepstatus = getInfodata.checksweep(stop=False)
                self.ITC_values["Sweep_status_software"] = sweepstatus
                self.ITC_window.checkSweep.setChecked(sweepstatus)

                getInfodata.sig_Infodata.connect(self.store_data_itc)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_general)
                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general("ITC: timeout")
                )

                # setting ITC values by GUI ITC window
                self.ITC_window.spinsetTemp.valueChanged.connect(
                    self.ITC_fun_setTemp_valcha
                )
                # self.ITC_window.spinsetTemp.editingFinished.connect(
                #     self.ITC_fun_setTemp_edfin)

                self.ITC_window.checkSweep.toggled["bool"].connect(
                    self.ITC_fun_checkSweep_toggled
                )

                self.ITC_window.dspinSetRamp.valueChanged.connect(
                    self.ITC_fun_setRamp_valcha
                )

                self.ITC_window.commandSendConfTemp.clicked.connect(
                    self.ITC_fun_sendConfTemp
                )

                def change_gas(self):
                    """to be worked in a separate worker thread (separate
                        time.sleep() from GUI)
                        change the opening percentage of the needle valve in a
                        repeatable fashion (go to zero, go to new value)
                        disable the GUI element during the operation

                        should be changed, to use signals to change GUI,
                        and possibly timers instead of time.sleep()
                        (QTimer not usefil in the second case)
                    """
                    if self.ITC_window.checkGas_gothroughzero.isChecked():
                        gas_new = self.threads["control_ITC"][0].set_gas_output
                        with self.dataLock:
                            gas_old = int(self.data["ITC"]["gas_flow_output"])
                        if gas_new == 0:
                            time_wait = 60 / 1e2 * gas_old + 5
                            self.threads["control_ITC"][0].setGasOutput()

                            self.ITC_window.spinsetGasOutput.setEnabled(False)
                            time.sleep(time_wait)
                            self.ITC_window.spinsetGasOutput.setEnabled(True)
                        else:
                            time1 = 60 / 1e2 * gas_old + 5
                            time2 = 60 / 1e2 * gas_new + 5
                            self.threads["control_ITC"][
                                0].gettoset_GasOutput(0)
                            self.threads["control_ITC"][0].setGasOutput()
                            self.ITC_window.spinsetGasOutput.setEnabled(False)
                            time.sleep(time1)
                            self.threads["control_ITC"][
                                0].gettoset_GasOutput(gas_new)
                            self.threads["control_ITC"][0].setGasOutput()
                            time.sleep(time2)
                            self.ITC_window.spinsetGasOutput.setEnabled(True)
                    else:
                        self.threads["control_ITC"][0].setGasOutput()

                self.ITC_window.spinsetGasOutput.valueChanged.connect(
                    lambda value: getInfodata.gettoset_GasOutput(value)
                )
                self.ITC_window.spinsetGasOutput.editingFinished.connect(
                    lambda: self.running_thread_tiny(
                        Workerclass(change_gas, self))
                )

                self.ITC_window.spinsetHeaterPercent.valueChanged.connect(
                    lambda value: getInfodata.gettoset_HeaterOutput(value)
                )
                self.ITC_window.spinsetHeaterPercent.editingFinished.connect(
                    lambda: getInfodata.setHeaterOutput()
                )

                self.ITC_window.spinsetProportionalID.valueChanged.connect(
                    lambda value: getInfodata.gettoset_Proportional(value)
                )
                self.ITC_window.spinsetProportionalID.editingFinished.connect(
                    lambda: getInfodata.setProportional()
                )

                self.ITC_window.spinsetPIntegrationD.valueChanged.connect(
                    lambda value: getInfodata.gettoset_Integral(value)
                )
                self.ITC_window.spinsetPIntegrationD.editingFinished.connect(
                    lambda: getInfodata.setIntegral()
                )

                self.ITC_window.spinsetPIDerivative.valueChanged.connect(
                    lambda value: getInfodata.gettoset_Derivative(value)
                )
                self.ITC_window.spinsetPIDerivative.editingFinished.connect(
                    lambda: getInfodata.setDerivative()
                )

                self.ITC_window.combosetHeatersens.activated["int"].connect(
                    lambda value: getInfodata.setHeaterSensor(value + 1)
                )

                self.ITC_window.combosetAutocontrol.activated["int"].connect(
                    lambda value: getInfodata.setAutoControl(value)
                )

                self.ITC_window.spin_threadinterval.valueChanged.connect(
                    lambda value: getInfodata.setInterval(value)
                )

                # thread.started.connect(getInfodata.work)
                # thread.start()
                self.window_SystemsOnline.checkaction_run_ITC.setChecked(True)
                self.logging_running_ITC = True

                self.sigs["ITC"]["useAutocheck"].emit(
                    self.window_settings.temp_ITC_useAutoPID
                )
                self.sigs["ITC"]["newFilePID"].emit(
                    self.window_settings.temp_ITC_PIDFile
                )
            except (VisaIOError, NameError) as e:
                self.window_SystemsOnline.checkaction_run_ITC.setChecked(False)
                self.show_error_general(e)

        else:
            # possibly implement putting the instrument back to local operation
            self.ITC_window.spinsetTemp.valueChanged.disconnect()
            # self.ITC_window.spinsetTemp.editingFinished.disconnect()
            self.ITC_window.spinsetGasOutput.valueChanged.disconnect()
            # self.ITC_window.spinsetGasOutput.editingFinished.disconnect()
            self.ITC_window.spinsetHeaterPercent.valueChanged.disconnect()
            # self.ITC_window.spinsetHeaterPercent.editingFinished.disconnect()
            self.ITC_window.spinsetProportionalID.valueChanged.disconnect()
            self.ITC_window.spinsetProportionalID.editingFinished.disconnect()
            self.ITC_window.spinsetPIntegrationD.valueChanged.disconnect()
            self.ITC_window.spinsetPIntegrationD.editingFinished.disconnect()
            self.ITC_window.spinsetPIDerivative.valueChanged.disconnect()
            self.ITC_window.spinsetPIDerivative.editingFinished.disconnect()
            self.ITC_window.combosetHeatersens.activated["int"].disconnect()
            self.ITC_window.combosetAutocontrol.activated["int"].disconnect()
            self.ITC_window.spin_threadinterval.valueChanged.disconnect()

            self.stopping_thread("control_ITC")
            self.window_SystemsOnline.checkaction_run_ITC.setChecked(False)
            self.logging_running_ITC = False

    @pyqtSlot(dict)
    def store_data_itc(self, data):
        """
            Calculate the rate of change of Temperature on the sensors [K/min]
            Store ITC data in self.data['ITC'], update ITC_window
        """
        self.store_data(data=data, device="ITC")
        # timedict = {'timeseconds': time.time(),
        #             'ReadableTime': convert_time(time.time()),
        #             'SearchableTime': convert_time_searchable(time.time())}
        # data.update(timedict)
        with self.dataLock:
            # print('storing: ', self.time_itc[-1]-time.time(), data['Sensor_1_K'])
            # self.time_itc.append(time.time())
            # self.data['ITC'].update(data)

            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained

            for key in self.data["ITC"]:
                if self.data["ITC"][key] is None:
                    self.data["ITC"][key] = np.nan
            # if not self.data['ITC']['Sensor_1_K'] is None:
            self.ITC_window.lcdTemp_sens1_K.display(
                self.data["ITC"]["Sensor_1_K"])
            # if not self.data['ITC']['Sensor_2_K'] is None:
            self.ITC_window.lcdTemp_sens2_K.display(
                self.data["ITC"]["Sensor_2_K"])
            # if not self.data['ITC']['Sensor_3_K'] is None:
            self.ITC_window.lcdTemp_sens3_K.display(
                self.data["ITC"]["Sensor_3_K"])

            # if not self.data['ITC']['set_temperature'] is None:
            self.ITC_window.lcdTemp_set.display(
                self.data["ITC"]["set_temperature"])
            # if not self.data['ITC']['temperature_error'] is None:
            self.ITC_window.lcdTemp_err.display(
                self.data["ITC"]["temperature_error"])
            # if not self.data['ITC']['heater_output_as_percent'] is None:
            try:
                self.ITC_window.progressHeaterPercent.setValue(
                    int(self.data["ITC"]["heater_output_as_percent"])
                )
                # if not self.data['ITC']['gas_flow_output'] is None:
                self.ITC_window.progressNeedleValve.setValue(
                    int(self.data["ITC"]["gas_flow_output"])
                )
            except ValueError:
                pass
            # if not self.data['ITC']['heater_output_as_voltage'] is None:
            self.ITC_window.lcdHeaterVoltage.display(
                self.data["ITC"]["heater_output_as_voltage"]
            )
            # if not self.data['ITC']['gas_flow_output'] is None:
            self.ITC_window.lcdNeedleValve_percent.display(
                self.data["ITC"]["gas_flow_output"]
            )
            # if not self.data['ITC']['proportional_band'] is None:
            self.ITC_window.lcdProportionalID.display(
                self.data["ITC"]["proportional_band"]
            )
            # if not self.data['ITC']['integral_action_time'] is None:
            self.ITC_window.lcdPIntegrationD.display(
                self.data["ITC"]["integral_action_time"]
            )
            # if not self.data['ITC']['derivative_action_time'] is None:
            self.ITC_window.lcdPIDerivative.display(
                self.data["ITC"]["derivative_action_time"]
            )

            self.ITC_window.lcdTemp_sens1_calcerr_K.display(
                self.data["ITC"]["Sensor_1_calerr_K"]
            )

            self.ITC_window.combosetAutocontrol.setCurrentIndex(
                self.data['ITC']['autocontrol'])

    # ------- ------- ILM
    def initialize_window_ILM(self):
        """initialize ILM Window"""
        self.ILM_window = Window_ui(ui_file=".\\Oxford\\ILM_control.ui")
        self.ILM_window.sig_closing.connect(
            lambda: self.action_show_ILM.setChecked(False)
        )

        self.window_SystemsOnline.checkaction_run_ILM.clicked["bool"].connect(
            self.run_ILM
        )
        self.action_show_ILM.triggered["bool"].connect(self.show_ILM)

    @pyqtSlot(bool)
    def run_ILM(self, boolean):
        """start/stop the Level Meter thread"""
        if boolean:
            try:
                getInfodata = self.running_thread_control(
                    ILM_Updater(
                        InstrumentAddress=ILM_Instrumentadress,
                        log=self._logger
                    ),
                    "ILM",
                    "control_ILM",
                )

                getInfodata.sig_Infodata.connect(self.store_data_ilm)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general("ILM: timeout")
                )

                self.ILM_window.combosetProbingRate_chan1.activated["int"].connect(
                    lambda value: self.threads["control_ILM"][0].setProbingSpeed(
                        value, 1
                    )
                )
                # self.ILM_window.combosetProbingRate_chan2.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 2))

                self.ILM_window.spin_threadinterval.valueChanged.connect(
                    lambda value: self.threads[
                        "control_ILM"][0].setInterval(value)
                )

                self.window_SystemsOnline.checkaction_run_ILM.setChecked(True)

            except (VisaIOError, NameError) as e:
                self.window_SystemsOnline.checkaction_run_ILM.setChecked(False)
                self.show_error_general(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.window_SystemsOnline.checkaction_run_ILM.setChecked(False)
            self.stopping_thread("control_ILM")

    @pyqtSlot(bool)
    def show_ILM(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.ILM_window.show()
        else:
            self.ILM_window.close()

    @pyqtSlot(dict)
    def store_data_ilm(self, data):
        """Store ILM data in self.data['ILM'], update ILM_window"""

        self.store_data(data=data, device="ILM")
        with self.dataLock:
            # data['date'] = convert_time(time.time())
            # self.data['ILM'].update(data)

            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained
            chan1 = (
                100
                if self.data["ILM"]["channel_1_level"] > 100
                else self.data["ILM"]["channel_1_level"]
            )
            chan2 = (
                100
                if self.data["ILM"]["channel_2_level"] > 100
                else self.data["ILM"]["channel_2_level"]
            )
            self.ILM_window.progressLevelHe.setValue(chan1)
            self.ILM_window.progressLevelN2.setValue(chan2)

            self.ILM_window.lcdLevelHe.display(
                self.data["ILM"]["channel_1_level"])
            self.ILM_window.lcdLevelN2.display(
                self.data["ILM"]["channel_2_level"])

            self.MainDock_HeLevel.setValue(chan1)
            self.MainDock_N2Level.setValue(chan2)
            # print(self.data['ILM']['channel_1_level'], self.data['ILM']['channel_2_level'])

    # ------- ------- IPS
    def initialize_window_IPS(self):
        """initialize PS Window"""
        self.IPS_window = Window_ui(ui_file=".\\Oxford\\IPS_control.ui")
        self.IPS_window.sig_closing.connect(
            lambda: self.action_show_IPS.setChecked(False)
        )

        self.window_SystemsOnline.checkaction_run_IPS.clicked["bool"].connect(
            self.run_IPS
        )
        self.action_show_IPS.triggered["bool"].connect(
            lambda value: self.show_window(self.IPS_window, value)
        )

        self.IPS_window.labelStatusMagnet.setText("")
        self.IPS_window.labelStatusCurrent.setText("")
        self.IPS_window.labelStatusActivity.setText("")
        self.IPS_window.labelStatusLocRem.setText("")
        self.IPS_window.labelStatusSwitchHeater.setText("")

    @pyqtSlot(bool)
    def run_IPS(self, boolean):
        """start/stop the Powersupply thread"""

        if boolean:
            try:
                getInfodata = self.running_thread_control(
                    IPS_Updater(
                        InstrumentAddress=IPS_Instrumentadress,
                        log=self._logger
                    ),
                    "IPS",
                    "control_IPS",
                )

                getInfodata.sig_Infodata.connect(self.store_data_ips)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general("IPS: timeout")
                )

                self.IPS_window.comboSetActivity.activated["int"].connect(
                    lambda value: self.threads[
                        "control_IPS"][0].setActivity(value)
                )
                self.IPS_window.comboSetSwitchHeater.activated["int"].connect(
                    lambda value: self.threads["control_IPS"][
                        0].setSwitchHeater(value)
                )

                self.IPS_window.spinSetFieldSetPoint.valueChanged.connect(
                    lambda value: self.threads["control_IPS"][0].gettoset_FieldSetPoint(
                        value
                    )
                )
                self.IPS_window.spinSetFieldSetPoint.editingFinished.connect(
                    lambda: self.threads["control_IPS"][0].setFieldSetPoint()
                )

                self.IPS_window.spinSetFieldSweepRate.valueChanged.connect(
                    lambda value: self.threads["control_IPS"][
                        0
                    ].gettoset_FieldSweepRate(value)
                )
                self.IPS_window.spinSetFieldSweepRate.editingFinished.connect(
                    lambda: self.threads["control_IPS"][0].setFieldSweepRate()
                )

                self.IPS_window.spin_threadinterval.valueChanged.connect(
                    lambda value: self.threads[
                        "control_IPS"][0].setInterval(value)
                )

                self.window_SystemsOnline.checkaction_run_IPS.setChecked(True)

            except (VisaIOError, NameError) as e:
                self.window_SystemsOnline.checkaction_run_IPS.setChecked(False)
                self.show_error_general(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.window_SystemsOnline.checkaction_run_IPS.setChecked(False)
            self.stopping_thread("control_IPS")

    @pyqtSlot(dict)
    def store_data_ips(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""

        self.store_data(data=data, device="IPS")

        with self.dataLock:
            # data['date'] = convert_time(time.time())
            # self.data['IPS'].update(data)

            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained
            self.IPS_window.lcdFieldSetPoint.display(
                self.data["IPS"]["FIELD_set_point"]
            )
            self.IPS_window.lcdFieldSweepRate.display(
                self.data["IPS"]["FIELD_sweep_rate"]
            )

            self.IPS_window.lcdOutputField.display(
                self.data["IPS"]["FIELD_output"])
            self.IPS_window.lcdMeasuredMagnetCurrent.display(
                self.data["IPS"]["measured_magnet_current"]
            )
            self.IPS_window.lcdOutputCurrent.display(
                self.data["IPS"]["CURRENT_output"])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_set_point'])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_sweep_rate'])

            self.IPS_window.lcdLeadResistance.display(
                self.data["IPS"]["lead_resistance"]
            )

            self.IPS_window.lcdPersistentMagnetField.display(
                self.data["IPS"]["persistent_magnet_field"]
            )
            self.IPS_window.lcdTripField.display(
                self.data["IPS"]["trip_field"])
            self.IPS_window.lcdPersistentMagnetCurrent.display(
                self.data["IPS"]["persistent_magnet_current"]
            )
            self.IPS_window.lcdTripCurrent.display(
                self.data["IPS"]["trip_current"])

            self.IPS_window.labelStatusMagnet.setText(
                self.data["IPS"]["status_magnet"])
            self.IPS_window.labelStatusCurrent.setText(
                self.data["IPS"]["status_current"]
            )
            self.IPS_window.labelStatusActivity.setText(
                self.data["IPS"]["status_activity"]
            )
            self.IPS_window.labelStatusLocRem.setText(
                self.data["IPS"]["status_locrem"])
            self.IPS_window.labelStatusSwitchHeater.setText(
                self.data["IPS"]["status_switchheater"]
            )

    # ------- LakeShore 350 -------
    def initialize_window_LakeShore350(self):
        """initialize LakeShore Window"""
        self.LakeShore350_window = Window_ui(
            ui_file=".\\LakeShore\\LakeShore350_control.ui"
        )
        self.LakeShore350_window.sig_closing.connect(
            lambda: self.action_show_LakeShore350.setChecked(False)
        )

        # self.LakeShore350_window.textSensor1_Kpmin.setAlignment(QtAlignRight)

        self.window_SystemsOnline.checkaction_run_LakeShore350.clicked["bool"].connect(
            self.run_LakeShore350
        )
        self.action_show_LakeShore350.triggered[
            "bool"].connect(self.show_LakeShore350)
        self.LakeShore350_Kpmin = None

    @pyqtSlot(bool)
    def run_LakeShore350(self, boolean):
        """start/stop the LakeShore350 thread"""

        if boolean:
            try:
                getInfodata = self.running_thread_control(
                    LakeShore350_Updater(
                        InstrumentAddress=LakeShore_InstrumentAddress,
                        comLock=self.GPIB_comLock,
                        log=self._logger),
                    "LakeShore350",
                    "control_LakeShore350",
                )

                getInfodata.sig_Infodata.connect(self.store_data_LakeShore350)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general("LakeShore350: timeout")
                )

                self.window_SystemsOnline.checkaction_run_LakeShore350.setChecked(
                    True)

            except (VisaIOError, NameError) as e:
                self.window_SystemsOnline.checkaction_run_LakeShore350.setChecked(
                    False)
                self.show_error_general("running: {}".format(e))
                self._logger.exception("could not start LakeShore350")

        else:
            self.window_SystemsOnline.checkaction_run_LakeShore350.setChecked(
                False)
            self.stopping_thread("control_LakeShore350")

            self.LakeShore350_window.spinSetTemp_K.valueChanged.disconnect()
            self.LakeShore350_window.spinSetTemp_K.editingFinished.disconnect()
            self.LakeShore350_window.spinSetRampRate_Kpmin.valueChanged.disconnect()
            self.LakeShore350_window.spinSetRampRate_Kpmin.editingFinished.disconnect()
            self.LakeShore350_window.comboSetInput_Sensor.activated[
                "int"].disconnect()

    @pyqtSlot(bool)
    def show_LakeShore350(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.LakeShore350_window.show()
        else:
            self.LakeShore350_window.close()

    # def calculate_Kpmin(self, data):
    # """calculate the rate of change of Temperature"""
    # coeffs = []
    # for sensordata in self.LakeShore350_Kpmin['Sensors'].values():
    #     coeffs.append(np.polynomial.polynomial.polyfit(
    #         self.LakeShore350_Kpmin['newtime'], sensordata, deg=1))

    # integrated_diff = dict(Sensor_1_Kpmin=coeffs[0][1] * 60,
    #                        Sensor_2_Kpmin=coeffs[1][1] * 60,
    #                        Sensor_3_Kpmin=coeffs[2][1] * 60,
    #                        Sensor_4_Kpmin=coeffs[3][1] * 60)

    # data.update(integrated_diff)

    # # advancing entries to the next slot
    # for i, entry in enumerate(self.LakeShore350_Kpmin['newtime'][:-1]):
    #     self.LakeShore350_Kpmin['newtime'][i + 1] = entry
    #     self.LakeShore350_Kpmin['newtime'][0] = time.time()
    #     for key in self.LakeShore350_Kpmin['Sensors'].keys():
    #         self.LakeShore350_Kpmin['Sensors'][key][
    #             i + 1] = self.LakeShore350_Kpmin['Sensors'][key][i]
    #         self.LakeShore350_Kpmin['Sensors'][
    #             key][0] = deepcopy(data[key])

    # self.LakeShore350_Kpmin['Sensors']['Sensor_2_K'][i+1] = self.LakeShore350_Kpmin['Sensors']['Sensor_2_K'][i]
    # self.LakeShore350_Kpmin['Sensors']['Sensor_3_K'][i+1] = self.LakeShore350_Kpmin['Sensors']['Sensor_3_K'][i]
    # self.LakeShore350_Kpmin['Sensors']['Sensor_4_K'][i+1] = self.LakeShore350_Kpmin['Sensors']['Sensor_4_K'][i]

    # including the new values
    # self.LakeShore350_Kpmin['Sensors']['Sensor_2_K'][0] = deepcopy(data['Sensor_2_K'])
    # self.LakeShore350_Kpmin['Sensors']['Sensor_3_K'][0] = deepcopy(data['Sensor_3_K'])
    # self.LakeShore350_Kpmin['Sensors']['Sensor_4_K'][0] = deepcopy(data['Sensor_4_K'])

    # data.update(dict(Sensor_1_Kpmin=integrated_diff['Sensor_1_Kpmin'],
    #                     Sensor_2_Kpmin=integrated_diff['Sensor_2_Kpmin'],
    #                     Sensor_3_Kpmin=integrated_diff['Sensor_3_Kpmin'],
    #                     Sensor_4_Kpmin=integrated_diff['Sensor_4_Kpmin']))

    # return integrated_diff, data

    @pyqtSlot(dict)
    def store_data_LakeShore350(self, data):
        """
            Calculate the rate of change of Temperature on the sensors [K/min]
            Store LakeShore350 data in self.data['LakeShore350'], update LakeShore350_window
        """

        slopes = [
            "Sensor_1_K_calc_slope",
            "Sensor_2_K_calc_slope",
            "Sensor_3_K_calc_slope",
            "Sensor_4_K_calc_slope",
        ]

        # coeffs, data = self.calculate_Kpmin(data)
        try:
            with self.dataLock_live:
                if any([self.data_live["LakeShore350"][value] for value in slopes]):
                    livedata = [
                        self.data_live["LakeShore350"][value][-1] for value in slopes
                    ]
                else:
                    livedata = [0] * 4
        except AttributeError:
            self.show_error_general(
                "please start live logging for LakeShore350 slope values!"
            )
            livedata = [0] * 4
        except KeyError:
            self.show_error_general(
                "please start live logging for LakeShore350 slope values!"
            )
            livedata = [0] * 4

        for GUI_element, co in zip(
            [
                self.LakeShore350_window.textSensor1_Kpmin,
                self.LakeShore350_window.textSensor2_Kpmin,
                self.LakeShore350_window.textSensor3_Kpmin,
                self.LakeShore350_window.textSensor4_Kpmin,
            ],
            livedata,
        ):
            if not co == 0:
                GUI_element.setText("{num:=+10.4f}".format(num=co))

        # data['date'] = convert_time(time.time())
        self.store_data(data=data, device="LakeShore350")

        with self.dataLock:
            # self.data['LakeShore350'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained

            self.LakeShore350_window.progressHeaterOutput_percentage.setValue(
                self.data["LakeShore350"]["Heater_Output_percentage"]
            )
            self.LakeShore350_window.lcdHeaterOutput_mW.display(
                self.data["LakeShore350"]["Heater_Output_mW"]
            )
            self.LakeShore350_window.lcdSetTemp_K.display(
                self.data["LakeShore350"]["Temp_K"]
            )
            # self.LakeShore350_window.lcdRampeRate_Status.display(self.data['LakeShore350']['RampRate_Status'])
            self.LakeShore350_window.lcdSetRampRate_Kpmin.display(
                self.data["LakeShore350"]["Ramp_Rate"]
            )

            self.LakeShore350_window.comboSetInput_Sensor.setCurrentIndex(
                int(self.data["LakeShore350"]["Input_Sensor"]) - 1
            )
            self.LakeShore350_window.lcdSensor1_K.display(
                self.data["LakeShore350"]["Sensor_1_K"]
            )
            self.LakeShore350_window.lcdSensor2_K.display(
                self.data["LakeShore350"]["Sensor_2_K"]
            )
            self.LakeShore350_window.lcdSensor3_K.display(
                self.data["LakeShore350"]["Sensor_3_K"]
            )
            self.LakeShore350_window.lcdSensor4_K.display(
                self.data["LakeShore350"]["Sensor_4_K"]
            )

            """NEW GUI to display P,I and D Parameters
            """
            self.LakeShore350_window.lcdLoopP_Param.display(
                self.data['LakeShore350']['Loop_P_Param'])
            self.LakeShore350_window.lcdLoopI_Param.display(
                self.data['LakeShore350']['Loop_I_Param'])
            self.LakeShore350_window.lcdLoopD_Param.display(
                self.data['LakeShore350']['Loop_D_Param'])

            # self.LakeShore350_window.lcdHeater_Range.display(self.date['LakeShore350']['Heater_Range'])

    # ------- Keithley 2182 + Keithley 6221 -------
    def initialize_window_Keithley(self):
        """initialize Keithley Window"""
        self.Keithley_window = Window_ui(
            ui_file=".\\Keithley\\Keithley_control.ui")
        self.Keithley_window.sig_closing.connect(
            lambda: self.action_show_Keithley.setChecked(False)
        )

        # -------- Nanovoltmeters

        confdict2182_1 = dict(
            clas=Keithley2182_Updater,
            instradress=Keithley2182_1_InstrumentAddress,
            dataname="Keithley2182_1",
            threadname="control_Keithley2182_1",
            GUI_number1=self.Keithley_window.lcdSensor1_V,
            GUI_menu_action=self.window_SystemsOnline.checkaction_run_Nanovolt_1,
            GUI_Box=self.Keithley_window.comboBox_1,
            GUI_Display=self.Keithley_window.lcdResistance1,
            GUI_CBox_Autozero=self.Keithley_window.checkBox_Autozero_1,
            GUI_CBox_FronAutozero=self.Keithley_window.checkBox_FrontAutozero_1,
            GUI_CBox_Display=self.Keithley_window.checkBox_Display_1,
            GUI_CBox_Autorange=self.Keithley_window.checkBox_Autorange_1,
        )

        confdict2182_2 = dict(
            clas=Keithley2182_Updater,
            instradress=Keithley2182_2_InstrumentAddress,
            dataname="Keithley2182_2",
            threadname="control_Keithley2182_2",
            GUI_number1=self.Keithley_window.lcdSensor2_V,
            GUI_menu_action=self.window_SystemsOnline.checkaction_run_Nanovolt_2,
            GUI_Box=self.Keithley_window.comboBox_2,
            GUI_Display=self.Keithley_window.lcdResistance2,
            GUI_CBox_Autozero=self.Keithley_window.checkBox_Autozero_2,
            GUI_CBox_FronAutozero=self.Keithley_window.checkBox_FrontAutozero_2,
            GUI_CBox_Display=self.Keithley_window.checkBox_Display_2,
            GUI_CBox_Autorange=self.Keithley_window.checkBox_Autorange_2,
        )

        confdict2182_3 = dict(
            clas=Keithley2182_Updater,
            instradress=Keithley2182_3_InstrumentAddress,
            dataname="Keithley2182_3",
            threadname="control_Keithley2182_3",
            GUI_number1=self.Keithley_window.lcdSensor3_V,
            GUI_menu_action=self.window_SystemsOnline.checkaction_run_Nanovolt_3,
            GUI_Box=self.Keithley_window.comboBox_3,
            GUI_Display=self.Keithley_window.lcdResistance3,
            GUI_CBox_Autozero=self.Keithley_window.checkBox_Autozero_3,
            GUI_CBox_FronAutozero=self.Keithley_window.checkBox_FrontAutozero_3,
            GUI_CBox_Display=self.Keithley_window.checkBox_Display_3,
            GUI_CBox_Autorange=self.Keithley_window.checkBox_Autorange_3,
        )

        # -------- Current Sources
        confdict6221_1 = dict(
            clas=Keithley6221_Updater,
            instradress=Keithley6221_1_InstrumentAddress,
            dataname="Keithley6221_1",
            threadname="control_Keithley6221_1",
            GUI_number2=self.Keithley_window.spinSetCurrent1_mA,
            GUI_push=self.Keithley_window.pushToggleOut_1,
            GUI_menu_action=self.window_SystemsOnline.checkaction_run_Current_1,
        )

        confdict6221_2 = dict(
            clas=Keithley6221_Updater,
            instradress=Keithley6221_2_InstrumentAddress,
            dataname="Keithley6221_2",
            threadname="control_Keithley6221_2",
            GUI_number2=self.Keithley_window.spinSetCurrent2_mA,
            GUI_push=self.Keithley_window.pushToggleOut_2,
            GUI_menu_action=self.window_SystemsOnline.checkaction_run_Current_2,
        )

        self.window_SystemsOnline.checkaction_run_Nanovolt_1.clicked["bool"].connect(
            lambda value: self.run_Keithley(value, **confdict2182_1)
        )
        self.window_SystemsOnline.checkaction_run_Nanovolt_2.clicked["bool"].connect(
            lambda value: self.run_Keithley(value, **confdict2182_2)
        )
        self.window_SystemsOnline.checkaction_run_Nanovolt_3.clicked["bool"].connect(
            lambda value: self.run_Keithley(value, **confdict2182_3)
        )

        self.window_SystemsOnline.checkaction_run_Current_1.clicked["bool"].connect(
            lambda value: self.run_Keithley(value, **confdict6221_1)
        )
        self.window_SystemsOnline.checkaction_run_Current_2.clicked["bool"].connect(
            lambda value: self.run_Keithley(value, **confdict6221_2)
        )

        self.action_show_Keithley.triggered["bool"].connect(self.show_Keithley)

    @pyqtSlot(bool)
    def run_Keithley(
        self,
        boolean,
        clas,
        instradress,
        dataname,
        threadname,
        GUI_menu_action,
        **kwargs,
    ):
        """start/stop the Keithley thread"""

        if "GUI_number2" in kwargs:
            clas = Keithley6221_Updater
        else:
            clas = Keithley2182_Updater

        if boolean:
            try:
                worker = self.running_thread_control(
                    clas(
                        InstrumentAddress=instradress,
                        comLock=self.GPIB_comLock,
                        log=self._logger
                    ),
                    dataname,
                    threadname
                )
                kwargs['threadname'] = threadname
                worker.sig_Infodata.connect(
                    lambda data: self.store_data_Keithley(
                        data, dataname, **kwargs)
                )
                worker.sig_visaerror.connect(self.show_error_general)
                worker.sig_assertion.connect(self.show_error_general)
                worker.sig_visatimeout.connect(
                    lambda: self.show_error_general(
                        "{0:s}: timeout".format(dataname))
                )

                # display data given by nanovoltmeters & calculate resistance

                # setting values for nanovoltmeters
                if "GUI_number1" in kwargs:
                    kwargs["GUI_CBox_Display"].toggled["bool"].connect(
                        lambda value: self.threads[
                            threadname][0].ToggleDisplay(value)
                    )
                    kwargs["GUI_CBox_Autozero"].toggled["bool"].connect(
                        lambda value: self.threads[threadname][
                            0].ToggleAutozero(value)
                    )
                    kwargs["GUI_CBox_FronAutozero"].toggled["bool"].connect(
                        lambda value: self.threads[threadname][0].ToggleFrontAutozero(
                            value
                        )
                    )
                    kwargs["GUI_CBox_Autorange"].toggled["bool"].connect(
                        lambda value: self.threads[threadname][
                            0].ToggleAutorange(value)
                    )

                    # check if delta between internal and present temperature is greater than 1 Kelvin
                    # if so then perform an ACAL and emit a signal
                    delta = abs(self.data[dataname][
                                'Internal_K'] - self.data[dataname]['Present_K'])
                    if delta > 1:
                        self.sig_acal_needed.emit()
                        kwargs['GUI_CBox_ACAL'].toggled['bool'].connect(
                            self.sig_acal_active.emit())
                        kwargs['GUI_CBox_ACAL'].toggled['bool'].connect(
                            lambda: self.threads[threadname][0].more_ACAL())

                # setting values for current source

                # setting Keithley values for current source by GUI Keithley
                # window

                if "GUI_number2" in kwargs:
                    kwargs["GUI_number2"].valueChanged.connect(
                        lambda value: self.threads[threadname][0].gettoset_Current_A(
                            value * 1e-3
                        )
                    )
                    kwargs["GUI_number2"].editingFinished.connect(
                        lambda: self.threads[threadname][0].setCurrent_A()
                    )
                    kwargs["GUI_number2"].editingFinished.connect(
                        lambda: self.store_data_Keithley(
                            dict(
                                changed_Current_A=self.threads[threadname][
                                    0
                                ].getCurrent_A()
                            ),
                            dataname,
                        )
                    )

                    if not self.threads[threadname][0].OutputOn:
                        # 'correct', as this reads
                        kwargs["GUI_push"].setText("Output ON")
                        # enable
                    if self.threads[threadname][0].OutputOn:
                        # 'correct', as this reads
                        kwargs["GUI_push"].setText("Output OFF")

                    kwargs["GUI_push"].clicked.connect(
                        lambda: self.Keithley_toggleOutput(
                            kwargs["GUI_push"], self.threads[threadname][0]
                        )
                    )
                    kwargs["GUI_push"].setEnabled(True)

                GUI_menu_action.setChecked(True)

            except (VisaIOError, NameError) as e:
                GUI_menu_action.setChecked(False)
                self.show_error_general("running: {}".format(e))
        else:
            GUI_menu_action.setChecked(False)
            self.stopping_thread(threadname)

            if "GUI_number2" in kwargs:
                kwargs["GUI_number2"].valueChanged.disconnect()
                kwargs["GUI_number2"].editingFinished.disconnect()

            if "GUI_push" in kwargs:
                kwargs["GUI_push"].clicked.disconnect()
                # kwargs['GUI_push'].setText('Output ON')
                kwargs["GUI_push"].setEnabled(False)

    @pyqtSlot()
    def Keithley_toggleOutput(self, GUI_Button, worker):
        worker.OutputOn = worker.getstatus()
        if not worker.OutputOn:
            worker.enable()
            GUI_Button.setText("Output OFF")  # ''reversed'', as this toggles!
            # enable
        elif worker.OutputOn:
            worker.disable()
            GUI_Button.setText("Output ON")  # ''reversed'', as this toggles!

        #    @pyqtSlot()
        #    def Keithley_checkDisplay(self, value):
        #        if value == 0:
        #            self.Keithley_window.checkBox_Display_1.setChecked(False)
        #            self.Keithley_window.checkBox_Display_2.setChecked(False)
        #            self.Keithley_window.checkBox_Display_3.setChecked(False)
        #        if value == 2:
        #            self.Keithley_window.checkBox_Display_1.setChecked(True)
        #            self.Keithley_window.checkBox_Display_2.setChecked(True)
        #            self.Keithley_window.checkBox_Display_3.setChecked(True)

        #    @pyqtSlot()
        #    def Keithley_checkAutozero(self, value):
        #        if value == 0:
        #            self.Keithley_window.checkBox_Autozero_1.setChecked(False)
        #            self.Keithley_window.checkBox_Autozero_2.setChecked(False)
        #            self.Keithley_window.checkBox_Autozero_3.setChecked(False)
        #        if value == 2:
        #            self.Keithley_window.checkBox_Autozero_1.setChecked(True)
        #            self.Keithley_window.checkBox_Autozero_2.setChecked(True)
        #            self.Keithley_window.checkBox_Autozero_3.setChecked(True)

        #    @pyqtSlot()
        #    def Keithley_checkFrontAutozero(self, value):
        #        if value == 0:
        #            self.Keithley_window.checkBox_FrontAutozero_1.setChecked(False)
        #            self.Keithley_window.checkBox_FrontAutozero_2.setChecked(False)
        #            self.Keithley_window.checkBox_FrontAutozero_3.setChecked(False)
        #        if value == 2:
        #            self.Keithley_window.checkBox_FrontAutozero_1.setChecked(True)
        #            self.Keithley_window.checkBox_FrontAutozero_2.setChecked(True)
        #            self.Keithley_window.checkBox_FrontAutozero_3.setChecked(True)

    @pyqtSlot()
    def Keithley_checkAutozero(self, value):
        pass

    @pyqtSlot()
    def Keithley_checkFrontAutozero(self, value):
        pass

    @pyqtSlot(bool)
    def show_Keithley(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.Keithley_window.show()
        else:
            self.Keithley_window.close()

    @pyqtSlot(dict)
    def store_data_Keithley(self, data, dataname, **kwargs):
        """
            Store Keithley data in self.data['Keithley'], update Keithley_window
        """
        self.store_data(data=data, device=dataname)

        with self.dataLock:
            # self.data[dataname].update(data)

            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained
            if 'GUI_number1' in kwargs:
                # alternative: if 'Keithley2182' in dataname:
                try:
                    # calculate and display resistance and voltage
                    if not str(kwargs['GUI_Box'].currentText()) == '--':
                        self.data[dataname]['Resistance_Ohm'] = self.data[dataname][
                            'Voltage_V'] / (self.data[str(kwargs['GUI_Box'].currentText()).strip(')').split('(')[1]]['Current_A'])
                    kwargs['GUI_number1'].display(
                        self.data[dataname]['Voltage_V'])
                    if 'Resistance_Ohm' in self.data[dataname]:
                        kwargs['GUI_Display'].display(
                            self.data[dataname]['Resistance_Ohm'])
                    # display internal and present temperature inside the
                    # voltmeter
                    kwargs['GUI_lcd_IntTemp'].display(
                        self.data[dataname]['Internal_K'])
                    kwargs['GUI_lcd_PreTemp'].display(
                        self.data[dataname]['Present_K'])

                except AttributeError as a_err:
                    if (
                        not a_err.args[0]
                        == "'NoneType' object has no attribute 'display'"
                    ):
                        self.show_error_general(
                            "{name}: {err}".format(
                                name=dataname, err=a_err.args[0])
                        )
                except KeyError as key_err:
                    self.show_error_general(
                        "{name}: {err}".format(
                            name=dataname, err=key_err.args[0])
                    )
                except ZeroDivisionError as z_err:
                    self.data[dataname]["Resistance_Ohm"] = np.nan

    # -------------- Lock-In SR 830  ------------------------
    def initialize_window_LockIn(self):
        """initialize PS Window"""
        self.LockIn_window = Window_ui(ui_file=".\\LockIn\\LockIn_control.ui")
        self.LockIn_window.sig_closing.connect(
            lambda: self.action_show_SR830.setChecked(False)
        )

        self.window_SystemsOnline.checkaction_run_SR830.clicked["bool"].connect(
            self.run_SR830
        )
        self.action_show_SR830.triggered["bool"].connect(
            lambda value: self.show_window(self.LockIn_window, value)
        )

        # self.IPS_window.labelStatusMagnet.setText('')
        # self.IPS_window.labelStatusCurrent.setText('')
        # self.IPS_window.labelStatusActivity.setText('')
        # self.IPS_window.labelStatusLocRem.setText('')
        # self.IPS_window.labelStatusSwitchHeater.setText('')

    @pyqtSlot(bool)
    def run_SR830(self, boolean):
        """start/stop the LockIn SR830 control thread"""

        if boolean:
            try:
                getInfodata = self.running_thread_control(
                    SR830_Updater(
                        InstrumentAddress=SR830_InstrumentAddress,
                        comLock=self.GPIB_comLock,
                        log=self._logger
                    ),
                    "SR830",
                    "control_SR830",
                )
                getInfodata.sig_Infodata.connect(self.store_data_SR830)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general("SR830: timeout")
                )

                # self.IPS_window.comboSetActivity.activated['int'].connect(
                #     lambda value: self.threads['control_IPS'][0].setActivity(value))
                # self.IPS_window.comboSetSwitchHeater.activated['int'].connect(
                # lambda value:
                # self.threads['control_IPS'][0].setSwitchHeater(value))

                self.LockIn_window.spinSetFrequency_Hz.valueChanged.connect(
                    lambda value: self.threads["control_SR830"][0].gettoset_Frequency(
                        value
                    )
                )

                self.LockIn_window.spinSetFrequency_Hz.editingFinished.connect(
                    lambda: self.threads["control_SR830"][0].setFrequency()
                )

                self.LockIn_window.spinSetVoltage_V.valueChanged.connect(
                    lambda value: self.threads["control_SR830"][0].gettoset_Voltage(
                        value
                    )
                )

                self.LockIn_window.spinSetVoltage_V.editingFinished.connect(
                    lambda: self.threads["control_SR830"][0].setVoltage()
                )

                self.LockIn_window.spinShuntResistance_kOhm.valueChanged.connect(
                    lambda value: self.threads["control_SR830"][0].getShuntResistance(
                        value * 1e3
                    )
                )
                self.LockIn_window.spinContactResistance_Ohm.valueChanged.connect(
                    lambda value: self.threads["control_SR830"][0].getContactResistance(
                        value
                    )
                )

                # self.IPS_window.spinSetFieldSweepRate.valueChanged.connect(
                #     lambda value: self.threads['control_IPS'][0].gettoset_FieldSweepRate(value))
                # self.IPS_window.spinSetFieldSweepRate.editingFinished.connect(
                # lambda: self.threads['control_IPS'][0].setFieldSweepRate())

                # self.IPS_window.spin_threadinterval.valueChanged.connect(
                # lambda value:
                # self.threads['control_IPS'][0].setInterval(value))

                self.window_SystemsOnline.checkaction_run_SR830.setChecked(
                    True)

            except (VisaIOError, NameError) as e:
                self.window_SystemsOnline.checkaction_run_SR830.setChecked(
                    False)
                self.show_error_general(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.window_SystemsOnline.checkaction_run_SR830.setChecked(False)
            self.stopping_thread("control_SR830")

    @pyqtSlot(dict)
    def store_data_SR830(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""

        self.store_data(data=data, device="SR830")

        with self.dataLock:
            # data['date'] = convert_time(time.time())
            # self.data['SR830'].update(data)

            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained

            self.LockIn_window.lcdSetFrequency_Hz.display(
                self.data["SR830"]["Frequency_Hz"]
            )
            self.LockIn_window.lcdSetVoltage_V.display(
                self.data["SR830"]["Voltage_V"])
            self.LockIn_window.textX_V.setText(
                "{num:=+13.12f}".format(num=self.data["SR830"]["X_V"])
            )

            self.LockIn_window.textSampleCurrent_mA.setText(
                "{num:=+8.6f}".format(num=self.data["SR830"]
                                      ["SampleCurrent_mA"])
            )
            self.LockIn_window.textSampleResistance_Ohm.setText(
                "{num:=+8.6f}".format(num=self.data["SR830"]
                                      ["SampleResistance_Ohm"])
            )

            self.LockIn_window.textY_V.setText(
                "{num:=+13.12f}".format(num=self.data["SR830"]["Y_V"])
            )
            self.LockIn_window.textR_V.setText(
                "{num:=+13.12f}".format(num=self.data["SR830"]["R_V"])
            )
            self.LockIn_window.textTheta_Deg.setText(
                "{num:=+8.6f}".format(num=self.data["SR830"]["Theta_Deg"])
            )

    # ------- MISC -------

    def printing(self, b):
        """arbitrary example function"""
        print(b)

    def initialize_window_Log_conf(self):
        """initialize Logging configuration window"""
        self.Log_conf_window = Logger_configuration()
        self.Log_conf_window.sig_closing.connect(
            lambda: self.action_Logging_configuration.setChecked(False)
        )
        self.Log_conf_window.sig_send_conf.connect(
            lambda conf: self.sig_logging_newconf.emit(conf)
        )

        self.window_SystemsOnline.checkaction_Logging.toggled["bool"].connect(
            self.run_logger
        )
        self.action_Logging_configuration.triggered["bool"].connect(
            self.show_logging_configuration
        )

    @pyqtSlot(bool)
    def run_logger(self, boolean):
        """start/stop the logging thread"""

        # read the last configuration of what shall be logged from a respective
        # file

        if boolean:
            logger = self.running_thread_control(
                main_Logger(self), None, "logger")
            # logger.sig_log.connect(self.logging_send_all)
            logger.sig_log.connect(
                lambda: self.sig_logging.emit(deepcopy(self.data)))
            logger.sig_configuring.connect(self.show_logging_configuration)
            self.logging_running_logger = True

        else:
            self.stopping_thread("logger")
            self.logging_running_logger = False

    # @pyqtSlot()
    # def logging_send_all(self):
    #     newdata = deepcopy(self.data)
    #     newdata.update(deepcopy(self.data_live))
    #     # print(newdata)
    #     self.sig_logging.emit(newdata)

    @pyqtSlot(bool)
    def show_logging_configuration(self, boolean):
        """display/close the logging configuration window"""
        if boolean:
            self.Log_conf_window.show()
        else:
            self.Log_conf_window.close()

    @pyqtSlot(bool)
    def run_logger_live(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""

        if boolean:
            # try:

            getInfodata = self.running_thread_control(
                live_Logger(mainthread=self), None, "control_Logging_live"
            )
            getInfodata.sig_assertion.connect(self.show_error_general)

            self.actionLogging_LIVE.setChecked(True)
            print("logging live online")
            # except VisaIOError as e:
            #     self.actionLogging_LIVE.setChecked(False)
            #     self.show_error_general(e)
            # print(e) # TODO: open window displaying the error message

        else:
            self.stopping_thread("control_Logging_live")
            self.actionLogging_LIVE.setChecked(False)
            self.data_live = dict()

    def initialize_window_Errors(self):
        """initialize Error Window"""
        self.Errors_window = Window_ui(ui_file='.\\configurations\\Errors.ui')
        self.Errors_window.sig_closing.connect(
            lambda: self.action_show_Errors.setChecked(False))

        self.Errors_window.textErrors.setHtml('')

        # self.action_run_Errors.triggered['bool'].connect(self.run_ITC)
        self.action_show_Errors.triggered['bool'].connect(self.show_Errors)
        # self.show_Errors(True)
        # self.Errors_window.showMinimized()

    @pyqtSlot(bool)
    def show_Errors(self, boolean):
        """display/close the Error window"""
        if boolean:
            self.Errors_window.show()
        else:
            self.Errors_window.close()

    # ----- Measurements ---------

    # # ------ OneShot/ TimeScanning -----------
    def initialize_window_OneShot(self):
        self.window_OneShot = Window_ui(
            # ui_file='.\\configurations\\OneShotMeasurement.ui')
            ui_file=".\\configurations\\OneShotMeasurement_multichannel.ui"
        )

        # self.window_OneShot.pushChoose_Datafile.connect()
        # self.window_OneShot.comboCurrentSource.addItems([])
        self.window_OneShot.commandMeasure.setEnabled(False)

        self.window_SystemsOnline.checkaction_run_OneShot_Measuring.clicked[
            "bool"
        ].connect(self.run_OneShot)
        self.action_show_OneShot_Measuring.triggered[
            "bool"].connect(self.show_OneShot)
        self.OneShot_running = False

    @pyqtSlot(bool)
    def run_OneShot(self, boolean):
        if boolean:

            OneShot = self.running_thread_control(
                OneShot_Thread_multichannel(
                    self), "measured", "control_OneShot"
            )
            OneShot.sig_assertion.connect(self.OneShot_errorHandling)

            self.window_OneShot.dspinExcitationCurrent_1_mA.valueChanged.connect(
                lambda value: OneShot.update_exc(1, value * 1e-3)
            )
            self.window_OneShot.dspinExcitationCurrent_2_mA.valueChanged.connect(
                lambda value: OneShot.update_exc(2, value * 1e-3)
            )

            self.window_OneShot.dspinIVstart.valueChanged.connect(
                lambda value: OneShot.update_iv(0, value)
            )
            self.window_OneShot.dspinIVstop.valueChanged.connect(
                lambda value: OneShot.update_iv(1, value)
            )
            self.window_OneShot.spinIVsteps.valueChanged.connect(
                lambda value: OneShot.update_iv(2, value)
            )

            self.window_OneShot.dspinInterval_s.valueChanged.connect(
                lambda value: OneShot.update_conf("interval", value)
            )

            self.window_OneShot.dSpinCurrent_revtime.valueChanged.connect(
                lambda value: OneShot.update_conf(
                    "current_reversal_time", value)
            )

            self.window_OneShot.commandMeasure.setEnabled(True)
            self.window_OneShot.commandStartSeries.setEnabled(True)
            self.window_OneShot.commandStopSeries.setEnabled(True)

            self.logging_timer = QTimer()
            self.logging_timer.timeout.connect(
                lambda: self.sig_measure_oneshot.emit())

            self.window_OneShot.commandMeasure.clicked.connect(
                lambda: self.sig_measure_oneshot.emit()
            )
            # for whatever reason, these need to be connected twice:
            #   only then both text AND color of the state indicator change!
            self.window_OneShot.commandStartSeries.clicked.connect(
                self.OneShot_start)
            self.window_OneShot.commandStartSeries.clicked.connect(
                self.OneShot_start)
            self.window_OneShot.commandStopSeries.clicked.connect(
                self.OneShot_stop)
            self.window_OneShot.commandStopSeries.clicked.connect(
                self.OneShot_stop)

            self.window_OneShot.pushChoose_Datafile.clicked.connect(
                lambda: self.OneShot_chooseDatafile(OneShot)
            )

            self.running_thread_control(
                measurement_Logger(self), None, "save_OneShot")
            OneShot.sig_storing.connect(
                lambda value: self.sig_log_measurement.emit(value)
            )
            # this is for saving the respective data
        else:
            self.stopping_thread("control_OneShot")
            self.stopping_thread("save_OneShot")
            self.window_OneShot.commandMeasure.setEnabled(False)
            self.window_OneShot.commandStartSeries.setEnabled(False)
            self.window_OneShot.commandStopSeries.setEnabled(False)

    # def OneShot_chooseInstrument(self, comboInt, mode, OneShot):
    #     current_sources = [None,
    #                        'control_Keithley6221_1',
    #                        'control_Keithley6221_2']
    #     Nanovolts = [None,
    #                  'control_Keithley2182_1',
    #                  'control_Keithley2182_2',
    #                  'control_Keithley2182_3']
    #     if mode == "RES":
    #         OneShot.update_conf('threadname_RES', Nanovolts[comboInt])
    #     elif mode == "CURR":
    #         OneShot.update_conf('threadname_CURR', current_sources[comboInt])

    def OneShot_start(self):
        """
            get the timer seconds, change the state to "running", start the timer
            this can only be invoked in case the control thread is working:
                the button is otherwise disabled
        """
        sec = self.threads["control_OneShot"][0].conf["interval"]
        msec = sec * 1e3
        green = QtGui.QColor(0, 255, 0)
        self.logging_timer.start(msec)
        self.window_OneShot.textrunning.setText("Running")
        self.window_OneShot.textrunning.setTextColor(green)
        self.window_OneShot.textinterval.setText(
            "{0:.2f} s ({1:.2f} min)".format(sec, sec / 60)
        )

        self.OneShot_running = True

    def OneShot_stop(self):
        """stop the timer, change the state to "stopped" """
        blue = QtGui.QColor(0, 0, 255)
        self.logging_timer.stop()
        self.window_OneShot.textrunning.setText("Stopped")
        self.window_OneShot.textrunning.setTextColor(blue)
        self.OneShot_running = False

    def OneShot_chooseDatafile(self, OneShot):
        try:
            current_file_data = OneShot.conf["datafile"]
        except KeyError:
            current_file_data = "c:/"
        new_file_data, __ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose Datafile", current_file_data, "Datafiles (*.dat)"
        )

        OneShot.update_conf("datafile", new_file_data)
        self.window_OneShot.lineDatafileLocation.setText(new_file_data)
        # print(OneShot)

    def OneShot_errorHandling(self, errortext):
        if "Key" in errortext:
            if any(x in errortext for x in ["None", "Keithley"]):
                self.window_OneShot.comboCurrentSource.setCurrentIndex(0)
                self.window_OneShot.comboNanovoltmeter.setCurrentIndex(0)
                self.show_error_general(errortext)
        self.show_error_general(errortext)

    def show_OneShot(self, boolean):
        """display/close the OneShot Measuring window"""
        if boolean:
            self.window_OneShot.show()
        else:
            self.window_OneShot.close()


if __name__ == "__main__":

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logger_2 = logging.getLogger('pyvisa')
    logger_2.setLevel(logging.INFO)
    logger_3 = logging.getLogger('PyQt5')
    logger_3.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger_2.addHandler(handler)
    logger_3.addHandler(handler)

    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow(app=app)
    form.show()
    print("date: ", dt.datetime.now(), "\nstartup time: ", time.time() - a)

    sys.exit(app.exec_())
