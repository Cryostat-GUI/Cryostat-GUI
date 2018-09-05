
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.uic import loadUi

import sys
import time
import datetime

import mainWindow_ui

from Oxford.ITCcontrol_ui import Ui_ITCcontrol
from Oxford.ITC_control import ITC_Updater as cls_itc



from pyvisa.errors import VisaIOError

from logger import main_Logger
from util import Window_ui




def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


# class ITC_ui(QtWidgets.QWidget):
#     """docstring for ITC_ui"""

#     sig_closing = pyqtSignal()

#     def __init__(self):
#         super().__init__()
#         loadUi('./Oxford/ITC_control.ui', self)

#     def closeEvent(self, event):
#         # do stuff
#         self.sig_closing.emit()
#         if True:
#             event.accept() # let the window close
#         else:
#             event.ignore()


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
        # self.ITC_ui = Ui_ITCcontrol()
        # self.ITC_ui.setupUi(self.ITC_window)
        # loadUi('./Oxford/ITC_control.ui', self.ITC_window)
        # monkeypatching ITC window closeEvent
        # self.ITC_window.closeEvent = self.closeEvent_ITC_window
        self.ITC_window = Window_ui('./Oxford/ITC_control.ui')
        self.ITC_window.sig_closing.connect(lambda: self.action_show_ITC.setChecked(False))


        self.logging_running_ITC = False
        self.logging_running_logger = False


        self.action_Logging.triggered['bool'].connect(self.run_logger)

        self.action_run_ITC.triggered['bool'].connect(self.run_ITC)
        self.action_show_ITC.triggered['bool'].connect(self.show_ITC)


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


    @pyqtSlot(bool)
    def run_logger(self, boolean):
        """start/stop the logging thread"""

        # read the last configuration of what shall be logged from a respective file
        conf = self.logging_read_configuration()

        if boolean: 
            logger = self.running_thread(main_Logger(self), None, 'logger', info = conf)
            logger.sig_log.connect(lambda : self.sig_logging.emit(self.data))
            self.logging_running_logger = True

        else: 
            self.stopping_thread('logger')
            self.logging_running_logger = False
         
    def logging_read_configuration(self):
        """method to read the last configuration of 
            what shall be logged from a respective file
        """
        pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow()
    form.show()
    sys.exit(app.exec_())

