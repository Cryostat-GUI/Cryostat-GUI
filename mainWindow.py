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

import time

a = time.time()


from PyQt5 import QtWidgets, QtGui
# from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
# from PyQt5.QtWidgets import QtAlignRight
from PyQt5.uic import loadUi


import sys
# import datetime
from threading import Lock
import numpy as np
from copy import deepcopy
from importlib import reload
import sqlite3

from pyvisa.errors import VisaIOError


import Oxford
import LakeShore
import Keithley

# from Oxford.ITC_control import ITC_Updater
# from Oxford.ILM_control import ILM_Updater
# from Oxford.IPS_control import IPS_Updater
# from LakeShore.LakeShore350_Control import LakeShore350_Updater
# from Keithley.Keithley2182_Control import Keithley2182_Updater
# from Keithley.Keithley6221_Control import Keithley6221_Updater

# from Sequence import OneShot_Thread
from Sequence import OneShot_Thread_multichannel

from logger import main_Logger, live_Logger, measurement_Logger
from logger import Logger_configuration

from util import Window_ui, Window_plotting
from util import convert_time
from util import convert_time_searchable
from util import Workerclass
from util import running_thread
from util import locking
from util import noKeyError

ITC_Instrumentadress = 'ASRL6::INSTR'
ILM_Instrumentadress = 'ASRL5::INSTR'
IPS_Instrumentadress = 'ASRL4::INSTR'
LakeShore_InstrumentAddress = 'GPIB0::1::INSTR'
Keithley2182_1_InstrumentAddress = 'GPIB0::2::INSTR'
Keithley2182_2_InstrumentAddress = 'GPIB0::3::INSTR'
Keithley2182_3_InstrumentAddress = 'GPIB0::4::INSTR'
Keithley6221_1_InstrumentAddress = 'GPIB0::5::INSTR'
Keithley6221_2_InstrumentAddress = 'GPIB0::6::INSTR'


class mainWindow(QtWidgets.QMainWindow):
    """This is the main GUI Window, where other windows will be spawned from"""

    sig_arbitrary = pyqtSignal()
    sig_logging = pyqtSignal(dict)
    sig_logging_newconf = pyqtSignal(dict)
    sig_running_new_thread = pyqtSignal()
    sig_log_measurement = pyqtSignal(dict)
    sig_measure_oneshot = pyqtSignal()
    sig_measure_oneshot_start = pyqtSignal()
    sig_measure_oneshot_stop = pyqtSignal()
    # sig_softwarecontrols = pyqtSignal(dict)

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        loadUi('.\\configurations\\Cryostat GUI.ui', self)
        # self.setupUi(self)
        self.threads = dict(Lock=Lock())
        # self.threads = dict()
        self.threads_tiny = list()
        self.data = dict()
        self.logging_bools = dict()

        self.logging_running_ITC = False
        self.logging_running_logger = False

        self.dataLock = Lock()
        self.dataLock_live = Lock()
        self.app = app

        QTimer.singleShot(0, self.initialize_all_windows)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.app.quit()

    def initialize_all_windows(self):
        """window and GUI initialisatoins"""
        self.window_SystemsOnline = Window_ui(
            ui_file='.\\configurations\\Systems_online.ui')
        self.actionSystems_Online.triggered.connect(
            lambda: self.window_SystemsOnline.show())

        self.initialize_window_ITC()
        self.initialize_window_ILM()
        self.initialize_window_IPS()
        self.initialize_window_Log_conf()
        self.initialize_window_LakeShore350()
        self.initialize_window_Keithley()
        self.initialize_window_Errors()
        self.show_data()
        self.window_SystemsOnline.checkactionLogging_LIVE.toggled[
            'bool'].connect(self.run_logger_live)

        self.initialize_window_OneShot()
        self.controls = [
            self.ITC_window.groupSettings,
            self.ILM_window.groupSettings,
            self.IPS_window.groupSettings,
            self.LakeShore350_window.groupSettings]
        self.controls_Lock = Lock()

        self.softwarecontrol_check()
        self.softwarecontrol_timer = QTimer()
        self.softwarecontrol_timer.timeout.connect(self.softwarecontrol_check)
        self.softwarecontrol_timer.start(100)
        # self.sig_softwarecontrols.connect(lambda value: self.softwarecontrol_toggle(value['controls'], value['lock'], value['bools'] ))

    # def softwarecontrol_toggle(self, controls, lock, bools):
    #     print('received signal: control:', controls, 'lock: ', lock, 'bool: ', bools)
    #     print('locked: ', lock.locked())
    #     if not bools:
    #         lock.acquire()
    #     for control in controls:
    #             control.setEnabled(bools)
    #             print('working on it')
    #     if bools:
    #         lock.release()
    #     print('locked: ', lock.locked())

    def softwarecontrol_toggle_locking(self, value):
        if value:
            self.controls_Lock.acquire()
        else:
            self.controls_Lock.release()

    def softwarecontrol_check(self):
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
        with self.threads['Lock']:
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
        with self.threads['Lock']:
            del self.threads[threadname]

    def show_error_general(self, text):
        self.show_error_textBrowser(text)

    def show_error_textBrowser(self, text):
        """ append error to Error window"""
        self.Errors_window.textErrors.append(
            '{} - {}'.format(convert_time(time.time()), text))

    def show_window(self, window, boolean):
        if boolean:
            window.show()
        else:
            window.close()

    # ------- plotting
    def connectdb(self, dbname):
        """connect to the database, provide the cursor for the whole class"""
        try:
            self.conn = sqlite3.connect(dbname)
            self.mycursor = self.conn.cursor()
        except sqlite3.connect.Error as err:
            raise AssertionError(
                "Logger: Couldn't establish connection {}".format(err))

    def show_data(self):  # a lot of work to do
        """connect GUI signals for plotting, setting up some of the needs of plotting"""
        self.action_plotDatabase.triggered.connect(
            self.show_dataplotdb_configuration)
        self.action_plotLive.triggered.connect(
            self.show_dataplotlive_configuration)
        self.windows_plotting = []
        self.plotting_window_count = 0

        #  these will hold the strings which the user selects to extract the data from db with the sql query and plot it
        # x,y1.. is for tablenames, x,y1.._plot is for column names in the
        # tables respectively
        self.plotting_instrument_for_x = 0
        self.plotting_instrument_for_y1 = 0
        self.plotting_instrument_for_y2 = 0

        self.plotting_comboValue_Axis_X_plot = 0
        self.plotting_comboValue_Axis_Y1_plot = 0
        self.plotting_data_y2_plot = 0

    def show_dataplotdb_configuration(self):
        self.dataplot_db = Window_ui(
            ui_file='.\\configurations\\Data_display_selection_database.ui')
        self.dataplot_db.show()
        #  populating the combobox instruments tab with tablenames:
        self.mycursor.execute(
            "SELECT name FROM sqlite_master where type='table'")
        axis2 = self.mycursor.fetchall()
        axis2.insert(0, ("-",))

        self.dataplot_db.comboInstr_Axis_X.clear()
        self.dataplot_db.comboInstr_Axis_Y1.clear()
        self.dataplot_db.comboInstr_Axis_Y2.clear()
        self.dataplot_db.comboInstr_Axis_Y3.clear()
        self.dataplot_db.comboInstr_Axis_Y4.clear()
        self.dataplot_db.comboInstr_Axis_Y5.clear()

        for i in axis2:
            self.dataplot_db.comboInstr_Axis_X.addItems(i)
            self.dataplot_db.comboInstr_Axis_Y1.addItems(i)
            self.dataplot_db.comboInstr_Axis_Y2.addItems(i)
            self.dataplot_db.comboInstr_Axis_Y3.addItems(i)
            self.dataplot_db.comboInstr_Axis_Y4.addItems(i)
            self.dataplot_db.comboInstr_Axis_Y5.addItems(i)
        self.dataplot_db.comboInstr_Axis_X.activated.connect(self.selection_x)
        self.dataplot_db.comboInstr_Axis_Y1.activated.connect(
            self.selection_y1)
        self.dataplot_db.buttonBox.clicked.connect(self.plotstart)

    def show_dataplotlive_configuration(self):
        """
            open the window for configuration of the Live-plotting to be done,
            fill the comboboxes with respective values, to choose from instruments
            connect to actions being taken in this configuration window
        """
        self.dataplot_live_conf = Window_ui(
            ui_file='.\\configurations\\Data_display_selection_live.ui')

        # initialize some "storage space" for data
        self.dataplot_live_conf.axes = dict()
        self.dataplot_live_conf.data = dict()

        if not hasattr(self, "data_live"):
            self.show_error_general('no live data to plot!')

            self.show_error_general(
                'If you want to see live data, start the live logger!')
            return
        self.dataplot_live_conf.show()

        with self.dataLock_live:
            axis_instrument = list(self.data_live)  # all the dictionary keys
        axis_instrument.insert(0, "-")  # for no chosen value by default
        self.dataplot_live_conf.comboInstr_Axis_X.clear()
        self.dataplot_live_conf.comboInstr_Axis_Y1.clear()
        self.dataplot_live_conf.comboInstr_Axis_Y2.clear()
        self.dataplot_live_conf.comboInstr_Axis_Y3.clear()
        self.dataplot_live_conf.comboInstr_Axis_Y4.clear()
        self.dataplot_live_conf.comboInstr_Axis_Y5.clear()

        # for i in axis_instrument:  # filling the comboboxes for the instrument
        # print(i, type(i))
        self.dataplot_live_conf.comboInstr_Axis_X.addItems(axis_instrument)
        self.dataplot_live_conf.comboInstr_Axis_Y1.addItems(axis_instrument)
        self.dataplot_live_conf.comboInstr_Axis_Y2.addItems(axis_instrument)
        self.dataplot_live_conf.comboInstr_Axis_Y3.addItems(axis_instrument)
        self.dataplot_live_conf.comboInstr_Axis_Y4.addItems(axis_instrument)
        self.dataplot_live_conf.comboInstr_Axis_Y5.addItems(axis_instrument)
        # actions in case instruments are chosen in comboboxes
        self.dataplot_live_conf.comboInstr_Axis_X.activated.connect(lambda: self.plotting_selection_instrument(GUI_value=self.dataplot_live_conf.comboValue_Axis_X,
                                                                                                               GUI_instr=self.dataplot_live_conf.comboInstr_Axis_X,
                                                                                                               livevsdb="LIVE",
                                                                                                               axis='X',
                                                                                                               dataplot=self.dataplot_live_conf))
        self.dataplot_live_conf.comboInstr_Axis_Y1.activated.connect(lambda: self.plotting_selection_instrument(GUI_value=self.dataplot_live_conf.comboValue_Axis_Y1,
                                                                                                                GUI_instr=self.dataplot_live_conf.comboInstr_Axis_Y1,
                                                                                                                livevsdb="LIVE",
                                                                                                                axis='Y1',
                                                                                                                dataplot=self.dataplot_live_conf))
        self.dataplot_live_conf.comboInstr_Axis_Y2.activated.connect(lambda: self.plotting_selection_instrument(GUI_value=self.dataplot_live_conf.comboValue_Axis_Y2,
                                                                                                                GUI_instr=self.dataplot_live_conf.comboInstr_Axis_Y2,
                                                                                                                livevsdb="LIVE",
                                                                                                                axis='Y2',
                                                                                                                dataplot=self.dataplot_live_conf))
        self.dataplot_live_conf.comboInstr_Axis_Y3.activated.connect(lambda: self.plotting_selection_instrument(GUI_value=self.dataplot_live_conf.comboValue_Axis_Y3,
                                                                                                                GUI_instr=self.dataplot_live_conf.comboInstr_Axis_Y3,
                                                                                                                livevsdb="LIVE",
                                                                                                                axis='Y3',
                                                                                                                dataplot=self.dataplot_live_conf))
        self.dataplot_live_conf.comboInstr_Axis_Y4.activated.connect(lambda: self.plotting_selection_instrument(GUI_value=self.dataplot_live_conf.comboValue_Axis_Y4,
                                                                                                                GUI_instr=self.dataplot_live_conf.comboInstr_Axis_Y4,
                                                                                                                livevsdb="LIVE",
                                                                                                                axis='Y4',
                                                                                                                dataplot=self.dataplot_live_conf))
        self.dataplot_live_conf.comboInstr_Axis_Y5.activated.connect(lambda: self.plotting_selection_instrument(GUI_value=self.dataplot_live_conf.comboValue_Axis_Y5,
                                                                                                                GUI_instr=self.dataplot_live_conf.comboInstr_Axis_Y5,
                                                                                                                livevsdb="LIVE",
                                                                                                                axis='Y5',
                                                                                                                dataplot=self.dataplot_live_conf))

        self.dataplot_live_conf.buttonBox.clicked.connect(
            lambda: self.plotting_display(dataplot=self.dataplot_live_conf))
        self.dataplot_live_conf.buttonBox.clicked.connect(
            lambda: self.dataplot_live_conf.close())
        self.dataplot_live_conf.buttonCancel.clicked.connect(
            lambda: self.dataplot_live_conf.close())

    def plotting_selection_instrument(self, livevsdb, GUI_instr, GUI_value, axis, dataplot):
        """
           filling the Value column combobox in case the corresponding
           element of the instrument column combobox was chosen
           thus:
                - check for the chosen instrument,
                - get the data for the new combobox
                - chose the action
        """

        instrument_name = GUI_instr.currentText()
        # print("instrument for x was set to: ",self.plotting_instrument_for_x)
        if livevsdb == "LIVE":
            with self.dataLock_live:
                try:
                    value_names = list(self.data_live[instrument_name])
                except KeyError:
                    self.show_error_general('plotting: do not choose "-" '
                                            'please, there is nothing behind it!')
                    return
        # elif livevsdb == "DB":
        #     axis = []
        #     self.mycursor.execute("SELECT * FROM {}".format(self.plotting_instrument_for_x))
        #     colnames= self.mycursor.description
            # for row in colnames:
            #     axis.append(row[0])
        GUI_value.clear()
        GUI_value.addItems(("-",))
        GUI_value.addItems(value_names)
        GUI_value.activated.connect(lambda: self.plotting_selection_value(GUI_instr=GUI_instr,
                                                                          GUI_value=GUI_value,
                                                                          livevsdb="LIVE",
                                                                          axis=axis,
                                                                          dataplot=dataplot))

    def x_changed(self):
        self.plotting_comboValue_Axis_X_plot = self.dataplot.comboValue_Axis_X.currentText()

    def plotting_selection_value(self, GUI_instr, GUI_value, livevsdb, axis, dataplot):
        value_name = GUI_value.currentText()
        instrument_name = GUI_instr.currentText()
        dataplot.axes[axis] = value_name

        if livevsdb == 'LIVE':
            with self.dataLock_live:
                try:
                    dataplot.data[axis] = self.data_live[
                        instrument_name][value_name]
                except KeyError:
                    self.show_error_general('plotting: do not choose "-" '
                                            'please, there is nothing behind it!')
                    return

    def plotting_display(self, dataplot):
        y = None
        try:
            x = dataplot.data['X']
            y = [dataplot.data[key] for key in dataplot.data if key != 'X']
        except KeyError:
            self.show_error_general(
                'Plotting: You certainly did not choose an X axis, try again!')
            return
        if y is None:
            self.show_error_general(
                'Plotting: You did not choose a single Y axis to plot, try again!')
            return
        data = [[x, yn] for yn in y]
        label_y = None
        try:
            label_y = dataplot.axes['Y1']
        except KeyError:
            for key in dataplot.axes:
                try:
                    label_y = dataplot.axes[key]
                except KeyError:
                    pass

        legend_labels = [dataplot.axes[key]
                         for key in sorted(dataplot.axes) if key != 'X']
        if label_y is None:
            self.show_error_general(
                'Plotting: You did not choose a single Y axis to plot, try again!')
            return
        self.plotting_window_count += 1
        number = deepcopy(self.plotting_window_count)
        window = Window_plotting(data=data,
                                 label_x=dataplot.axes['X'],
                                 label_y=label_y,
                                 legend_labels=legend_labels,
                                 lock=self.dataLock_live,
                                 number=number)
        # print(type(window))
        window.sig_closing.connect(lambda:
                                   self.plotting_deleting_window(window, number))
        self.windows_plotting.append(window)
        window.show()

    def plotting_deleting_window(self, window, number):
        """delete the window entry in the list of windows
            was planned to fix the memory leak, not sure if it really works
        """
        for ct, w in enumerate(self.windows_plotting):
            if w.number == number:
                del self.windows_plotting[ct]

    def selection_y1(self, dataplot, livevsdb):
        dataplot.comboValue_Axis_Y1.addItems(tuple("-"))
        instrument_for_y1 = self.dataplot.comboInstr_Axis_Y1.currentText()

        axis = []
        if livevsdb == "LIVE":
            axis = list(self.data_live[instrument_for_y1])
        # elif livevsdb == "DB":
        #     self.mycursor.execute("SELECT * FROM {}".format(self.plotting_instrument_for_y1))
        #     colnames= self.mycursor.description
            # for row in colnames:
            #     axis.append(row[0])
        self.dataplot.comboValue_Axis_Y1.addItems(axis)
        self.dataplot.comboValue_Axis_Y1.activated.connect(self.y1_changed)

    def y1_changed(self):
        self.plotting_comboValue_Axis_Y1_plot = self.dataplot.comboValue_Axis_Y1.currentText()

    # gotta have an if statement for the case when x and y values are from
    # different tables
    def plotstart(self):
        print(self.plotting_comboValue_Axis_X_plot,
              self.plotting_comboValue_Axis_Y1_plot, self.plotting_instrument_for_x)
        array1 = []
        array2 = []
        if self.plotting_instrument_for_x == self.plotting_instrument_for_y1:
            sql = "SELECT {},{} from {} ".format(
                self.plotting_comboValue_Axis_X_plot, self.plotting_comboValue_Axis_Y1_plot, self.plotting_instrument_for_x)
            self.mycursor.execute(sql)
            data = self.mycursor.fetchall()

            for row in data:
                array1.append(list(row))

            # this is for is for omiting 'None' values from the array, skipping
            # this step would cause the plot to break!

            nparray = np.asarray(array1)[np.asarray(array1) != np.array(None)]

            # After renaming x to instrument_for_x and y1 to instrument_for_y1, the nparray became 1 dimensional, so the
            # original code:nparray_x = nparray[:,[0]] did not work, this is a workaround, i have no idea what caused it.
            # selecting different instruments for x and y doesn't have this
            # problem as the data is stored in separate arrays.

            nparray_x = nparray[0::2]
            nparray_y = nparray[1::2]

            plt.figure()
            plt.plot(nparray_x, nparray_y)
            # labels:
            plt.xlabel(self.plotting_comboValue_Axis_X_plot)
            plt.ylabel(self.plotting_comboValue_Axis_Y1_plot)

            plt.draw()

            plt.show()
        else:
            sql = "SELECT {} FROM {}".format(
                self.plotting_comboValue_Axis_X_plot, self.plotting_instrument_for_x)
            self.mycursor.execute(sql)
            data = self.mycursor.fetchall()

            for row in data:
                array1.append(list(row))
            nparray_x = np.asarray(
                array1)[np.asarray(array1) != np.array(None)]

            sql = "SELECT {} FROM {}".format(
                self.plotting_comboValue_Axis_Y1_plot, self.plotting_instrument_for_y1)
            self.mycursor.execute(sql)
            data = self.mycursor.fetchall()

            for row in data:
                array2.append(list(row))
            nparray_y = np.asarray(
                array2)[np.asarray(array2) != np.array(None)]

            # there can be still some problems if the dimensions don't match
            # so:
            if len(nparray_x) > len(nparray_y):
                nparray_x = nparray_x[0:len(nparray_y)]
            else:
                nparray_y = nparray_y[0:len(nparray_x)]

            plt.figure()
            plt.plot(nparray_x, nparray_y)
            # labels:
            plt.xlabel(self.plotting_comboValue_Axis_X_plot +
                       " from table: " + str(self.plotting_instrument_for_x))
            plt.ylabel(self.plotting_comboValue_Axis_Y1_plot +
                       " from table: " + str(self.plotting_instrument_for_y1))

            plt.draw()

            plt.show()

    # ------- Oxford Instruments
    # ------- ------- ITC
    def initialize_window_ITC(self):
        """initialize ITC Window"""
        self.ITC_window = Window_ui(ui_file='.\\Oxford\\ITC_control.ui')
        self.ITC_window.sig_closing.connect(
            lambda: self.action_show_ITC.setChecked(False))

        self.window_SystemsOnline.checkaction_run_ITC.clicked[
            'bool'].connect(self.run_ITC)
        self.action_show_ITC.triggered['bool'].connect(
            lambda value: self.show_window(self.ITC_window, value))
        # self.mdiArea.addSubWindow(self.ITC_window)

    @pyqtSlot(float)
    @noKeyError
    def ITC_fun_setTemp_valcha(self, value):
        self.threads['control_ITC'][0].gettoset_Temperature(value)

    @pyqtSlot()
    @noKeyError
    def ITC_fun_setTemp_edfin(self):
        self.threads['control_ITC'][0].setTemperature()

    @pyqtSlot(float)
    @noKeyError
    def ITC_fun_setRamp_valcha(self, value):
        self.threads['control_ITC'][0].gettoset_sweepRamp(value)

    @pyqtSlot()
    @noKeyError
    def ITC_fun_setRamp_edfin(self):
        self.threads['control_ITC'][0].setSweepRamp()

    @pyqtSlot(bool)
    def run_ITC(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""
        global Oxford
        O_ITC = reload(Oxford.ITC_control)
        ITC_Updater = O_ITC.ITC_Updater

        if boolean:
            try:
                # self.ITC = itc503('COM6')
                # getInfodata = cls_itc(self.ITC)
                getInfodata = self.running_thread_control(ITC_Updater(
                    ITC_Instrumentadress), 'ITC', 'control_ITC')

                getInfodata.sig_Infodata.connect(self.store_data_itc)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_general)
                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general('ITC: timeout'))

                # setting ITC values by GUI ITC window
                self.ITC_window.spinsetTemp.valueChanged.connect(
                    self.ITC_fun_setTemp_valcha)
                self.ITC_window.spinsetTemp.editingFinished.connect(
                    self.ITC_fun_setTemp_edfin)

                self.ITC_window.checkSweep.toggled['bool'].connect(
                    lambda value: getInfodata.setSweepStatus(value))

                self.ITC_window.dspinSetRamp.valueChanged.connect(
                    self.ITC_fun_setRamp_valcha)
                self.ITC_window.dspinSetRamp.editingFinished.connect(
                    self.ITC_fun_setRamp_edfin)

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
                        gas_new = self.threads['control_ITC'][0].set_gas_output
                        with self.dataLock:
                            gas_old = int(self.data['ITC']['gas_flow_output'])
                        if gas_new == 0:
                            time_wait = 60 / 1e2 * gas_old + 5
                            self.threads['control_ITC'][0].setGasOutput()

                            self.ITC_window.spinsetGasOutput.setEnabled(False)
                            time.sleep(time_wait)
                            self.ITC_window.spinsetGasOutput.setEnabled(True)
                        else:
                            time1 = 60 / 1e2 * gas_old + 5
                            time2 = 60 / 1e2 * gas_new + 5
                            self.threads['control_ITC'][
                                0].gettoset_GasOutput(0)
                            self.threads['control_ITC'][0].setGasOutput()
                            self.ITC_window.spinsetGasOutput.setEnabled(False)
                            time.sleep(time1)
                            self.threads['control_ITC'][
                                0].gettoset_GasOutput(gas_new)
                            self.threads['control_ITC'][0].setGasOutput()
                            time.sleep(time2)
                            self.ITC_window.spinsetGasOutput.setEnabled(True)
                    else:
                        self.threads['control_ITC'][0].setGasOutput()

                self.ITC_window.spinsetGasOutput.valueChanged.connect(
                    lambda value: getInfodata.gettoset_GasOutput(value))
                self.ITC_window.spinsetGasOutput.editingFinished.connect(
                    lambda: self.running_thread_tiny(Workerclass(change_gas, self)))

                self.ITC_window.spinsetHeaterPercent.valueChanged.connect(
                    lambda value: getInfodata.gettoset_HeaterOutput(value))
                self.ITC_window.spinsetHeaterPercent.editingFinished.connect(
                    lambda: getInfodata.setHeaterOutput())

                self.ITC_window.spinsetProportionalID.valueChanged.connect(
                    lambda value: getInfodata.gettoset_Proportional(value))
                self.ITC_window.spinsetProportionalID.editingFinished.connect(
                    lambda: getInfodata.setProportional())

                self.ITC_window.spinsetPIntegrationD.valueChanged.connect(
                    lambda value: getInfodata.gettoset_Integral(value))
                self.ITC_window.spinsetPIntegrationD.editingFinished.connect(
                    lambda: getInfodata.setIntegral())

                self.ITC_window.spinsetPIDerivative.valueChanged.connect(
                    lambda value: getInfodata.gettoset_Derivative(value))
                self.ITC_window.spinsetPIDerivative.editingFinished.connect(
                    lambda: getInfodata.setDerivative())

                self.ITC_window.combosetHeatersens.activated['int'].connect(
                    lambda value: getInfodata.setHeaterSensor(value + 1))

                self.ITC_window.combosetAutocontrol.activated['int'].connect(
                    lambda value: getInfodata.setAutoControl(value))

                self.ITC_window.spin_threadinterval.valueChanged.connect(
                    lambda value: getInfodata.setInterval(value))

                # thread.started.connect(getInfodata.work)
                # thread.start()
                self.window_SystemsOnline.checkaction_run_ITC.setChecked(True)
                self.logging_running_ITC = True
            except VisaIOError as e:
                self.window_SystemsOnline.checkaction_run_ITC.setChecked(False)
                self.show_error_general(e)
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
            self.window_SystemsOnline.checkaction_run_ITC.setChecked(False)
            self.logging_running_ITC = False

    # @pyqtSlot(bool)
    # def show_ITC(self, boolean):
    #     """display/close the ITC data & control window"""
    #     if boolean:
    #         self.ITC_window.show()
    #     else:
    #         self.ITC_window.close()

    @pyqtSlot(dict)
    def store_data_itc(self, data):
        """
            Calculate the rate of change of Temperature on the sensors [K/min]
            Store ITC data in self.data['ITC'], update ITC_window
        """

        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time()),
                    'SearchableTime': convert_time_searchable(time.time())}
        data.update(timedict)
        with self.dataLock:
            # print('storing: ', self.time_itc[-1]-time.time(), data['Sensor_1_K'])
            # self.time_itc.append(time.time())
            self.data['ITC'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained

            for key in self.data['ITC']:
                if self.data['ITC'][key] is None:
                    self.data['ITC'][key] = np.nan
            # if not self.data['ITC']['Sensor_1_K'] is None:
            self.ITC_window.lcdTemp_sens1_K.display(
                self.data['ITC']['Sensor_1_K'])
            # if not self.data['ITC']['Sensor_2_K'] is None:
            self.ITC_window.lcdTemp_sens2_K.display(
                self.data['ITC']['Sensor_2_K'])
            # if not self.data['ITC']['Sensor_3_K'] is None:
            self.ITC_window.lcdTemp_sens3_K.display(
                self.data['ITC']['Sensor_3_K'])

            # if not self.data['ITC']['set_temperature'] is None:
            self.ITC_window.lcdTemp_set.display(
                self.data['ITC']['set_temperature'])
            # if not self.data['ITC']['temperature_error'] is None:
            self.ITC_window.lcdTemp_err.display(
                self.data['ITC']['temperature_error'])
            # if not self.data['ITC']['heater_output_as_percent'] is None:
            try:
                self.ITC_window.progressHeaterPercent.setValue(
                    int(self.data['ITC']['heater_output_as_percent']))
                # if not self.data['ITC']['gas_flow_output'] is None:
                self.ITC_window.progressNeedleValve.setValue(
                    int(self.data['ITC']['gas_flow_output']))
            except ValueError:
                pass
            # if not self.data['ITC']['heater_output_as_voltage'] is None:
            self.ITC_window.lcdHeaterVoltage.display(
                self.data['ITC']['heater_output_as_voltage'])
            # if not self.data['ITC']['gas_flow_output'] is None:
            self.ITC_window.lcdNeedleValve_percent.display(
                self.data['ITC']['gas_flow_output'])
            # if not self.data['ITC']['proportional_band'] is None:
            self.ITC_window.lcdProportionalID.display(
                self.data['ITC']['proportional_band'])
            # if not self.data['ITC']['integral_action_time'] is None:
            self.ITC_window.lcdPIntegrationD.display(
                self.data['ITC']['integral_action_time'])
            # if not self.data['ITC']['derivative_action_time'] is None:
            self.ITC_window.lcdPIDerivative.display(
                self.data['ITC']['derivative_action_time'])

    # ------- ------- ILM
    def initialize_window_ILM(self):
        """initialize ILM Window"""
        self.ILM_window = Window_ui(ui_file='.\\Oxford\\ILM_control.ui')
        self.ILM_window.sig_closing.connect(
            lambda: self.action_show_ILM.setChecked(False))

        self.window_SystemsOnline.checkaction_run_ILM.clicked[
            'bool'].connect(self.run_ILM)
        self.action_show_ILM.triggered['bool'].connect(self.show_ILM)

    @pyqtSlot(bool)
    def run_ILM(self, boolean):
        """start/stop the Level Meter thread"""
        global Oxford
        O_ILM = reload(Oxford.ILM_control)
        ILM_Updater = O_ILM.ILM_Updater
        if boolean:
            try:
                getInfodata = self.running_thread_control(ILM_Updater(
                    InstrumentAddress=ILM_Instrumentadress), 'ILM', 'control_ILM')

                getInfodata.sig_Infodata.connect(self.store_data_ilm)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general('ILM: timeout'))

                self.ILM_window.combosetProbingRate_chan1.activated['int'].connect(
                    lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 1))
                # self.ILM_window.combosetProbingRate_chan2.activated['int'].connect(lambda value: self.threads['control_ILM'][0].setProbingSpeed(value, 2))

                self.ILM_window.spin_threadinterval.valueChanged.connect(
                    lambda value: self.threads['control_ILM'][0].setInterval(value))

                self.window_SystemsOnline.checkaction_run_ILM.setChecked(True)

            except VisaIOError as e:
                self.window_SystemsOnline.checkaction_run_ILM.setChecked(False)
                self.show_error_general(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.window_SystemsOnline.checkaction_run_ILM.setChecked(False)
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
        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time()),
                    'SearchableTime': convert_time_searchable(time.time())}
        data.update(timedict)
        with self.dataLock:
            # data['date'] = convert_time(time.time())
            self.data['ILM'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained
            chan1 = 100 if self.data['ILM'][
                'channel_1_level'] > 100 else self.data['ILM']['channel_1_level']
            chan2 = 100 if self.data['ILM'][
                'channel_2_level'] > 100 else self.data['ILM']['channel_2_level']
            self.ILM_window.progressLevelHe.setValue(chan1)
            self.ILM_window.progressLevelN2.setValue(chan2)

            self.ILM_window.lcdLevelHe.display(
                self.data['ILM']['channel_1_level'])
            self.ILM_window.lcdLevelN2.display(
                self.data['ILM']['channel_2_level'])

            self.MainDock_HeLevel.setValue(chan1)
            self.MainDock_N2Level.setValue(chan2)
            # print(self.data['ILM']['channel_1_level'], self.data['ILM']['channel_2_level'])

    # ------- ------- IPS
    def initialize_window_IPS(self):
        """initialize PS Window"""
        self.IPS_window = Window_ui(ui_file='.\\Oxford\\IPS_control.ui')
        self.IPS_window.sig_closing.connect(
            lambda: self.action_show_IPS.setChecked(False))

        self.window_SystemsOnline.checkaction_run_IPS.clicked[
            'bool'].connect(self.run_IPS)
        self.action_show_IPS.triggered['bool'].connect(self.show_IPS)

        self.IPS_window.labelStatusMagnet.setText('')
        self.IPS_window.labelStatusCurrent.setText('')
        self.IPS_window.labelStatusActivity.setText('')
        self.IPS_window.labelStatusLocRem.setText('')
        self.IPS_window.labelStatusSwitchHeater.setText('')

    @pyqtSlot(bool)
    def run_IPS(self, boolean):
        """start/stop the Powersupply thread"""
        global Oxford
        O_IPS = reload(Oxford.IPS_control)
        IPS_Updater = O_IPS.IPS_Updater

        if boolean:
            try:
                getInfodata = self.running_thread_control(IPS_Updater(
                    InstrumentAddress=IPS_Instrumentadress), 'IPS', 'control_IPS')

                getInfodata.sig_Infodata.connect(self.store_data_ips)
                # getInfodata.sig_visaerror.connect(self.printing)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general('IPS: timeout'))

                self.IPS_window.comboSetActivity.activated['int'].connect(
                    lambda value: self.threads['control_IPS'][0].setActivity(value))
                self.IPS_window.comboSetSwitchHeater.activated['int'].connect(
                    lambda value: self.threads['control_IPS'][0].setSwitchHeater(value))

                self.IPS_window.spinSetFieldSetPoint.valueChanged.connect(
                    lambda value: self.threads['control_IPS'][0].gettoset_FieldSetPoint(value))
                self.IPS_window.spinSetFieldSetPoint.editingFinished.connect(
                    lambda: self.threads['control_IPS'][0].setFieldSetPoint())

                self.IPS_window.spinSetFieldSweepRate.valueChanged.connect(
                    lambda value: self.threads['control_IPS'][0].gettoset_FieldSweepRate(value))
                self.IPS_window.spinSetFieldSweepRate.editingFinished.connect(
                    lambda: self.threads['control_IPS'][0].setFieldSweepRate())

                self.IPS_window.spin_threadinterval.valueChanged.connect(
                    lambda value: self.threads['control_IPS'][0].setInterval(value))

                self.window_SystemsOnline.checkaction_run_IPS.setChecked(True)

            except VisaIOError as e:
                self.window_SystemsOnline.checkaction_run_IPS.setChecked(False)
                self.show_error_general(e)
                # print(e) # TODO: open window displaying the error message
        else:
            self.window_SystemsOnline.checkaction_run_IPS.setChecked(False)
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
        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time()),
                    'SearchableTime': convert_time_searchable(time.time())}
        data.update(timedict)
        with self.dataLock:
            # data['date'] = convert_time(time.time())
            self.data['IPS'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained
            self.IPS_window.lcdFieldSetPoint.display(
                self.data['IPS']['FIELD_set_point'])
            self.IPS_window.lcdFieldSweepRate.display(
                self.data['IPS']['FIELD_sweep_rate'])

            self.IPS_window.lcdOutputField.display(
                self.data['IPS']['FIELD_output'])
            self.IPS_window.lcdMeasuredMagnetCurrent.display(
                self.data['IPS']['measured_magnet_current'])
            self.IPS_window.lcdOutputCurrent.display(
                self.data['IPS']['CURRENT_output'])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_set_point'])
            # self.IPS_window.lcdXXX.display(self.data['IPS']['CURRENT_sweep_rate'])

            self.IPS_window.lcdLeadResistance.display(
                self.data['IPS']['lead_resistance'])

            self.IPS_window.lcdPersistentMagnetField.display(
                self.data['IPS']['persistent_magnet_field'])
            self.IPS_window.lcdTripField.display(
                self.data['IPS']['trip_field'])
            self.IPS_window.lcdPersistentMagnetCurrent.display(
                self.data['IPS']['persistent_magnet_current'])
            self.IPS_window.lcdTripCurrent.display(
                self.data['IPS']['trip_current'])

            self.IPS_window.labelStatusMagnet.setText(
                self.data['IPS']['status_magnet'])
            self.IPS_window.labelStatusCurrent.setText(
                self.data['IPS']['status_current'])
            self.IPS_window.labelStatusActivity.setText(
                self.data['IPS']['status_activity'])
            self.IPS_window.labelStatusLocRem.setText(
                self.data['IPS']['status_locrem'])
            self.IPS_window.labelStatusSwitchHeater.setText(
                self.data['IPS']['status_switchheater'])

    # ------- LakeShore 350 -------
    def initialize_window_LakeShore350(self):
        """initialize LakeShore Window"""
        self.LakeShore350_window = Window_ui(
            ui_file='.\\LakeShore\\LakeShore350_control.ui')
        self.LakeShore350_window.sig_closing.connect(
            lambda: self.action_show_LakeShore350.setChecked(False))

        # self.LakeShore350_window.textSensor1_Kpmin.setAlignment(QtAlignRight)

        self.window_SystemsOnline.checkaction_run_LakeShore350.clicked[
            'bool'].connect(self.run_LakeShore350)
        self.action_show_LakeShore350.triggered[
            'bool'].connect(self.show_LakeShore350)
        self.LakeShore350_Kpmin = None

    @pyqtSlot(bool)
    def run_LakeShore350(self, boolean):
        """start/stop the LakeShore350 thread"""
        global LakeShore
        LC = reload(LakeShore.LakeShore350_Control)
        LakeShore350_Updater = LC.LakeShore350_Updater

        if boolean:
            try:
                getInfodata = self.running_thread_control(LakeShore350_Updater(
                    InstrumentAddress=LakeShore_InstrumentAddress), 'LakeShore350', 'control_LakeShore350')

                getInfodata.sig_Infodata.connect(self.store_data_LakeShore350)
                # getInfodata.sig_visaerror.connect(self.printing)
                getInfodata.sig_visaerror.connect(self.show_error_general)
                # getInfodata.sig_assertion.connect(self.printing)
                getInfodata.sig_assertion.connect(self.show_error_general)

                getInfodata.sig_visatimeout.connect(
                    lambda: self.show_error_general('LakeShore350: timeout'))

                # self.func_LakeShore350_setKpminLength(5)

                # setting LakeShore values by GUI LakeShore window
                self.LakeShore350_window.spinSetTemp_K.valueChanged.connect(
                    lambda value: self.threads['control_LakeShore350'][0].gettoset_Temp_K(value))
                self.LakeShore350_window.spinSetTemp_K.editingFinished.connect(
                    lambda: self.threads['control_LakeShore350'][0].setTemp_K())

                self.LakeShore350_window.spinSetRampRate_Kpmin.valueChanged.connect(
                    lambda value: self.threads['control_LakeShore350'][0].gettoset_Ramp_Rate_K(value))
                self.LakeShore350_window.spinSetRampRate_Kpmin.editingFinished.connect(
                    lambda: self.threads['control_LakeShore350'][0].setRamp_Rate_K())

                # allows to choose from different inputs to connect to output 1
                # control loop. default is input 1.

                self.LakeShore350_window.comboSetInput_Sensor.activated['int'].connect(
                    lambda value: self.threads['control_LakeShore350'][0].setInput(value + 1))
                # self.LakeShore350_window.spinSetInput_Sensor.editingFinished.(lambda
                # value: self.threads['control_LakeShore350'][0].setInput())

                self.LakeShore350_window.checkRamp_Status.toggled['bool'].connect(
                    lambda value: self.threads['control_LakeShore350'][0].setStatusRamp(value))

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

                self.LakeShore350_window.spin_threadinterval.valueChanged.connect(
                    lambda value: self.threads['control_LakeShore350'][0].setInterval(value))

                self.window_SystemsOnline.checkaction_run_LakeShore350.setChecked(
                    True)

            except VisaIOError as e:
                self.window_SystemsOnline.checkaction_run_LakeShore350.setChecked(
                    False)
                self.show_error_general('running: {}'.format(e))
        else:
            self.window_SystemsOnline.checkaction_run_LakeShore350.setChecked(
                False)
            self.stopping_thread('control_LakeShore350')

            self.LakeShore350_window.spinSetTemp_K.valueChanged.disconnect()
            self.LakeShore350_window.spinSetTemp_K.editingFinished.disconnect()
            self.LakeShore350_window.spinSetRampRate_Kpmin.valueChanged.disconnect()
            self.LakeShore350_window.spinSetRampRate_Kpmin.editingFinished.disconnect()
            self.LakeShore350_window.comboSetInput_Sensor.activated[
                'int'].disconnect()

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

        slopes = ['Sensor_1_K_calc_slope', 'Sensor_2_K_calc_slope',
                  'Sensor_3_K_calc_slope', 'Sensor_4_K_calc_slope']

        # coeffs, data = self.calculate_Kpmin(data)
        try:
            with self.dataLock_live:
                if any([self.data_live['LakeShore350'][value]
                        for value in slopes]):
                    livedata = [self.data_live['LakeShore350'][value][-1]
                                for value in slopes]
                else:
                    livedata = [0] * 4
        except AttributeError:
            self.show_error_general(
                'please start live logging for LakeShore350 slope values!')
            livedata = [0] * 4
        except KeyError:
            self.show_error_general(
                'please start live logging for LakeShore350 slope values!')
            livedata = [0] * 4

        for GUI_element, co in zip([self.LakeShore350_window.textSensor1_Kpmin,
                                    self.LakeShore350_window.textSensor2_Kpmin,
                                    self.LakeShore350_window.textSensor3_Kpmin,
                                    self.LakeShore350_window.textSensor4_Kpmin],
                                   livedata):
            if not co == 0:
                GUI_element.setText('{num:=+10.4f}'.format(num=co))

        # data['date'] = convert_time(time.time())
        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time()),
                    'SearchableTime': convert_time_searchable(time.time())}
        data.update(timedict)
        with self.dataLock:
            self.data['LakeShore350'].update(data)
            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained

            self.LakeShore350_window.progressHeaterOutput_percentage.setValue(
                self.data['LakeShore350']['Heater_Output_percentage'])
            self.LakeShore350_window.lcdHeaterOutput_mW.display(
                self.data['LakeShore350']['Heater_Output_mW'])
            self.LakeShore350_window.lcdSetTemp_K.display(
                self.data['LakeShore350']['Temp_K'])
            # self.LakeShore350_window.lcdRampeRate_Status.display(self.data['LakeShore350']['RampRate_Status'])
            self.LakeShore350_window.lcdSetRampRate_Kpmin.display(
                self.data['LakeShore350']['Ramp_Rate'])

            self.LakeShore350_window.comboSetInput_Sensor.setCurrentIndex(
                int(self.data['LakeShore350']['Input_Sensor']) - 1)
            self.LakeShore350_window.lcdSensor1_K.display(
                self.data['LakeShore350']['Sensor_1_K'])
            self.LakeShore350_window.lcdSensor2_K.display(
                self.data['LakeShore350']['Sensor_2_K'])
            self.LakeShore350_window.lcdSensor3_K.display(
                self.data['LakeShore350']['Sensor_3_K'])
            self.LakeShore350_window.lcdSensor4_K.display(
                self.data['LakeShore350']['Sensor_4_K'])

            """NEW GUI to display P,I and D Parameters
            """
            # self.LakeShore350_window.lcdLoopP_Param.display(self.data['LakeShore350']['Loop_P_Param'])
            # self.LakeShore350_window.lcdLoopI_Param.display(self.data['LakeShore350']['Loop_I_Param'])
            # self.LakeShore350_window.lcdLoopD_Param.display(self.data['LakeShore350']['Loop_D_Param'])

            # self.LakeShore350_window.lcdHeater_Range.display(self.date['LakeShore350']['Heater_Range'])

   # ------- Keithley 2182 + Keithley 6221 -------
    def initialize_window_Keithley(self):
        """initialize Keithley Window"""
        self.Keithley_window = Window_ui(
            ui_file='.\\Keithley\\Keithley_control.ui')
        self.Keithley_window.sig_closing.connect(
            lambda: self.action_show_Keithley.setChecked(False))

        # -------- Nanovoltmeters
        confdict2182_1 = dict(clas=Keithley.Keithley2182_Control.Keithley2182_Updater,
                              instradress=Keithley2182_1_InstrumentAddress,
                              dataname='Keithley2182_1',
                              threadname='control_Keithley2182_1',
                              GUI_number1=self.Keithley_window.lcdSensor1_V,
                              GUI_menu_action=self.window_SystemsOnline.checkaction_run_Nanovolt_1,
                              GUI_Box=self.Keithley_window.comboBox_1,
                              GUI_Display=self.Keithley_window.lcdResistance1,
                              GUI_CBox_Autozero=self.Keithley_window.checkBox_Autozero_1,
                              GUI_CBox_FronAutozero=self.Keithley_window.checkBox_FrontAutozero_1,
                              GUI_CBox_Display=self.Keithley_window.checkBox_Display_1,
                              GUI_CBox_Autorange=self.Keithley_window.checkBox_Autorange_1)

        confdict2182_2 = dict(clas=Keithley.Keithley2182_Control.Keithley2182_Updater,
                              instradress=Keithley2182_2_InstrumentAddress,
                              dataname='Keithley2182_2',
                              threadname='control_Keithley2182_2',
                              GUI_number1=self.Keithley_window.lcdSensor2_V,
                              GUI_menu_action=self.window_SystemsOnline.checkaction_run_Nanovolt_2,
                              GUI_Box=self.Keithley_window.comboBox_2,
                              GUI_Display=self.Keithley_window.lcdResistance2,
                              GUI_CBox_Autozero=self.Keithley_window.checkBox_Autozero_2,
                              GUI_CBox_FronAutozero=self.Keithley_window.checkBox_FrontAutozero_2,
                              GUI_CBox_Display=self.Keithley_window.checkBox_Display_2,
                              GUI_CBox_Autorange=self.Keithley_window.checkBox_Autorange_2)

        confdict2182_3 = dict(clas=Keithley.Keithley2182_Control.Keithley2182_Updater,
                              instradress=Keithley2182_3_InstrumentAddress,
                              dataname='Keithley2182_3',
                              threadname='control_Keithley2182_3',
                              GUI_number1=self.Keithley_window.lcdSensor3_V,
                              GUI_menu_action=self.window_SystemsOnline.checkaction_run_Nanovolt_3,
                              GUI_Box=self.Keithley_window.comboBox_3,
                              GUI_Display=self.Keithley_window.lcdResistance3,
                              GUI_CBox_Autozero=self.Keithley_window.checkBox_Autozero_3,
                              GUI_CBox_FronAutozero=self.Keithley_window.checkBox_FrontAutozero_3,
                              GUI_CBox_Display=self.Keithley_window.checkBox_Display_3,
                              GUI_CBox_Autorange=self.Keithley_window.checkBox_Autorange_3)

        # -------- Current Sources
        confdict6221_1 = dict(clas=Keithley.Keithley6221_Control.Keithley6221_Updater,
                              instradress=Keithley6221_1_InstrumentAddress,
                              dataname='Keithley6221_1',
                              threadname='control_Keithley6221_1',
                              GUI_number2=self.Keithley_window.spinSetCurrent1_A,
                              GUI_push=self.Keithley_window.pushToggleOut_1,
                              GUI_menu_action=self.window_SystemsOnline.checkaction_run_Current_1)

        confdict6221_2 = dict(clas=Keithley.Keithley6221_Control.Keithley6221_Updater,
                              instradress=Keithley6221_2_InstrumentAddress,
                              dataname='Keithley6221_2',
                              threadname='control_Keithley6221_2',
                              GUI_number2=self.Keithley_window.spinSetCurrent2_A,
                              GUI_push=self.Keithley_window.pushToggleOut_2,
                              GUI_menu_action=self.window_SystemsOnline.checkaction_run_Current_2)

        self.window_SystemsOnline.checkaction_run_Nanovolt_1.clicked['bool'].connect(
            lambda value: self.run_Keithley(value, **confdict2182_1))
        self.window_SystemsOnline.checkaction_run_Nanovolt_2.clicked['bool'].connect(
            lambda value: self.run_Keithley(value, **confdict2182_2))
        self.window_SystemsOnline.checkaction_run_Nanovolt_3.clicked['bool'].connect(
            lambda value: self.run_Keithley(value, **confdict2182_3))

        self.window_SystemsOnline.checkaction_run_Current_1.clicked['bool'].connect(
            lambda value: self.run_Keithley(value, **confdict6221_1))
        self.window_SystemsOnline.checkaction_run_Current_2.clicked['bool'].connect(
            lambda value: self.run_Keithley(value, **confdict6221_2))

        self.action_show_Keithley.triggered['bool'].connect(self.show_Keithley)

    @pyqtSlot(bool)
    def run_Keithley(self, boolean, clas, instradress, dataname, threadname, GUI_menu_action, **kwargs):
        """start/stop the Keithley thread"""
        global Keithley
        # global Keithley6221_Updater
        # global Keithley2182_Updater
        K_2182 = reload(Keithley.Keithley2182_Control)
        K_6221 = reload(Keithley.Keithley6221_Control)

        if 'GUI_number2' in kwargs:
            clas = K_6221.Keithley6221_Updater
        else:
            clas = K_2182.Keithley2182_Updater

        if boolean:
            try:
                worker = self.running_thread_control(
                    clas(InstrumentAddress=instradress), dataname, threadname)
                kwargs['threadname'] = threadname
                worker.sig_Infodata.connect(
                    lambda data: self.store_data_Keithley(data, dataname, **kwargs))
                worker.sig_visaerror.connect(self.show_error_general)
                worker.sig_assertion.connect(self.show_error_general)
                worker.sig_visatimeout.connect(
                    lambda: self.show_error_general('{0:s}: timeout'.format(dataname)))

                # display data given by nanovoltmeters & calculate resistance

                # setting values for nanovoltmeters
                if 'GUI_number1' in kwargs:
                    kwargs['GUI_CBox_Display'].toggled['bool'].connect(
                        lambda value: self.threads[threadname][0].ToggleDisplay(value))
                    kwargs['GUI_CBox_Autozero'].toggled['bool'].connect(
                        lambda value: self.threads[threadname][0].ToggleAutozero(value))
                    kwargs['GUI_CBox_FronAutozero'].toggled['bool'].connect(
                        lambda value: self.threads[threadname][0].ToggleFrontAutozero(value))
                    kwargs['GUI_CBox_Autorange'].toggled['bool'].connect(
                        lambda value: self.threads[threadname][0].ToggleAutorange(value))

                # setting values for current source

                # setting Keithley values for current source by GUI Keithley
                # window

                if 'GUI_number2' in kwargs:
                    kwargs['GUI_number2'].valueChanged.connect(
                        lambda value: self.threads[threadname][0].gettoset_Current_A(value))
                    kwargs['GUI_number2'].editingFinished.connect(
                        lambda: self.threads[threadname][0].setCurrent_A())
                    kwargs['GUI_number2'].editingFinished.connect(lambda: self.store_data_Keithley(
                        dict(changed_Current_A=self.threads[threadname][0].getCurrent_A()), dataname))

                    if not self.threads[threadname][0].OutputOn:
                        # 'correct', as this reads
                        kwargs['GUI_push'].setText('Output ON')
                        # enable
                    if self.threads[threadname][0].OutputOn:
                        # 'correct', as this reads
                        kwargs['GUI_push'].setText('Output OFF')

                    kwargs['GUI_push'].clicked.connect(lambda: self.Keithley_toggleOutput(
                        kwargs['GUI_push'], self.threads[threadname][0]))
                    kwargs['GUI_push'].setEnabled(True)

                GUI_menu_action.setChecked(True)

            except VisaIOError as e:
                GUI_menu_action.setChecked(False)
                self.show_error_general('running: {}'.format(e))
        else:
            GUI_menu_action.setChecked(False)
            self.stopping_thread(threadname)

            if 'GUI_number2' in kwargs:
                kwargs['GUI_number2'].valueChanged.disconnect()
                kwargs['GUI_number2'].editingFinished.disconnect()

            if 'GUI_push' in kwargs:
                kwargs['GUI_push'].clicked.disconnect()
                # kwargs['GUI_push'].setText('Output ON')
                kwargs['GUI_push'].setEnabled(False)

    @pyqtSlot()
    def Keithley_toggleOutput(self, GUI_Button, worker):
        worker.OutputOn = worker.getstatus()
        if not worker.OutputOn:
            worker.enable()
            GUI_Button.setText('Output OFF')  # ''reversed'', as this toggles!
            # enable
        elif worker.OutputOn:
            worker.disable()
            GUI_Button.setText('Output ON')  # ''reversed'', as this toggles!

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
        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time()),
                    'SearchableTime': convert_time_searchable(time.time())}
        data.update(timedict)
        with self.dataLock:
            self.data[dataname].update(data)

            # this needs to draw from the self.data['INSTRUMENT'] so that in case one of the keys did not show up,
            # since the command failed in the communication with the device,
            # the last value is retained
            if 'GUI_number1' in kwargs:
                try:
                    if not str(kwargs['GUI_Box'].currentText()) == '--':
                        self.data[dataname]['Resistance_Ohm'] = self.data[dataname][
                            'Voltage_V'] / (self.data[str(kwargs['GUI_Box'].currentText()).strip(')').split('(')[1]]['Current_A'])
                    kwargs['GUI_number1'].display(
                        self.data[dataname]['Voltage_V'])
                    if 'Resistance_Ohm' in self.data[dataname]:
                        kwargs['GUI_Display'].display(
                            self.data[dataname]['Resistance_Ohm'])
                except AttributeError as a_err:
                    if not a_err.args[0] == "'NoneType' object has no attribute 'display'":
                        self.show_error_general('{name}: {err}'.format(
                            name=dataname, err=a_err.args[0]))
                except KeyError as key_err:
                    self.show_error_general('{name}: {err}'.format(
                        name=dataname, err=key_err.args[0]))
                except ZeroDivisionError as z_err:
                    self.data[dataname]['Resistance_Ohm'] = np.nan

    # ------- MISC -------

    def printing(self, b):
        """arbitrary example function"""
        print(b)

    def initialize_window_Log_conf(self):
        """initialize Logging configuration window"""
        self.Log_conf_window = Logger_configuration()
        self.Log_conf_window.sig_closing.connect(
            lambda: self.action_Logging_configuration.setChecked(False))
        self.Log_conf_window.sig_send_conf.connect(
            lambda conf: self.sig_logging_newconf.emit(conf))

        self.window_SystemsOnline.checkaction_Logging.toggled[
            'bool'].connect(self.run_logger)
        self.action_Logging_configuration.triggered[
            'bool'].connect(self.show_logging_configuration)

    @pyqtSlot(bool)
    def run_logger(self, boolean):
        """start/stop the logging thread"""

        # read the last configuration of what shall be logged from a respective
        # file

        if boolean:
            logger = self.running_thread_control(
                main_Logger(self), None, 'logger')
            # logger.sig_log.connect(self.logging_send_all)
            logger.sig_log.connect(
                lambda: self.sig_logging.emit(deepcopy(self.data)))
            logger.sig_configuring.connect(self.show_logging_configuration)
            self.logging_running_logger = True

        else:
            self.stopping_thread('logger')
            self.logging_running_logger = False

    @pyqtSlot()
    def logging_send_all(self):
        newdata = deepcopy(self.data)
        newdata.update(deepcopy(self.data_live))
        # print(newdata)
        self.sig_logging.emit(newdata)

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
                live_Logger(self), None, 'control_Logging_live')
            getInfodata.sig_assertion.connect(self.show_error_general)

            self.actionLogging_LIVE.setChecked(True)
            print('logging live online')
            # except VisaIOError as e:
            #     self.actionLogging_LIVE.setChecked(False)
            #     self.show_error_general(e)
            # print(e) # TODO: open window displaying the error message

        else:
            self.stopping_thread('control_Logging_live')
            self.actionLogging_LIVE.setChecked(False)
            self.data_live = dict()

    def initialize_window_OneShot(self):
        self.window_OneShot = Window_ui(
            # ui_file='.\\configurations\\OneShotMeasurement.ui')
            ui_file='.\\configurations\\OneShotMeasurement_multichannel.ui')

        # self.window_OneShot.pushChoose_Datafile.connect()
        # self.window_OneShot.comboCurrentSource.addItems([])
        self.window_OneShot.commandMeasure.setEnabled(False)

        self.window_SystemsOnline.checkaction_run_OneShot_Measuring.clicked[
            'bool'].connect(self.run_OneShot)
        self.action_show_OneShot_Measuring.triggered[
            'bool'].connect(self.show_OneShot)

    @pyqtSlot(bool)
    def run_OneShot(self, boolean):
        if boolean:

            OneShot = self.running_thread_control(
                OneShot_Thread_multichannel(self), 'measured', 'control_OneShot')
            OneShot.sig_assertion.connect(self.OneShot_errorHandling)

            self.window_OneShot.dspinExcitationCurrent_1_A.valueChanged.connect(
                lambda value: OneShot.update_exc(1, value))
            self.window_OneShot.dspinExcitationCurrent_2_A.valueChanged.connect(
                lambda value: OneShot.update_exc(2, value))

            self.window_OneShot.dspinIVstart.valueChanged.connect(
                lambda value: OneShot.update_iv(0, value))
            self.window_OneShot.dspinIVstop.valueChanged.connect(
                lambda value: OneShot.update_iv(1, value))
            self.window_OneShot.spinIVsteps.valueChanged.connect(
                lambda value: OneShot.update_iv(2, value))

            self.window_OneShot.commandMeasure.setEnabled(True)
            self.window_OneShot.commandStartSeries.setEnabled(True)
            self.window_OneShot.commandStopSeries.setEnabled(True)

            self.logging_timer = QTimer()
            self.logging_timer.timeout.connect(
                lambda: self.sig_measure_oneshot.emit())

            self.window_OneShot.commandMeasure.clicked.connect(
                lambda: self.sig_measure_oneshot.emit())
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

            self.window_OneShot.dspinInterval_s.valueChanged.connect(
                lambda value: OneShot.update_conf('interval', value))

            self.window_OneShot.pushChoose_Datafile.clicked.connect(
                lambda: self.OneShot_chooseDatafile(OneShot))

            self.running_thread_control(
                measurement_Logger(self), None, 'save_OneShot')
            OneShot.sig_storing.connect(
                lambda value: self.sig_log_measurement.emit(value))
            # this is for saving the respective data
        else:
            self.stopping_thread('control_OneShot')
            self.stopping_thread('save_OneShot')
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
        '''
            get the timer seconds, change the state to "running", start the timer
            this can only be invoked in case the control thread is working:
                the button is otherwise disabled
        '''
        sec = self.threads['control_OneShot'][0].conf['interval']
        msec = sec * 1e3
        green = QtGui.QColor(0, 255, 0)
        self.logging_timer.start(msec)
        self.window_OneShot.textrunning.setText('Running')
        self.window_OneShot.textrunning.setTextColor(green)
        self.window_OneShot.textinterval.setText(
            '{0:.2f} s ({1:.2f} min)'.format(sec, sec / 60))

    def OneShot_stop(self):
        '''stop the timer, change the state to "stopped" '''
        blue = QtGui.QColor(0, 0, 255)
        self.logging_timer.stop()
        self.window_OneShot.textrunning.setText('Stopped')
        self.window_OneShot.textrunning.setTextColor(blue)

    def OneShot_chooseDatafile(self, OneShot):
        try:
            current_file_data = OneShot.conf['datafile']
        except KeyError:
            current_file_data = 'c:/'
        new_file_data, __ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                                  'Choose Datafile',
                                                                  current_file_data,
                                                                  "Datafiles (*.dat)")

        OneShot.update_conf('datafile', new_file_data)
        self.window_OneShot.lineDatafileLocation.setText(new_file_data)
        # print(OneShot)

    def OneShot_errorHandling(self, errortext):
        if 'Key' in errortext:
            if any(x in errortext for x in ['None', 'Keithley']):
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

    def initialize_window_Errors(self):
        """initialize Error Window"""
        self.Errors_window = Window_ui(ui_file='.\\configurations\\Errors.ui')
        self.Errors_window.sig_closing.connect(
            lambda: self.action_show_Errors.setChecked(False))

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
    form = mainWindow(app=app)
    form.show()
    print(time.time() - a)
    sys.exit(app.exec_())
