
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.uic import loadUi

import sys
import time
import datetime

# import mainWindow_ui

# from Oxford.ITCcontrol_ui import Ui_ITCcontrol
from Oxford.ITC_control import ITC_Updater
from Oxford.ILM_control import ILM_Updater



from pyvisa.errors import VisaIOError

from logger import main_Logger
from logger import Logger_configuration #Logger_configuration
from util import Window_ui


ITC_Instrumentadress = 'COM6'


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

        self.initialize_window_ITC()
        self.initialize_window_ILM()
        self.initialize_window_Log_conf()





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
            self.data[dataname] = list()

        thread.started.connect(worker.work)
        thread.start()
        return worker

    def stopping_thread(self, threadname):
        """Stop the thread specified by the argument threadname, delete its entry in self.threads"""

        # self.threads[threadname][0].stop()
        self.threads[threadname][1].quit()
        self.threads[threadname][1].wait()
        del self.threads[threadname]

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
                getInfodata = self.running_thread(ITC_Updater('COM6'), 'ITC', 'control_ITC')

                getInfodata.sig_Infodata.connect(self.store_data_itc)
                getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visatimeout.connect(lambda: print('timeout'))


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
                print(e) # TODO: open window displaying the error message

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
        data['date'] = convert_time(time.time())
        self.data['ITC'].append(data)
        self.ITC_window.lcdTemp_sens1.display(self.data['ITC'][-1]['sensor_1_temperature'])
        self.ITC_window.lcdTemp_sens2.display(self.data['ITC'][-1]['sensor_2_temperature'])
        self.ITC_window.lcdTemp_sens3.display(self.data['ITC'][-1]['sensor_3_temperature'])
        self.ITC_window.lcdTemp_set.display(self.data['ITC'][-1]['set_temperature'])
        self.ITC_window.lcdTemp_err.display(self.data['ITC'][-1]['temperature_error'])
        self.ITC_window.progressHeaterPercent.setValue(self.data['ITC'][-1]['heater_output_as_percent'])
        self.ITC_window.lcdHeaterVoltage.display(self.data['ITC'][-1]['heater_output_as_voltage'])
        self.ITC_window.progressNeedleValve.setValue(self.data['ITC'][-1]['gas_flow_output'])
        self.ITC_window.lcdProportionalID.display(self.data['ITC'][-1]['proportional_band'])
        self.ITC_window.lcdPIntegrationD.display(self.data['ITC'][-1]['integral_action_time'])
        self.ITC_window.lcdPIDerivative.display(self.data['ITC'][-1]['derivative_action_time'])
        

    def printing(self,b):
        """arbitrary exmple function"""
        print(b)

    def initialize_window_Log_conf(self):
        """initialize Logging configuration window"""
        self.Log_conf_window = Logger_configuration(ui_file='.\\configurations\\Logger_conf.ui')
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


    def initialize_window_ILM(self):
        """initialize ILM Window"""
        self.ILM_window = Window_ui(ui_file='.\\Oxford\\ILM_control.ui')
        self.ILM_window.sig_closing.connect(lambda: self.action_show_ILM.setChecked(False))

        self.action_run_ILM.triggered['bool'].connect(self.run_ILM)
        self.action_show_ILM.triggered['bool'].connect(self.show_ILM)

    @pyqtSlot(bool)
    def run_ILM(self, boolean):
        """start/stop the logging thread"""

        # read the last configuration of what shall be logged from a respective file

        if boolean: 
            try: 
                getInfodata = self.running_thread(ILM_Updater(InstrumentAddress='COM5'),'ILM', 'control_ILM')

                getInfodata.sig_Infodata.connect(self.store_data_ilm)
                getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visatimeout.connect(lambda: print('timeout'))

                self.ILM_window.combosetProbingRate_chan1.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 1))
                self.ILM_window.combosetProbingRate_chan2.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 2))

                self.action_run_ILM.setChecked(True)
            
            except VisaIOError as e:
                self.action_run_ILM.setChecked(False)
                print(e) # TODO: open window displaying the error message
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
        data['date'] = convert_time(time.time())
        self.data['ILM'].append(data)
        self.MainDock_HeLevel.setValue(self.data['ILM'][-1]['channel_1_level'])
        self.MainDock_N2Level.setValue(self.data['ILM'][-1]['channel_2_level'])
        print(self.data['ILM'][-1]['channel_1_level'], self.data['ILM'][-1]['channel_2_level'])

        

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow()
    form.show()
    sys.exit(app.exec_())

