
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets


import time
import pickle
import os
import sqlite3
import numpy as np
from numpy.polynomial.polynomial import polyfit as nppolyfit
from copy import deepcopy
import math


from util import AbstractLoopThread
from util import AbstractEventhandlingThread
from util import Window_ui
from util import convert_time
from util import convert_time_searchable
from util import convert_time_date


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
    sql.append(
        '''CREATE TABLE python_temp_{table} AS SELECT * FROM {table}'''.format(table=tablename))
    sql.append('''DROP TABLE {table}'''.format(table=tablename))
    # sql.append("CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY)".format(tablename))
    sql.append('''CREATE TABLE IF NOT EXISTS {} '''.format(
        tablename) + sql_buildDictTableString(dictname))
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
        self.general_spinSetInterval_Live.valueChanged.connect(
            lambda value: self.setValue('general', 'interval_live', value))

        self.pushBrowseFileLocation.clicked.connect(self.window_FileDialogSave)
        self.lineFilelocation.textEdited.connect(
            lambda value: self.setValue('general', 'logfile_location', value))

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
        # print(f'setting {value} to {bools}')

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
        conf['Keithley Current'] = dict()
        conf['Keithley Volt'] = dict()
        conf['general'] = dict(logfile_location='',
                               interval=2,
                               interval_live=1)
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
                    if 'interval' not in self.conf['general']:
                        self.conf['general']['interval'] = 5
                    self.general_spinSetInterval.setValue(
                        self.conf['general']['interval'])
                    if 'interval_live' not in self.conf['general']:
                        self.conf['general']['interval_live'] = 1
                    self.general_spinSetInterval_Live.setValue(
                        self.conf['general']['interval_live'])
                    if 'logfile_location' not in self.conf['general']:
                        string = 'C:/Users/Neven/GitHub/Cryostat-GUI/Log{}.db'
                        self.conf['general'][
                            'logfile_location'] = string.format(
                                convert_time_date(time.time()))
                    self.lineFilelocation.setText(
                        self.conf['general']['logfile_location'])
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
        # print('updating conf:', conf)
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
            self.sig_assertion.emit(
                'Logger: Couldn\'t establish connection: {}'.format(err))
            return False

    def createtable(self, tablename, dictname):
        """create the sql table if it does not exist,
            with all columns named after the keys in the dictionary
        """

        sql = "CREATE TABLE IF NOT EXISTS {} ".format(tablename)
        sql += sql_buildDictTableString(dictname)
        # print(sql)
        try:
            self.mycursor.execute(sql)
        except OperationalError as err:
            # print(err)
            pass

        # We should try to find a nicer a solution without try and except
        # #try:
        for key in dictname.keys():
            try:
                sql = """ALTER TABLE  {} ADD COLUMN {} {}""".format(
                    tablename, key, typeof(dictname[key]))
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
                                                                                                 value=SQLFormatting(
                                                                                                     var),
                                                                                                 sec='''timeseconds''',
                                                                                                 sec_now=dictname['timeseconds'])
                    self.mycursor.execute(sql)
        except OperationalError as err:
            print(err)
            # do not know whether this will work
            raise AssertionError(err.args[0])

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

        names = ['ITC',
                 'ILM',
                 'IPS',
                 'LakeShore350',
                 'Keithley2182_1',
                 'Keithley2182_2',
                 'Keithley2182_3',
                 'Keithley6220_1',
                 'Keithley6220_2']

        timedict = {'timeseconds': time.time(),
                    'ReadableTime': convert_time(time.time())}

        # for name in names:
        #     if name in data:
        #         data[name].update(timedict)

        self.connected = self.connectdb(
            self.conf['general']['logfile_location'])
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
        self.interval = 1
        self.length_list = 60
        self.data = mainthread.data
        self.dataLock = mainthread.dataLock
        self.dataLock_live = mainthread.dataLock_live

        # self.time_names = ['logging_timeseconds', 'timeseconds',
        # 'logging_ReadableTime', 'ReadableTime',
        # 'logging_SearchableTime', 'SearchableTime']
        self.calculations = {'ar_mean': lambda time, value: np.nanmean(value),
                             'stddev': lambda time, value: np.nanstd(value),
                             'stderr': lambda time, value: np.nanstd(value) / np.sqrt(len(value)),
                             'stddev_rel': lambda time, value: np.nanstd(value) / np.nanmean(value),
                             'stderr_rel': lambda time, value: np.nanstd(value) / (np.nanmean(value) * np.sqrt(len(value))),
                             # 'test': lambda time, value: print(time),
                             'slope': lambda time, value: nppolyfit(time, value, deg=1, full=True),  # still need to convert to minutes
                             'slope_of_mean': lambda time, value: nppolyfit(time, value, deg=1)[1] * 60
                             }
        self.slopes = {'slope': lambda value, mean: value[0][1] * 60,  # minutes,
                       'slope_rel': lambda value, mean: value[0][1] / mean * 60,  # minutes,
                       'slope_residuals': lambda value, mean: value[1][0][0] * 60 if len(value[1][0]) > 0 else np.nan}
        self.noCalc = ['time', 'Time', 'logging', 'band', 'Loop', 'Range', 'Setup', 'calc']
        self.pre_init()
        self.initialisation()
        mainthread.sig_running_new_thread.connect(self.pre_init)
        mainthread.sig_running_new_thread.connect(self.initialisation)
        mainthread.sig_logging_newconf.connect(self.update_conf)

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
            QTimer.singleShot(self.interval * 1e3, self.worker)

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
            QTimer.singleShot(self.interval * 1e3, self.worker)

    def running(self):
        """
            go through all stored values for every instrument,
            and append them to the list which will be plotted
        """
        try:
            # print("live logger trying to log")
            with self.dataLock_live:
                with self.dataLock:
                    # print(self.data_live)
                    for instr in self.data:
                        timedict = dict(logging_timeseconds=time.time() - self.startingtime,
                                        # logging_ReadableTime=convert_time(
                                        # time.time()),
                                        # logging_SearchableTime=convert_time_searchable(time.time())
                                        )
                        dic = deepcopy(self.data[instr])
                        dic.update(timedict)

                        # print(times[0])
                        for varkey in dic:
                            # print(instr, varkey)
                            self.data_live[instr][
                                varkey].append(dic[varkey])
                        if self.time_init:
                            times = [float(x) for x in self.data_live[
                                instr]['logging_timeseconds']]
                        else:
                            times = [0]
                    # print('first time')
                for instr in self.data_live:
                    # print('before ', len(times), len(self.data_live[instr]['logging_timeseconds']))
                    for varkey in self.data_live[instr]:
                        # if 'calc' not in varkey:
                        # print(instr, varkey)
                        for calc in self.calculations:
                            # print(varkey)
                            if all([x not in varkey for x in self.noCalc]):
                                # print(varkey, calc)
                                if self.time_init:
                                    self.calculations_perform(
                                        instr, varkey, calc, times)
                        if self.count > self.length_list:
                            self.counting = False
                            # print('pop at general ', instr, varkey)
                            self.data_live[instr][varkey].pop(0)

        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        except KeyError as key:
            self.sig_assertion.emit("live logger" + key.args[0])
        self.time_init = True
        if self.counting == True:
            self.count += 1

    def calculations_perform(self, instr, varkey, calc, times):
        if calc == 'slope':
            # print('fitting', instr, varkey)
            # print(self.data_live[instr][varkey])
            fit = self.calculations[calc](times, self.data_live[instr][varkey])
            for name, calc_slope in zip(self.slopes.keys(), self.slopes.values()):
                self.data_live[instr]['{key}_calc_{c}'.format(key=varkey, c=name)].append(calc_slope(
                    fit, self.data_live[instr]['{key}_calc_{c}'.format(key=varkey, c='ar_mean')][-1]))
        elif calc == 'slope_of_mean':
            times_spec = deepcopy(times)
            # if self.counting:
                # print('cutting the time')
            while len(times_spec) > len(self.data_live[instr]['{key}_calc_{c}'.format(key=varkey, c='ar_mean')]):
                times_spec.pop(0)
            # print(len(times_spec), len(self.data_live[instr][
                  # '{key}_calc_{c}'.format(key=varkey, c='ar_mean')]))
            fit = self.data_live[instr]['{key}_calc_{c}'.format(key=varkey, c=calc)].append(
                self.calculations[calc](times_spec, self.data_live[instr]['{key}_calc_{c}'.format(key=varkey, c='ar_mean')]))
        else:
            try:
                self.data_live[instr]['{key}_calc_{c}'.format(key=varkey, c=calc)].append(
                    self.calculations[calc](times, self.data_live[instr][varkey]))

            except TypeError as e_type:
                # raise AssertionError(e_type.args[0])
                # print('TYPE CALC')
                pass
            except ValueError as e_val:
                raise AssertionError(e_val.args[0])
        # if not self.counting:
        #     print('pop at calc: ', instr, varkey, calc)
        #     self.data_live[instr][
        #         '{key}_calc_{c}'.format(key=varkey, c=calc)].pop(0)

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
                        # logging_ReadableTime=0,
                        # logging_SearchableTime=0
                        )
        self.time_init = False
        self.count = 0
        self.counting = True
        with self.dataLock:
            with self.dataLock_live:
                self.mainthread.data_live = deepcopy(self.data)
                self.data_live = self.mainthread.data_live
                for instrument in self.data:
                    dic = self.data[instrument]
                    dic.update(timedict)
                    self.data_live[instrument].update(timedict)
                    for variablekey in dic:
                        self.data_live[instrument][variablekey] = []
                        if all([x not in variablekey for x in self.noCalc]):
                            for calc in self.calculations:
                                self.data_live[instrument][
                                    '{key}_calc_{c}'.format(key=variablekey, c=calc)] = []
                            for calc in self.slopes:
                                self.data_live[instrument][
                                    '{key}_calc_{c}'.format(key=variablekey, c=calc)] = []
        self.initialised = True

    def setLength(self, length):
        """set the number of measurements the calculation should be conducted over"""

        if self.length_list > length:
            with self.dataLock_live:
                for instr in self.data_live:
                    for varkey in self.data_live[instr]:
                        self.data_live[instr][varkey] = self.data_live[
                            instr][varkey][(self.length_list - length):]
        elif self.length_list < length:
            with self.dataLock_live:
                for instr in self.data_live:
                    for varkey in self.data_live[instr]:
                        self.data_live[instr][varkey] = [
                            np.nan] * (length - self.length_list) + self.data_live[instr][varkey]
        self.length_list = length

    def update_conf(self, conf):
        """
            - update the configuration with one being sent.
        """
        self.interval = conf['general']['interval_live']


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
        # self.mainthread.sig_log_measurement_newconf.connect(self.update_conf)

        # QTimer.singleShot(5e2, lambda: self.sig_configuring.emit(True))

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
        # try:
        #     if not self.data:
        #         self.sig_assertion.emit("DataSaver: empty filename! (at least!)")
        # except NameError:
        #     # configuration not yet done
        #     self.sig_assertion.emit("DataSaver: you need to specify the configuration before storing data!")
        datastring = '\n {T_mean_K:.3E} {T_std_K:.3E} {R_mean_Ohm:.14E} {R_std_Ohm:.14E} {timeseconds} {ReadableTime}'.format(
            **data)

        if os.path.isfile(data['datafile']):
            try:
                with open(data['datafile'], 'a') as f:
                    f.write(datastring)
            except IOError as err:
                self.sig_assertion.emit("DataSaver: " + err.args[0])
        else:
            try:
                with open(data['datafile'], 'w') as f:
                    f.write("# Measurement started on {date} \n".format(date=convert_time(self.starttime)) +
                            "# temp_sample [K], T_std [K], resistance [Ohm], R_std [Ohm], time[s], date \n")
                    f.write(datastring)
            except IOError as err:
                self.sig_assertion.emit("DataSaver: " + err.args[0])


if __name__ == '__main__':
    dbname = 'He_first_cooldown.db'
    conn = sqlite3.connect(dbname)
    mycursor = conn.cursor()
