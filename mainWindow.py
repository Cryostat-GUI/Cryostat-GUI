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


Classes:
    mainWindow:
        The main GUI class for the PyQt application

    Author(s):
        bklebel (Benjamin Klebel)
        adtera
        Acronis
----------------------------------------------------------------------------------------
"""


from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
# from PyQt5.QtWidgets import QtAlignRight
from PyQt5.uic import loadUi

import sys
import time
import datetime
from threading import Lock
import numpy as np
from copy import deepcopy

from Oxford.ITC_control import ITC_Updater
from Oxford.ILM_control import ILM_Updater
from Oxford.IPS_control import IPS_Updater
from LakeShore.LakeShore350_Control import LakeShore350_Updater
from Keithley.Keithley2182_Control import Keithley2182_Updater
from Keithley.Keithley6220_Control import Keithley6220_Updater

from pyvisa.errors import VisaIOError

from logger import main_Logger, live_Logger
from logger import Logger_configuration
from util import Window_ui


ITC_Instrumentadress = 'ASRL6::INSTR'
ILM_Instrumentadress = 'ASRL5::INSTR'
IPS_Instrumentadress = 'ASRL4::INSTR'
LakeShore_InstrumentAddress = 'GPIB0::12::INSTR'
Keithley2181_1_InstrumentAddress = 'GPIB0::2::INSTR' 
Keithley2181_2_InstrumentAddress = 'GPIB0::3::INSTR'
Keithley2181_3_InstrumentAddress = 'GPIB0::4::INSTR'
Keithley6220_1_InstrumentAddress = 'GPIB0::5::INSTR'
Keithley6220_2_InstrumentAddress = 'GPIB0::6::INSTR'


def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


class mainWindow(QtWidgets.QMainWindow): #, mainWindow_ui.Ui_Cryostat_Main):
    """This is the main GUI Window, where other windows will be spawned from"""

    sig_arbitrary = pyqtSignal()
    sig_logging = pyqtSignal(dict)
    sig_logging_newconf = pyqtSignal(dict)

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)
        self.threads = dict()
        self.data = dict()
        self.logging_bools = dict()

        self.logging_running_ITC = False
        self.logging_running_logger = False

        self.dataLock = Lock()
        self.app = app


        QTimer.singleShot(0, self.initialize_all_windows)


    def closeEvent(self, event):
        super(mainWindow, self).closeEvent(event)
        self.app.quit()


    def initialize_all_windows(self):
        self.initialize_window_ITC()
        self.initialize_window_ILM()
        self.initialize_window_IPS()
        self.initialize_window_Log_conf()
        self.initialize_window_LakeShore350()
        self.initialize_window_Keithley()
        self.initialize_window_Errors()




    def running_thread(self, worker, dataname, threadname, info=None, **kwargs):
        """Set up a new Thread, and insert the worker class, which runs in the new thread

            Args:
                worker - the class (as a class instance) which should run inside
                dataname - the name for which a dict entry should be made in the self.data dict,
                        in case the Thread is passing data (e.g. sensors, instrument status...)
                threadname - the name as which the thread will be listed in self.threads,
                        to be used for e.g. signals
                        listing the thread in self.threads is also important to protect it
                        from garbage collection!

            Returns:
                the worker class instance, useful for connecting signals directly
        """

        thread = QThread()
        self.threads[threadname] = (worker, thread)
        worker.moveToThread(thread)

        if dataname in self.data or dataname == None:
            pass
        else:
            with self.dataLock:
                self.data[dataname] = dict()

        thread.started.connect(worker.work)
        thread.start()
        return worker

    def stopping_thread(self, threadname):
        """Stop the thread specified by the argument threadname, delete its entry in self.threads"""

        # self.threads[threadname][0].stop()
        self.threads[threadname][1].quit()
        self.threads[threadname][1].wait()
        del self.threads[threadname]

    def show_error_textBrowser(self, text):
        """ append error to Error window"""
        self.Errors_window.textErrors.append('{} - {}'.format(convert_time(time.time()),text))

    # ------- Oxford Instruments
    # ------- ------- ITC
    def initialize_window_ITC(self):
        """initialize ITC Window"""
        self.ITC_window = Window_ui(ui_file='.\\Oxford\\ITC_control.ui')
        self.ITC_window.sig_closing.connect(lambda: self.action_show_ITC.setChecked(False))

        self.action_run_ITC.triggered['bool'].connect(self.run_ITC)
        self.action_show_ITC.triggered['bool'].connect(self.show_ITC)
        # self.mdiArea.addSubWindow(self.ITC_window)

    @pyqtSlot(bool)
    def run_ITC(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""

        if boolean:
            try:
                # self.ITC = itc503('COM6')
                # getInfodata = cls_itc(self.ITC)
                getInfodata = self.running_thread(ITC_Updater(ITC_Instrumentadress), 'ITC', 'control_ITC')

                getInfodata.sig_Infodata.connect(self.store_data_itc)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_textBrowser)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata.sig_visatimeout.connect(lambda: self.show_error_textBrowser('ITC: timeout'))

                self.data['ITC'] =  dict(set_temperature = 0,
                                         Sensor_1_K =0,
                                         Sensor_2_K =0,
                                         Sensor_3_K =0,
                                         temperature_error =0,
                                         heater_output_as_percent =0,
                                         heater_output_as_voltage =0,
                                         gas_flow_output =0,
                                         proportional_band =0,
                                         integral_action_time =0,
                                         derivative_action_time = 0)
                integration_length = 7
                self.ITC_Kpmin = dict(newtime = [time.time()]*integration_length,
                                                Sensor_1_K = [0]*integration_length,
                                                Sensor_2_K = [0]*integration_length,
                                                Sensor_3_K = [0]*integration_length,
                                                Sensor_4_K = [0]*integration_length)

                # setting ITC values by GUI ITC window
                self.ITC_window.spinsetTemp.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Temperature(value))
                self.ITC_window.spinsetTemp.editingFinished.connect(lambda: self.threads['control_ITC'][0].setTemperature())

                self.ITC_window.spinsetGasOutput.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_GasOutput(value))
                self.ITC_window.spinsetGasOutput.editingFinished.connect(lambda : self.threads['control_ITC'][0].setGasOutput())

                self.ITC_window.spinsetHeaterPercent.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_HeaterOutput(value))
                self.ITC_window.spinsetHeaterPercent.editingFinished.connect(lambda : self.threads['control_ITC'][0].setHeaterOutput())

                self.ITC_window.spinsetProportionalID.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Proportional(value))
                self.ITC_window.spinsetProportionalID.editingFinished.connect(lambda : self.threads['control_ITC'][0].setProportional())

                self.ITC_window.spinsetPIntegrationD.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Integral(value))
                self.ITC_window.spinsetPIntegrationD.editingFinished.connect(lambda : self.threads['control_ITC'][0].setIntegral())

                self.ITC_window.spinsetPIDerivative.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Derivative(value))
                self.ITC_window.spinsetPIDerivative.editingFinished.connect(lambda : self.threads['control_ITC'][0].setDerivative())

                self.ITC_window.combosetHeatersens.activated['int'].connect(lambda value: self.threads['control_ITC'][0].setHeaterSensor(value + 1))

                self.ITC_window.combosetAutocontrol.activated['int'].connect(lambda value: self.threads['control_ITC'][0].setAutoControl(value))

                self.ITC_window.spin_threadinterval.valueChanged.connect(lambda value: self.threads['control_ITC'][0].setInterval(value))

                # thread.started.connect(getInfodata.work)
                # thread.start()
                self.action_run_ITC.setChecked(True)
                self.logging_running_ITC = True
            except VisaIOError as e:
                self.action_run_ITC.setChecked(False)
                self.show_error_textBrowser(e)
                # print(e) # TODO: open window displaying the error message

        else:
            # possibly implement putting the instrument back to local operation
            self.ITC_window.spinsetTemp.valueChanged.disconnect()
            self.ITC_window.spinsetTemp.editingFinished.disconnect()
            self.ITC_window.spinsetGasOutput.valueChanged.disconnect()
            self.ITC_window.spinsetGasOutput.editingFinished.disconnect()
            self.ITC_window.spinsetHeaterPercent.valueChanged.disconnect()
            self.ITC_window.spinsetHeaterPercent.editingFinished.disconnect()
            self.ITC_window.spinsetProportionalID.valueChanged.disconnect()
            self.ITC_window.spinsetProportionalID.editingFinished.disconnect()
            self.ITC_window.spinsetPIntegrationD.valueChanged.disconnect()
            self.ITC_window.spinsetPIntegrationD.editingFinished.disconnect()
            self.ITC_window.spinsetPIDerivative.valueChanged.disconnect()
            self.ITC_window.spinsetPIDerivative.editingFinished.disconnect()
            self.ITC_window.combosetHeatersens.activated['int'].disconnect()
            self.ITC_window.combosetAutocontrol.activated['int'].disconnect()
            self.ITC_window.spin_threadinterval.valueChanged.disconnect()

            self.stopping_thread('control_ITC')
            self.action_run_ITC.setChecked(False)
            self.logging_running_ITC = False

    @pyqtSlot(bool)
    def show_ITC(self, boolean):
        """display/close the ITC data & control window"""
        if boolean:
            self.ITC_window.show()
        else:
            self.ITC_window.close()

    @pyqtSlot(dict)
    def store_data_itc(self, data):
        """
            Calculate the rate of change of Temperature on the sensors [K/min]
            Store ITC data in self.data['ITC'], update ITC_window
        """

        timediffs = [(entry-self.ITC_Kpmin['newtime'][i+1])/60 for i, entry in enumerate(self.ITC_Kpmin['newtime'][:-1])]# -self.ITC_Kpmin['newtime'])/60
        tempdiffs = dict(Sensor_1_Kpmin=[entry-self.ITC_Kpmin['Sensor_1_K'][i+1] for i, entry in enumerate(self.ITC_Kpmin['Sensor_1_K'][:-1])],
                            Sensor_2_Kpmin=[entry-self.ITC_Kpmin['Sensor_2_K'][i+1] for i, entry in enumerate(self.ITC_Kpmin['Sensor_2_K'][:-1])],
                            Sensor_3_Kpmin=[entry-self.ITC_Kpmin['Sensor_3_K'][i+1] for i, entry in enumerate(self.ITC_Kpmin['Sensor_3_K'][:-1])])
        #integrating over the lists, to get an integrated rate of Kelvin/min
        integrated_diff = dict(Sensor_1_Kpmin=np.mean(np.array(tempdiffs['Sensor_1_Kpmin'])/np.array(timediffs)),
                                Sensor_2_Kpmin=np.mean(np.array(tempdiffs['Sensor_2_Kpmin'])/np.array(timediffs)),
                                Sensor_3_Kpmin=np.mean(np.array(tempdiffs['Sensor_3_Kpmin'])/np.array(timediffs)))


        if not integrated_diff['Sensor_1_Kpmin'] == 0:
            self.ITC_window.lcdTemp_sens1_Kpmin.display(integrated_diff['Sensor_1_Kpmin'])
        if not integrated_diff['Sensor_2_Kpmin'] == 0:
            self.ITC_window.lcdTemp_sens2_Kpmin.display(integrated_diff['Sensor_2_Kpmin'])
        if not integrated_diff['Sensor_3_Kpmin'] == 0:
            self.ITC_window.lcdTemp_sens3_Kpmin.display(integrated_diff['Sensor_3_Kpmin'])


        # advancing entries to the next slot
        for i, entry in enumerate(self.ITC_Kpmin['newtime'][:-1]):
            self.ITC_Kpmin['newtime'][i+1] = entry
            self.ITC_Kpmin['Sensor_1_K'][i+1] = self.ITC_Kpmin['Sensor_1_K'][i]
            self.ITC_Kpmin['Sensor_2_K'][i+1] = self.ITC_Kpmin['Sensor_2_K'][i]
            self.ITC_Kpmin['Sensor_3_K'][i+1] = self.ITC_Kpmin['Sensor_3_K'][i]

        # including the new values
        self.ITC_Kpmin['newtime'][0] = time.time()
        self.ITC_Kpmin['Sensor_1_K'][0] = deepcopy(data['Sensor_1_K'])
        self.ITC_Kpmin['Sensor_2_K'][0] = deepcopy(data['Sensor_2_K'])
        self.ITC_Kpmin['Sensor_3_K'][0] = deepcopy(data['Sensor_3_K'])
        data.update(dict(Sensor_1_Kpmin=integrated_diff['Sensor_1_Kpmin'],
                            Sensor_2_Kpmin=integrated_diff['Sensor_2_Kpmin'],
                            Sensor_3_Kpmin=integrated_diff['Sensor_3_Kpmin']))


        data['date'] = convert_time(time.time())
        with self.dataLock:
            self.data['ITC'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device, the last value is retained
            self.ITC_window.lcdTemp_sens1_K.display(self.data['ITC']['Sensor_1_K'])
            self.ITC_window.lcdTemp_sens2_K.display(self.data['ITC']['Sensor_2_K'])
            self.ITC_window.lcdTemp_sens3_K.display(self.data['ITC']['Sensor_3_K'])

            self.ITC_window.lcdTemp_set.display(self.data['ITC']['set_temperature'])
            self.ITC_window.lcdTemp_err.display(self.data['ITC']['temperature_error'])
            self.ITC_window.progressHeaterPercent.setValue(self.data['ITC']['heater_output_as_percent'])
            self.ITC_window.lcdHeaterVoltage.display(self.data['ITC']['heater_output_as_voltage'])
            self.ITC_window.progressNeedleValve.setValue(self.data['ITC']['gas_flow_output'])
            self.ITC_window.lcdNeedleValve_percent.display(self.data['ITC']['gas_flow_output'])
            self.ITC_window.lcdProportionalID.display(self.data['ITC']['proportional_band'])
            self.ITC_window.lcdPIntegrationD.display(self.data['ITC']['integral_action_time'])
            self.ITC_window.lcdPIDerivative.display(self.data['ITC']['derivative_action_time'])


    # ------- ------- ILM
    def initialize_window_ILM(self):
        """initialize ILM Window"""
        self.ILM_window = Window_ui(ui_file='.\\Oxford\\ILM_control.ui')
        self.ILM_window.sig_closing.connect(lambda: self.action_show_ILM.setChecked(False))

        self.action_run_ILM.triggered['bool'].connect(self.run_ILM)
        self.action_show_ILM.triggered['bool'].connect(self.show_ILM)

    @pyqtSlot(bool)
    def run_ILM(self, boolean):
        """start/stop the Level Meter thread"""


        if boolean:
            try:
                getInfodata = self.running_thread(ILM_Updater(InstrumentAddress=ILM_Instrumentadress),'ILM', 'control_ILM')

                getInfodata.sig_Infodata.connect(self.store_data_ilm)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_textBrowser)
                getInfodata.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata.sig_visatimeout.connect(lambda: self.show_error_textBrowser('ILM: timeout'))

                self.ILM_window.combosetProbingRate_chan1.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 1))
                # self.ILM_window.combosetProbingRate_chan2.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 2))

                self.ILM_window.spin_threadinterval.valueChanged.connect(lambda value: self.threads['control_ILM'][0].setInterval(value))

                self.action_run_ILM.setChecked(True)

            except VisaIOError as e:
                self.action_run_ILM.setChecked(False)
                self.show_error_textBrowser(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.action_run_ILM.setChecked(False)
            self.stopping_thread('control_ILM')

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
        with self.dataLock:
            data['date'] = convert_time(time.time())
            self.data['ILM'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device, the last value is retained
            chan1 = 100 if self.data['ILM']['channel_1_level'] > 100 else self.data['ILM']['channel_1_level']
            chan2 = 100 if self.data['ILM']['channel_2_level'] > 100 else self.data['ILM']['channel_2_level']
            self.ILM_window.progressLevelHe.setValue(chan1)
            self.ILM_window.progressLevelN2.setValue(chan2)

            self.ILM_window.lcdLevelHe.display(self.data['ILM']['channel_1_level'])
            self.ILM_window.lcdLevelN2.display(self.data['ILM']['channel_2_level'])

            self.MainDock_HeLevel.setValue(chan1)
            self.MainDock_N2Level.setValue(chan2)
            # print(self.data['ILM']['channel_1_level'], self.data['ILM']['channel_2_level'])

    # ------- ------- IPS
    def initialize_window_IPS(self):
        """initialize PS Window"""
        self.IPS_window = Window_ui(ui_file='.\\Oxford\\IPS_control.ui')
        self.IPS_window.sig_closing.connect(lambda: self.action_show_IPS.setChecked(False))

        self.action_run_IPS.triggered['bool'].connect(self.run_IPS)
        self.action_show_IPS.triggered['bool'].connect(self.show_IPS)

        self.IPS_window.labelStatusMagnet.setText('')
        self.IPS_window.labelStatusCurrent.setText('')
        self.IPS_window.labelStatusActivity.setText('')
        self.IPS_window.labelStatusLocRem.setText('')
        self.IPS_window.labelStatusSwitchHeater.setText('')

    @pyqtSlot(bool)
    def run_IPS(self, boolean):
        """start/stop the Powersupply thread"""

        if boolean:
            try:
                getInfodata = self.running_thread(IPS_Updater(InstrumentAddress=IPS_Instrumentadress),'IPS', 'control_IPS')

                getInfodata.sig_Infodata.connect(self.store_data_ips)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_textBrowser)
                getInfodata.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata.sig_visatimeout.connect(lambda: self.show_error_textBrowser('IPS: timeout'))

                self.IPS_window.comboSetActivity.activated['int'].connect(lambda value: self.threads['control_IPS'][0].setActivity(value))
                self.IPS_window.comboSetSwitchHeater.activated['int'].connect(lambda value: self.threads['control_IPS'][0].setSwitchHeater(value))

                self.IPS_window.spinSetFieldSetPoint.valueChanged.connect(lambda value: self.threads['control_IPS'][0].gettoset_FieldSetPoint(value))
                self.IPS_window.spinSetFieldSetPoint.editingFinished.connect(lambda: self.threads['control_IPS'][0].setFieldSetPoint())

                self.IPS_window.spinSetFieldSweepRate.valueChanged.connect(lambda value: self.threads['control_IPS'][0].gettoset_FieldSweepRate(value))
                self.IPS_window.spinSetFieldSweepRate.editingFinished.connect(lambda: self.threads['control_IPS'][0].setFieldSweepRate())

                self.IPS_window.spin_threadinterval.valueChanged.connect(lambda value: self.threads['control_IPS'][0].setInterval(value))

                self.action_run_IPS.setChecked(True)

            except VisaIOError as e:
                self.action_run_IPS.setChecked(False)
                self.show_error_textBrowser(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.action_run_IPS.setChecked(False)
            self.stopping_thread('control_IPS')

    @pyqtSlot(bool)
    def show_IPS(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.IPS_window.show()
        else:
            self.IPS_window.close()

    @pyqtSlot(dict)
    def store_data_ips(self, data):
        """Store PS data in self.data['ILM'], update PS_window"""
        with self.dataLock:
            data['date'] = convert_time(time.time())
            self.data['IPS'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device, the last value is retained
            self.IPS_window.lcdFieldSetPoint.display(self.data['IPS']['FIELD_set_point'])
            self.IPS_window.lcdFieldSweepRate.display(self.data['IPS']['FIELD_sweep_rate'])

            self.IPS_window.lcdOutputField.display(self.data['IPS']['FIELD_output'])
            self.IPS_window.lcdMeasuredMagnetCurrent.display(self.data['IPS']['measured_magnet_current'])
            self.IPS_window.lcdOutputCurrent.display(self.data['IPS']['CURRENT_output'])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_set_point'])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_sweep_rate'])

            self.IPS_window.lcdLeadResistance.display(self.data['IPS']['lead_resistance'])

            self.IPS_window.lcdPersistentMagnetField.display(self.data['IPS']['persistent_magnet_field'])
            self.IPS_window.lcdTripField.display(self.data['IPS']['trip_field'])
            self.IPS_window.lcdPersistentMagnetCurrent.display(self.data['IPS']['persistent_magnet_current'])
            self.IPS_window.lcdTripCurrent.display(self.data['IPS']['trip_current'])

            self.IPS_window.labelStatusMagnet.setText(self.data['IPS']['status_magnet'])
            self.IPS_window.labelStatusCurrent.setText(self.data['IPS']['status_current'])
            self.IPS_window.labelStatusActivity.setText(self.data['IPS']['status_activity'])
            self.IPS_window.labelStatusLocRem.setText(self.data['IPS']['status_locrem'])
            self.IPS_window.labelStatusSwitchHeater.setText(self.data['IPS']['status_switchheater'])


    # ------- LakeShore 350 -------
    def initialize_window_LakeShore350(self):
        """initialize LakeShore Window"""
        self.LakeShore350_window = Window_ui(ui_file='.\\LakeShore\\LakeShore350_control.ui')
        self.LakeShore350_window.sig_closing.connect(lambda: self.action_show_LakeShore350.setChecked(False))

        # self.LakeShore350_window.textSensor1_Kpmin.setAlignment(QtAlignRight)

        self.action_run_LakeShore350.triggered['bool'].connect(self.run_LakeShore350)
        self.action_show_LakeShore350.triggered['bool'].connect(self.show_LakeShore350)
        self.LakeShore350_Kpmin = None

    def func_LakeShore350_setKpminLength(self, length):
        """set the number of measurements the calculation should be conducted over"""
        if not self.LakeShore350_Kpmin:
            self.LakeShore350_Kpmin = dict( newtime=[time.time()]*length,
                                            Sensors=dict(
                                                Sensor_1_K=[0]*length,
                                                Sensor_2_K=[0]*length,
                                                Sensor_3_K=[0]*length,
                                                Sensor_4_K=[0]*length),
                                            length=length)
        elif self.LakeShore350_Kpmin['length'] > length:
            self.LakeShore350_Kpmin['newtime'] = self.LakeShore350_Kpmin['newtime'][:length]
            for sensor in self.LakeShore350_Kpmin['Sensors']:
                sensor = sensor[:length]
            self.LakeShore350_Kpmin['length'] = length
        elif self.LakeShore350_Kpmin['length'] < length:
            self.LakeShore350_Kpmin['newtime'] += [time.time()]*(length-self.LakeShore350_Kpmin['length'])
            for sensor in self.LakeShore350_Kpmin['Sensors']:
                sensor += [0]*(length-self.LakeShore350_Kpmin['length'])
            self.LakeShore350_Kpmin['length'] = length


    @pyqtSlot(bool)
    def run_LakeShore350(self, boolean):
        """start/stop the LakeShore350 thread"""

        if boolean:
            try:
                getInfodata = self.running_thread(LakeShore350_Updater(InstrumentAddress=LakeShore_InstrumentAddress),'LakeShore350', 'control_LakeShore350')

                getInfodata.sig_Infodata.connect(self.store_data_LakeShore350)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_textBrowser)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata.sig_visatimeout.connect(lambda: self.show_error_textBrowser('LakeShore350: timeout'))

                self.func_LakeShore350_setKpminLength(5)

                # setting LakeShore values by GUI LakeShore window
                self.LakeShore350_window.spinSetTemp_K.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Temp_K(value))
                self.LakeShore350_window.spinSetTemp_K.editingFinished.connect(lambda: self.threads['control_LakeShore350'][0].setTemp_K())

                self.LakeShore350_window.spinSetRampRate_Kpmin.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Ramp_Rate_K(value))
                self.LakeShore350_window.spinSetRampRate_Kpmin.editingFinished.connect(lambda: self.threads['control_LakeShore350'][0].setRamp_Rate_K())

                # allows to choose from different inputs to connect to output 1 control loop. default is input 1.

                self.LakeShore350_window.comboSetInput_Sensor.activated['int'].connect(lambda value: self.threads['control_LakeShore350'][0].setInput(value + 1))
                # self.LakeShore350_window.spinSetInput_Sensor.editingFinished.(lambda value: self.threads['control_LakeShore350'][0].setInput())


                """ NEW GUI controls P, I and D values for Control Loop PID Values Command
                # """
                # self.LakeShore350_window.spinSetLoopP_Param.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_LoopP_Param(value))
                # self.LakeShore350_window.spinSetLoopP_Param.Finished.connect(lambda: self.threads['control_LakeShore350'][0].setLoopP_Param())

                # self.LakeShore350_window.spinSetLoopI_Param.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_LoopI_Param(value))
                # self.LakeShore350_window.spinSetLoopI_Param.Finished.connect(lambda: self.threads['control_LakeShore350'][0].setLoopI_Param())

                # self.LakeShore350_window.spinSetLoopD_Param.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_LoopD_Param(value))
                # self.LakeShore350_window.spinSetLoopD_Param.Finished.connect(lambda: self.threads['control_LakeShore350'][0].setLoopD_Param())

                """ NEW GUI Heater Range and Ouput Zone
                """

                # self.LakeShore350_window.comboSetHeater_Range.activated['int'].connect(lambda value: self.threads['control_LakeShore350'][0].setHeater_Range(value))

                #self.LakeShore350_window.spinSetHeater_Range.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Heater_Range(value))
                #self.LakeShore350_window.spinSetHeater_Range.Finished.connect(lambda: self.threads['control_LakeShore350'][0].setHeater_Range())

                # self.LakeShore350_window.spinSetUpper_Bound.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Upper_Bound(value))
                # self.LakeShore350_window.spinSetZoneP_Param.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_ZoneP_Param(value))
                # self.LakeShore350_window.spinSetZoneI_Param.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_ZoneI_Param(value))
                # self.LakeShore350_window.spinSetZoneD_Param.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_ZoneD_Param(value))
                # self.LakeShore350_window.spinSetZoneMout.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_ZoneMout(value))
                # self.LakeShore350_window.spinSetZone_Range.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Zone_Range(value))
                # self.LakeShore350_window.spinSetZone_Rate.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Zone_Rate(value))


                self.LakeShore350_window.spin_threadinterval.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].setInterval(value))


                self.action_run_LakeShore350.setChecked(True)

            except VisaIOError as e:
                self.action_run_LakeShore350.setChecked(False)
                self.show_error_textBrowser('running: {}'.format(e))
        else:
            self.action_run_LakeShore350.setChecked(False)
            self.stopping_thread('control_LakeShore350')

            self.LakeShore350_window.spinSetTemp_K.valueChanged.disconnect()
            self.LakeShore350_window.spinSetTemp_K.editingFinished.disconnect()
            self.LakeShore350_window.spinSetRampRate_Kpmin.valueChanged.disconnect()
            self.LakeShore350_window.spinSetRampRate_Kpmin.editingFinished.disconnect()
            self.LakeShore350_window.comboSetInput_Sensor.activated['int'].disconnect()

    @pyqtSlot(bool)
    def show_LakeShore350(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.LakeShore350_window.show()
        else:
            self.LakeShore350_window.close()

    def calculate_Kpmin(self, data):
        """calculate the rate of change of Temperature"""
        coeffs = []
        for sensordata in self.LakeShore350_Kpmin['Sensors'].values():
            coeffs.append(np.polynomial.polynomial.polyfit(self.LakeShore350_Kpmin['newtime'], sensordata, deg=1))

        integrated_diff = dict(Sensor_1_Kpmin=coeffs[0][1]*60,
                                Sensor_2_Kpmin=coeffs[1][1]*60,
                                Sensor_3_Kpmin=coeffs[2][1]*60,
                                Sensor_4_Kpmin=coeffs[3][1]*60)

        data.update(integrated_diff)


        # advancing entries to the next slot
        for i, entry in enumerate(self.LakeShore350_Kpmin['newtime'][:-1]):
            self.LakeShore350_Kpmin['newtime'][i+1] = entry
            self.LakeShore350_Kpmin['newtime'][0] = time.time()
            for key in self.LakeShore350_Kpmin['Sensors'].keys(): 
                self.LakeShore350_Kpmin['Sensors'][key][i+1] = self.LakeShore350_Kpmin['Sensors'][key][i]
                self.LakeShore350_Kpmin['Sensors'][key][0] = deepcopy(data[key])


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

        return integrated_diff, data

    @pyqtSlot(dict)
    def store_data_LakeShore350(self, data):
        """
            Calculate the rate of change of Temperature on the sensors [K/min]
            Store LakeShore350 data in self.data['LakeShore350'], update LakeShore350_window
        """

        coeffs, data = self.calculate_Kpmin(data)

        for GUI_element, co in zip([self.LakeShore350_window.textSensor1_Kpmin,
                                    self.LakeShore350_window.textSensor2_Kpmin,
                                    self.LakeShore350_window.textSensor3_Kpmin,
                                    self.LakeShore350_window.textSensor4_Kpmin],
                                   coeffs.values()):
            if not co == 0:
                GUI_element.setText('{num:=+10.4f}'.format(num=co))

        data['date'] = convert_time(time.time())
        with self.dataLock:
            self.data['LakeShore350'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device, the last value is retained

            self.LakeShore350_window.progressHeaterOutput_percentage.setValue(self.data['LakeShore350']['Heater_Output_percentage'])
            self.LakeShore350_window.lcdHeaterOutput_mW.display(self.data['LakeShore350']['Heater_Output_mW'])
            self.LakeShore350_window.lcdSetTemp_K.display(self.data['LakeShore350']['Temp_K'])
            # self.LakeShore350_window.lcdRampeRate_Status.display(self.data['LakeShore350']['RampRate_Status'])
            self.LakeShore350_window.lcdSetRampRate_Kpmin.display(self.data['LakeShore350']['Ramp_Rate'])

            self.LakeShore350_window.comboSetInput_Sensor.setCurrentIndex(int(self.data['LakeShore350']['Input_Sensor'])-1)
            self.LakeShore350_window.lcdSensor1_K.display(self.data['LakeShore350']['Sensor_1_K'])
            self.LakeShore350_window.lcdSensor2_K.display(self.data['LakeShore350']['Sensor_2_K'])
            self.LakeShore350_window.lcdSensor3_K.display(self.data['LakeShore350']['Sensor_3_K'])
            self.LakeShore350_window.lcdSensor4_K.display(self.data['LakeShore350']['Sensor_4_K'])

            """NEW GUI to display P,I and D Parameters
            """
            # self.LakeShore350_window.lcdLoopP_Param.display(self.data['LakeShore350']['Loop_P_Param'])
            # self.LakeShore350_window.lcdLoopI_Param.display(self.data['LakeShore350']['Loop_I_Param'])
            # self.LakeShore350_window.lcdLoopD_Param.display(self.data['LakeShore350']['Loop_D_Param'])

            # self.LakeShore350_window.lcdHeater_Range.display(self.date['LakeShore350']['Heater_Range'])



   # ------- Keithley 2182 + Keithley 6220 -------
    def initialize_window_Keithley(self):
        """initialize Keithley Window"""
        self.Keithley_window = Window_ui(ui_file='.\\Keithley\\Keithley_control.ui')
        self.Keithley_window.sig_closing.connect(lambda: self.action_show_Keithley.setChecked(False))

        self.action_run_Keithley.triggered['bool'].connect(self.run_Keithley)
        self.action_show_Keithley.triggered['bool'].connect(self.show_Keithley)


    @pyqtSlot(bool)
    def run_Keithley(self, boolean):
        """start/stop the Keithley thread"""

        if boolean:
            try:
                # setting first Keithley6220 
                getInfodata1 = self.running_thread(Keithley6220_Updater(InstrumentAddress=Keithley6220_1_InstrumentAddress),'Keithley6220_1', 'control_Keithley6220_1')

                getInfodata1.sig_Infodata.connect(self.store_data_Keithley)
                getInfodata1.sig_visaerror.connect(self.show_error_textBrowser)
                getInfodata1.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata1.sig_visatimeout.connect(lambda: self.show_error_textBrowser('Keithley6220_1: timeout'))

                # setting second Keithley6220 
                getInfodata2 = self.running_thread(Keithley6220_Updater(InstrumentAddress=Keithley6220_2_InstrumentAddress),'Keithley6220_2', 'control_Keithley6220_2')

                getInfodata2.sig_Infodata.connect(self.store_data_Keithley)
                getInfodata2.sig_visaerror.connect(self.show_error_textBrowser)
                getInfodata2.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata2.sig_visatimeout.connect(lambda: self.show_error_textBrowser('Keithley6220_2: timeout'))

                ## setting first Keithley2182 
                #getInfodata3 = self.running_thread(Keithley2182_Updater(InstrumentAddress=Keithley2182_1_InstrumentAddress),'Keithley2182_1', 'control_Keithley2182_1')
#
                #getInfodata3.sig_Infodata.connect(self.store_data_Keithley)
                #getInfodata3.sig_visaerror.connect(self.show_error_textBrowser)
                #getInfodata3.sig_assertion.connect(self.show_error_textBrowser)
                #getInfodata3.sig_visatimeout.connect(lambda: self.show_error_textBrowser('Keithley2182_1: timeout'))
#
                ## setting second Keithley2182 
                #getInfodata4 = self.running_thread(Keithley2182_Updater(InstrumentAddress=Keithley2182_2_InstrumentAddress),'Keithley2182_2', 'control_Keithley2182_2')
#
                #getInfodata4.sig_Infodata.connect(self.store_data_Keithley)
                #getInfodata4.sig_visaerror.connect(self.show_error_textBrowser)
                #getInfodata4.sig_assertion.connect(self.show_error_textBrowser)
                #getInfodata4.sig_visatimeout.connect(lambda: self.show_error_textBrowser('Keithley2182_2: timeout'))
#
                ## setting third Keithley2182 
                #getInfodata5 = self.running_thread(Keithley2182_Updater(InstrumentAddress=Keithley2182_3_InstrumentAddress),'Keithley2182_3', 'control_Keithley2182_3')
#
                #getInfodata5.sig_Infodata.connect(self.store_data_Keithley)
                #getInfodata5.sig_visaerror.connect(self.show_error_textBrowser)
                #getInfodata5.sig_assertion.connect(self.show_error_textBrowser)
                #getInfodata5.sig_visatimeout.connect(lambda: self.show_error_textBrowser('Keithley2182_3: timeout'))


                # setting Keithley values by GUI LakeShore window
                self.Keithley_window.spinSetCurrent1_mA.valueChanged.connect(lambda value: self.threads['control_Keithley6220_1'][0].gettoset_Current_A(value))
                self.Keithley_window.spinSetCurrent1_mA.editingFinished.connect(lambda: self.threads['control_Keithley6220_1'][0].setCurrent_A())

                self.Keithley_window.pushButton1.clicked.connect(lambda: self.threads['control_Keithley6220_1'][0].disable())

                self.Keithley_window.spinSetCurrent2_mA.valueChanged.connect(lambda value: self.threads['control_Keithley6220_2'][0].gettoset_Current_A(value))
                self.Keithley_window.spinSetCurrent2_mA.editingFinished.connect(lambda: self.threads['control_Keithley6220_2'][0].setCurrent_A())                

                self.Keithley_window.pushButton2.clicked.connect(lambda: self.threads['control_Keithley6220_2'][0].disable())


                self.action_run_Keithley.setChecked(True)

            except VisaIOError as e:
                self.action_run_Keithley.setChecked(False)
                self.show_error_textBrowser('running: {}'.format(e))
        else:
            self.action_run_Keithley.setChecked(False)
            self.stopping_thread('control_Keithley6220_1')
            self.stopping_thread('control_Keithley6220_2')

            self.Keithley_window.spinSetCurrent1_mA.valueChanged.disconnect()
            self.Keithley_window.spinSetCurrent1_mA.editingFinished.disconnect()
            self.Keithley_window.spinSetCurrent2_mA.valueChanged.disconnect()
            self.Keithley_window.spinSetCurrent2_mA.editingFinished.disconnect()

            self.Keithley_window.pushButton1.clicked.disconnect()
            self.Keithley_window.pushButton2.clicked.disconnect()

    @pyqtSlot(bool)
    def show_Keithley(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.Keithley_window.show()
        else:
            self.Keithley_window.close()


    @pyqtSlot(dict)
    def store_data_Keithley(self, data):
        """
            Store Keithley data in self.data['Keithley'], update Keithley_window
        """

        with self.dataLock:
            self.data['Keithley'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device, the last value is retained

            self.Keithley_window.lcdSensor1_nV.display(self.data['Keithley2182_1']['Voltage_nV'])
            self.Keithley_window.lcdSensor2_nV.display(self.data['Keithley2182_2']['Voltage_nV'])
            self.Keithley_window.lcdSensor3_nV.display(self.data['Keithley2182_3']['Voltage_nV'])




    # ------- MISC -------

    def printing(self,b):
        """arbitrary example function"""
        print(b)

    def initialize_window_Log_conf(self):
        """initialize Logging configuration window"""
        self.Log_conf_window = Logger_configuration()
        self.Log_conf_window.sig_closing.connect(lambda: self.action_Logging_configuration.setChecked(False))
        self.Log_conf_window.sig_send_conf.connect(lambda conf: self.sig_logging_newconf.emit(conf))

        self.action_Logging.triggered['bool'].connect(self.run_logger)
        self.action_Logging_configuration.triggered['bool'].connect(self.show_logging_configuration)

    @pyqtSlot(bool)
    def run_logger(self, boolean):
        """start/stop the logging thread"""

        # read the last configuration of what shall be logged from a respective file

        if boolean:
            logger = self.running_thread(main_Logger(self), None, 'logger')
            logger.sig_log.connect(lambda : self.sig_logging.emit(deepcopy(self.data)))
            logger.sig_configuring.connect(self.show_logging_configuration)
            self.logging_running_logger = True

        else:
            self.stopping_thread('logger')
            self.logging_running_logger = False

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
            try:

                getInfodata = self.running_thread(live_Logger(self), None, 'control_Logging_live')
                getInfodata.sig_assertion.connect(self.show_error_textBrowser)

                self.actionLogging_LIVE.setChecked(True)
            except VisaIOError as e:
                self.action_run_ITC.setChecked(False)
                self.show_error_textBrowser(e)
                # print(e) # TODO: open window displaying the error message

        else:
            self.stopping_thread('control_Logging_live')
            self.actionLogging_LIVE.setChecked(False)


    def initialize_window_Errors(self):
        """initialize Error Window"""
        self.Errors_window = Window_ui(ui_file='.\\configurations\\Errors.ui')
        self.Errors_window.sig_closing.connect(lambda: self.action_show_Errors.setChecked(False))

        self.Errors_window.textErrors.setHtml('')

        # self.action_run_Errors.triggered['bool'].connect(self.run_ITC)
        self.action_show_Errors.triggered['bool'].connect(self.show_Errors)

    @pyqtSlot(bool)
    def show_Errors(self, boolean):
        """display/close the Error window"""
        if boolean:
            self.Errors_window.show()
        else:
            self.Errors_window.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    a = time.time()
    form = mainWindow(app=app)
    form.show()
    print(time.time()-a)
    sys.exit(app.exec_())

