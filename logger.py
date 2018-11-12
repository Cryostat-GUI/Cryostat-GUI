
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
from util import AbstractEventhandlingThread
from util import Window_ui
from util import convert_time
from util import convert_time_searchable


from sqlite3 import OperationalError


def testing_NaN(variable):
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


def SQLFormatting(variable):
    if isinstance(variable, (float, int)):
        return variable
    else:
        return f"""'{variable}'"""


def typeof(dictkey):
    if isinstance(dictkey, float):
        return "REAL"
    elif isinstance(dictkey, int):
        return "INTEGER"
    else:
        return "TEXT"


def sql_buildDictTableString(dictname):
    string = '''(id INTEGER PRIMARY KEY'''
    for key in dictname.keys():
        string += ''',{key} {typ}'''.format(key=key, typ=typeof(dictname[key]))
    string += ''')'''
    # print(string)
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


class Logger_configuration(Window_ui):
    """docstring for Logger_configuration"""

    sig_send_conf = pyqtSignal(dict)

    ITC_sensors = dict(
        set_temperature=False,
        sensor_1_temperature=False,
        sensor_2_temperature=False,
        sensor_3_temperature=False,
        temperature_error=False,
        heater_output_as_percent=False,
        heater_output_as_voltage=False,
        gas_flow_output=False,
        proportional_band=False,
        integral_action_time=False,
        derivative_action_time=False)

    def __init__(self, parent=None, **kwargs):
        super(Logger_configuration, self).__init__(
            ui_file='.\\configurations\\Logger_conf.ui', **kwargs)

        self.read_configuration()

        self.general_threads_ITC.toggled.connect(
                lambda value: self.setValue('ITC', 'thread', value))
        self.general_threads_ITC.toggled.connect(
                lambda b: self.ITC_thread_running.setChecked(b))
        self.general_threads_ILM.toggled.connect(
                lambda value: self.setValue('ILM', 'thread', value))
        self.general_threads_ILM.toggled.connect(
                lambda b: self.ILM_thread_running.setChecked(b))
        self.general_threads_PS.toggled.connect(
                lambda value: self.setValue('PS', 'thread', value))
        self.general_threads_PS.toggled.connect(
                lambda b: self.PS_thread_running.setChecked(b))
        self.general_threads_Lakeshore350.toggled.connect(
                lambda value: self.setValue('Lakeshore350', 'thread', value))
        self.general_threads_Lakeshore350.toggled.connect(
                lambda b: self.Lakeshore350_thread_running.setChecked(b))

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

        self.general_spinSetInterval.valueChanged.connect(
                lambda value: self.setValue('general', 'interval', value))

        self.pushBrowseFileLocation.clicked.connect(self.window_FileDialogSave)

        self.buttonBox_finish.accepted.connect(
            lambda: self.sig_send_conf.emit(deepcopy(self.conf)))
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
        '''
            search for configuration file,
            load it if found,
            initialise new dict if not found
        '''
        configurations = os.listdir(r'.\\configurations')
        if 'log_conf.pickle' in configurations:
            with open('configurations/log_conf.pickle', 'rb') as handle:
                self.conf = pickle.load(handle)
                if 'general' in self.conf:
                    if 'interval' in self.conf['general']:
                        self.general_spinSetInterval.setValue(self.conf['general']['interval'])
                    if 'logfile_location' in self.conf['general']:
                        self.lineFilelocation.setText(self.conf['general']['logfile_location'])
        else:
            self.conf = self.initialise_dicts()

    def window_FileDialogSave(self):
        dbname, __ = QtWidgets.QFileDialog.getSaveFileName(
           self, 'Choose Database File Location',
           'c:\\', "Database Files - SQLite3 (*.db)")
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

        self.interval = 5  # 5s interval for logging as initialisation

        self.mainthread.sig_logging.connect(self.store_data)
        self.mainthread.sig_logging_newconf.connect(self.update_conf)

        QTimer.singleShot(5e2, lambda: self.sig_configuring.emit(True))
        self.configuration_done = False
        self.conf_done_layer2 = False

        self.not_yet_initialised = False
        self.local_list = []

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
            return True
        except sqlite3.connect.Error as err:
            # raise AssertionError("Logger: Couldn't establish connection {}".format(err))
            self.sig_assertion.emit('Logger: Couldn\'t establish connection: {}'.format(err))
            return False

    def createtable(self,tablename,dictname):
        """create the sql table if it does not exist,
            with all columns named after the keys in the dictionary
        """

        sql="CREATE TABLE IF NOT EXISTS {} ".format(tablename)
        sql += sql_buildDictTableString(dictname)
        # print(sql)
        try:
            self.mycursor.execute(sql)
        except OperationalError as err:
            # print(err)
            pass

        #We should try to find a nicer a solution without try and except
        # #try:
        for key in dictname.keys():
            try:
                sql = """ALTER TABLE  {} ADD COLUMN {} {}""".format(tablename,key,typeof(dictname[key]))
                # print(sql)
                self.mycursor.execute(sql)
            except OperationalError as err:
                # print(err)
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
        sql = """INSERT INTO {} ({}) VALUES ({})""".format(
                    tablename, 'timeseconds', dictname['timeseconds'])
        self.mycursor.execute(sql)

        # for key in dictname.keys():
        #     sql="""UPDATE {table} SET {column}={value} WHERE {sec}={sec_now}""".format(table=tablename,
        #                                                 column=key,
        #                                                 value=SQLFormatting(dictname[key]),
        #                                                 sec='''timeseconds''',
        #                                                 sec_now=dictname['timeseconds'])
        #     self.mycursor.execute(sql)
        # print('vor testing')

        # print('nach testing')
        try:
            for key in dictname:
                # print(key, 'key')
                var, bools = testing_NaN(dictname[key])
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
            print(err)
            raise AssertionError(err.args[0])# do not know whether this will work

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

    def correcting_database_types(self, name, data):
        """
            correct the types of the database entries,
            in case something was overlooked
            NOT OPERATIONAL, there is a bug somehwere...
        """
        sql = change_to_correct_types(name, data[name])
        for ct, command in enumerate(sql):
            print(command)
            if ct >= 2:
                sq = """SELECT id from python_temp_{}""".format(name)
                self.mycursor.execute(sq)
                # print(self.mycursor.fetchall()[-5:])
            self.mycursor.execute(command)

    def storing_to_database(self, data, names):
        """store data to the database"""
        for name in names:
            try:
                # self.correcting_database_types(name, data)

                self.createtable(name, data[name])

                # inserting in the measured values:
                self.updatetable(name, data[name])

            except AssertionError as assertion:
                self.sig_assertion.emit(assertion.args[0])
            except KeyError as key:
                self.sig_assertion.emit(key.args[0])

    @pyqtSlot(dict)
    def store_data(self, data):
        """storing logging data
            what data should be logged is set in self.conf
            or will be set there eventually at any rate
        """
        self.operror = False
        if self.not_yet_initialised:
            return

        names = ['ITC', 'ILM', 'IPS', 'LakeShore350']
        # timedict = {'timeseconds': time.time(),
        #             'ReadableTime': convert_time(time.time())}

        # for name in names:
        #     if name in data:
        #         data[name].update(timedict)

        self.connected = self.connectdb(self.conf['general']['logfile_location'])
        if not self.connected:
            self.sig_assertion.emit('no connection, storing locally')
            self.local_list.append(data)
            return

        try:
            with self.conn:
                self.mycursor = self.conn.cursor()
                if len(self.local_list) > 0:
                    for entry in self.local_list:
                        self.storing_to_database(entry, names)
                    self.local_list = []

                self.storing_to_database(data, names)
        except OperationalError as e:
            self.operror = True
            self.local_list.append(data)
            self.sig_assertion.emit(e.args[0])
        except sqlite3.Error as er:
            if not self.operror:
                self.local_list.append(data)
            self.sig_assertion.emit(er.args[0])
            print(er)

        # data.update(timedict)


class live_Logger(AbstractLoopThread):
    """docstring for live_Logger"""

    def __init__(self, mainthread, **kwargs):
        super(live_Logger, self).__init__()
        self.mainthread = mainthread
        self.interval = 5
        self.pre_init()
        self.initialisation()
        self.mainthread.sig_running_new_thread.connect(self.pre_init)
        self.mainthread.sig_running_new_thread.connect(self.initialisation)

        self.time_names = ['logging_timeseconds', 'timeseconds',
                           'logging_ReadableTime', 'ReadableTime',
                           'logging_SearchableTime', 'SearchableTime']
        # buggy because it will erase all previous data!

        # QTimer.singleShot(*1e3, self.worker)

    @pyqtSlot()  # int
    def work(self):
        """
            class method which (here) starts the run,
            as soon as the initialisation was done.
        """
        try:
            while not self.initialised:
                time.sleep(0.02)
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
            while not self.initialised:
                time.sleep(0.02)
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
            # print("live logger trying to log")
            with self.mainthread.dataLock:
                with self.mainthread.dataLock_live:
                    # print(self.mainthread.data_live)
                    for instr in self.mainthread.data:
                        timedict = dict(logging_timeseconds=time.time()-self.startingtime,
                                        logging_ReadableTime=convert_time(time.time()),
                                        logging_SearchableTime=convert_time_searchable(time.time()))
                        dic = deepcopy(self.mainthread.data[instr])
                        dic.update(timedict)
                        for varkey in dic:
                            self.mainthread.data_live[instr][varkey].append(dic[varkey])
                            if len(self.mainthread.data_live[instr][varkey]) > 1000:
                                self.mainthread.data_live[instr][varkey].pop(0)

        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        except KeyError as key:
            self.sig_assertion.emit("live logger"+key.args[0])

    def pre_init(self):
        self.initialised = False

    def initialisation(self):
        """
           copy the current data-dict,
           update for logging times,
           insert empty lists in all values
        """
        self.startingtime = time.time()
        timedict = dict(logging_timeseconds=0,
                        logging_ReadableTime=0,
                        logging_SearchableTime=0)
        with self.mainthread.dataLock:
            with self.mainthread.dataLock_live:
                self.mainthread.data_live = deepcopy(self.mainthread.data)
                for instrument in self.mainthread.data:
                    dic = self.mainthread.data[instrument]
                    dic.update(timedict)
                    self.mainthread.data_live[instrument].update(timedict)
                    for variablekey in dic:
                        self.mainthread.data_live[instrument][variablekey] = []
        self.initialised = True


class Logger_measurement_configuration(Window_ui):
    """docstring for Logger_configuration"""

    sig_send_conf = pyqtSignal(dict)

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            ui_file='.\\configurations\\Log_meas_conf.ui', **kwargs)

        self.pushBrowseFileLocation.clicked.connect(self.window_FileDialogSave)
        self.conf = self.initialise_dicts()

        # self.buttonBox_finish.accepted.connect(
        #     lambda: self.sig_send_conf.emit(deepcopy(self.conf)))
        self.buttonBox_finish.accepted.connect(self.close_and_safe)
        self.buttonBox_finish.rejected.connect(self.close)

    def close_and_safe(self):
        """save the configuration dict to a file, close the window afterwards"""
        self.sig_send_conf.emit(deepcopy(self.conf))
        # with open('configurations/log_conf.pickle', 'wb') as handle:
        #     pickle.dump(self.conf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        self.close()

    def setValue(self, value, bools):
        """set a bool value according to the instrument and specific"""
        self.conf[value] = bools

    def initialise_dicts(self):
        """initialise the conf dict, in case it was not handed down
            return the empty conf dict
        """
        conf = dict(datafile='')
        return conf

    def window_FileDialogSave(self):
        dbname, __ = QtWidgets.QFileDialog.getSaveFileName(
           self, 'Choose Datafile Location',
           'c:\\', "Data Files (*.dat)")
        self.lineFilelocation.setText(dbname)
        self.setValue('datafile', dbname)


class measurement_Logger(AbstractEventhandlingThread):
    """This is the datasaving thread
    """

    # sig_configuring = pyqtSignal(bool)
    sig_log = pyqtSignal()

    def __init__(self, mainthread, **kwargs):
        super().__init__(**kwargs)
        self.mainthread = mainthread

        self.starttime = time.time()

        self.mainthread.sig_log_measurement.connect(self.store_data)
        self.mainthread.sig_log_measurement_newconf.connect(self.update_conf)

        QTimer.singleShot(5e2, lambda: self.sig_configuring.emit(True))

    def update_conf(self, conf):
        """
            - update the configuration with one being sent.

        """
        self.conf = conf

    @pyqtSlot(dict)
    def store_data(self, data):
        """storing logging data
            what data should be logged is set in self.conf
            or will be set there eventually at any rate
        """
        # timedict = {'timeseconds': time.time(),
        #             'ReadableTime': convert_time(time.time())}
        try:
            if not self.conf:
                self.sig_assertion.emit("DataSaver: empty filename! (at least!)")
        except NameError:
            # configuration not yet done
            self.sig_assertion.emit("DataSaver: you need to specify the configuration before storing data!")
        datastring = '\n {T_mean_K:.3E} {T_std_K:.3E} {R_mean_Ohm:.14E} {R_std_Ohm:.14E} {time}'.format(**data)

        if os.path.isfile(self.conf['datafile']):
            try:
                with open(self.conf['datafile'], 'a') as f:
                    f.write(datastring)
            except IOError as err:
                self.sig_assertion.emit("DataSaver: "+ err.args[0])
        else:
            try:
                with open(self.conf['datafile'], 'w') as f:
                    f.write("# Measurement started on {date} \n".format(date=convert_time(self.starttime)) +
                            "# temp_sample [K], T_std [K], resistance [Ohm], R_std [Ohm], time[s] \n")
                    f.write(datastring)
            except IOError as err:
                self.sig_assertion.emit("DataSaver: "+ err.args[0])


if __name__ == '__main__':
    dbname = 'He_first_cooldown.db'
    conn = sqlite3.connect(dbname)
    mycursor = conn.cursor()
