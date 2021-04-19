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
import time as t
from PyQt5 import QtWidgets, QtGui
from datetime import datetime as dt
# from PyQt5.QtCore import QObject
# from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QSettings
from datetime import datetime as dt2
import datetime

# from PyQt5.QtWidgets import QtAlignRight
from PyQt5.uic import loadUi

import subprocess
import os
import sys
import datetime as dt3
from threading import Lock
import numpy as np
from copy import deepcopy
import logging

#import json

from pyvisa.errors import VisaIOError

from drivers import ApplicationExit
#import measureSequences as mS

# import Oxford
# from Oxford.ITC_control import ITC_Updater
# from Oxford.ILM_control import ILM_Updater
# from Oxford.IPS_control import IPS_Updater
# from LakeShore.LakeShore350_Control import LakeShore350_Updater
# from Keithley.Keithley2182_Control import Keithley2182_Updater
# from Keithley.Keithley6221_Control import Keithley6221_Updater

# from LockIn.LockIn_SR830_control import SR830_Updater

#from Sequence import OneShot_Thread
#from Sequence import OneShot_Thread_multichannel
#from Sequence import Sequence_Thread

#from loggingFunctionality.logger import main_Logger
#from loggingFunctionality.logger import live_Logger
#from loggingFunctionality.logger import measurement_Logger
#from loggingFunctionality.logger import Logger_configuration
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
from util.zmqcomms import zmqquery_handle
from util.zmqcomms import genericAnswer
from util.zmqcomms import zmqMainControl
from pid import PidFile
from pid import PidFileError
errorfile = "Errors\\" + dt3.datetime.now().strftime("%Y%m%d") + ".error"

class check_active(AbstractLoopThread):
    """Makes a Thread that checks if Windowsservice is running """
    a="init"
    data = {}
    def __init__(self, Instrument=None, test=None, **kwargs):

        super().__init__(**kwargs)
        self.__name__ = "MainWindow_check_active"
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.setInterval(0.2)
        #self.button=button
        self.instrument=Instrument
        self.test=test
        #p1 = subprocess.run('sc query "CryostatGui_%s" | find "RUNNING"' % self.instrument, capture_output=True, text=True, shell=True)
        #self.a = p1.stdout
        #self.data["state"]=self.a
        #self.sig_Infodata.emit(deepcopy(self.data))


    def running(self):

        p2 = subprocess.run('sc query "CryostatGui_%s" | find "RUNNING"' % self.instrument, capture_output=True, text=True, shell=True)
        if self.a != p2.stdout:
            self.data["state"]=p2.stdout
            self.sig_Infodata.emit(deepcopy(self.data))
            print("test")
        
        self.a=p2.stdout

class get_data(AbstractLoopThreadDataStore):
    """Thread that gets data from broker and sends them to mainGui"""
    sig_sr830 = pyqtSignal(dict)
    sig_sr860 = pyqtSignal(dict)
    sig_keithley2182 = pyqtSignal(dict)
    sig_keithley6221 = pyqtSignal(dict)
    sig_lakeshore350 = pyqtSignal(dict)
    sig_ilm211 = pyqtSignal(dict)
    sig_itc503 = pyqtSignal(dict)
    sig_ips120 = pyqtSignal(dict)
    sig_state_keithley6221 = pyqtSignal(dict)
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.__name__ = "get_data_mainWindow"
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.data_sr830={}
        self.data_sr860={}
        self.data_keithley2182={}
        self.data_keithley6221={}
        self.data_lakeshore350={}
        self.data_ilm211={}
        self.data_itc503={}
        self.data_ips120={}
        self.crash_keithley6221={}
        self.multipl_keithley=0
    def running(self):
        self.run_finished=False
        #print(self.data_main)
        #self.sig_Infodata.emit(deepcopy(self.data_main))
        t.sleep(1)

        self.run_finished=True
    def store_data(self,ID,data):
        if ID == "SR830_1":
        	self.data_sr830.update(data)
        	self.sig_sr830.emit(deepcopy(self.data_sr830))
        if ID == "sr860_1":
        	self.data_sr860.update(data)
        	self.sig_sr860.emit(deepcopy(self.data_sr860))
        if ID == "Keithley2182_1":
        	self.data_keithley2182.update(data)
        	self.sig_keithley2182.emit(deepcopy(self.data_keithley2182))
        if ID == "Keithley6221_1":
        	self.data_keithley6221.update(data)
        	self.sig_keithley6221.emit(deepcopy(self.data_keithley6221))
        	if datetime.datetime.strptime('%s' %self.data_keithley6221["time"], '%Y-%m-%d %H:%M:%S.%f') < dt.now()-datetime.timedelta(minutes=5):
        		self.multipl_keithley= self.multipl_keithley+1
        		self.crash_keithley6221["state"] = "crashed"
        		self.crash_keithley6221["multipl"] = self.multipl_keithley
        		self.sig_state_keithley6221.emit(self.crash_keithley6221)
        		print("%s" %self.multipl_keithley)
        	else:
       			print("ho")
       			self.multipl_keithley=0
        if ID == "LakeShore350":
        	self.data_lakeshore350.update(data)
        	self.sig_lakeshore350.emit(deepcopy(self.data_lakeshore350))
        if ID == "ILM":
        	self.data_ilm211.update(data)
        	self.sig_ilm211.emit(deepcopy(self.data_ilm211))
        if ID == "ITC":
        	self.data_itc503.update(data)
        	self.sig_itc503.emit(deepcopy(self.data_itc503))
        if ID == "IPS":
        	self.data_ips120.update(data)
        	self.sig_ips120.emit(deepcopy(self.data_ips120))
        else:
        	print("no signal")





class mainWindow(AbstractMainApp,Window_ui,zmqMainControl):
    error_message_start={}
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

    sig_sr830 = pyqtSignal(dict)
    sig_sr860 = pyqtSignal(dict)
    sig_keithley2182 = pyqtSignal(dict)
    sig_keithley6221 = pyqtSignal(dict)
    sig_lakeshore350 = pyqtSignal(dict)
    sig_ilm211 = pyqtSignal(dict)
    sig_itc503 = pyqtSignal(dict)
    sig_ips120 = pyqtSignal(dict)
   
    def __init__(self, app, Lockin=None, identity=None, prometheus_port=None, **kwargs):
        self._Lockin = Lockin
        self._identity=identity
        self.prometheus_port = prometheus_port
        super().__init__(**kwargs)
        loadUi(".\\configurations\\test.ui", self)
        # self.setupUi(self)

        self.__name__ = "MainWindow"
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.threads = dict(Lock=Lock())
        # self.threads = dict()

        self.controls = ["c"]
        self.threads_tiny = []
        
        self.sr830_check_state_data = {}
        self.itc503_check_state_data = {}
        self.ilm211_check_state_data = {}
        self.sr860_check_state_data = {}
        self.lakeshore350_check_state_data = {}
        self.keithley6221_check_state_data = {} 
        self.keithley2182_check_state_data = {}       

        self.data_sr830={'Frequency_Hz': 999, 'Voltage_V': 999, 'X_V': 999, 'Y_V': 999, 'R_V': 999,'Theta_Deg': 999,
        'ShuntResistance_user_Ohm': 999,'SampleResistance_Ohm' : 999,'SampleCurrent_A' : 999,'ContactResistance_user_Ohm': 999,}
        self.data_sr860={'Frequency_Hz': 999, 'Voltage_V': 999, 'X_V': 999, 'Y_V': 999, 'R_V': 999,'Theta_Deg': 999,
        'ShuntResistance_user_Ohm': 999,'SampleResistance_Ohm' : 999,'SampleCurrent_A' : 999,'ContactResistance_user_Ohm': 999}
        self.data_keithley2182={"TemperatureInternal_K":999, "Voltage_V": 999,"TemperaturePresent_K": 999}
        self.data_keithley6221={"Current_A": 999, "set_Output": 1}
        self.data_lakeshore350={"Sensor_1_K": 999,"Sensor_2_K": 999,"Sensor_3_K":999,"Sensor_4_K": 999,"set_temperature": 999,"heater_output_as_percent": 999
        ,"heater_output_as_voltage": 999,"Loop_P_Param":999,"Loop_I_Param":999,"Loop_D_Param":999,"Input_Sensor":999,"Ramp_Rate":999,"Heater_Output_mW":999, "Temp_K":999}
        self.data_ilm211={"channel_1_level": 999,"channel_2_level": 999}
        self.data_itc503={"Sensor_1_K": 999,"Sensor_2_K": 999,"Sensor_3_K":999,"Sensor_3_K": 999,"set_temperature": 999,"temperature_error":999,"heater_output_as_voltage": 999,"gas_flow_output": 999,
        "proportional_band": 999,"integral_action_time": 999,"derivative_action_time": 999,"Sensor_1_calerr_K": 999,"heater_output_as_percent": 999, "gas_flow_output": 999,'interval_thread': 999}
        self.data_ips120={}
        self.ITC_values={}
        self.lakeshore_values={}

        self.state_keithley6221={}
        
        self.logging_bools = {}
        self.logging_running_ITC = False
        self.logging_running_logger = False
        self.button = self.sr830_main_state
        self.dataLock = Lock()
        self.dataLock_live = Lock()
        self.GPIB_comLock = Lock()
        self.app = app
        self.identity='sr830'
        self.command='measure_Resistance'
        self.get_data = self.running_thread_control(get_data(),'get data')
        self.get_data.sig_Infodata.connect(self.update_data)
        QTimer.singleShot(0, self.runnning_mainWindow)
        #QTimer.singleShot(0,self.get_data)
        #with open(errorfile, "a") as f:
        #    f.write("{} - {}\n".format(convert_time(time.time()), "STARTUP PROGRAM"))
        #instrument_text=Record()
    def runnning_mainWindow(self):
        """initialize all the windows for main GUi"""
        self.initialize_sr830()
        self.initialize_window_Errors()
        self.initialize_window_ITC()
        self.initialize_ilm211()
        self.initialize_sr860()
        self.initialize_window_LakeShore350()
        self.initialize_window_Keithley6221()
        self.initialize_window_Keithley2182()
      
    def show_window_button_pressed(self,window):
        """show and close window when show button is pressed"""
        window.show()
        window.raise_()

    def update_data(self,data):
        """gets data from thread and update all the individuell GUIS"""
        self.data.update(data)
        #print(self.data)
        self.SR830_Updater(self.data)
        self.ITC503_Updater(self.data)
        self.ilm211_Updater(self.data)
        self.SR860_Updater(self.data)
        #self.start_instument.release()
    def start_instrument(self,instrument=None):
        self.instrument= instrument
        p1 = subprocess.run('sc query "CryostatGui_%s" | find "RUNNING"' % self.instrument, capture_output=True, text=True, shell=True)
        a = p1.stdout

        if "RUNNING" in a:
            p2 = subprocess.run('sc stop "CryostatGui_%s"' % self.instrument) 
        else: 
            p2 = subprocess.run('sc start "CryostatGui_%s"' % self.instrument)
        if p2.returncode!=0:
            self.show_error_general("Couldn´t start or stop service CryostatGui_%s" % self.instrument)  
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
    #--------Lakeshore350
    def initialize_window_LakeShore350(self):
        """initialize LakeShore Window"""
        self.LakeShore350_window = Window_ui(
            ui_file=".\\LakeShore\\lakeShore350_Qwidget.ui"
        )
        self.LakeShore350_window.sig_closing.connect(
            lambda: self.action_show_LakeShore350.setChecked(False)
        )
        self.get_data.sig_lakeshore350.connect(self.Lakeshore350_Updater)
        
        self.get_active_state_lakeshore350= self.running_thread_control(check_active(Instrument='lakeshore350'),'check_state_lakeshore350')
        self.get_active_state_lakeshore350.sig_Infodata.connect(self.update_check_state_lakeshore350)

        # self.LakeShore350_window.textSensor1_Kpmin.setAlignment(QtAlignRight)
        #connecting buttons in the main Window
        self.lakeshore350_main_start.clicked["bool"].connect(
            lambda value: self.start_instrument(instrument='Lakeshore350')
            )
        self.lakeshore350_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.LakeShore350_window)
        )
        self.action_show_LakeShore350.triggered["bool"].connect(self.show_LakeShore350)
        self.LakeShore350_Kpmin = None
        #connecting buttons to send commands upstream
        #changing the temp buttons
        self.LakeShore350_window.spinSetTemp_K.valueChanged.connect(self.fun_setTemp_valcha_lakeshore350)
        self.LakeShore350_window.checkRamp_Status.toggled["bool"].connect(self.fun_checkSweep_toggled_lakeshore350)
        self.LakeShore350_window.spinSetRamp_Kpmin.valueChanged.connect(self.fun_setRamp_valcha_lakeshore350)
        self.LakeShore350_window.commandSendConfTemp.clicked.connect(self.fun_sendConfTemp_lakeshore350)

        self.LakeShore350_window.pushButtonHeaterOut.clicked.connect(
        	lambda: self.commanding(ID="LakeShore350",message=dictdump({"setHeaterOut" : 0})))

        self.LakeShore350_window.comboSetInput_Sensor.activated["int"].connect(
        	lambda value: self.commanding(ID="LakeShore350",message=dictdump({"setInput_Sensor" : value+1})))

        self.LakeShore350_window.spinSetLoopP_Param.valueChanged.connect(lambda value: self.gettoset_Proportional_lakeshore350(value))
        self.LakeShore350_window.send_command_spinSetLoopP_Param.clicked.connect(self.setProportional_lakeshore350)

        self.LakeShore350_window.spinSetLoopI_Param.valueChanged.connect(lambda value:self.gettoset_Integral_lakeshore350(value))
        self.LakeShore350_window.send_command_spinSetLoopI_Param.clicked.connect(lambda: self.setIntegral_lakeshore3550())

        self.LakeShore350_window.spinSetLoopD_Param.valueChanged.connect(lambda value: self.gettoset_Derivative_lakeshore350(value))
        self.LakeShore350_window.send_command_spinSetLoopD_Param.clicked.connect(lambda: self.setDerivative_lakeshore350())
        #set Interval not implemented in controlClient
        self.LakeShore350_window.spin_threadinterval.valueChanged.connect(lambda value: self.gettoset_Interval_lakeshore350(value))
        self.LakeShore350_window.send_command_spin_threadinterval.clicked.connect(lambda: self.setInterval_lakeshore350())

    @pyqtSlot(bool)
    def show_LakeShore350(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.LakeShore350_window.show()
        else:
            self.LakeShore350_window.close()
    def update_check_state_lakeshore350(self,data):
    	"""Updates the state Label in the main GUI"""
    	self.lakeshore350_check_state_data.update(data)
    	print("update_check")
    	if "RUNNING" in data["state"]:
    		self.lakeshore350_main_state.setText("Running")
    		self.lakeshore350_main_state.setStyleSheet("color:green")
    	else:
    		self.lakeshore350_main_state.setText("Not Running")
    		self.lakeshore350_main_state.setStyleSheet("color:red") 
    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setTemp_valcha_lakeshore350(self, value):
        # self.threads['control_ITC'][0].gettoset_Temperature(value)
        self.lakeshore_values["setTemp"] = value
        self.lakeshore_values["end"] = value

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setRamp_valcha_lakeshore350(self, value):
        self.lakeshore_values["SweepRate"] = value
        # self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot(bool)
    @ExceptionHandling
    def fun_checkSweep_toggled_lakeshore350(self, boolean):
        self.lakeshore_values["isSweep"] = boolean

    @pyqtSlot()
    @ExceptionHandling
    def fun_sendConfTemp_lakeshore350(self):
    	"""sends command to change conf Temp, sends a dict with all the necessary Information for the setTemp
    	function in the ITC controlClient"""
    	self.commanding(ID="LakeShore350",message=dictdump({"setInterval" : self.lakeshore_values}))

    @pyqtSlot()
    @ExceptionHandling
    def setProportional_lakeshore350(self):
        """sends command to set Proportional of the instrument

        prop: Proportional band, in steps of 0.0001K.
        """
        self.commanding(ID="Lakeshore350", message=dictdump({"setProportional" : self.set_prop_lakeshore350}))

    @pyqtSlot()
    @ExceptionHandling
    def setIntegral_lakeshore3550(self):
        """sends command to set Integral of the instrument

        integral: Integral action time, in steps of 0.1 minute.
                    Ranges from 0 to 140 minutes.
        """
        self.commanding(ID="LakeShore350", message=dictdump({"setIntegral" : self.set_integral_lakeshore350}))

    @pyqtSlot()
    @ExceptionHandling
    def setDerivative_lakeshore350(self):
        """sends command to set Derivative of the instrument

        derivative: Derivative action time.
        Ranges from 0 to 273 minutes.
        """
        self.commanding(ID="LakeShore350", message=dictdump({"setDerivative" : self.set_derivative_lakeshore350}))

    @pyqtSlot()
    @ExceptionHandling
    def setInterval_lakeshore350(self):
        """sends command to set interval of the instrument ( not implemented in controlClient for the ITC)
        """
        self.commanding(ID="Lakeshore350", message=dictdump({"setInterval" : self.set_interval_lakeshore350}))    
    @pyqtSlot(float)
    def gettoset_Proportional_lakeshore350(self, value):
        """receive and store the value to set the proportional (PID)"""
        self.set_prop_lakeshore350 = value

    @pyqtSlot(float)
    def gettoset_Integral_lakeshore350(self, value):
        """receive and store the value to set the integral (PID)"""
        self.set_integral_lakeshore350 = value

    @pyqtSlot(float)
    def gettoset_Derivative_lakeshore350(self, value):
        """receive and store the value to set the derivative (PID)"""
        self.set_derivative_lakeshore350 = value
    @pyqtSlot(float)
    def gettoset_Interval_lakeshore350(self, value):
    	"""receive and store the value to set the interval"""
    	self.set_interval_lakeshore350 = value
    @pyqtSlot(dict)
    def Lakeshore350_Updater(self, data):
        """
        Calculate the rate of change of Temperature on the sensors [K/min]
        Store LakeShore350 data in self.data['LakeShore350'], update LakeShore350_window
        """
        self.data_lakeshore350.update(data)
        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # self.data['LakeShore350'].update(data)
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        self.LakeShore350_window.progressHeaterOutput_percentage.setValue(
            self.data["Heater_Output_percentage"]
        )
        self.LakeShore350_window.lcdHeaterOutput_mW.display(self.data["Heater_Output_mW"])
        self.LakeShore350_window.lcdSetTemp_K.display(self.data["Temp_K"])
        # self.lcdRampeRate_Status.display(self.data['RampRate_Status'])
        self.LakeShore350_window.lcdSetRampRate_Kpmin.display(self.data["Ramp_Rate"])

        self.LakeShore350_window.comboSetInput_Sensor.setCurrentIndex(int(self.data["Input_Sensor"]) - 1)
        self.LakeShore350_window.lcdSensor1_K.display(self.data["Sensor_1_K"])
        self.LakeShore350_window.lcdSensor2_K.display(self.data["Sensor_2_K"])
        self.LakeShore350_window.lcdSensor3_K.display(self.data["Sensor_3_K"])
        self.LakeShore350_window.lcdSensor4_K.display(self.data["Sensor_4_K"])

        """NEW GUI to display P,I and D Parameters
        """
        self.LakeShore350_window.lcdLoopP_Param.display(self.data["Loop_P_Param"])
        self.LakeShore350_window.lcdLoopI_Param.display(self.data["Loop_I_Param"])
        self.LakeShore350_window.lcdLoopD_Param.display(self.data["Loop_D_Param"])
    # --------Keithleys
    #---------------Keithley 6221
    def initialize_window_Keithley6221(self):
        self.keithley6221_window = Window_ui(ui_file=".\\Keithley\\K6221_QWidget.ui")
        self.keithley6221_window.sig_closing.connect(
            lambda: self.action_show_Keithley.setChecked(False)
        )
        self.get_data.sig_keithley6221.connect(self.Keithley6221_Updater)
        self.keithley6221_main_start.clicked["bool"].connect(
            lambda value: self.start_instrument(instrument='keithley6221')
            )
        self.action_show_Keithley.triggered["bool"].connect(
            lambda value: self.show_window(self.keithley6221_window, value)
        )
        self.keithley6221_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.keithley6221_window)
        )
        self.get_data.sig_state_keithley6221.connect(self.crasherror_keithley6221)
        # self.mdiArea.addSubWindow(self.ITC_window)
        self.get_active_state_keithley6221 = self.running_thread_control(check_active(Instrument='keithley6221'),'check_state_keithley6221')
        self.get_active_state_keithley6221.sig_Infodata.connect(self.update_check_state_keithley6221)
        self.keithley6221_window.spinSetCurrent_mA.valueChanged.connect(lambda value: self.gettoset_spinSetCurrent_keithley6221(value))
        self.keithley6221_window.send_command_spinSetCurrent_mA.clicked.connect(lambda: self.set_spinSetCurrent_keithley6221())
        self.keithley6221_window.pushToggleOut.clicked.connect(lambda value: self.output_keithley6221_clicked())
        self.keithley6221_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.keithley6221_window)
        )
    def crasherror_keithley6221(self,data):
    	self.state_keithley6221.update(data)
    	if self.state_keithley6221["state"]=="crashed":
    		if self.state_keithley6221["multipl"]==1:
    			 self.show_error_general("Service CryostatGui_Keithley6221 crashed")
    			 self.keithley6221_main_state.setText("Running")


    def output_keithley6221_clicked(self):
    	if self.data_keithley6221["set_Output"] == 1:
    		self.commanding(ID="Keithley6221_1",message=dictdump({"set_Output": 0}))
    	else:
    		self.commanding(ID="Keithley6221_1",message=dictdump({"set_Output": 1}))

    def set_spinSetCurrent_keithley6221(self):
    	"""Send command to controleClient to set spinCurrent in mA"""
    	self.commanding(ID="Keithley6221_1",message=dictdump({"set_Current_A": self.set_spinCurrent_keithley6221}))   	
    def gettoset_spinSetCurrent_keithley6221(self,value):
    	"""receive and store the value to set the spinCurrent"""
    	self.set_spinCurrent_keithley6221 = value
    def Keithley6221_Updater(self,data):
    	"""Updater function for the Keithley6221 Window"""
    	self.data_keithley6221.update(data)
    	#self.keithley6221_window.spinSetCurrent_mA.display(self.data_keithley6221("Current_A"))
    	if self.data_keithley6221["set_Output"] == 1:
    		self.keithley6221_window.pushToggleOut.setText("Output is On")
    	else:
    		self.keithley6221_window.pushToggleOut.setText("Output is OFF")
    def update_check_state_keithley6221(self,data):
    	"""Updates the state Label in the main GUI"""
    	self.keithley6221_check_state_data.update(data)
    	print("update_check")
    	if "RUNNING" in data["state"]:
    		self.keithley6221_main_state.setText("Running")
    		self.keithley6221_main_state.setStyleSheet("color:green")
    	else:
    		self.keithley6221_main_state.setText("Not Running")
    		self.keithley6221_main_state.setStyleSheet("color:red") 
    #---------------Keithley 6221
    def initialize_window_Keithley2182(self):
        self.keithley2182_window = Window_ui(ui_file=".\\Keithley\\K2182_QWidget.ui")
        self.keithley2182_window.sig_closing.connect(
            lambda: self.action_show_Keithley.setChecked(False)
        )
        self.get_data.sig_keithley2182.connect(self.Keithley2182_Updater)
        self.keithley2182_main_start.clicked["bool"].connect(
            lambda value: self.start_instrument(instrument='keithley2182')
            )
        self.action_show_Keithley.triggered["bool"].connect(
            lambda value: self.show_window(self.keithley6221_window, value)
        )
        self.keithley2182_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.keithley2182_window)
        )
        
        self.get_active_state_keithley2182 = self.running_thread_control(check_active(Instrument='keithley2182'),'check_state_keithley2182')
        self.get_active_state_keithley2182.sig_Infodata.connect(self.update_check_state_keithley2182)
        self.keithley2182_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.keithley2182_window)
        )
        #all the QCheckboxes
        self.keithley2182_window.checkBox_Display_1.stateChanged.connect(lambda value: self.send_command_display_keithley2182(value))
        self.keithley2182_window.checkBox_Autozero_1.stateChanged.connect(lambda value: self.send_command_autozero_keithley2182(value))
        self.keithley2182_window.checkBox_FrontAutozero_1.stateChanged.connect(lambda value: self.send_command_frontautozero_keithley2182(value))
        self.keithley2182_window.checkBox_Autorange_1.stateChanged.connect(lambda value: self.send_command_autorange_keithley2182(value))
    def send_command_autorange_keithley2182(self, state):
    	"""sends autorange command to the controlClient"""
    	if state == 2:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"Autorange_1": 1}))
    	else:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"Autorange_1": 0}))      	
    def send_command_frontautozero_keithley2182(self, state):
    	"""send fronAutozero command to the controlClient"""
    	if state == 2:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"frontAutozero_1": 1}))
    	else:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"frontAutozero_1": 0}))    	
    def send_command_autozero_keithley2182(self,state):
    	"""sends autozero command to the controlClient"""
    	if state == 2:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"Autozero_1": 1}))
    	else:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"Autozero_1": 0}))
    def send_command_display_keithley2182(self,state):
    	"""sends Display command to the controlClient"""
    	if state == 2:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"Display_1": 1}))
    	else:
    		self.commanding(ID="Keithley2182_1",message=dictdump({"Display_1": 0}))
    def Keithley2182_Updater(self,data):
    	"""Updater function for the Keithley6221 Window"""
    	self.data_keithley2182.update(data)
    	self.keithley2182_window.textVoltage_V.display(self.data_keithley2182("Voltage_V"))
    	self.keithley2182_window.textTempInternal_K.display(self.data_keithley2182("TemperatureInternal_K"))
    	self.keithley2182_window.textTempPresent_K.display(self.data_keithley2182("TemperaturePresent_K"))

    def update_check_state_keithley2182(self,data):
    	"""Updates the state Label in the main GUI"""
    	self.keithley2182_check_state_data.update(data)
    	print("update_check")
    	if "RUNNING" in data["state"]:
    		self.keithley2182_main_state.setText("Running")
    		self.keithley2182_main_state.setStyleSheet("color:green")
    	else:
    		self.keithley2182_main_state.setText("Not Running")
    		self.keithley2182_main_state.setStyleSheet("color:red") 


    # ------- Oxford Instruments
    #---------------- IPS
    def initialize_window_ips(self):
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
        self.get_data.sig_ips120.connect(IPS211_Updater)

        self.IPS_window.labelStatusMagnet.setText("")
        self.IPS_window.labelStatusCurrent.setText("")
        self.IPS_window.labelStatusActivity.setText("")
        self.IPS_window.labelStatusLocRem.setText("")
        self.IPS_window.labelStatusSwitchHeater.setText("")
    @pyqtSlot(dict)
    def IPS211_Updater(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""

        self.data_ips120.update(data)

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

            self.IPS_window.lcdOutputField.display(self.data["IPS"]["FIELD_output"])
            self.IPS_window.lcdMeasuredMagnetCurrent.display(
                self.data["IPS"]["measured_magnet_current"]
            )
            self.IPS_window.lcdOutputCurrent.display(self.data["IPS"]["CURRENT_output"])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_set_point'])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_sweep_rate'])

            self.IPS_window.lcdLeadResistance.display(
                self.data["IPS"]["lead_resistance"]
            )

            self.IPS_window.lcdPersistentMagnetField.display(
                self.data["IPS"]["persistent_magnet_field"]
            )
            self.IPS_window.lcdTripField.display(self.data["IPS"]["trip_field"])
            self.IPS_window.lcdPersistentMagnetCurrent.display(
                self.data["IPS"]["persistent_magnet_current"]
            )
            self.IPS_window.lcdTripCurrent.display(self.data["IPS"]["trip_current"])

            self.IPS_window.labelStatusMagnet.setText(self.data["IPS"]["status_magnet"])
            self.IPS_window.labelStatusCurrent.setText(
                self.data["IPS"]["status_current"]
            )
            self.IPS_window.labelStatusActivity.setText(
                self.data["IPS"]["status_activity"]
            )
            self.IPS_window.labelStatusLocRem.setText(self.data["IPS"]["status_locrem"])
            self.IPS_window.labelStatusSwitchHeater.setText(
                self.data["IPS"]["status_switchheater"]
            )

    # ------- ------- ITC  
    def initialize_window_ITC(self):
        """initialize ITC Window"""
        self.ITC_window = Window_ui(ui_file=".\\Oxford\\itc503_Qwidget.ui")
        self.ITC_window.sig_closing.connect(
            lambda: self.action_show_ITC.setChecked(False)
        )
        #fragen ob implementieren oder python file öffenen
        #self.window_SystemsOnline.checkaction_run_ITC.clicked["bool"].connect(
        #    self.run_ITC
        #)
        self.get_data.sig_itc503.connect(self.ITC503_Updater)
        self.itc503_main_start.clicked["bool"].connect(
            lambda value: self.start_instrument(instrument='itc503')
            )
        self.action_show_ITC.triggered["bool"].connect(
            lambda value: self.show_window(self.ITC_window, value)
        )
        self.itc503_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.ITC_window)
        )
        # self.mdiArea.addSubWindow(self.ITC_window)
        self.get_active_state_itc503= self.running_thread_control(check_active(Instrument='itc503'),'check_state_itc503')
        self.get_active_state_itc503.sig_Infodata.connect(self.update_check_state_itc503)
        self.ITC_values = dict(setTemperature=4, SweepRate=2)

        #changing the temp buttons
        self.ITC_window.spinSetTemp_K.valueChanged.connect(self.fun_setTemp_valcha)
        self.ITC_window.checkRamp_Status.toggled["bool"].connect(self.fun_checkSweep_toggled)
        self.ITC_window.spinSetRamp_Kpmin.valueChanged.connect(self.fun_setRamp_valcha)
        self.ITC_window.commandSendConfTemp.clicked.connect(self.fun_sendConfTemp)

        #other buttons
       	self.ITC_window.spinsetGasOutput.valueChanged.connect(self.gettoset_GasOutput_itc503)
        self.ITC_window.send_command_spinsetGasOutput.clicked.connect(self.setGasOutput_itc503)
        self.ITC_window.checkGas_gothroughzero.toggled["bool"].connect(self.send_gas_gothroughzero)


        self.ITC_window.spinsetHeaterPercent.valueChanged.connect(self.gettoset_HeaterOutput_itc503)
        self.ITC_window.send_command_spinsetHeaterPercent.clicked.connect(self.setHeaterOutput_itc503)

        self.ITC_window.spinsetProportionalID.valueChanged.connect(
            self.gettoset_Proportional_itc503
        )
        self.ITC_window.send_command_spinsetProportionalID.clicked.connect(self.setProportional_itc503)

        self.ITC_window.spinsetPIntegrationD.valueChanged.connect(self.gettoset_Integral_itc503)
        self.ITC_window.send_command_spinsetPIntegrationD.clicked.connect(self.setIntegral_itc503)

        self.ITC_window.spinsetPIDerivative.valueChanged.connect(self.gettoset_Derivative_itc503)
        self.ITC_window.send_command_spinsetPIDerivative.clicked.connect(self.setDerivative_itc503)

        self.ITC_window.combosetHeatersens.activated["int"].connect(
            lambda value: self.commanding(ID="ITC", message=dictdump({"setHeaterSensor" : value+1}))
        )

        self.ITC_window.combosetAutocontrol.activated["int"].connect(
        	lambda value: self.commanding(ID="ITC", message=dictdump({"setAutoControl" : value}))
        	)
        self.ITC_window.checkUseAuto.toggled["bool"].connect(self.send_useauto)
        self.ITC_window.pushConfLoad.clicked.connect(self.send_confLoad_itc503)
        self.ITC_window.pushConfBrowse.clicked.connect(self.window_FileDialogOpen)
        # -------------------------------------------------------------------------------------------------------------------------
        #buttons set Interval is not implemented in Controle client
        self.ITC_window.spin_threadinterval.valueChanged.connect(self.gettoset_Interval_itc503)
        self.ITC_window.send_command_spin_threadinterval.clicked.connect(self.setInterval_itc503)
    @ExceptionHandling
    def window_FileDialogOpen(self, test):
        # print(test)
        fname, __ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose PID configuration file", "c:\\", ".conf(*.conf)"
        )
        self.ITC_window.lineConfFile.setText(fname)
        self._PIDFile = fname
        # self.setValue('general', 'logfile_location', fname)

        try:
            with open(fname) as f:
                self.ITC_window.setText(f.read())
        except OSError as e:
            self._logger.exception(e)
        except TypeError as e:
            self._logger.error(f"missing Filename! (TypeError: {e})")
    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setTemp_valcha(self, value):
        # self.threads['control_ITC'][0].gettoset_Temperature(value)
        self.ITC_values["setTemp"] = value
        self.ITC_values["end"] = value

    @pyqtSlot(float)
    @ExceptionHandling
    def fun_setRamp_valcha(self, value):
        self.ITC_values["SweepRate"] = value
        # self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot(bool)
    @ExceptionHandling
    def fun_checkSweep_toggled(self, boolean):
        self.ITC_values["isSweep"] = boolean

    @pyqtSlot()
    @ExceptionHandling
    def fun_sendConfTemp(self):
    	"""sends command to change conf Temp, sends a dict with all the necessary Information for the setTemp
    	function in the ITC controlClient"""
    	self.commanding(ID="ITC",message=dictdump({"setTemp_K" : self.ITC_values}))
    @pyqtSlot(float)
    def gettoset_GasOutput_itc503(self, value):
        """receive and store the value to set the gas_output"""
        self.set_gas_output_itc503 = value
    @pyqtSlot(float)
    def gettoset_HeaterOutput_itc503(self, value):
        """receive and store the value to set the heater_output"""
        self.set_heater_output_itc503 = value
    @pyqtSlot(bool)
    def send_gas_gothroughzero(self, boolean):
    	"""send command when gas_gothroughzero is checked"""
    	self.commanding(ID="ITC",message=dictdump({"gothroughzero" : boolean}))
    @pyqtSlot(bool)
    def send_useauto(self, boolean):
    	"""send command when checkUseAuto is checked"""
    	self.useAuto_value = boolean
    @pyqtSlot()
    def send_confLoad_itc503(self):
    	self.commanding(ID="ITC",message=dictdump({"ConfLoaD" : "dummy", "PIDFile": self._PIDFile, "useAuto": self.useAuto_value}))

    @pyqtSlot()
    @ExceptionHandling
    def setGasOutput_itc503(self):
        """set GasOutput of the instrument

        gas_output: Sets the percent of the maximum gas
                output in units of 1%.
                Min: 0. Max: 99.
        """
        self.commanding(ID="ITC", message=dictdump({"setGasOutput" : self.set_gas_output_itc503}))
    @pyqtSlot()
    @ExceptionHandling
    def setHeaterOutput_itc503(self):
        """sends command to set HeaterOutput of the instrument

        heater_output: Sets the percent of the maximum
                    heater output in units of 0.1%.
                    Min: 0. Max: 999.
        """
        self.commanding(ID="ITC", message=dictdump({"setHeaterOutput" : self.set_heater_output_itc503}))


    @pyqtSlot()
    @ExceptionHandling
    def setProportional_itc503(self):
        """sends command to set Proportional of the instrument

        prop: Proportional band, in steps of 0.0001K.
        """
        self.commanding(ID="ITC", message=dictdump({"setProportional" : self.set_prop_itc503}))

    @pyqtSlot()
    @ExceptionHandling
    def setIntegral_itc503(self):
        """sends command to set Integral of the instrument

        integral: Integral action time, in steps of 0.1 minute.
                    Ranges from 0 to 140 minutes.
        """
        self.commanding(ID="ITC", message=dictdump({"setIntegral" : self.set_integral_itc503}))

    @pyqtSlot()
    @ExceptionHandling
    def setDerivative_itc503(self):
        """sends command to set Derivative of the instrument

        derivative: Derivative action time.
        Ranges from 0 to 273 minutes.
        """
        self.commanding(ID="ITC", message=dictdump({"setDerivative" : self.set_derivative_itc503}))

    @pyqtSlot()
    @ExceptionHandling
    def setInterval_itc503(self):
        """sends command to set interval of the instrument ( not implemented in controlClient for the ITC)
        """
        self.commanding(ID="ITC", message=dictdump({"setInterval" : self.set_interval_itc503}))    
    @pyqtSlot(float)
    def gettoset_Proportional_itc503(self, value):
        """receive and store the value to set the proportional (PID)"""
        self.set_prop_itc503 = value

    @pyqtSlot(float)
    def gettoset_Integral_itc503(self, value):
        """receive and store the value to set the integral (PID)"""
        self.set_integral_itc503 = value

    @pyqtSlot(float)
    def gettoset_Derivative_itc503(self, value):
        """receive and store the value to set the derivative (PID)"""
        self.set_derivative_itc503 = value
    @pyqtSlot(float)
    def gettoset_Interval_itc503(self, value):
    	"""receive and store the value to set the interval"""
    	self.set_interval_itc503 = value

    def update_check_state_itc503(self,data):
    	"""Updates the state Label in the main GUI"""
    	self.itc503_check_state_data.update(data)
    	print("update_check")
    	if "RUNNING" in data["state"]:
    		self.itc503_main_state.setText("Running")
    		self.itc503_main_state.setStyleSheet("color:green")
    	else:
    		self.itc503_main_state.setText("Not Running")
    		self.itc503_main_state.setStyleSheet("color:red") 
        
    def ITC503_Updater(self, data):
        """
        Calculate the rate of change of Temperature on the sensors [K/min]
        Store ITC data in self.data['ITC'], update ITC_window
        """
        # with self.dataLock:
        # print('storing: ', self.time_itc[-1]-time.time(), data['Sensor_1_K'])
        # self.time_itc.append(time.time())
        self.data_itc503.update(data)

        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        for key in self.data:
            if self.data[key] is None:
                self.data[key] = np.nan
        # if not self.data['Sensor_1_K'] is None:
        self.ITC_window.lcdTemp_sens1_K.display(self.data_itc503["Sensor_1_K"])
        # if not self.data['Sensor_2_K'] is None:
        self.ITC_window.lcdTemp_sens2_K.display(self.data_itc503["Sensor_2_K"])
        # if not self.data['Sensor_3_K'] is None:
        self.ITC_window.lcdTemp_sens3_K.display(self.data_itc503["Sensor_3_K"])

        # if not self.data['set_temperature'] is None:
        self.ITC_window.lcdTemp_set.display(self.data_itc503["set_temperature"])
        # if not self.data['temperature_error'] is None:
        self.ITC_window.lcdTemp_err.display(self.data_itc503["temperature_error"])
        # if not self.data['heater_output_as_percent'] is None:
        try:
            self.ITC_window.progressHeaterPercent.setValue(
                int(self.data_itc503["heater_output_as_percent"])
            )
            # if not self.data['gas_flow_output'] is None:
            self.ITC_window.progressNeedleValve.setValue(int(self.data_itc503["gas_flow_output"]))
        except ValueError:
            pass
        # if not self.data['heater_output_as_voltage'] is None:
        self.ITC_window.lcdHeaterVoltage.display(self.data_itc503["heater_output_as_voltage"])
        # if not self.data['gas_flow_output'] is None:
        self.ITC_window.lcdNeedleValve_percent.display(self.data_itc503["gas_flow_output"])
        # if not self.data['proportional_band'] is None:
        self.ITC_window.lcdProportionalID.display(self.data_itc503["proportional_band"])
        # if not self.data['integral_action_time'] is None:
        self.ITC_window.lcdPIntegrationD.display(self.data_itc503["integral_action_time"])
        # if not self.data['derivative_action_time'] is None:
        self.ITC_window.lcdPIDerivative.display(self.data_itc503["derivative_action_time"])

        self.ITC_window.lcdTemp_sens1_calcerr_K.display(self.data_itc503["Sensor_1_calerr_K"])

        #self.ITC_window.combosetAutocontrol.setCurrentIndex(self.data["autocontrol"])

    # ------- ------- ILM
    def initialize_ilm211(self):
        self.initialize_window_ILM()
        self.ilm211_main_start.clicked.connect(
            lambda value: self.start_instrument(instrument='ilm211')
            )
        self.get_data.sig_ilm211.connect(self.ilm211_Updater)
        self.get_active_state_ilm211= self.running_thread_control(check_active(Instrument='ilm211'),'check_state_ilm211')
        self.get_active_state_ilm211.sig_Infodata.connect(self.update_check_state_ilm211)
    def initialize_window_ILM(self):
        """initialize ILM Window"""
        self.ILM_window = Window_ui(ui_file=".\\Oxford\\ILM_Qwidget.ui")
        self.ILM_window.sig_closing.connect(
            lambda: self.action_show_ILM.setChecked(False)
        )
        self.ilm211_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.ILM_window)
        )
        self.ILM_window.combosetProbingRate_chan1.activated["int"].connect(
                lambda value: self.commanding(ID="ILM",message=dictdump({"setProbingSpeed": value}))
            )
        self.ILM_window.spin_threadinterval.valueChanged.connect(
                lambda value: self.gettoset_spinThreadinterval_ilm211(value)
            )
        self.ILM_window.send_command_spin_threadinterval.clicked.connect(lambda: self.set_spinThreadinterval_ilm211())
        #self.window_SystemsOnline.checkaction_run_ILM.clicked["bool"].connect(
        #    self.run_ILM
        #)
        self.action_show_ILM.triggered["bool"].connect(self.show_ILM)
    @pyqtSlot()
    @ExceptionHandling
    def set_spinThreadinterval_ilm211(self):
    	"""sends command to send spinThreadinterval"""
    	self.commanding(ID="ILM",message=dictdump({"setInterval" : self.spinThreadinterval_ilm211}))
    @pyqtSlot()
    def gettoset_spinThreadinterval_ilm211(self,value):
    	"""saves value for spinThreadinterval"""
    	self.spinThreadinterval_ilm211 = value
    def update_check_state_ilm211(self,data):
    	"""updates the state Label for the ILM in the main GUI"""
    	self.ilm211_check_state_data.update(data)
    	print("update_check")
    	if "RUNNING" in data["state"]:
    		self.ilm211_main_state.setText("Running")
    		self.ilm211_main_state.setStyleSheet("color:green")
    	else:
    		self.ilm211_main_state.setText("Not Running")
    		self.ilm211_main_state.setStyleSheet("color:red")
    @pyqtSlot(dict)
    def ilm211_Updater(self, data):
        """
        Store Device data in self.data, update values in GUI
        """
        self.data_ilm211.update(data)

        # data['date'] = convert_time(time.time())
        # self.store_data(data=data, device='LakeShore350')

        # with self.dataLock:
        # this needs to draw from the self.data so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        # -----------------------------------------------------------------------------------------------------------
        # update the GUI
        chan1 = (
            100 if self.data_ilm211["channel_1_level"] > 100 else self.data_ilm211["channel_1_level"]
        )
        chan2 = (
            100 if self.data_ilm211["channel_2_level"] > 100 else self.data_ilm211["channel_2_level"]
        )
        self.ILM_window.progressLevelHe.setValue(chan1)
        self.ILM_window.progressLevelN2.setValue(chan2)

        #tooltip = u"ILM\nHe: {:.1f}\nN2: {:.1f}".format(chan1, chan2)
        #self.ILM_window.pyqt_sysTray.setToolTip(tooltip)

        self.ILM_window.lcdLevelHe.display(self.data_ilm211["channel_1_level"])
        self.ILM_window.lcdLevelN2.display(self.data_ilm211["channel_2_level"])
    @pyqtSlot(bool)
    def show_ILM(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.ILM_window.show()
        else:
            self.ILM_window.close()


        # ----------------------------------------------------- 
    # -------------- Lock-In SR 830  ------------------------
    def initialize_sr830(self):
        self.initialize_window_LockInsr830()
        self.sr830_main_start.clicked["bool"].connect(
            lambda value: self.start_instrument(instrument='sr830')
            )
        self.get_data.sig_sr830.connect(self.SR830_Updater)
        self.get_active_state_sr830= self.running_thread_control(check_active(Instrument='sr830'),'check_state_sr830')
        self.get_active_state_sr830.sig_Infodata.connect(self.update_check_state_sr830)


    def initialize_window_LockInsr830(self):
        """initialize PS Window"""
        self.LockIn_window_sr830 = Window_ui(ui_file=".\\LockIn\\LockIn_control.ui")
        self.LockIn_window_sr830.sig_closing.connect(
            lambda: self.action_show_SR830.setChecked(False)
        )


        self.action_show_SR830.triggered["bool"].connect(
            lambda value: self.show_window(self.LockIn_window_sr830, value)
        )
        self.sr830_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.LockIn_window_sr830)
        )
        
        self.LockIn_window_sr830.spinSetFrequency_Hz.valueChanged.connect(
            lambda value: self.gettoset_Frequency_sr830(
                value
                )
        )
        self.LockIn_window_sr830.send_command_frequency.clicked.connect(lambda: self.setFrequency_sr830()
    	)
        
        self.LockIn_window_sr830.spinSetVoltage_V.valueChanged.connect(
            lambda value: self.gettoset_Voltage_sr830(
                value
                )
        )
        self.LockIn_window_sr830.send_command_voltage.clicked.connect(lambda: self.setVoltage_sr830()
        )
        
        self.LockIn_window_sr830.spinShuntResistance_kOhm.valueChanged.connect(
            lambda value: self.getShuntResistance_sr830(
                value * 1e3
                )
        )
        self.LockIn_window_sr830.send_command_shunt_resistor.clicked.connect(lambda: self.setShuntResistance_sr830())
        self.LockIn_window_sr830.spinContactResistance_Ohm.valueChanged.connect(
            lambda value: self.getContactResistance_sr830(
                value
                )
        )
        self.LockIn_window_sr830.send_command_sample.clicked.connect(lambda: self.setContactResistance_sr830())
    def start_instrument_sr830_pressed(self,instrument=None):
        self.instrument= instrument
        p1 = subprocess.run('sc query "CryostatGui_%s" | find "RUNNING"' % self.instrument, capture_output=True, text=True, shell=True)
        a = p1.stdout

        if "RUNNING" in a:
            p2 = subprocess.run('sc stop "CryostatGui_%s"' % self.instrument) 
        else: 
            p2 = subprocess.run('sc start "CryostatGui_%s"' % self.instrument)
        if p2.returncode!=0:
            self.show_error_general("Couldn´t start or stop service CryostatGui_%s" % self.instrument)  
    def update_check_state_sr830(self,data):
        self.sr830_check_state_data.update(data)
        print("update_check")
        if "RUNNING" in data["state"]:
            self.sr830_main_state.setText("Running")

            self.sr830_main_state.setStyleSheet("color:green")
        else:
            self.sr830_main_state.setText("Not Running")
            self.sr830_main_state.setStyleSheet("color:red")  
    @pyqtSlot()
    @ExceptionHandling
    def setFrequency_sr830(self, f_Hz=None):
        """set a frequency"""
        self.commanding(ID="SR830_1",message=dictdump({"setFrequency": self.set_Frequency_Hz_sr830}))
    @pyqtSlot()
    @ExceptionHandling
    def setVoltage_sr830(self, Voltage_V=None):
        """set a voltage"""
        self.commanding(ID="SR830_1",message=dictdump({"setVoltage": self.set_Voltage_V_sr830}))
    @pyqtSlot()
    @ExceptionHandling
    def setShuntResistance_sr830(self, ShuntResitance_Ohm=None):
        """sets shunt resistance"""
        self.commanding(ID="SR830_1",message=dictdump({"setShuntResistance": self.ShuntResistance_Ohm_sr830}))
    @pyqtSlot()
    @ExceptionHandling
    def setContactResistance_sr830(self, ContactResistance_Ohm=None):
        """sets contact resistance"""
        self.commanding(ID="SR830_1",message=dictdump({"setContactResistance": self.ContactResistance_Ohm_sr830,}))
    
    @pyqtSlot()
    def gettoset_Frequency_sr830(self, value):
        """receive and store the value to set the frequency"""
        self.set_Frequency_Hz_sr830 = value

    @pyqtSlot()
    def gettoset_Voltage_sr830(self, value):
        """receive and store the value to set the voltage"""
        self.set_Voltage_V_sr830 = value

    @pyqtSlot()
    def getShuntResistance_sr830(self, value):
        """receive and store the value of the shunt resistance"""
        self.ShuntResistance_Ohm_sr830 = value

    @pyqtSlot()
    def getContactResistance_sr830(self, value):
        """receive and store the value of the samples' contact resistance"""
        self.ContactResistance_Ohm_sr830 = value
    @pyqtSlot(dict)
    def SR830_Updater(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""
        self.data_sr830.update(data)
        # data['date'] = convert_time(time.time())
        # self.data['SR830'].update(data)
        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        self.LockIn_window_sr830.lcdSetFrequency_Hz.display(self.data_sr830["Frequency_Hz"])
        self.LockIn_window_sr830.lcdSetVoltage_V.display(self.data_sr830["Voltage_V"])
        self.LockIn_window_sr830.textX_V.setText("{num:=+13.12f}".format(num=self.data_sr830["X_V"]))
        self.LockIn_window_sr830.textSampleCurrent_mA.setText(
            "{num:=+8.6f}".format(num=self.data_sr830["SampleCurrent_A"])
        )
        self.LockIn_window_sr830.textSampleResistance_Ohm.setText(
            "{num:=+8.6f}".format(num=self.data_sr830["SampleResistance_Ohm"])
        )

        self.LockIn_window_sr830.textY_V.setText("{num:=+13.12f}".format(num=self.data_sr830["Y_V"]))
        self.LockIn_window_sr830.textR_V.setText("{num:=+13.12f}".format(num=self.data_sr830["R_V"]))
        self.LockIn_window_sr830.textTheta_Deg.setText("{num:=+8.6f}".format(num=self.data_sr830["Theta_Deg"]))

#----------------sr860-----------------------
    def initialize_sr860(self):
        """initialize sr860"""
        self.initialize_window_LockIn_sr860()
        self.sr860_main_start.clicked["bool"].connect(
            lambda value: self.start_instrument(instrument='sr860')
            )
        self.get_data.sig_sr860.connect(self.SR860_Updater)
        self.get_active_state_sr860= self.running_thread_control(check_active(Instrument='sr860'),'check_state_sr860')
        self.get_active_state_sr860.sig_Infodata.connect(self.update_check_state_sr860)


    def initialize_window_LockIn_sr860(self):
        """initialize PS Window"""
        self.LockIn_window_sr860 = Window_ui(ui_file=".\\LockIn\\LockIn_control.ui")
        #self.LockIn_window_sr860.sig_closing.connect(
        #    lambda: self.action_show_SR860.setChecked(False)
        #)


        #self.action_show_SR830.triggered["bool"].connect(
        #    lambda value: self.show_window(self.LockIn_window_sr830, value)
        #)
        self.sr860_main_show.clicked["bool"].connect(
            lambda value: self.show_window_button_pressed(self.LockIn_window_sr860)
        )
        
        self.LockIn_window_sr860.spinSetFrequency_Hz.valueChanged.connect(
            lambda value: self.gettoset_Frequency_sr860(
                value
                )
        )
        self.LockIn_window_sr860.send_command_frequency.clicked.connect(lambda: self.setFrequency_sr860()
    	)
        
        self.LockIn_window_sr860.spinSetVoltage_V.valueChanged.connect(
            lambda value: self.gettoset_Voltage_sr860(
                value
                )
        )
        self.LockIn_window_sr860.send_command_voltage.clicked.connect(lambda: self.setVoltage_sr860()
        )
        
        self.LockIn_window_sr860.spinShuntResistance_kOhm.valueChanged.connect(
            lambda value: self.getShuntResistance_sr860(
                value * 1e3
                )
        )
        self.LockIn_window_sr860.send_command_shunt_resistor.clicked.connect(lambda: self.setShuntResistance_sr860())
        self.LockIn_window_sr860.spinContactResistance_Ohm.valueChanged.connect(
            lambda value: self.getContactResistance_sr860(
                value
                )
        )
        self.LockIn_window_sr860.send_command_sample.clicked.connect(lambda: self.setContactResistance_sr860())
    def update_check_state_sr860(self,data):
        self.sr860_check_state_data.update(data)
        print("update_check")
        if "RUNNING" in data["state"]:
            self.sr860_main_state.setText("Running")

            self.sr860_main_state.setStyleSheet("color:green")
        else:
            self.sr860_main_state.setText("Not Running")
            self.sr860_main_state.setStyleSheet("color:red")  
    @pyqtSlot()
    @ExceptionHandling
    def setFrequency_sr860(self, f_Hz=None):
        """set a frequency"""
        self.commanding(ID="SR860_1",message=dictdump({"setFrequency": self.set_Frequency_Hz_sr860}))
    @pyqtSlot()
    @ExceptionHandling
    def setVoltage_sr860(self, Voltage_V=None):
        """set a voltage"""
        self.commanding(ID="SR860_1",message=dictdump({"setVoltage": self.set_Voltage_V_sr860}))
    @pyqtSlot()
    def gettoset_Frequency_sr860(self, value):
        """receive and store the value to set the frequency"""
        self.set_Frequency_Hz_sr860 = value
    @pyqtSlot()
    @ExceptionHandling
    def setShuntResistance_sr860(self, ShuntResitance_Ohm=None):
        """sets shunt resistance"""
        self.commanding(ID="SR860_1",message=dictdump({"setShuntResistance": self.ShuntResistance_Ohm_sr860}))
    @pyqtSlot()
    @ExceptionHandling
    def setContactResistance_sr860(self, ContactResistance_Ohm=None):
        """sets contact resistance"""
        self.commanding(ID="SR860_1",message=dictdump({"setContactResistance": self.ContactResistance_Ohm_sr860}))
    @pyqtSlot()
    def gettoset_Voltage_sr860(self, value):
        """receive and store the value to set the voltage"""
        self.set_Voltage_V_sr860 = value

    @pyqtSlot()
    def getShuntResistance_sr860(self, value):
        """receive and store the value of the shunt resistance"""
        self.ShuntResistance_Ohm_sr860 = value

    @pyqtSlot()
    def getContactResistance_sr860(self, value):
        """receive and store the value of the samples' contact resistance"""
        self.ContactResistance_Ohm_sr860 = value
    @pyqtSlot(dict)
    def SR860_Updater(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""
        self.data_sr860.update(data)
        # data['date'] = convert_time(time.time())
        # self.data['SR830'].update(data)
        # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
        # since the command failed in the communication with the device,
        # the last value is retained

        self.LockIn_window_sr860.lcdSetFrequency_Hz.display(self.data_sr860["Frequency_Hz"])
        self.LockIn_window_sr860.lcdSetVoltage_V.display(self.data_sr860["Voltage_V"])
        self.LockIn_window_sr860.textX_V.setText("{num:=+13.12f}".format(num=self.data_sr860["X_V"]))

        self.LockIn_window_sr860.textSampleCurrent_mA.setText(
            "{num:=+8.6f}".format(num=self.data_sr860["SampleCurrent_A"])
        )
        self.LockIn_window_sr860.textSampleResistance_Ohm.setText(
            "{num:=+8.6f}".format(num=self.data_sr860["SampleResistance_Ohm"])
        )

        self.LockIn_window_sr860.textY_V.setText("{num:=+13.12f}".format(num=self.data_sr860["Y_V"]))
        self.LockIn_window_sr860.textR_V.setText("{num:=+13.12f}".format(num=self.data_sr860["R_V"]))
        self.LockIn_window_sr860.textTheta_Deg.setText("{num:=+8.6f}".format(num=self.data_sr860["Theta_Deg"]))
        #----------Window_errors--------------
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
            "{} - {}".format(dt3.datetime.now().strftime("%Y-%m-%d  %H:%M:%S.%f"), text)
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
    form = mainWindow(app=app, ui_file=".\\configurations\\test.ui", identity="MainWindow_1", Lockin=None, prometheus_port=8006)
    form.show()
    print("date: ", dt3.datetime.now(), "\nstartup time: ", time.time() - a)

    sys.exit(app.exec_())