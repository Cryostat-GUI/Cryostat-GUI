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

#a = time.time()
from PyQt5 import QtWidgets, QtGui
from datetime import datetime as dt

# from PyQt5.QtCore import QObject
# from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
import datetime

# from PyQt5.QtWidgets import QtAlignRight
from PyQt5.uic import loadUi

import subprocess
import os
import sys
from threading import Lock
import numpy as np
from copy import deepcopy
import logging

# import json

from pyvisa.errors import VisaIOError

from drivers import ApplicationExit

# import measureSequences as mS

# import Oxford
# from Oxford.ITC_control import ITC_Updater
# from Oxford.ILM_control import ILM_Updater
# from Oxford.IPS_control import IPS_Updater
# from LakeShore.LakeShore350_Control import LakeShore350_Updater
# from Keithley.Keithley2182_Control import Keithley2182_Updater
# from Keithley.Keithley6221_Control import Keithley6221_Updater

# from LockIn.LockIn_SR830_control import SR830_Updater

# from Sequence import OneShot_Thread
# from Sequence import OneShot_Thread_multichannel
# from Sequence import Sequence_Thread

# from loggingFunctionality.logger import main_Logger
# from loggingFunctionality.logger import live_Logger
# from loggingFunctionality.logger import measurement_Logger
# from loggingFunctionality.logger import Logger_configuration
from loggingFunctionality.logger import calculate_timediff
from util.zmqcomms import dictdump
from util import loops_off
from settings import windowSettings
from util import BlockedError
from util import AbstractLoopThreadDataStore
from util import noblockLock
from util import Window_ui
from util import convert_time
from util import convert_time_searchable
from util import Workerclass
from util import running_thread
from util import AbstractLoopThread
from util import noKeyError
from util import Window_plotting_specification
from util import ExceptionHandling
from util import AbstractMainApp
from util import AbstractThread
from util import Window_trayService_ui
from util import readPID_fromFile
from util.zmqcomms import zmqquery_handle
from util.zmqcomms import genericAnswer
from util.zmqcomms import zmqMainControl
from pid import PidFile
from pid import PidFileError

errorfile = "Errors\\" + dt.now().strftime("%Y%m%d") + ".error"


class check_active(AbstractLoopThread):
    """Thread that checks if Windowsservice is running """

    a = "init"
    data = {}

    def __init__(self, Instrument, prefix, **kwargs):

        super().__init__(**kwargs)
        self.__name__ = "MainWindow_check_active"
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.setInterval(0.2)
        self.instrument = Instrument
        self.prefix = prefix

    def running(self):

        p2 = subprocess.run(
            'sc query "{0}{1}" | find "RUNNING"'.format(self.prefix,self.instrument),
            capture_output=True,
            text=True,
            shell=True,
        )
        if self.a != p2.stdout:
            self.data["state"] = p2.stdout
            self.data["instrument"] = self.instrument
            self.sig_Infodata.emit(deepcopy(self.data))

        self.a = p2.stdout


class get_data(AbstractLoopThreadDataStore):
    """Thread that gets data from broker and sends them to mainGui"""
    sig_all = pyqtSignal(dict)
    sig_state_all = pyqtSignal(dict)

    def __init__(self, **kwargs):
        super().__init__(port_data=5570, **kwargs)
        self.__name__ = "get_data_mainWindow"
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.data_all = {}
        self.crash_all = {}

    def running(self):
        self.run_finished = False
        # print(self.data_main)
        # self.sig_Infodata.emit(deepcopy(self.data_main))
        time.sleep(1)

        self.run_finished = True
    def check_crash(self, noblock):
    	if not calculate_timediff(self.data_all["realtime"], 60*5):
    		self.crash_all["state"] = "crashed"
    		if noblock is False:
    			self.crash_all["noblock"] = 0
    		else:
    			self.crash_all["noblock"] = 1
    		self.crash_all["ID"] = ID
    		self.sig_all.emit(self.crash_all)
    	else:
    		self.crash_all["state"] = "running"
    		self.crash_all["noblock"] = 1
    		self.crash_all["ID"] = ID
    		self.sig_state_all.emit(self.crash_all)

    def store_data(self, ID, data):
        self.data_all.update(data)
        self.data_all["ID"] = ID
        if self.data_all["noblock"] is False:
            self.sig_all.emit(deepcopy(self.data_all))
            self.check_crash(noblock=self.data_all["noblock"])
        else:
        	self.check_crash(noblock=self.data_all["noblock"])

class mainWindow(AbstractMainApp, Window_ui, zmqMainControl):
    error_message_start = {}
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

    sig_closing = pyqtSignal()

    def __init__(self, app, identity=None, **kwargs):
        self._identity = identity
        super().__init__(**kwargs)
        loadUi(".\\configurations\\testnew.ui", self)
        # self.setupUi(self)

        self.__name__ = "MainWindow"
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.threads = dict(Lock=Lock())
        # self.threads = dict()
        c = QPushButton()
        self.controls = {c}
        self.threads_tiny = []
        # dict for the checking state function
        self.check_state_data = {
            "Keithley6221_1": {},
            "Keithley6221_2": {},
            "Keithley2182_1": {},
            "Keithley2182_2": {},
            "Keithley2182_3": {},
            "LakeShore350": {},
            "ITC": {},
            "ips120_1": {},
            "ILM": {},
            "sr830_1": {},
            "SR860_1": {}}
        # dict for updating Client GUIS
        self.data_instruments = {
            "Keithley6221_1": {},
            "Keithley6221_2": {},
            "Keithley2182_1": {},
            "Keithley2182_2": {},
            "Keithley2182_3": {},
            "LakeShore350": {},
            "ITC": {},
            "ips120_1": {}, 
            "ILM": {},
            "sr830_1": {},
            "SR860_1": {}
        }
        self.lockin_data_list = [
            "Frequency_Hz",
            "Voltage_V",
            "X_V",
            "Y_V",
            "R_V",
            "Theta_Deg",
            "ShuntResistance_user_Ohm",
            "SampleResistance_Ohm",
            "SampleCurrent_mA",
            "ContactResistance_user_Ohm",
        ]
        self.keithley2182_data_list = [
            "TemperatureInternal_K",
            "Voltage_V",
            "TemperaturePresent_K",]
        self.keithley6221_data_list = ["Current_A", "set_Output", "OutputOn"]
        self.lakeshore350_data_list = [
            "Sensor_1_K",
            "Sensor_2_K",
            "Sensor_3_K",
            "Sensor_4_K",
            "set_temperature",
            "heater_output_as_percent",
            "heater_output_as_voltage",
            "Loop_P_Param",
            "Loop_I_Param",
            "Loop_D_Param",
            "Input_Sensor",
            "Ramp_Rate",
            "Heater_Output_mW",
            "Temp_K",
        ]
        self.ilm211_data_list = ["channel_1_level", "channel_2_level"]
        self.itc503_data_list = [
        	"Sensor_1_K",
            "Sensor_2_K",
            "Sensor_3_K",
            "set_temperature",
            "temperature_error",
            "heater_output_as_voltage",
            "gas_flow_output",
            "proportional_band",
            "integral_action_time",
            "derivative_action_time",
            "Sensor_1_calerr_K",
            "heater_output_as_percent",
            "interval_thread"
        ]
        self.ips120_data_list = [
        	"field_set_point",
            "field_sweep_rate",
            "output_field",
            "measured_magnet_current",
            "output_current",
            "lead_resistance",
            "persistent_magnet_field",
            "trip_field",
            "status_magnet",
            "status_current",
            "status_activity",
            "status_locrem",
            "status_switchheater"]
        for key in self.lockin_data_list:
        	self.data_instruments["sr830_1"][key] = None
        	self.data_instruments["SR860_1"][key] = None
        for key in self.keithley2182_data_list:
        	self.data_instruments["Keithley2182_1"][key] = None
        	self.data_instruments["Keithley2182_2"][key] = None
        	self.data_instruments["Keithley2182_3"][key] = None
        for key in self.keithley6221_data_list:
        	self.data_instruments["Keithley6221_1"][key] = None
        	self.data_instruments["Keithley6221_2"][key] = None
        for key in self.lakeshore350_data_list:
        	self.data_instruments["LakeShore350"][key] = None
        for key in self.ilm211_data_list:
        	self.data_instruments["ILM"][key] = None
        for key in self.itc503_data_list:
        	self.data_instruments["ITC"][key] = None
        for key in self.ips120_data_list:
        	self.data_instruments["ips120_1"][key] = None


        # Dict in which the Data of all instruments is saved,
        # shouldthread = makes sure that after deleting a row in the main Gui 
        #				and then add the same row the thread ckeck_state isn't create a second time
        # lock = locks buttones that aren't implemented if the row is deleted
        # multipl = so that not more than 1 error window is create if an instrument crashes   
        self.instrument_dict = {
            "Keithley6221_1": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.Keithley6221_Updater},
            "Keithley6221_2": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.Keithley6221_Updater},
            "Keithley2182_1": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.Keithley2182_Updater},
            "Keithley2182_2": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.Keithley2182_Updater},
            "Keithley2182_3": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.Keithley2182_Updater},
            "LakeShore350": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.Lakeshore350_Updater},
            "ITC": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.ITC503_Updater},
            "ips120_1": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.IPS120},
            "ILM": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.ilm211_Updater},
            "sr830_1": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.SR830_Updater},
            "SR860_1": {"shouldthread": 0, "lock": 0, "multipl": 0,"method_update_gui": self.SR860_Updater},
        }
        self.instruments = self.instrument_dict.keys() 
        self.prefix='Test_CryostatGUI_'
        self.logging_bools = {}
        self.logging_running_ITC = False
        self.logging_running_logger = False
        self.dataLock = Lock()
        self.dataLock_live = Lock()
        self.row_numbers = 0
        # self.app = app
        self.initialize_window_Errors()
        self.select_instrument.addItems(self.instruments)
        self.select_instrument.setCurrentText("Chose Instrument")
        self.add_instrument.clicked.connect(
            lambda x: self.add_row(
                instrument=self.select_instrument.currentText(),
                index=self.select_instrument.currentIndex(),
            )
        )

        self.delete_instrument.clicked.connect(
            lambda x: self.delete_row(
                instrument=self.select_instrument_delete.currentText(),
                index=self.select_instrument_delete.currentIndex(),
            )
        )

        self.actionNew_Sequence.triggered.connect(self.window_FileDialogOpen_sequence)
        self.pushSequenceRun.clicked.connect(self.start_sequence)
        self.initialize_row_start()
        self.get_data = self.running_thread_control(get_data(), "get data")
        self.get_data.sig_all.connect(self.update_data)
        self.get_data.sig_state_all.connect(self.crasherror_generelly)
        # QTimer.singleShot(0, self.runnning_mainWindow)
        # QTimer.singleShot(0, self.load_settings_itc503)
        # instrument_text=Record()
    def initialize_row_start(self):
        """Initialize all instruments when the Gui is started"""
        while self.select_instrument.currentText() != "":
            self.add_row(instrument= self.select_instrument.currentText(), index=self.select_instrument.currentIndex())
    def delete_row(self, instrument, index):
        """deletes instrument row"""
        self.row_numbers_delete = self.instrument_dict[instrument]["row"]
        self.gridLayout_2.removeWidget(
            self.instrument_dict[instrument]["maintext"]
        )
        self.instrument_dict[instrument]["maintext"].deleteLater()
        del self.instrument_dict[instrument]["maintext"]

        self.gridLayout_2.removeWidget(self.instrument_dict[instrument]["state"])
        self.instrument_dict[instrument]["state"].deleteLater()
        del self.instrument_dict[instrument]["state"]

        self.gridLayout_2.removeWidget(self.instrument_dict[instrument]["start"])
        self.instrument_dict[instrument]["start"].deleteLater()
        del self.instrument_dict[instrument]["start"]

        self.gridLayout_2.removeWidget(self.instrument_dict[instrument]["show"])
        self.instrument_dict[instrument]["show"].deleteLater()
        del self.instrument_dict[instrument]["show"]

        self.gridLayout_2.removeWidget(
            self.instrument_dict[instrument]["remote"]
        )
        self.instrument_dict[instrument]["remote"].deleteLater()
        del self.instrument_dict[instrument]["remote"]

        self.select_instrument.addItem(instrument)
        self.select_instrument_delete.removeItem(index)
        self.instrument_dict[instrument]["shouldthread"] = 1
        self.instrument_dict[instrument]["lock"] = 0
    def add_row(self, instrument, index):
        """adds a row with new instrument"""
        self.row_numbers = self.row_numbers + 1
        self.instrument_dict[instrument]["maintext"] = QLabel(
        	instrument
        	)
        self.instrument_dict[instrument]["state"] = QLabel("")
        self.instrument_dict[instrument]["start"] = QPushButton(
        	"start/stop"
        	)
        self.instrument_dict[instrument]["show"] = QPushButton(
                "show Window"
                )
        self.instrument_dict[instrument]["remote"] = QLabel("")
        self.instrument_dict[instrument]["row"] = self.row_numbers
        self.instrument_dict[instrument]["lock"] = 1
        self.gridLayout_2.addWidget(
        	self.instrument_dict[instrument]["maintext"],
        	self.row_numbers,
        	0,
        	)
        self.gridLayout_2.addWidget(
        	self.instrument_dict[instrument]["state"],
        	self.row_numbers,
        	1,
        	)
        self.gridLayout_2.addWidget(
        	self.instrument_dict[instrument]["start"],
        	self.row_numbers,
        	2,
        	)
        self.gridLayout_2.addWidget(
        	self.instrument_dict[instrument]["show"],
        	self.row_numbers,
        	3,
        	)
        self.gridLayout_2.addWidget(
        	self.instrument_dict[instrument]["remote"],
        	self.row_numbers,
        	4,
        	)
        self.select_instrument_delete.addItem(instrument)
        self.select_instrument.removeItem(index)
        self.initialize_row(instrument= instrument)

    def initialize_row(self, instrument):
        """connecting row buttons with functions"""
        if "Keithley6221" in instrument:
            self.initialize_window_Keithley6221(instrument)
        if "Keithley2182" in instrument:
            self.initialize_window_Keithley2182(instrument)
        if "LakeShore350" in instrument:
            self.initialize_window_LakeShore350(instrument)
        if "ips120" in instrument:
            self.initialize_window_ips(instrument)
        if "ITC" in instrument:
            self.initialize_window_ITC(instrument)
            self.load_settings_itc503(self.instrument_dict["%s" % instrument])
        if "ILM" in instrument:
            self.initialize_ilm211(instrument)
        if "sr830" in instrument:
            self.initialize_sr830(instrument)
        if "SR860" in instrument:
            self.initialize_sr860(instrument)

    def show_window_button_pressed(self, window):
        """show and close window when show button is pressed"""
        window.show()
        window.raise_()

    def update_data(self, data):
        """gets data from thread and update all the individual GUIS"""
        self.instrument_dict[data["ID"]]["method_update_gui"](data)

    def start_instrument(self, instrument=None):
        """function that starts and stop ControlClient windows services"""
        p1 = subprocess.run(
             'sc query "{0}{1}" | find "RUNNING"'.format(self.prefix, instrument),
            capture_output=True,
            text=True,
            shell=True,
        )
        a = p1.stdout

        if "RUNNING" in a:
            p2 = subprocess.run('sc stop "{0}{1}"'.format(self.prefix, instrument))
        else:
            p2 = subprocess.run('sc start "{0}{1}"'.format(self.prefix, instrument))
            self.show_error_general(
                "Couldn´t start or stop service {0}{1}".format(self.prefix, instrument)
            )

    @staticmethod
    def show_window(window, boolean=None):
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

    def start_sequence(self):
        """starts the sequence python file not finished!"""
        subprocess.run("python %s" % self.fname_sequence)

    @ExceptionHandling
    def window_FileDialogOpen_sequence(self, dummy=False):
        """Opens Window to select sequence"""
        self.fname_sequence, __ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose sequence configuration file", "c:\\", ".conf(*.conf)"
        )
        self.labelSequenceSelected.setText(os.path.basename(self.fname_sequence))
        # self.setValue('general', 'logfile_location', fname)

        # try:
        #   with open(self.fname_sequence) as f:
        # except OSError as e:
        #   self._logger.exception(e)
        # except TypeError as e:
        #    self._logger.error(f"missing Filename! (TypeError: {e})")

    def crasherror_generelly(self, data):
        """Function that checks if ControlClient is crashed. state_instrumentname["noblock"] shows if instrument is currently blocked"""
        self.instrument_dict[data["ID"]]["multipl"] = (
            self.instrument_dict[data["ID"]]["multipl"] + 1
        )
        if data["state"] == "crashed":
            if self.instrument_dict[data["ID"]]["multipl"] == 1:
                self.show_error_general("Service CryostatGui_{0} crashed".format(self.instrument_dict[data["ID"]]))
                if self.instrument_dict[data["ID"]]["lock"] == 1:
                    self.instrument_dict[data["ID"]]["state"].setText(data["state"])
        else:
            if self.instrument_dict[data["ID"]]["lock"] == 1:
                self.instrument_dict[data["ID"]]["state"].setText(data["state"])

    def update_check_state_generell(self, data):
        """Updates the state Label in the main GUI"""
        #if function prevents error if row doesn't exist
        if self.instrument_dict[data["instrument"]]["lock"] == 1:
            if "RUNNING" in data["state"]:
                self.instrument_dict[data["instrument"]]["state"].setText("Running")
                self.instrument_dict[data["instrument"]]["state"].setStyleSheet(
                    "color:green"
                )
            else:
                self.instrument_dict[data["instrument"]]["state"].setText("Not Running")
                self.instrument_dict[data["instrument"]]["state"].setStyleSheet(
                    "color:red"
                )
    def initialize_state_threade(self, instrument):
    	#function which checks if it should make a new thread to check instrument state 
    	if self.instrument_dict[instrument]["shouldthread"] == 0:
    		self.instrument_dict[instrument][
    		"get_state"
    		] = self.running_thread_control(
    			check_active(
    				Instrument=self.instrument_dict[instrument]["ID"],
    				prefix=self.prefix
    				),
    			"check_state_%s"
    			% self.instrument_dict[instrument]["ID"],
    			)
    		self.instrument_dict[instrument][
    		"get_state"
    		].sig_Infodata.connect(self.update_check_state_generell)
    	else:
    		self.p2 = subprocess.run(
    			'sc query "Test_CryostatGui_%s" | find "RUNNING"'
    			% self.instrument_dict[instrument]["ID"],
    			capture_output=True,
    			text=True,
    			shell=True,
    			)
    		self.instrument_dict[instrument]["state_init"] = {}
    		self.instrument_dict[instrument]["state_init"][
    		"state"
    		] = self.p2.stdout
    		self.instrument_dict[instrument]["state_init"][
    		"instrument"
    		] = self.instrument_dict[instrument]["ID"]
    		self.update_check_state_generell(
    			self.instrument_dict[instrument]["state_init"])


    # --------Lakeshore350
    def initialize_window_LakeShore350(self, instrument_Lakeshore350):
        """initialize LakeShore Window"""
        self.instrument_dict[instrument_Lakeshore350][
            "ID"
        ] = instrument_Lakeshore350
        self.instrument_dict[instrument_Lakeshore350]["window"] = Window_ui(
            ui_file=".\\LakeShore\\lakeShore350_Qwidget.ui",
            parent=self,
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].sig_closing.connect(lambda: self.action_show_LakeShore350.setChecked(False))

        self.initialize_state_threade(instrument_Lakeshore350)

        self.instrument_dict[instrument_Lakeshore350]["start"].clicked[
            "bool"
        ].connect(
            lambda value: self.start_instrument(
                instrument="%s"
                % self.instrument_dict[instrument_Lakeshore350]["ID"]
            )
        )
        self.instrument_dict[instrument_Lakeshore350]["show"].clicked[
            "bool"
        ].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_Lakeshore350]["window"]
            )
        )
        # self.action_show_LakeShore350.triggered["bool"].connect(self.show_LakeShore350)

        self.LakeShore350_Kpmin = None
        self.instrument_dict[instrument_Lakeshore350]["values"]={}
        self.instrument_dict[instrument_Lakeshore350]["values"]["temp"] = {"isSweep": False, "SweepRate": 0.0}
        # self.instrument_dict["%s"%instrument_Lakeshore350]["values"]=dict
        # connecting buttons to send commands upstream

        # changing the temp buttons
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].spinSetTemp_K.valueChanged.connect(
            lambda value: self.fun_setTemp_valcha_lakeshore350(
                value,
                instr=self.instrument_dict[instrument_Lakeshore350][
                    "values"
                ]["temp"],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].checkRamp_Status.toggled["bool"].connect(
       			lambda value: self.fun_checkSweep_toggled_lakeshore350(
                instr=self.instrument_dict[instrument_Lakeshore350],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].spinSetRamp_Kpmin.valueChanged.connect(
            lambda value: self.fun_setRamp_valcha_lakeshore350(
                value,
                instr=self.instrument_dict[instrument_Lakeshore350],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].commandSendConfTemp.clicked.connect(
            lambda value: self.fun_sendConfTemp_lakeshore350(
                instr=self.instrument_dict[instrument_Lakeshore350]
            )
        )

        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].pushButtonHeaterOut.clicked.connect(
            lambda: self.commanding(
                ID=self.instrument_dict[instrument_Lakeshore350]["ID"],
                message=dictdump({"setHeaterOut": 0}),
            )
        )

        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].comboSetInput_Sensor.activated["int"].connect(
            lambda value: self.commanding(
                ID=self.instrument_dict[instrument_Lakeshore350]["ID"],
                message=dictdump({"setInput_Sensor": value + 1}),
            )
        )

        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].spinSetLoopP_Param.valueChanged.connect(
            lambda value: self.gettoset_Proportional_lakeshore350(
                value,
                instr=self.instrument_dict[instrument_Lakeshore350],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].send_command_spinSetLoopP_Param.clicked.connect(
            lambda value: self.setProportional_lakeshore350(
                instr=self.instrument_dict[instrument_Lakeshore350]
            )
        )

        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].spinSetLoopI_Param.valueChanged.connect(
            lambda value: self.gettoset_Integral_lakeshore350(
                value,
                instr=self.instrument_dict[instrument_Lakeshore350],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].send_command_spinSetLoopI_Param.clicked.connect(
            lambda: self.setIntegral_lakeshore3550(
                instr=self.instrument_dict[instrument_Lakeshore350]
            )
        )

        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].spinSetLoopD_Param.valueChanged.connect(
            lambda value: self.gettoset_Derivative_lakeshore350(
                value,
                instr=self.instrument_dict[instrument_Lakeshore350],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].send_command_spinSetLoopD_Param.clicked.connect(
            lambda: self.setDerivative_lakeshore350(
                instr=self.instrument_dict[instrument_Lakeshore350]
            )
        )
        # set Interval not implemented in controlClient
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].spin_threadinterval.valueChanged.connect(
            lambda value: self.gettoset_Interval_lakeshore350(
                value,
                instr=self.instrument_dict[instrument_Lakeshore350],
            )
        )
        self.instrument_dict[instrument_Lakeshore350][
            "window"
        ].send_command_spin_threadinterval.clicked.connect(
            lambda: self.setInterval_lakeshore350(
                instr=self.instrument_dict["%s" % instrument_Lakeshore350]
            )
        )

    @pyqtSlot(bool)
    def show_LakeShore350(self, boolean, instr):
        """display/close the ILM data & control window"""
        if boolean:
            instr["window"].show()
        else:
            instr["window"].close()

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setTemp_valcha_lakeshore350(self, value, instr):
        """stores data waiting to be send upstream"""

        instr["setTemp"] = value
        instr["end"] = value
        instr["isSweepStartCurrent"] = True
        instr["start"] = None

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setRamp_valcha_lakeshore350(self, value, instr):
        instr["values"]["temp"]["SweepRate"] = value

    @pyqtSlot(bool)
    @ExceptionHandling
    def fun_checkSweep_toggled_lakeshore350(self, boolean, instr):
        instr["values"]["temp"]["isSweep"] = boolean

    @pyqtSlot()
    @ExceptionHandling
    def fun_sendConfTemp_lakeshore350(self, instr):
        """sends command to change conf Temp, sends a dict with all the necessary Information for the setTemp
        unction in the ITC controlClient"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setTemp_K": instr["values"]["temp"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setProportional_lakeshore350(self, instr):
        """sends command to set Proportional of the instrument

        prop: Proportional band, in steps of 0.0001K.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setProportional": instr["values"]["set_prop"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setIntegral_lakeshore3550(self, instr):
        """sends command to set Integral of the instrument

        integral: Integral action time, in steps of 0.1 minute.
                    Ranges from 0 to 140 minutes.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setIntegral": instr["values"]["set_integral"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setDerivative_lakeshore350(self, instr):
        """sends command to set Derivative of the instrument

        derivative: Derivative action time.
        Ranges from 0 to 273 minutes.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setDerivative": instr["values"]["set_derivative"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setInterval_lakeshore350(self, instr):
        """sends command to set interval of the instrument ( not implemented in controlClient for the ITC)"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setInterval": instr["values"]["set_interval"]}),
        )

    @pyqtSlot(float)
    def gettoset_Proportional_lakeshore350(self, value, instr):
        """receive and store the value to set the proportional (PID)"""
        instr["values"]["set_prop"] = value

    @pyqtSlot(float)
    def gettoset_Integral_lakeshore350(self, value, instr):
        """receive and store the value to set the integral (PID)"""
        instr["values"]["set_integral"] = value

    @pyqtSlot(float)
    def gettoset_Derivative_lakeshore350(self, value, instr):
        """receive and store the value to set the derivative (PID)"""
        instr["values"]["set_derivative"] = value

    @pyqtSlot(float)
    def gettoset_Interval_lakeshore350(self, value, instr):
        """receive and store the value to set the interval"""
        instr["values"]["set_interval"] = value

    @pyqtSlot(dict)
    def Lakeshore350_Updater(self, data):
        """
        Calculate the rate of change of Temperature on the sensors [K/min]
        Store LakeShore350 data in self.data['LakeShore350'], update LakeShore350_window
        """
        self.data_instruments[data["ID"]].update(data)
        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # self.data['LakeShore350'].update(data)
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained
        if self.instrument_dict[data["ID"]]["lock"] == 1:
            self.instrument_dict[data["ID"]][
                "window"
            ].progressHeaterOutput_percentage.setValue(
                self.data_instruments[data["ID"]]["Heater_Output_percentage"]
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdHeaterOutput_mW.display(self.data_instruments[data["ID"]]["Heater_Output_mW"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSetTemp_K.display(self.data_instruments[data["ID"]]["Temp_K"])
            # self.lcdRampeRate_Status.display(self.data['RampRate_Status'])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSetRampRate_Kpmin.display(self.data_instruments[data["ID"]]["Ramp_Rate"])

            self.instrument_dict[data["ID"]][
                "window"
            ].comboSetInput_Sensor.setCurrentIndex(
                int(self.data_instruments[data["ID"]]["Input_Sensor"]) - 1
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSensor1_K.display(self.data_instruments[data["ID"]]["Sensor_1_K"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSensor2_K.display(self.data_instruments[data["ID"]]["Sensor_2_K"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSensor3_K.display(self.data_instruments[data["ID"]]["Sensor_3_K"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSensor4_K.display(self.data_instruments[data["ID"]]["Sensor_4_K"])

            """NEW GUI to display P,I and D Parameters
            """
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdLoopP_Param.display(self.data_instruments[data["ID"]]["Loop_P_Param"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdLoopI_Param.display(self.data_instruments[data["ID"]]["Loop_I_Param"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdLoopD_Param.display(self.data_instruments[data["ID"]]["Loop_D_Param"])

    # --------Keithleys
    # ---------------Keithley 6221
    def initialize_window_Keithley6221(self, instrument_Keithley6221):

        self.instrument_dict[instrument_Keithley6221][
            "ID"
        ] = instrument_Keithley6221
        self.instrument_dict[instrument_Keithley6221]["window"] = Window_ui(
            ui_file=".\\Keithley\\K6221_QWidget.ui",
            parent=self,
        )
        self.instrument_dict[instrument_Keithley6221][
            "window"
        ].sig_closing.connect(lambda: self.action_show_Keithley.setChecked(False))
        self.instrument_dict[instrument_Keithley6221]["multipl"] = 0
        self.instrument_dict[instrument_Keithley6221][
            "Data"
        ] = self.data_instruments["Keithley6221_1"]
        self.instrument_dict[instrument_Keithley6221]["start"].clicked[
            "bool"
        ].connect(
            lambda value: self.start_instrument(
                instrument=self.instrument_dict[instrument_Keithley6221]["ID"]
            )
        )
        self.instrument_dict[instrument_Keithley6221]["spinsetCurrent"] = 0.0
        self.action_show_Keithley.triggered["bool"].connect(
            lambda value: self.show_window(
                self.instrument_dict[instrument_Keithley6221]["window"], value
            )
        )
        self.instrument_dict[instrument_Keithley6221]["show"].clicked[
            "bool"
        ].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_Keithley6221]["window"]
            )
        )

        self.instrument_dict[instrument_Keithley6221]["values"]={}
        # self.mdiArea.addSubWindow(self.ITC_window)
        self.initialize_state_threade(instrument_Keithley6221)

        self.instrument_dict[instrument_Keithley6221][
            "window"
        ].spinSetCurrent_mA.valueChanged.connect(
            lambda value: self.gettoset_spinSetCurrent_keithley6221(
                value=value,
                instr=self.instrument_dict[instrument_Keithley6221],
            )
        )
        self.instrument_dict[instrument_Keithley6221][
            "window"
        ].send_command_spinSetCurrent_mA.clicked.connect(
            lambda: self.set_spinSetCurrent_keithley6221(
                instr=self.instrument_dict[instrument_Keithley6221]
            )
        )
        self.instrument_dict[instrument_Keithley6221][
            "window"
        ].pushToggleOut.clicked.connect(
            lambda value: self.output_keithley6221_clicked(
                instr=self.instrument_dict[instrument_Keithley6221]
            )
        )
        self.instrument_dict[instrument_Keithley6221]["show"].clicked[
            "bool"
        ].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_Keithley6221]["window"]
            )
        )
    def output_keithley6221_clicked(self, instr):
        """sends command to setOutput"""
        if instr["Data"]["OutputOn"] == 1 or instr["Data"]["OutputOn"] == None:
            self.commanding(
                ID=instr["ID"], message=dictdump({"set_Output": 0})
            )
        else:
            self.commanding(
                ID=instr["ID"], message=dictdump({"set_Output": 1})
            )

    def set_spinSetCurrent_keithley6221(self, instr):
        """Send command to controleClient to set spinCurrent in mA"""

        self.commanding(
            ID=instr["ID"],
            message=dictdump({"set_Current_A": instr["values"]["spinsetCurrent"]}),
        )

    def gettoset_spinSetCurrent_keithley6221(self, value, instr):
        """receive and store the value to set the spinCurrent"""
        instr["values"]["spinsetCurrent"] = value * 1e-3

    def Keithley6221_Updater(self, data):
        """Updater function for the Keithley6221 Window"""
        self.data_instruments[data["ID"]].update(data)
        if self.instrument_dict[data["ID"]]["lock"] == 1:
            self.instrument_dict[data["ID"]]["Data"].update(
                data
            )

            """self.instrument_dict[data["ID"]][
                "window"
            ].spinSetCurrent_mA.display(
                self.instrument_dict[data["ID"]]["Data"][
                    "Current_A"
                ]
            )"""
            if (
                self.data_instruments[data["ID"]][
                    "OutputOn"
                ]
                == 1
            ):
                self.instrument_dict[data["ID"]][
                    "window"
                ].pushToggleOut.setText("Output is On")
            else:
                self.instrument_dict[data["ID"]][
                    "window"
                ].pushToggleOut.setText("Output is OFF")
    # ---------------Keithley 2182
    def initialize_window_Keithley2182(self, instrument_Keithley2182):

        self.instrument_dict[instrument_Keithley2182][
            "ID"
        ] = instrument_Keithley2182
        self.instrument_dict[instrument_Keithley2182]["window"] = Window_ui(
            ui_file=".\\Keithley\\K2182_QWidget.ui",
            parent=self,
        )
        self.instrument_dict[instrument_Keithley2182][
            "window"
        ].sig_closing.connect(lambda: self.action_show_Keithley.setChecked(False))
        self.instrument_dict[instrument_Keithley2182]["multipl"] = 0
        self.instrument_dict[instrument_Keithley2182]["start"].clicked[
            "bool"
        ].connect(
            lambda value: self.start_instrument(
                instrument=self.instrument_dict[instrument_Keithley2182]["ID"]
            )
        )
        self.action_show_Keithley.triggered["bool"].connect(
            lambda value: self.show_window(
                self.instrument_dict[instrument_Keithley2182]["ID"], value
            )
        )
        self.instrument_dict[instrument_Keithley2182]["show"].clicked[
            "bool"
        ].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_Keithley2182]["window"]
            )
        )

        self.instrument_dict[instrument_Keithley2182]["values"] = {} 
        self.initialize_state_threade(instrument_Keithley2182)

        # all the QCheckboxes
        self.instrument_dict[instrument_Keithley2182][
            "window"
        ].checkBox_Display_1.stateChanged.connect(
            lambda value: self.send_command_display_keithley2182(
                value,
                instr=self.instrument_dict[instrument_Keithley2182],
            )
        )
        self.instrument_dict[instrument_Keithley2182][
            "window"
        ].checkBox_Autozero_1.stateChanged.connect(
            lambda value: self.send_command_autozero_keithley2182(
                value,
                instr=self.instrument_dict[instrument_Keithley2182],
            )
        )
        self.instrument_dict[instrument_Keithley2182][
            "window"
        ].checkBox_FrontAutozero_1.stateChanged.connect(
            lambda value: self.send_command_frontautozero_keithley2182(
                value,
                instr=self.instrument_dict[instrument_Keithley2182],
            )
        )
        self.instrument_dict[instrument_Keithley2182][
            "window"
        ].checkBox_Autorange_1.stateChanged.connect(
            lambda value: self.send_command_autorange_keithley2182(
                value,
                instr=self.instrument_dict[instrument_Keithley2182],
            )
        )
    def send_command_autorange_keithley2182(self, state, instr):
        """sends auto-range command to the controlClient"""
        if state == 2:
            self.commanding(
                ID=instr["ID"], message=dictdump({"Autorange_1": 1})
            )
        else:
            self.commanding(
                ID=instr["ID"], message=dictdump({"Autorange_1": 0})
            )

    def send_command_frontautozero_keithley2182(self, state, instr):
        """send fronAutozero command to the controlClient"""
        if state == 2:
            self.commanding(
                ID=instr["ID"],
                message=dictdump({"frontAutozero_1": 1}),
            )
        else:
            self.commanding(
                ID=instr["ID"],
                message=dictdump({"frontAutozero_1": 0}),
            )

    def send_command_autozero_keithley2182(self, state, instr):
        """sends auto-zero command to the controlClient"""
        if state == 2:
            self.commanding(
                ID=instr["ID"], message=dictdump({"Autozero_1": 1})
            )
        else:
            self.commanding(
                ID=instr["ID"], message=dictdump({"Autozero_1": 0})
            )

    def send_command_display_keithley2182(self, state, instr):
        """sends Display command to the controlClient"""
        if state == 2:
            self.commanding(
                ID=instr["ID"], message=dictdump({"Display_1": 1})
            )
        else:
            self.commanding(
                ID=instr["ID"], message=dictdump({"Display_1": 0})
            )

    def Keithley2182_Updater(self, data):
        """Updater function for the Keithley6221 Window"""
        self.data_instruments[data["ID"]].update(data)
        if self.instrument_dict[data["ID"]]["lock"] == 1:

            self.instrument_dict[data["ID"]][
                "window"
            ].textVoltage_V.setText(
                "%s"
                % self.data_instruments[data["ID"]][
                    "Voltage_V"
                ]
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].textTempInternal_K.setText(
                "%s"
                % self.data_instruments[data["ID"]][
                    "TemperatureInternal_K"
                ]
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].textTempPresent_K.setText(
                "%s"
                % self.data_instruments[data["ID"]][
                    "TemperaturePresent_K"
                ]
            )
    # ------- Oxford Instruments
    # ---------------- IPS
    def initialize_window_ips(self, instrument_ips120):
        """initialize PS Window"""
        self.instrument_dict[instrument_ips120]["ID"] = instrument_ips120
        self.instrument_dict[instrument_ips120]["window"] = Window_ui(
            ui_file=".\\Oxford\\IPS_Qwidget.ui",
            parent=self,
        )
        self.instrument_dict[instrument_ips120]["window"].sig_closing.connect(
            lambda: self.action_show_IPS.setChecked(False)
        )
        self.instrument_dict[instrument_ips120]["Data"] = {}
        self.instrument_dict[instrument_ips120]["multipl"] = 0
        # self.window_SystemsOnline.checkaction_run_IPS.clicked["bool"].connect(
        #    self.run_IPS
        # )
        self.action_show_IPS.triggered["bool"].connect(
            lambda value: self.show_window(
                self.instrument_dict[instrument_ips120]["window"], value
            )
        )
        self.initialize_state_threade(instrument_ips120)

        self.instrument_dict[instrument_ips120]["show"].clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_ips120]["window"]
            )
        )

        self.instrument_dict[instrument_ips120]["values"]={}

        self.instrument_dict[instrument_ips120][
            "window"
        ].labelStatusMagnet.setText("")
        self.instrument_dict[instrument_ips120][
            "window"
        ].labelStatusCurrent.setText("")
        self.instrument_dict[instrument_ips120][
            "window"
        ].labelStatusActivity.setText("")
        self.instrument_dict[instrument_ips120][
            "window"
        ].labelStatusLocRem.setText("")
        self.instrument_dict[instrument_ips120][
            "window"
        ].labelStatusSwitchHeater.setText("")

        self.instrument_dict[instrument_ips120][
            "window"
        ].spinSetFieldSetPoint.valueChanged.connect(
            lambda value: self.gettoset_fieldsetpoint_ips120(
                value, instr=self.instrument_dict[instrument_ips120]
            )
        )
        self.instrument_dict[instrument_ips120][
            "window"
        ].send_command_spinSetFieldSetPoint.clicked.connect(
            lambda value: self.setfieldsetpoint_ips120(
                instr=self.instrument_dict[instrument_ips120]
            )
        )

        self.instrument_dict[instrument_ips120][
            "window"
        ].spinSetFieldSweepRate.valueChanged.connect(
            lambda value: self.gettoset_fieldsweeprate_ips120(
                value, instr=self.instrument_dict[instrument_ips120]
            )
        )
        self.instrument_dict[instrument_ips120][
            "window"
        ].send_command_spinSetFieldSweepRate.clicked.connect(
            lambda value: self.setfieldsweeprate_ips120(
                instr=self.instrument_dict[instrument_ips120]
            )
        )

        self.instrument_dict[instrument_ips120][
            "window"
        ].spin_threadinterval.valueChanged.connect(
            lambda value: self.gettoset_Interval_ips120(
                value, instr=self.instrument_dict[instrument_ips120]
            )
        )
        self.instrument_dict[instrument_ips120][
            "window"
        ].send_command_spin_threadinterval.clicked.connect(
            lambda value: self.setInterval_ips120(
                instr=self.instrument_dict[instrument_ips120]
            )
        )

        self.instrument_dict[instrument_ips120][
            "window"
        ].comboSetActivity.activated["int"].connect(
            lambda value: self.commanding(
                ID=self.instrument_dict[instrument_ips120]["ID"],
                message=dictdump({"activity": value}),
            )
        )
        self.instrument_dict[instrument_ips120][
            "window"
        ].comboSetSwitchHeater.activated["int"].connect(
            lambda value: self.commanding(
                ID=self.instrument_dict[instrument_ips120]["ID"],
                message=dictdump({"switchheater": value}),
            )
        )
    @pyqtSlot()
    @ExceptionHandling
    def setfieldsetpoint_ips120(self, instr):
        """sends command to set FieldSetPoint of the instrument"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setfieldsetpoint": instr["values"]["setfieldsetpoint"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setfieldsweeprate_ips120(self, instr):
        """sends command to set FieldSweepRate of the instrument"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump(
                {"setfieldsweeprate": instr["values"]["setfieldsweeprate"]}
            ),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setInterval_ips120(self, instr):
        """sends command to set Interval of the instrument"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setInterval": instr["values"]["setInterval"]}),
        )

    @pyqtSlot(float)
    def gettoset_fieldsetpoint_ips120(self, value, instr):
        """receive and store the value to set the FieldSetPoint"""
        instr["values"]["setfieldsetpoint"] = value

    @pyqtSlot(float)
    def gettoset_fieldsweeprate_ips120(self, value, instr):
        """receive and store the value to set the FieldSweepRate"""
        instr["values"]["setfieldsweeprate"] = value

    @pyqtSlot(float)
    def gettoset_Interval_ips120(self, value, instr):
        """receive and store the value to set the interval"""
        instr["values"]["setInterval"] = value

    @pyqtSlot(dict)
    def IPS120(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""

        self.data_instruments[data["ID"]].update(data)
        self.instrument_dict[data["ID"]]["Data"].update(data)
        if self.instrument_dict[data["ID"]]["lock"] == 1:
            with self.dataLock:
                # data['date'] = convert_time(time.time())
                # self.data['IPS'].update(data)

                # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
                # since the command failed in the communication with the device,
                # the last value is retained
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdFieldSetPoint.display(self.data_instruments[data["ID"]]["field_set_point"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdFieldSweepRate.display(self.data_instruments[data["ID"]]["field_sweep_rate"])

                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdOutputField.display(self.data_instruments[data["ID"]]["output_field"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdMeasuredMagnetCurrent.display(
                    self.data_instruments[data["ID"]]["magnet_current"]
                )
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdOutputCurrent.display(self.data_instruments[data["ID"]]["output_current"])
                # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_set_point'])
                # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_sweep_rate'])

                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdLeadResistance.display(self.data_instruments[data["ID"]]["lead_resistance"])

                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdPersistentMagnetField.display(
                    self.data_instruments[data["ID"]]["persistent_magnet_field"]
                )
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdTripField.display(self.data_instruments[data["ID"]]["trip_field"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdPersistentMagnetCurrent.display(
                    self.data_instruments[data["ID"]]["persistent_magnet_current"]
                )
                self.instrument_dict[data["ID"]][
                    "window"
                ].lcdTripCurrent.display(self.data_instruments[data["ID"]]["trip_current"])

                self.instrument_dict[data["ID"]][
                    "window"
                ].labelStatusMagnet.setText(self.data_instruments[data["ID"]]["status_magnet"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].labelStatusCurrent.setText(self.data_instruments[data["ID"]]["status_current"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].labelStatusActivity.setText(self.data_instruments[data["ID"]]["status_activity"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].labelStatusLocRem.setText(self.data_instruments[data["ID"]]["status_locrem"])
                self.instrument_dict[data["ID"]][
                    "window"
                ].labelStatusSwitchHeater.setText(
                    self.data_instruments[data["ID"]]["status_switchheater"]
                )

    # ------- ------- ITC
    def initialize_window_ITC(self, instrument_itc503):
        """initialize ITC Window"""
        self.instrument_dict[instrument_itc503]["ID"] = instrument_itc503
        self.instrument_dict[instrument_itc503]["window"] = Window_ui(
            ui_file=".\\Oxford\\itc503_Qwidget.ui",
            parent=self,
        )
        self.instrument_dict[instrument_itc503]["window"].sig_closing.connect(
            lambda: self.action_show_ITC.setChecked(False)
        )
        self.instrument_dict[instrument_itc503]["multipl"] = 0
        self.instrument_dict[instrument_itc503]["start"].clicked["bool"].connect(
            lambda value: self.start_instrument(
                instrument=self.instrument_dict[instrument_itc503]["ID"]
            )
        )
        self.action_show_ITC.triggered["bool"].connect(
            lambda value: self.show_window(
                self.instrument_dict[instrument_itc503]["window"], value
            )
        )
        self.instrument_dict[instrument_itc503]["show"].clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_itc503]["window"]
            )
        )
        self.initialize_state_threade(instrument_itc503)
        self.instrument_dict[instrument_itc503]["values"]={}
        self.instrument_dict[instrument_itc503]["values"]["temp"] = {
            #"setTemperature": 4,
            "SweepRate": 2,
        }

        # changing the temp buttons
        self.instrument_dict[instrument_itc503][
            "window"
        ].spinSetTemp_K.valueChanged.connect(
            lambda value: self.fun_setTemp_valcha(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].checkRamp_Status.toggled["bool"].connect(
            lambda value: self.fun_checkSweep_toggled(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].spinSetRamp_Kpmin.valueChanged.connect(
            lambda value: self.fun_setRamp_valcha(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].commandSendConfTemp.clicked.connect(
            lambda value: self.fun_sendConfTemp(
                instr=self.instrument_dict[instrument_itc503]
            )
        )

        # other buttons
        self.instrument_dict[instrument_itc503][
            "window"
        ].spinsetGasOutput.valueChanged.connect(
            lambda value: self.gettoset_GasOutput_itc503(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].send_command_spinsetGasOutput.clicked.connect(
            lambda value: self.setGasOutput_itc503(
                instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].checkGas_gothroughzero.toggled["bool"].connect(
            lambda value: self.send_gas_gothroughzero(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )

        self.instrument_dict[instrument_itc503][
            "window"
        ].spinsetHeaterPercent.valueChanged.connect(
            lambda value: self.gettoset_HeaterOutput_itc503(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].send_command_spinsetHeaterPercent.clicked.connect(
            lambda value: self.setHeaterOutput_itc503(
                instr=self.instrument_dict[instrument_itc503]
            )
        )

        self.instrument_dict[instrument_itc503][
            "window"
        ].spinsetProportionalID.valueChanged.connect(
            lambda value: self.gettoset_Proportional_itc503(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].send_command_spinsetProportionalID.clicked.connect(
            lambda value: self.setProportional_itc503(
                instr=self.instrument_dict[instrument_itc503]
            )
        )

        self.instrument_dict[instrument_itc503][
            "window"
        ].spinsetPIntegrationD.valueChanged.connect(
            lambda value: self.gettoset_Integral_itc503(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].send_command_spinsetPIntegrationD.clicked.connect(
            lambda value: self.setIntegral_itc503(
                instr=self.instrument_dict[instrument_itc503]
            )
        )

        self.instrument_dict[instrument_itc503][
            "window"
        ].spinsetPIDerivative.valueChanged.connect(
            lambda value: self.gettoset_Derivative_itc503(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].send_command_spinsetPIDerivative.clicked.connect(
            lambda value: self.setDerivative_itc503(
                instr=self.instrument_dict[instrument_itc503]
            )
        )

        self.instrument_dict[instrument_itc503][
            "window"
        ].combosetHeatersens.activated["int"].connect(
            lambda value: self.commanding(
                ID=self.self.instrument_dict[instrument_itc503]["ID"],
                message=dictdump({"setHeaterSensor": value + 1}),
            )
        )

        self.instrument_dict[instrument_itc503][
            "window"
        ].combosetAutocontrol.activated["int"].connect(
            lambda value: self.commanding(
                ID="%s" % self.instrument_dict[instrument_itc503]["ID"],
                message=dictdump({"setAutoControl": value}),
            )
        )
        self.instrument_dict[instrument_itc503]["window"].checkUseAuto.toggled[
            "bool"
        ].connect(
            lambda value: self.fun_useAutoPID(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].pushConfLoad.clicked.connect(
            lambda value: self.fun_PIDFile_send_itc503(
                dummy="dummy",
                instr=self.instrument_dict[instrument_itc503],
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].pushConfBrowse.clicked.connect(
            lambda value: self.window_FileDialogOpen(
                instr=self.instrument_dict[instrument_itc503]
            )
        )
        # -------------------------------------------------------------------------------------------------------------------------
        # buttons set Interval is not implemented in Control client
        self.instrument_dict[instrument_itc503][
            "window"
        ].spin_threadinterval.valueChanged.connect(
            lambda value: self.gettoset_Interval_itc503(
                value, instr=self.instrument_dict[instrument_itc503]
            )
        )
        self.instrument_dict[instrument_itc503][
            "window"
        ].send_command_spin_threadinterval.clicked.connect(
            lambda value: self.setInterval_itc503(
                instr=self.instrument_dict[instrument_itc503]
            )
        )
    @ExceptionHandling
    def window_FileDialogOpen(self, instr):
        fname, __ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose PID configuration file", "c:\\", ".conf(*.conf)"
        )
        instr["window"].lineConfFile.setText(fname)
        instr["_PIDFile"] = fname
        # self.setValue('general', 'logfile_location', fname)

        try:
            with open(fname) as f:
                instr["window"].textConfShow_current.setText(f.read())
        except OSError as e:
            self._logger.exception(e)
        except TypeError as e:
            self._logger.error(f"missing Filename! (TypeError: {e})")

    def load_settings_itc503(self, instr):
        """load all settings store in the QSettings
        set corresponding values in the 'Global Settings' window"""
        settings = QSettings("TUW", "CryostatGUI")
        try:
            instr["_useAutoPID"] = bool(
                settings.value("%s_useAutoPID" % instr["ID"], int)
            )
            instr["_PIDFile"] = settings.value(
                "%s_PIDFile" % instr["ID"], str
            )
        except KeyError as e:
            QTimer.singleShot(20 * 1e3, self.load_settings)
            # self.show_error_general(f'could not find a key: {e}')
            self._logger.warning(f"key {e} was not found in the settings")
        del settings

        instr["window"].checkUseAuto.setChecked(
            instr["_useAutoPID"]
        )
        if isinstance(instr["_PIDFile"], str):
            text = instr["_PIDFile"]
        else:
            text = ""
        instr["window"].lineConfFile.setText(text)
        self.fun_PIDFile_read(instr=instr)

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setTemp_valcha(self, value, instr):
        # self.threads['control_ITC'][0].gettoset_Temperature(value)
        instr["values"]["temp"]["setTemp"] = value
        instr["values"]["temp"]["end"] = value
        instr["values"]["temp"]["start"] = None
        instr["values"]["temp"]["isSweepStartCurrent"] = True

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setRamp_valcha(self, value, instr):
        instr["values"]["temp"]["SweepRate"] = value
        # self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot(bool)
    @ExceptionHandling
    def fun_checkSweep_toggled(self, value, instr):
        instr["values"]["temp"]["isSweep"] = value

    @pyqtSlot()
    @ExceptionHandling
    def fun_sendConfTemp(self, instr):
        """sends command to change conf Temp, sends a dict with all the necessary Information for the setTemp
        function in the ITC controlClient"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setTemp_K": instr["values"]["temp"]}),
        )

    @pyqtSlot(float)
    def gettoset_GasOutput_itc503(self, value, instr):
        """receive and store the value to set the gas_output"""
        instr["values"]["setGasOutput"] = value

    @pyqtSlot(float)
    def gettoset_HeaterOutput_itc503(self, value, instr):
        """receive and store the value to set the heater_output"""
        instr["values"]["setHeaterOutput"] = value

    @pyqtSlot(bool)
    def send_gas_gothroughzero(self, boolean, instr):
        """send command when gas_gothroughzero is checked"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"gothroughzero": boolean}),
        )

    def fun_useAutoPID(self, boolean, instr):
        """set the variable for the softwareAutoPID
        emit signal to notify Thread
        store it in settings"""
        instr["_useAutoPID"] = boolean
        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue("%s_useAutoPID" % instr["ID"], int(boolean))
        del settings

    @ExceptionHandling
    def setPIDFile(self, file, instr):
        """reaction to signal: set AutoPID lookup file"""
        instr["PIDFile"] = file
        instr["PID_configuration"] = readPID_fromFile(
            instr["PIDFile"]
        )

    @ExceptionHandling
    def setCheckAutoPID(self, boolean, instr):
        """reaction to signal: set AutoPID behavior"""
        instr["useAutoPID"] = boolean

    @ExceptionHandling
    def fun_PIDFile_read(self, instr):
        try:
            with open(instr["_PIDFile"]) as f:
                instr["window"].textConfShow_current.setText(f.read())
        except OSError as e:
            self._logger.exception(e)
        except TypeError as e:
            self._logger.error(f"missing Filename! (TypeError: {e})")

    @ExceptionHandling
    def fun_PIDFile_send_itc503(self, dummy, instr):
        """reaction to signal: ITC PID file: send and store permanently"""
        if isinstance(instr["_PIDFile"], str):
            text = instr["_PIDFile"]
        else:
            text = ""
        self.commanding(
            ID=instr["ID"],
            message=dictdump(
                {
                    "ConfLoaD": "dummy",
                    "PIDFile": instr["_PIDFile"],
                    "useAuto": instr["_useAutoPID"],
                }
            ),
        )

        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue(
            "%s_PIDFile" % instr["ID"], instr["_PIDFile"]
        )
        del settings
        self.fun_PIDFile_read(instr=instr)

    @pyqtSlot()
    @ExceptionHandling
    def setGasOutput_itc503(self, instr):
        """set GasOutput of the instrument

        gas_output: Sets the percent of the maximum gas
                output in units of 1%.
                Min: 0. Max: 99.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setGasOutput": instr["values"]["setGasOutput"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setHeaterOutput_itc503(self, instr):
        """sends command to set HeaterOutput of the instrument

        heater_output: Sets the percent of the maximum
                    heater output in units of 0.1%.
                    Min: 0. Max: 999.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setHeaterOutput": instr["values"]["setHeaterOutput"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setProportional_itc503(self, instr):
        """sends command to set Proportional of the instrument

        prop: Proportional band, in steps of 0.0001K.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setProportional": instr["values"]["setProportional"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setIntegral_itc503(self, instr):
        """sends command to set Integral of the instrument

        integral: Integral action time, in steps of 0.1 minute.
                    Ranges from 0 to 140 minutes.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setIntegral": instr["values"]["setIntegral"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setDerivative_itc503(self, instr):
        """sends command to set Derivative of the instrument

        derivative: Derivative action time.
        Ranges from 0 to 273 minutes.
        """
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setDerivative": instr["values"]["setDerivative"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setInterval_itc503(self, instr):
        """sends command to set interval of the instrument ( not implemented in controlClient for the ITC)"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setInterval": instr["values"]["setInterval"]}),
        )

    @pyqtSlot(float)
    def gettoset_Proportional_itc503(self, value, instr):
        """receive and store the value to set the proportional (PID)"""
        instr["values"]["setProportional"] = value

    @pyqtSlot(float)
    def gettoset_Integral_itc503(self, value, instr):
        """receive and store the value to set the integral (PID)"""
        instr["values"]["setIntegral"] = value

    @pyqtSlot(float)
    def gettoset_Derivative_itc503(self, value, instr):
        """receive and store the value to set the derivative (PID)"""
        instr["values"]["setDerivative"] = value

    @pyqtSlot(float)
    def gettoset_Interval_itc503(self, value, instr):
        """receive and store the value to set the interval"""
        instr["values"]["setInterval"] = value
    def ITC503_Updater(self, data):
        """
        Calculate the rate of change of Temperature on the sensors [K/min]
        Store ITC data in self.data['ITC'], update ITC_window
        """
        # with self.dataLock:
        # print('storing: ', self.time_itc[-1]-time.time(), data['Sensor_1_K'])
        # self.time_itc.append(time.time())
        self.data_instruments[data["ID"]].update(data)
        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained
        if self.instrument_dict[data["ID"]]["lock"] == 1:
            for key in self.data:
                if self.data[key] is None:
                    self.data[key] = np.nan
            # if not self.data['Sensor_1_K'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdTemp_sens1_K.display(self.data_instruments[data["ID"]]["Sensor_1_K"])
            # if not self.data['Sensor_2_K'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdTemp_sens2_K.display(self.data_instruments[data["ID"]]["Sensor_2_K"])
            # if not self.data['Sensor_3_K'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdTemp_sens3_K.display(self.data_instruments[data["ID"]]["Sensor_3_K"])

            # if not self.data['set_temperature'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdTemp_set.display(self.data_instruments[data["ID"]]["set_temperature"])
            # if not self.data['temperature_error'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdTemp_err.display(self.data_instruments[data["ID"]]["temperature_error"])
            # if not self.data['heater_output_as_percent'] is None:
            try:
                self.instrument_dict[data["ID"]][
                    "window"
                ].progressHeaterPercent.setValue(
                    int(self.data_instruments[data["ID"]]["heater_output_as_percent"])
                )
                # if not self.data['gas_flow_output'] is None:
                self.instrument_dict[data["ID"]][
                    "window"
                ].progressNeedleValve.setValue(int(self.data_instruments[data["ID"]]["gas_flow_output"]))
            except ValueError:
                pass
            # if not self.data['heater_output_as_voltage'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdHeaterVoltage.display(self.data_instruments[data["ID"]]["heater_output_as_voltage"])
            # if not self.data['gas_flow_output'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdNeedleValve_percent.display(self.data_instruments[data["ID"]]["gas_flow_output"])
            # if not self.data['proportional_band'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdProportionalID.display(self.data_instruments[data["ID"]]["proportional_band"])
            # if not self.data['integral_action_time'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdPIntegrationD.display(self.data_instruments[data["ID"]]["integral_action_time"])
            # if not self.data['derivative_action_time'] is None:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdPIDerivative.display(self.data_instruments[data["ID"]]["derivative_action_time"])

            self.instrument_dict[data["ID"]][
                "window"
            ].lcdTemp_sens1_calcerr_K.display(self.data_instruments[data["ID"]]["Sensor_1_calerr_K"])

        # self.ITC_window.combosetAutocontrol.setCurrentIndex(self.data["autocontrol"])

    # ------- ------- ILM
    def initialize_ilm211(self, instrument_ilm211):
        self.instrument_dict[instrument_ilm211]["ID"] = instrument_ilm211
        self.instrument_dict[instrument_ilm211]["start"].clicked.connect(
            lambda value: self.start_instrument(
                instrument=self.instrument_dict[instrument_ilm211]["ID"]
            )
        )
        self.instrument_dict[instrument_ilm211]["mulitpl"] = 0
        self.initialize_state_threade(instrument_ilm211)
        self.instrument_dict[instrument_ilm211]["window"] = Window_ui(
            ui_file=".\\Oxford\\ILM_Qwidget.ui",
            parent=self,
        )
        self.instrument_dict[instrument_ilm211]["window"].sig_closing.connect(
            lambda: self.action_show_ILM.setChecked(False)
        )
        self.instrument_dict[instrument_ilm211]["show"].clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_ilm211]["window"]
            )
        )
        self.instrument_dict[instrument_ilm211][
            "window"
        ].combosetProbingRate_chan1.activated["int"].connect(
            lambda value: self.commanding(
                ID=self.instrument_dict[instrument_ilm211]["ID"],
                message=dictdump({"setProbingSpeed": value}),
            )
        )
        self.instrument_dict[instrument_ilm211][
            "window"
        ].spin_threadinterval.valueChanged.connect(
            lambda value: self.gettoset_spinThreadinterval_ilm211(
                value, instr=self.instrument_dict[instrument_ilm211]
            )
        )
        self.instrument_dict[instrument_ilm211][
            "window"
        ].send_command_spin_threadinterval.clicked.connect(
            lambda: self.set_spinThreadinterval_ilm211(
                instr=self.instrument_dict[instrument_ilm211]
            )
        )
        self.instrument_dict[instrument_ilm211]["values"] = {}
        # self.window_SystemsOnline.checkaction_run_ILM.clicked["bool"].connect(
        #    self.run_ILM
        # )
        # self.action_show_ILM.triggered["bool"].connect(self.show_ILM)
    @pyqtSlot()
    @ExceptionHandling
    def set_spinThreadinterval_ilm211(self, instr):
        """sends command to send spinThreadinterval"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setInterval": instr["values"]["setInterval"]}),
        )

    @pyqtSlot()
    def gettoset_spinThreadinterval_ilm211(self, value, instr):
        """saves value for spinThreadinterval"""
        instr["values"]["setInterval"] = value
    @pyqtSlot(dict)
    def ilm211_Updater(self, data):
        """
        Store Device data in self.data, update values in GUI
        """
        self.data_instruments[data["ID"]].update(data)

        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        # -----------------------------------------------------------------------------------------------------------
        # update the GUI
        if self.instrument_dict[data["ID"]]["lock"] == 1:
            chan1 = (
                100
                if self.data_instruments[data["ID"]]["channel_1_level"] > 100
                else self.data_instruments[data["ID"]]["channel_1_level"]
            )
            chan2 = (
                100
                if self.data_instruments[data["ID"]]["channel_2_level"] > 100
                else self.data_instruments[data["ID"]]["channel_2_level"]
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].progressLevelHe.setValue(chan1)
            self.instrument_dict[data["ID"]][
                "window"
            ].progressLevelN2.setValue(chan2)

            # tooltip = u"ILM\nHe: {:.1f}\nN2: {:.1f}".format(chan1, chan2)
            # self.ILM_window.pyqt_sysTray.setToolTip(tooltip)

            self.instrument_dict[data["ID"]][
                "window"
            ].lcdLevelHe.display(self.data_instruments[data["ID"]]["channel_1_level"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdLevelN2.display(self.data_instruments[data["ID"]]["channel_2_level"])

    @pyqtSlot(bool)
    def show_ILM(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.ILM_window.show()
        else:
            self.ILM_window.close()

        # -----------------------------------------------------

    # -------------- Lock-In SR 830  ------------------------
    def initialize_sr830(self, instrument_sr830):
        self.instrument_dict[instrument_sr830]["ID"] = instrument_sr830

        self.instrument_dict[instrument_sr830]["start"].clicked["bool"].connect(
            lambda value: self.start_instrument(
                instrument=self.instrument_dict[instrument_sr830]["ID"]
            )
        )
        self.instrument_dict[instrument_sr830]["multipl"] = 0
        self.initialize_state_threade(instrument_sr830)
        self.instrument_dict[instrument_sr830]["window"] = Window_ui(
            ui_file=".\\LockIn\\LockIn_control.ui",
            parent=self,
        )
        self.instrument_dict[instrument_sr830]["window"].sig_closing.connect(
            lambda: self.action_show_SR830.setChecked(False)
        )

        self.action_show_SR830.triggered["bool"].connect(
            lambda value: self.show_window(
                self.instrument_dict[instrument_sr830]["window"], value
            )
        )
        self.instrument_dict[instrument_sr830]["show"].clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_sr830]["window"]
            )
        )

        self.instrument_dict[instrument_sr830][
            "window"
        ].spinSetFrequency_Hz.valueChanged.connect(
            lambda value: self.gettoset_Frequency_sr830(
                value, instr=self.instrument_dict[instrument_sr830]
            )
        )
        self.instrument_dict[instrument_sr830][
            "window"
        ].send_command_frequency.clicked.connect(
            lambda: self.setFrequency_sr830(
                instr=self.instrument_dict[instrument_sr830]
            )
        )

        self.instrument_dict[instrument_sr830][
            "window"
        ].spinSetVoltage_V.valueChanged.connect(
            lambda value: self.gettoset_Voltage_sr830(
                value, instr=self.instrument_dict[instrument_sr830]
            )
        )
        self.instrument_dict[instrument_sr830][
            "window"
        ].send_command_voltage.clicked.connect(
            lambda: self.setVoltage_sr830(
                instr=self.instrument_dict[instrument_sr830]
            )
        )

        self.instrument_dict[instrument_sr830][
            "window"
        ].spinShuntResistance_kOhm.valueChanged.connect(
            lambda value: self.getShuntResistance_sr830(
                value * 1e3,
                instr=self.instrument_dict[instrument_sr830],
            )
        )
        self.instrument_dict[instrument_sr830][
            "window"
        ].send_command_shunt_resistor.clicked.connect(
            lambda: self.setShuntResistance_sr830(
                instr=self.instrument_dict[instrument_sr830]
            )
        )
        self.instrument_dict[instrument_sr830][
            "window"
        ].spinContactResistance_Ohm.valueChanged.connect(
            lambda value: self.getContactResistance_sr830(
                value, instr=self.instrument_dict[instrument_sr830]
            )
        )
        self.instrument_dict[instrument_sr830][
            "window"
        ].send_command_sample.clicked.connect(
            lambda: self.setContactResistance_sr830(
                instr=self.instrument_dict[instrument_sr830]
            )
        )
        self.instrument_dict[instrument_sr830]["values"] = {}
    @pyqtSlot()
    @ExceptionHandling
    def setFrequency_sr830(self, instr, f_Hz=None):
        """set a frequency"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setFrequency": instr["values"]["setFrequency"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setVoltage_sr830(self, instr, Voltage_V=None):
        """set a voltage"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setVoltage": instr["values"]["setVoltage"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setShuntResistance_sr830(self, instr, ShuntResitance_Ohm=None):
        """sets shunt resistance"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump(
                {"setShuntResistance": instr["values"]["setShuntResistance"]}
            ),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setContactResistance_sr830(
        self, instr, ContactResistance_Ohm=None
    ):
        """sets contact resistance"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump(
                {
                    "setContactResistance": instr["values"]["setContactResistance"],
                }
            ),
        )

    @pyqtSlot()
    def gettoset_Frequency_sr830(self, value, instr):
        """receive and store the value to set the frequency"""
        instr["values"]["setFrequency"] = value

    @pyqtSlot()
    def gettoset_Voltage_sr830(self, value, instr):
        """receive and store the value to set the voltage"""
        instr["values"]["setVoltage"] = value

    @pyqtSlot()
    def getShuntResistance_sr830(self, value, instr):
        """receive and store the value of the shunt resistance"""
        instr["values"]["setShuntResistance"] = value

    @pyqtSlot()
    def getContactResistance_sr830(self, value, instr):
        """receive and store the value of the samples' contact resistance"""
        instr["values"]["setContactResistance"] = value

    @pyqtSlot(dict)
    def SR830_Updater(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""
        self.data[data["ID"]].update(data)
        # data['date'] = convert_time(time.time())
        # self.data['SR830'].update(data)
        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained
        if self.instrument_dict[data["ID"]]["lock"] == 1:
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSetFrequency_Hz.display(self.data_instruments[data["ID"]]["Frequency_Hz"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSetVoltage_V.display(self.data_instruments[data["ID"]]["Voltage_V"])
            self.instrument_dict[data["ID"]][
                "window"
            ].textX_V.setText("{num:=+13.12f}".format(num=self.data_instruments[data["ID"]]["X_V"]))
            self.instrument_dict[data["ID"]][
                "window"
            ].textSampleCurrent_mA.setText(
                "{num:=+8.6f}".format(num=self.data_instruments[data["ID"]]["SampleCurrent_mA"])
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].textSampleResistance_Ohm.setText(
                "{num:=+8.6f}".format(num=self.data_instruments[data["ID"]]["SampleResistance_Ohm"])
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].textY_V.setText("{num:=+13.12f}".format(num=self.data_instruments[data["ID"]]["Y_V"]))
            self.instrument_dict[data["ID"]][
                "window"
            ].textR_V.setText("{num:=+13.12f}".format(num=self.data_instruments[data["ID"]]["R_V"]))
            self.instrument_dict[data["ID"]][
                "window"
            ].textTheta_Deg.setText(
                "{num:=+8.6f}".format(num=self.data_instruments[data["ID"]]["Theta_Deg"])
            )

    # ----------------sr860-----------------------
    def initialize_sr860(self, instrument_sr860):
        """initialize sr860"""
        self.instrument_dict[instrument_sr860]["ID"] = instrument_sr860

        self.instrument_dict[instrument_sr860]["start"].clicked["bool"].connect(
            lambda value: self.start_instrument(
                instrument=self.instrument_dict[instrument_sr860]["ID"]
            )
        )
        self.instrument_dict[instrument_sr860]["state_data"] = {}
        self.instrument_dict[instrument_sr860]["multipl"] = 0
        self.initialize_state_threade(instrument_sr860)
        self.instrument_dict[instrument_sr860]["values"] = {}

        self.instrument_dict[instrument_sr860]["window"] = Window_ui(
            ui_file=".\\LockIn\\LockIn_control.ui",
            parent=self,
        )
        # self.LockIn_window_sr860.sig_closing.connect(
        #    lambda: self.action_show_SR860.setChecked(False)
        # )

        # self.action_show_SR830.triggered["bool"].connect(
        #    lambda value: self.show_window(self.LockIn_window_sr830, value)
        # )
        self.instrument_dict[instrument_sr860]["show"].clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(
                self.instrument_dict[instrument_sr860]["window"]
            )
        )

        self.instrument_dict[instrument_sr860][
            "window"
        ].spinSetFrequency_Hz.valueChanged.connect(
            lambda value: self.gettoset_Frequency_sr860(
                value, instr=self.instrument_dict[instrument_sr860]
            )
        )
        self.instrument_dict[instrument_sr860][
            "window"
        ].send_command_frequency.clicked.connect(
            lambda: self.setFrequency_sr860(
                instr=self.instrument_dict[instrument_sr860]
            )
        )

        self.instrument_dict[instrument_sr860][
            "window"
        ].spinSetVoltage_V.valueChanged.connect(
            lambda value: self.gettoset_Voltage_sr860(
                value, instr=self.instrument_dict[instrument_sr860]
            )
        )
        self.instrument_dict[instrument_sr860][
            "window"
        ].send_command_voltage.clicked.connect(
            lambda: self.setVoltage_sr860(
                instr=self.instrument_dict[instrument_sr860]
            )
        )

        self.instrument_dict[instrument_sr860][
            "window"
        ].spinShuntResistance_kOhm.valueChanged.connect(
            lambda value: self.getShuntResistance_sr860(
                value * 1e3,
                instr=self.instrument_dict[instrument_sr860],
            )
        )
        self.instrument_dict[instrument_sr860][
            "window"
        ].send_command_shunt_resistor.clicked.connect(
            lambda: self.setShuntResistance_sr860(
                instr=self.instrument_dict[instrument_sr860]
            )
        )
        self.instrument_dict[instrument_sr860][
            "window"
        ].spinContactResistance_Ohm.valueChanged.connect(
            lambda value: self.getContactResistance_sr860(
                value, instr=self.instrument_dict[instrument_sr860]
            )
        )
        self.instrument_dict[instrument_sr860][
            "window"
        ].send_command_sample.clicked.connect(
            lambda: self.setContactResistance_sr860(
                instr=self.instrument_dict[instrument_sr860]
            )
        )
    @pyqtSlot()
    @ExceptionHandling
    def setFrequency_sr860(self, instr, f_Hz=None):
        """set a frequency"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setFrequency": instr["values"]["setFrequency"]}),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setVoltage_sr860(self, instr, Voltage_V=None):
        """set a voltage"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump({"setVoltage": instr["values"]["setVoltage"]}),
        )

    @pyqtSlot()
    def gettoset_Frequency_sr860(self, value, instr):
        """receive and store the value to set the frequency"""
        instr["setFrequency"]["values"] = value

    @pyqtSlot()
    @ExceptionHandling
    def setShuntResistance_sr860(self, instr, ShuntResitance_Ohm=None):
        """sets shunt resistance"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump(
                {"setShuntResistance": instr["values"]["setShuntResistance"]}
            ),
        )

    @pyqtSlot()
    @ExceptionHandling
    def setContactResistance_sr860(
        self, instr, ContactResistance_Ohm=None
    ):
        """sets contact resistance"""
        self.commanding(
            ID=instr["ID"],
            message=dictdump(
                {"setContactResistance": instr["values"]["setContactResistance"]}
            ),
        )

    @pyqtSlot()
    def gettoset_Voltage_sr860(self, value, instr):
        """receive and store the value to set the voltage"""
        instr["values"]["setVoltage"] = value

    @pyqtSlot()
    def getShuntResistance_sr860(self, value, instr):
        """receive and store the value of the shunt resistance"""
        instr["values"]["setShuntResistance"] = value

    @pyqtSlot()
    def getContactResistance_sr860(self, value, instr):
        """receive and store the value of the samples' contact resistance"""
        instr["values"]["setContactResistance"] = value

    @pyqtSlot(dict)
    def SR860_Updater(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""
        self.data_instruments[data["ID"]].update(data)
        # data['date'] = convert_time(time.time())
        # self.data['SR830'].update(data)
        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained
        if self.instrument_dict[data["ID"]]["lock"] == 1:

            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSetFrequency_Hz.display(self.data_instruments[data["ID"]]["Frequency_Hz"])
            self.instrument_dict[data["ID"]][
                "window"
            ].lcdSetVoltage_V.display(self.data_instruments[data["ID"]]["Voltage_V"])
            self.instrument_dict[data["ID"]][
                "window"
            ].textX_V.setText("{num:=+13.12f}".format(num=self.data_instruments[data["ID"]]["X_V"]))

            self.instrument_dict[data["ID"]][
                "window"
            ].textSampleCurrent_mA.setText(
                "{num:=+8.6f}".format(num=self.data_instruments[data["ID"]]["SampleCurrent_mA"])
            )
            self.instrument_dict[data["ID"]][
                "window"
            ].textSampleResistance_Ohm.setText(
                "{num:=+8.6f}".format(num=self.data_instruments[data["ID"]]["SampleResistance_Ohm"])
            )

            self.instrument_dict[data["ID"]][
                "window"
            ].textY_V.setText("{num:=+13.12f}".format(num=self.data_instruments[data["ID"]]["Y_V"]))
            self.instrument_dict[data["ID"]][
                "window"
            ].textR_V.setText("{num:=+13.12f}".format(num=self.data_instruments[data["ID"]]["R_V"]))
            self.instrument_dict[data["ID"]][
                "window"
            ].textTheta_Deg.setText(
                "{num:=+8.6f}".format(num=self.data_instruments[data["ID"]]["Theta_Deg"])
            )
        # ----------Window_errors--------------

    def initialize_window_Errors(self):
        """initialize Error Window"""
        self.Errors_window = Window_ui(ui_file=".\\configurations\\Errors.ui")
        self.Errors_window.sig_closing.connect(
            lambda: self.action_show_Errors.setChecked(False)
        )

        self.Errors_window.textErrors.setHtml("")

        # self.action_run_Errors.triggered['bool'].connect(self.run_ITC)
        self.action_show_Errors.triggered["bool"].connect(self.show_Errors)
        # self.show_Errors(True)
        # self.Errors_window.showMinimized()

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
            "{} - {}".format(dt.now().strftime("%Y-%m-%d  %H:%M:%S.%f"), text)
        )
        if not self.Errors_window.checkSilence.isChecked():
            self.Errors_window.show()
            self.Errors_window.raise_()
        # self.Errors_window.activateWindow()

    @pyqtSlot(bool)
    def show_Errors(self, boolean):
        """display/close the Error window"""
        if boolean:
            self.Errors_window.show()
        else:
            self.Errors_window.close()


if __name__ == "__main__":

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logger_2 = logging.getLogger("pyvisa")
    logger_2.setLevel(logging.INFO)
    logger_3 = logging.getLogger("PyQt5")
    logger_3.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger_2.addHandler(handler)
    logger_3.addHandler(handler)

    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow(
        app=app,
        ui_file=".\\configurations\\testnew.ui",
        identity="MainWindow_1"
    )
    form.show()
    # print("date: ", dt.now(), "\nstartup time: ", time.time() - a)

    sys.exit(app.exec_())
