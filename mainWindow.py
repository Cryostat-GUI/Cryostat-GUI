
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

import sys
import time
import datetime

import mainWindow_ui

from Oxford.ITCcontrol_ui import Ui_ITCcontrol
from Oxford.ITC_control import ITC_Updater as cls_itc



from pyvisa.errors import VisaIOError

from logger import main_Logger


class mainWindow(QtWidgets.QMainWindow): #, mainWindow_ui.Ui_Cryostat_Main):
    """This is the main GUI Window"""
    
    sig_arbitrary = pyqtSignal()
    sig_logging = pyqtSignal(dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        loadUi('Cryostat GUI.ui', self)
        # self.setupUi(self)
        self.threads = dict()
        self.data = dict()
        self.logging_bools = dict()

        # initialize ITC Window
        self.ITC_ui = Ui_ITCcontrol()
        self.ITC_ui.setupUi(self.ITC_window)


        self.action_Logging.triggered['bool'].connect(self.run_logger)

        self.action_run_ITC.triggered['bool'].connect(self.run_ITC)
        self.action_show_ITC.triggered['bool'].connect(self.show_ITC)


    def running_thread(self, worker, dataname, threadname, **kwargs):
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

        self.threads[threadname][0].stop()
        self.threads[threadname][1].quit()
        self.threads[threadname][1].wait()
        del self.threads[threadname]


    @pyqtSlot(bool)
    def run_ITC(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""

        if boolean:
            try:
                # self.ITC = itc503('COM6')
                # getInfodata = cls_itc(self.ITC)
                getInfodata = self.running_thread(cls_itc('COM6'), 'ITC', 'control_ITC')

                getInfodata.sig_Infodata.connect(self.store_data_itc)
                getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visatimeout.connect(lambda: print('timeout'))


                # setting ITC values by GUI ITC window
                self.ITC_ui.spinsetTemp.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Temperature(value))
                self.ITC_ui.spinsetTemp.editingFinished.connect(lambda: self.threads['control_ITC'][0].setTemperature())

                self.ITC_ui.spinsetGasOutput.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_GasOutput(value))
                self.ITC_ui.spinsetGasOutput.editingFinished.connect(lambda : self.threads['control_ITC'][0].setGasOutput())

                self.ITC_ui.spinsetHeaterPercent.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_HeaterOutput(value))
                self.ITC_ui.spinsetHeaterPercent.editingFinished.connect(lambda : self.threads['control_ITC'][0].setHeaterOutput())

                self.ITC_ui.spinsetProportionalID.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Proportional(value))
                self.ITC_ui.spinsetProportionalID.editingFinished.connect(lambda : self.threads['control_ITC'][0].setProportional())

                self.ITC_ui.spinsetPIntegrationD.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Integral(value))
                self.ITC_ui.spinsetPIntegrationD.editingFinished.connect(lambda : self.threads['control_ITC'][0].setIntegral())

                self.ITC_ui.spinsetPIDerivative.valueChanged.connect(lambda value: self.threads['control_ITC'][0].gettoset_Derivative(value))
                self.ITC_ui.spinsetPIDerivative.editingFinished.connect(lambda : self.threads['control_ITC'][0].setDerivative())

                self.ITC_ui.combosetHeatersens.activated['int'].connect(lambda value: self.threads['control_ITC'][0].setHeaterSensor(value + 1))

                self.ITC_ui.combosetAutocontrol.activated['int'].connect(lambda value: self.threads['control_ITC'][0].setAutoControl(value))


                # thread.started.connect(getInfodata.work)
                # thread.start()
                self.action_run_ITC.setChecked(True)
            except VisaIOError as e:
                self.action_run_ITC.setChecked(False)
                print(e) # TODO: open window displaying the error message

        else:
            self.action_run_ITC.setChecked(False)
            # possibly implement putting the instrument back to local operation
            self.stopping_thread('control_ITC')

    @pyqtSlot(bool)
    def show_ITC(self, boolean):
        """method which will display the ITC window"""
        if boolean:
            self.ITC_window.show()
        else:
            self.ITC_window.close()

    @pyqtSlot(dict)
    def store_data_itc(self, data):
        """Store ITC data in self.data['ITC'], update ITC_ui"""
        data['date'] = convert_time(time.time())
        self.data['ITC'].append(data)
        self.ITC_ui.lcdTemp_sens1.display(self.data['ITC'][-1]['sensor_1_temperature'])
        self.ITC_ui.lcdTemp_sens2.display(self.data['ITC'][-1]['sensor_2_temperature'])
        self.ITC_ui.lcdTemp_sens3.display(self.data['ITC'][-1]['sensor_3_temperature'])
        self.ITC_ui.lcdTemp_set.display(self.data['ITC'][-1]['set_temperature'])
        self.ITC_ui.lcdTemp_err.display(self.data['ITC'][-1]['temperature_error'])
        self.ITC_ui.progressHeaterPercent.setValue(self.data['ITC'][-1]['heater_output_as_percent'])
        self.ITC_ui.lcdHeaterVoltage.display(self.data['ITC'][-1]['heater_output_as_voltage'])
        self.ITC_ui.progressNeedleValve.setValue(self.data['ITC'][-1]['gas_flow_output'])
        self.ITC_ui.lcdProportionalID.display(self.data['ITC'][-1]['proportional_band'])
        self.ITC_ui.lcdPIntegrationD.display(self.data['ITC'][-1]['integral_action_time'])
        self.ITC_ui.lcdPIDerivative.display(self.data['ITC'][-1]['derivative_action_time'])
        

    def printing(self,b):
        """arbitrary exmple function"""
        print(b)


    @pyqtSlot(bool)
    def run_logger(self, boolean):
        """start/stop the logging thread"""

        # read the last configuration of what shall be logged from a respective file
        conf = self.logging_read_configuration()

        if boolean: 
            logger = self.running_thread(main_Logger(self), None, 'logger')
            logger.sig_log.connect(lambda : self.sig_logging.emit(self.data))

        else: 
            self.stopping_thread('logger')
         
    def logging_read_configuration(self):
        """method to read the last configuration of 
            what shall be logged from a respective file
        """
        pass


def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow()
    form.show()
    sys.exit(app.exec_())

