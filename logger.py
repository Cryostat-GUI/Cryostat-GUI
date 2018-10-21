

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets

# import sys
import datetime
import time
import pickle
import os
import sqlite3
import numpy as np
from copy import deepcopy
import math


from util import AbstractLoopThread
from util import Window_ui

from sqlite3 import OperationalError


def SQLFormatting(variable):
    if isinstance(variable, (float, int)):
        return variable
    else:
        return f"""'{variable}'"""


def typeof(dictkey):
    if isinstance(dictkey,float):
        return "REAL"
    elif isinstance(dictkey,int):
        return "INTEGER"
    else:
        return "TEXT"


def sql_buildDictTableString(dictname):
    string = '''(id INTEGER PRIMARY KEY'''
    for key in dictname.keys():
        string += ''',{key} {typ}'''.format(key=key, typ=typeof(dictname[key]))
    string += ''')'''
    return string


def change_to_correct_types(tablename, dictname):
    sql = []
    if not dictname:
        raise AssertionError('Logger: dict does not yet exist')
    sql.append('''PRAGMA foreign_keys = 0''')
    sql.append('''CREATE TABLE python_temp_{table} AS SELECT * FROM {table}'''.format(table=tablename))
    sql.append('''DROP TABLE {table}'''.format(table=tablename))
    # sql.append("CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY)".format(tablename))
    sql.append('''CREATE TABLE IF NOT EXISTS {} '''.format(tablename) + sql_buildDictTableString(dictname))
    # for key in dictname.keys():
    #     sql.append("ALTER TABLE  {} ADD COLUMN {} {}".format(tablename,key,typeof(dictname[key])))

    sql_temp = '''INSERT INTO {table} (id'''.format(table=tablename)
    for key in dictname.keys():
        sql_temp += ',{}'.format(key)
    sql_temp += ''') SELECT id'''
    for key in dictname.keys():
        sql_temp += ''',{}'''.format(key)
    sql_temp += ''' FROM python_temp_{table}'''.format(table=tablename)
    sql.append(sql_temp)
    sql.append('''DROP TABLE python_temp_{table}'''.format(table=tablename))
    sql.append('''PRAGMA foreign_keys = 1''')
    return sql


def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


class Logger_configuration(Window_ui):
    """docstring for Logger_configuration"""

    sig_send_conf = pyqtSignal(dict)

    ITC_sensors = dict(
        set_temperature = False,
        sensor_1_temperature = False,
        sensor_2_temperature = False,
        sensor_3_temperature = False,
        temperature_error = False,
        heater_output_as_percent = False,
        heater_output_as_voltage = False,
        gas_flow_output = False,
        proportional_band = False,
        integral_action_time = False,
        derivative_action_time = False)

    def __init__(self, parent=None, **kwargs):
        super(Logger_configuration, self).__init__(ui_file='.\\configurations\\Logger_conf.ui', **kwargs)

        self.read_configuration()

        self.general_threads_ITC.toggled.connect(lambda value: self.setValue('ITC', 'thread', value))
        self.general_threads_ITC.toggled.connect(lambda b: self.ITC_thread_running.setChecked(b))
        self.general_threads_ILM.toggled.connect(lambda value: self.setValue('ILM', 'thread', value))
        self.general_threads_ILM.toggled.connect(lambda b: self.ILM_thread_running.setChecked(b))
        self.general_threads_PS.toggled.connect(lambda value: self.setValue('PS', 'thread', value))
        self.general_threads_PS.toggled.connect(lambda b: self.PS_thread_running.setChecked(b))
        self.general_threads_Lakeshore350.toggled.connect(lambda value: self.setValue('Lakeshore350', 'thread', value))
        self.general_threads_Lakeshore350.toggled.connect(lambda b: self.Lakeshore350_thread_running.setChecked(b))
        self.general_spinSetInterval.valueChanged.connect(lambda value: self.setValue('general','interval', value) )

        # self.general_threads_Current1.toggled.connect(lambda value: self.setValue('Current1', 'thread', value))
        # self.general_threads_Current1.toggled.connect(lambda b: self.Current1_thread_running.setChecked(b))
        # self.general_threads_Current2.toggled.connect(lambda value: self.setValue('Current2', 'thread', value))
        # self.general_threads_Current2.toggled.connect(lambda b: self.Current2_thread_running.setChecked(b))
        # self.general_threads_Nano1.toggled.connect(lambda value: self.setValue('Nano1', 'thread', value))
        # self.general_threads_Nano1.toggled.connect(lambda b: self.Nano1_thread_running.setChecked(b))
        # self.general_threads_Nano2.toggled.connect(lambda value: self.setValue('Nano2', 'thread', value))
        # self.general_threads_Nano2.toggled.connect(lambda b: self.Nano2_thread_running.setChecked(b))
        # self.general_threads_Nano3.toggled.connect(lambda value: self.setValue('Nano3', 'thread', value))

        # self.general_threads_Nano3.toggled.connect(lambda b: self.Nano3_thread_running.setChecked(b))

        self.pushBrowseFileLocation.clicked.connect(self.window_FileDialogSave)

        self.buttonBox_finish.accepted.connect(lambda: self.sig_send_conf.emit(deepcopy(self.conf)))
        self.buttonBox_finish.accepted.connect(self.close_and_safe)
        self.buttonBox_finish.rejected.connect(self.close)


    def close_and_safe(self):
        """save the configuration dict to a file, close the window afterwards"""
        self.sig_send_conf.emit(self.conf)
        with open('configurations/log_conf.pickle', 'wb') as handle:
            pickle.dump(self.conf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        self.close()


    def setValue(self, instrument, value, bools):
        """set a bool value according to the instrument and specific"""
        self.conf[instrument][value] = bools

    def initialise_dicts(self):
        """initialise the conf dict, in case it was not handed down
            return the empty conf dict
        """

        self.ITC_sensors.update(dict(thread=False))
        conf = dict()
        conf['ITC'] = self.ITC_sensors
        conf['ILM'] = dict()
        conf['PS'] = dict()
        conf['Lakeshore350'] = dict()
        conf['Keithley Current']  = dict()
        conf['Keithley Volt']   = dict()
        conf['general'] = dict(logfile_location='', interval=2)
        return conf

    def read_configuration(self):
        '''search for configuration file, load it if found, initialise new dict if not found'''
        configurations = os.listdir(r'.\\configurations')
        if 'log_conf.pickle' in configurations:
            with open('configurations/log_conf.pickle', 'rb') as handle:
                self.conf = pickle.load(handle)
        else:
            self.conf = self.initialise_dicts()


    def window_FileDialogSave(self):
        dbname, __ = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose Database File Location',
           'c:\\',"Database Files - SQLite3 (*.db)")
        self.lineFilelocation.setText(dbname)
        self.setValue('general', 'logfile_location', dbname)


class main_Logger(AbstractLoopThread):
    """This is a the logging worker thread
    """

    sig_configuring = pyqtSignal(bool)
    sig_log = pyqtSignal()


    def __init__(self, mainthread, **kwargs):
        super().__init__(**kwargs)
        self.mainthread = mainthread

        self.interval = 5 # 5s interval for logging as initialisation


        self.mainthread.sig_logging.connect(self.store_data)
        self.mainthread.sig_logging_newconf.connect(self.update_conf)

        QTimer.singleShot(5e2, lambda: self.sig_configuring.emit(True))
        self.configuration_done = False
        self.conf_done_layer2 = False

        # self.dbname = 'He_first_cooldown.db'

        # QTimer.singleShot(1e3, self.initialise)
        self.not_yet_initialised = False

    def running(self):

        try:
            # print('logging running')
            if self.configuration_done:
                self.sig_log.emit()
                if not self.conf_done_layer2:
                    self.sig_configuring.emit(False)
                    self.conf_done_layer2 = True

        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])

    def update_conf(self, conf):
        """
            - update the configuration with one being sent.
            - set the configuration done bool to True,
                so that self.running will actually log
            - set self.conf_done_layer2 to False,
                so that the configuring thread will be quit.

        """
        self.conf = conf
        self.interval = self.conf['general']['interval']
        self.configuration_done = True
        self.conf_done_layer2 = False

    def connectdb(self, dbname):
        """connect to the sqlite database"""
        try:
            self.conn = sqlite3.connect(dbname)
        except sqlite3.connect.Error as err:
            raise AssertionError("Logger: Couldn't establish connection {}".format(err))

    def createtable(self,tablename,dictname):
        """create the sql table if it does not exist,
            with all columns named after the keys in the dictionary
        """

        sql="CREATE TABLE IF NOT EXISTS {} ".format(tablename)
        sql += sql_buildDictTableString(dictname)
        self.mycursor.execute(sql)

        #We should try to find a nicer a solution without try and except
        # #try:
        for key in dictname.keys():
            try:
                sql = """ALTER TABLE  {} ADD COLUMN {} {}""".format(tablename,key,dictname[key])
                self.mycursor.execute(sql)
            except OperationalError as err:
                pass  # Logger: probably the column already exists, no problem.
        #         # self.sig_assertion.emit("Logger: probably the column already exists, no problem. ({})".format(err))

    def updatetable(self, tablename, dictname):
        """insert a new row into the database table with all data
            a table-updating scheme was chosen to loop through all key-value pairs,
            instead of an approach where the sql command-string is built in the loop
            thus:
                - insert a new row into the database table with the time
                - loop through the dict
                    - update the newly made row with the key-value pair of the dict in the loop
        """
        # print('ichi update')
        if not dictname:
            # print('no column like this!!!')
            raise AssertionError('Logger: dict does not yet exist')
        sql = """INSERT INTO {} ({}) VALUES ({})""".format(tablename, 'timeseconds', dictname['timeseconds'])
        self.mycursor.execute(sql)

        # for key in dictname.keys():
        #     sql="""UPDATE {table} SET {column}={value} WHERE {sec}={sec_now}""".format(table=tablename,
        #                                                 column=key,
        #                                                 value=SQLFormatting(dictname[key]),
        #                                                 sec='''timeseconds''',
        #                                                 sec_now=dictname['timeseconds'])
        #     self.mycursor.execute(sql)
        # print('vor testing')
        def testing(variable):
            try:
                if variable is not None:
                    var = float(variable)
                    bo = math.isnan(var)
                else:
                    var = 0
                    bo = True
            except ValueError:
                var = variable
                bo = False
            return var, bo
        # print('nach testing')
        try:
            for key in dictname:
                # print(key, 'key')
                var, bools = testing(dictname[key])
                # print(var, bools, type(var))
                if not bools:
                    # print('ich arbeite')
                    sql = """UPDATE {table} SET {column}={value} WHERE {sec}={sec_now}""".format(table=tablename,
                                                            column=key,
                                                            value=SQLFormatting(var),
                                                            sec='''timeseconds''',
                                                            sec_now=dictname['timeseconds'])
                    self.mycursor.execute(sql)
        except OperationalError as err:
            raise AssertionError(err.args[0])# do not know whether this will work
        self.conn.commit()

    def printtable(self, tablename, dictname, date1, date2):
        """ print the data of one table between two dates
            (given in time.time())
        """

        for colnames in dictname.keys():
            print(colnames, end=',', flush=True)
        print('\n')

        sql = """SELECT * from {} WHERE timeseconds BETWEEN {} AND {}""".format(
                            tablename, date1, date2)
        self.mycursor.execute(sql)

        data = self.mycursor.fetchall()
        for row in data:
            print(row)

    def exportdatatoarr(self, tablename, colnamelist):
        """export the data (defined by the list of columns) from a table (tablename)

            returns:
                numpy array containing all the data,
                in the same order as in the colnamelist
        """

        array = []
        sql = """SELECT {}""".format(colnamelist[0])
        if len(colnamelist) > 1:
            for x in colnamelist[1:]:
                sql += """,{}""".format(x)
        sql += """ from {} """.format(tablename)
        self.mycursor.execute(sql)
        data = self.mycursor.fetchall()
        for row in data:
            array.append(list(row))
        nparray = np.asarray(array)
        return nparray

    @pyqtSlot(dict)
    def store_data(self, data):
        """storing logging data
            what data should be logged is set in self.conf
            or will be set there eventually at any rate
        """
        if self.not_yet_initialised:
            return
        self.connectdb(self.conf['general']['logfile_location'])
        self.mycursor = self.conn.cursor()

        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time())}

        data.update(timedict)

        names = ['ITC', 'ILM', 'IPS', 'LakeShore350']
        for name in names:
            try:
                data[name].update(timedict)
                # sql = change_to_correct_types(name, data[name])
                # for ct, command in enumerate(sql):
                    # print(command)
                    # if ct >=2:
                    #     sq="""SELECT id from python_temp_{}""".format(name)
                    #     self.mycursor.execute(sq)
                        # print(self.mycursor.fetchall()[-5:])
                    # self.mycursor.execute(command)
                self.createtable(name, data[name])

                #inserting in the measured values:
                self.updatetable(name, data[name])

            except AssertionError as assertion:
                self.sig_assertion.emit(assertion.args[0])
            except KeyError as key:
                self.sig_assertion.emit(key.args[0])


class live_Logger(AbstractLoopThread):
    """docstring for live_Logger"""

    def __init__(self, mainthread, **kwargs):
        super(live_Logger, self).__init__()
        self.mainthread = mainthread
        self.interval = 2
        self.initialised = False

        # QTimer.singleShot(*1e3, self.worker)

    @pyqtSlot()  # int
    def work(self):
        """
            class method which (here) starts the run,
            as soon as the initialisation was done.
        """
        try:
            while not self.initialised:
                pass
            self.running()
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval*1e3, self.worker)

    @pyqtSlot()  # int
    def worker(self):
        """
            class method which is working all the time,
            while the thread is running, keeping the event loop busy
        """
        try:
            self.running()
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval*1e3, self.worker)

    def running(self):
        """
            go through all stored values for every instrument,
            and append them to the list which will be plotted
        """
        try:
            with self.mainthread.dataLock:
                for instr in self.mainthread.data:
                    for varkey in self.mainthread.data[instr]:
                        self.mainthread.data_live[instr][varkey].append(
                            self.mainthread.data[instr][varkey])

        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        except KeyError as key:
            self.sig_assertion.emit(key.args[0])

    def initialisation(self):
        """copy the current data-dict, insert empty lists in all values"""
        with self.mainthread.dataLock:
            self.mainthread.data_live = self.mainthread.data
            for instrument in self.mainthread.data:
                for variablekey in self.mainthread.data[instrument]:
                    self.mainthread.data_live[instrument][variablekey] = []
        self.initialised = True


if __name__ == '__main__':
    dbname = 'He_first_cooldown.db'
    conn = sqlite3.connect(dbname)
    mycursor = conn.cursor()
