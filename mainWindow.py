
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.uic import loadUi

import sys
import time
import datetime
from threading import Lock

# import mainWindow_ui

# from Oxford.ITCcontrol_ui import Ui_ITCcontrol
from Oxford.ITC_control import ITC_Updater
from Oxford.ILM_control import ILM_Updater
from Oxford.IPS_control import IPS_Updater
from Lakeshore.LakeShore350_control import LakeShore350_Updater



from pyvisa.errors import VisaIOError

from logger import main_Logger
from logger import Logger_configuration #Logger_configuration
from util import Window_ui


ITC_Instrumentadress = 'ASRL6::INSTR'
ILM_Instrumentadress = 'ASRL5::INSTR'
IPS_Instrumentadress = 'ASRL4::INSTR'
LakeShore_Instrumentaddress = 'GPIB0::12::INSTR'


def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


class mainWindow(QtWidgets.QMainWindow): #, mainWindow_ui.Ui_Cryostat_Main):
    """This is the main GUI Window, where other windows will be spawned from"""
    
    sig_arbitrary = pyqtSignal()
    sig_logging = pyqtSignal(dict)
    sig_logging_newconf = pyqtSignal(dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)
        self.threads = dict()
        self.data = dict()
        self.logging_bools = dict()

        self.logging_running_ITC = False
        self.logging_running_logger = False

        self.dataLock = Lock()


        QTimer.singleShot(0, self.initialize_all_windows)


    def initialize_all_windows(self):
        self.initialize_window_ITC()
        self.initialize_window_ILM()
        self.initialize_window_IPS()
        self.initialize_window_Log_conf()
        self.initialize_window_Lakeshore350()
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
        """Store ITC data in self.data['ITC'], update ITC_window"""
        with self.dataLock: 
            data['date'] = convert_time(time.time())
            self.data['ITC'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up, 
            # since the command failed in the communication with the device, the last value is retained
            self.ITC_window.lcdTemp_sens1.display(self.data['ITC']['sensor_1_temperature'])
            self.ITC_window.lcdTemp_sens2.display(self.data['ITC']['sensor_2_temperature'])
            self.ITC_window.lcdTemp_sens3.display(self.data['ITC']['sensor_3_temperature'])
            self.ITC_window.lcdTemp_set.display(self.data['ITC']['set_temperature'])
            self.ITC_window.lcdTemp_err.display(self.data['ITC']['temperature_error'])
            self.ITC_window.progressHeaterPercent.setValue(self.data['ITC']['heater_output_as_percent'])
            self.ITC_window.lcdHeaterVoltage.display(self.data['ITC']['heater_output_as_voltage'])
            self.ITC_window.progressNeedleValve.setValue(self.data['ITC']['gas_flow_output'])
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
            self.ILM_window.progressLevelHe.setValue(self.data['ILM']['channel_1_level'])
            self.ILM_window.progressLevelN2.setValue(self.data['ILM']['channel_2_level'])

            self.MainDock_HeLevel.setValue(self.data['ILM']['channel_1_level'])
            self.MainDock_N2Level.setValue(self.data['ILM']['channel_2_level'])
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

        self.action_run_LakeShore350.triggered['bool'].connect(self.run_LakeShore350)
        self.action_show_Lakeshore350.triggered['bool'].connect(self.show_LakeShore350)

    @pyqtSlot(bool)
    def run_LakeShore350(self, boolean):
        """start/stop the LakeShore350 thread"""

        if boolean: 
            try: 
                getInfodata = self.running_thread(LakeShore350_Updater(LakeShore_InstrumentAddress),'LakeShore350', 'control_LakeShore350')

                getInfodata.sig_Infodata.connect(self.store_data_LakeShore350)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_textBrowser)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_textBrowser)
                getInfodata.sig_visatimeout.connect(lambda: self.show_error_textBrowser('LakeShore350: timeout'))


                # setting LakeShore values by GUI LakeShore window
                self.LakeShore350_window.spinSetTemp_K.valueChanged.connect(lambda value: self.threads['control_LakeShore350'][0].gettoset_Temp_K(value))
                self.LakeShore350_window.spinSetTemp_K.editingFinished.connect(lambda value: self.threads['control_LakeShore350'][0].setTemp_K())

                self.LakeShore350_window.spinSetHeater_mW.valueChanged.
                self.LakeShore350_window.spinSetHeater_mW.editingFinished.



                self.action_run_LakeShore350.setChecked(True)
            
            except VisaIOError as e:
                self.action_run_LakeShore350.setChecked(False)
                print(e) # TODO: open window displaying the error message
        else: 
            self.action_run_LakeShore350.setChecked(False)
            self.stopping_thread('control_LakeShore350')

    @pyqtSlot(bool)
    def show_LakeShore350(self, boolean):
        """display/close the ILM data & control window"""
        if boolean:
            self.LakeShore350_window.show()
        else:
            self.LakeShore350_window.close()


        """
            self.textErrors = QtWidgets.QTextBrowser(Form)
            self.textErrors.setObjectName("textErrors")
            self.lcdHeaterOutput_mW = QtWidgets.QLCDNumber(Form)
            self.lcdHeaterOutput_mW.setObjectName("lcdHeaterOutput_mW")
            self.lcdSetTemp_K = QtWidgets.QLCDNumber(Form)
            self.lcdSetTemp_K.setObjectName("lcdSetTemp_K")
            self.spinSetTemp_K = QtWidgets.QDoubleSpinBox(Form)
            self.spinSetTemp_K.setDecimals(4)
            self.spinSetTemp_K.setMaximum(300.0)
            self.spinSetTemp_K.setObjectName("spinSetTemp_K")
            self.lcdSetHeater_mW = QtWidgets.QLCDNumber(Form)
            self.lcdSetHeater_mW.setObjectName("lcdSetHeater_mW")
            self.spinSetHeater_mW = QtWidgets.QDoubleSpinBox(Form)
            self.spinSetHeater_mW.setDecimals(1)
            self.spinSetHeater_mW.setMaximum(1000.0)
            self.spinSetHeater_mW.setObjectName("spinSetHeater_mW")
            self.lcdSensor1_K = QtWidgets.QLCDNumber(Form)
            self.lcdSensor1_K.setObjectName("lcdSensor1_K")
            self.lcdSensor2_K = QtWidgets.QLCDNumber(Form)
            self.lcdSensor2_K.setObjectName("lcdSensor2_K")
            self.lcdSensor3_K = QtWidgets.QLCDNumber(Form)
            self.lcdSensor3_K.setObjectName("lcdSensor3_K")
            self.lcdSensor4_K = QtWidgets.QLCDNumber(Form)
            self.lcdSensor4_K.setObjectName("lcdSensor4_K")

            self.spinXXX.valueChanged.connect(self.method)
            self.spinXXX.valueChanged.connect(lambda: self.threads['somethread'].THREAD_Class_method())
            self.spinXXX.valueChanged.connect(lambda value: self.threads['somethread'].THREAD_Class_method(value))
            self.lcdXXX.display(some_number)
            self.textXXX.setText(some_string)
        """


        @pyqtSlot(dict)
        def store_data_LakeShore350(self, data):
        """Store LakeShore350 data in self.data['LakeShore350'], update LakeShore350_window"""
        with self.dataLock: 
            data['date'] = convert_time(time.time())
            self.data['Lakeshore350'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up, 
            # since the command failed in the communication with the device, the last value is retained
            self.LakeShore350_window.lcdHeaterOutput_mW.display(self.data['Lakeshore350']['Heater_Output_mW'])
            self.LakeShore350_window.lcdSetTemp_K.display(self.data['Lakeshore350']['Temp_K'])
            self.LakeShore350_window.lcdSetHeater_mW.display(self.data['Lakeshore350']['Heater_mW'])

            self.LakeShore350_window.lcdSensor1_K.display(self.data['LakeShore350']['Sensor_1_K'])
            self.LakeShore350_window.lcdSensor2_K.display(self.data['LakeShore350']['Sensor_2_K'])
            self.LakeShore350_window.lcdSensor3_K.display(self.data['LakeShore350']['Sensor_3_K'])
            self.LakeShore350_window.lcdSensor4_K.display(self.data['LakeShore350']['Sensor_4_K'])     



    # ------- MISC -------

    def printing(self,b):
        """arbitrary exmple function"""
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
            logger.sig_log.connect(lambda : self.sig_logging.emit(self.data))
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
    form = mainWindow()
    form.show()
    print(time.time()-a)
    sys.exit(app.exec_())

