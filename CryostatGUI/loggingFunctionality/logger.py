import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets

import pandas as pd
import time
import pickle
import sqlite3

# import pandas as pd
import numpy as np
from numpy.polynomial.polynomial import polyfit as nppolyfit
from copy import deepcopy
from threading import Lock
import math

from datetime import datetime


from prometheus_client import start_http_server
from prometheus_client import Gauge


from util import AbstractLoopThread
from util import AbstractLoopThreadDataStore
from util import AbstractEventhandlingThread
from util import Window_ui
from util import convert_time
from util import convert_time_searchable
from util import convert_time_date
from util import AbstractMainApp
from util import Window_trayService_ui


from sqlite3 import OperationalError


import logging

logger = logging.getLogger("CryostatGUI.loggingFunctionality")


def slope_from_timestampX(tmp_):
    """casting datetime into seconds:
    dt = pandas series of datetime objects
    seconds = dt.astype('int64') // 1e9

    """
    slope = pd.Series(
        np.gradient(tmp_.values, tmp_.index.astype("int64") // 1e9),
        tmp_.index,
        name="slope",
    )
    return slope


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
    except TypeError:
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
    string = """(id INTEGER PRIMARY KEY"""
    for key in dictname.keys():
        string += """,{key} {typ}""".format(key=key, typ=typeof(dictname[key]))
    string += """)"""
    # print(string)
    return string


def change_to_correct_types(tablename, dictname):
    sql = []
    if not dictname:
        raise AssertionError("Logger: dict does not yet exist")
    sql.append("""PRAGMA foreign_keys = 0""")
    sql.append(
        """CREATE TABLE python_temp_{table} AS SELECT * FROM {table}""".format(
            table=tablename
        )
    )
    sql.append("""DROP TABLE {table}""".format(table=tablename))
    # sql.append("CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY
    # KEY)".format(tablename))
    sql.append(
        """CREATE TABLE IF NOT EXISTS {} """.format(tablename)
        + sql_buildDictTableString(dictname)
    )
    # for key in dictname.keys():
    # sql.append("ALTER TABLE  {} ADD COLUMN {}
    # {}".format(tablename,key,typeof(dictname[key])))

    sql_temp = """INSERT INTO {table} (id""".format(table=tablename)
    for key in dictname.keys():
        sql_temp += ",{}".format(key)
    sql_temp += """) SELECT id"""
    for key in dictname.keys():

        sql_temp += """,{}""".format(key)
    sql_temp += """ FROM python_temp_{table}""".format(table=tablename)
    sql.append(sql_temp)
    sql.append("""DROP TABLE python_temp_{table}""".format(table=tablename))
    sql.append("""PRAGMA foreign_keys = 1""")
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
        derivative_action_time=False,
    )

    def __init__(self, **kwargs):
        super().__init__(ui_file=".\\configurations\\Logger_conf.ui", **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        self.read_configuration()

        self.general_spinSetInterval.valueChanged.connect(
            lambda value: self.setValue("general", "interval", value)
        )
        self.general_spinSetInterval_Live.valueChanged.connect(
            lambda value: self.setValue("general", "interval_live", value)
        )

        self.pushBrowseFileLocation.clicked.connect(self.window_FileDialogSave)
        self.lineFilelocation.textEdited.connect(
            lambda value: self.setValue("general", "logfile_location", value)
        )

        self.buttonBox_finish.accepted.connect(
            lambda: self.sig_send_conf.emit(deepcopy(self.conf))
        )
        self.buttonBox_finish.accepted.connect(self.close_and_safe)
        self.buttonBox_finish.rejected.connect(self.close)

    def close_and_safe(self):
        """save the configuration dict to a file, close the window afterwards"""
        self.sig_send_conf.emit(self.conf)
        with open("configurations/log_conf.pickle", "wb") as handle:
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
        conf = {}
        conf["ITC"] = self.ITC_sensors
        conf["ILM"] = {}
        conf["PS"] = {}
        conf["Lakeshore350"] = {}
        conf["Keithley Current"] = {}
        conf["Keithley Volt"] = {}
        conf["general"] = dict(logfile_location="", interval=2, interval_live=1)
        return conf

    def read_configuration(self):
        """
        search for configuration file,
        load it if found,
        initialise new dict if not found
        """
        configurations = os.listdir(r".\\configurations")
        if "log_conf.pickle" in configurations:
            with open("configurations/log_conf.pickle", "rb") as handle:
                self.conf = pickle.load(handle)
                if "general" in self.conf:
                    if "interval" not in self.conf["general"]:
                        self.conf["general"]["interval"] = 5
                    self.general_spinSetInterval.setValue(
                        self.conf["general"]["interval"]
                    )
                    if "interval_live" not in self.conf["general"]:
                        self.conf["general"]["interval_live"] = 1
                    self.general_spinSetInterval_Live.setValue(
                        self.conf["general"]["interval_live"]
                    )
                    if "logfile_location" not in self.conf["general"]:
                        string = "C:/Users/Neven/GitHub/Cryostat-GUI/Log{}.db"
                        self.conf["general"]["logfile_location"] = string.format(
                            convert_time_date(time.time())
                        )
                    self.lineFilelocation.setText(
                        self.conf["general"]["logfile_location"]
                    )
        else:
            self.conf = self.initialise_dicts()

    def window_FileDialogSave(self):
        dbname, __ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose Database File Location",
            "c:\\",
            "Database Files - SQLite3 (*.db)",
        )
        self.lineFilelocation.setText(dbname)
        self.setValue("general", "logfile_location", dbname)


class main_Logger(AbstractLoopThread):
    """This is a the logging worker thread"""

    sig_configuring = pyqtSignal(bool)
    sig_log = pyqtSignal()

    def __init__(self, mainthread=None, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.mainthread = mainthread

        self.interval = 5  # 5s interval for logging as initialisation

        self.mainthread.sig_logging.connect(self.store_data)
        self.mainthread.sig_logging_newconf.connect(self.update_conf)

        QTimer.singleShot(5e2, lambda: self.sig_configuring.emit(True))
        self.configuration_done = False
        self.conf_done_layer2 = False

        self.not_yet_initialised = False
        self.local_list = []

        self.houroffset = (datetime.now() - datetime.utcnow()).total_seconds() / 3600

    def running(self):
        """perpetual logging function, which is asking for logging data"""
        try:
            if self.configuration_done:
                self.sig_log.emit()
                if not self.conf_done_layer2:
                    self.sig_configuring.emit(False)
                    self.conf_done_layer2 = True

        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
            self._logger.exception(assertion)

    def update_conf(self, conf):
        """
        - update the configuration with one being sent.
        - set the configuration done bool to True,
            so that self.running will actually log
        - set self.conf_done_layer2 to False,
            so that the configuring thread will be quit.

        """
        self.conf = conf
        self.interval = self.conf["general"]["interval"]
        self.configuration_done = True
        self.conf_done_layer2 = False

    def connectdb(self, dbname):
        """connect to the sqlite database"""
        try:
            self.conn = sqlite3.connect(dbname)
            return True
        except sqlite3.connect.Error as err:
            self.sig_assertion.emit(
                "Logger: Couldn't establish connection: {}".format(err)
            )
            self._logger.exception(err)
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
        except OperationalError:
            # print(err)
            self._logger.debug(
                "encountered OperationalError from sqlite (table of column might already exist)"
            )
            pass

        for key in dictname.keys():
            try:
                sql = """ALTER TABLE  {} ADD COLUMN {} {}""".format(
                    tablename, key, typeof(dictname[key])
                )
                # print(sql)
                self.mycursor.execute(sql)
            except OperationalError:
                self._logger.debug(
                    "encountered OperationalError from sqlite (table of column might already exist)"
                )
                # print(err)
                pass  # Logger: probably the column already exists, no problem.

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
            raise AssertionError("Logger: dict does not yet exist")
        sql = """INSERT INTO {} ({}) VALUES ({})""".format(
            tablename, "timeseconds", dictname["timeseconds"]
        )
        self.mycursor.execute(sql)

        try:
            for key in dictname:
                var, bools = testing_NaN(dictname[key])
                if isinstance(var, type(datetime.now())):
                    var = (
                        "UTC"
                        + "{:+05.0f} ".format(self.houroffset)
                        + var.strftime("%Y-%m-%d  %H:%M:%S.%f")
                    )
                if not bools:
                    sql = """UPDATE {table} SET {column}={value} WHERE {sec}={sec_now}""".format(
                        table=tablename,
                        column=key,
                        value=SQLFormatting(var),
                        sec="""timeseconds""",
                        sec_now=dictname["timeseconds"],
                    )
                    self.mycursor.execute(sql)
        except OperationalError as err:
            print(err)
            # do not know whether this will work
            raise AssertionError(err.args[0])

    def printtable(self, tablename, dictname, date1, date2):
        """print the data of one table between two dates
        (given in time.time())
        """

        for colnames in dictname.keys():
            print(colnames, end=",", flush=True)
        print("\n")

        sql = """SELECT * from {} WHERE timeseconds BETWEEN {} AND {}""".format(
            tablename, date1, date2
        )
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
        self._logger.debug(f"storing {data} in database")
        for name in names:
            self._logger.debug(f"store {name}")
            try:
                # self.correcting_database_types(name, data)

                self.createtable(name, data[name])

                # inserting in the measured values:
                self.updatetable(name, data[name])

            except AssertionError as assertion:
                self.sig_assertion.emit(assertion.args[0])
                self._logger.exception(assertion)
            except KeyError as key:
                self.sig_assertion.emit(key.args[0])
                self._logger.exception(key)

    @pyqtSlot(dict)
    def store_data(self, data):
        """storing logging data
        what data should be logged is set in self.conf
        or will be set there eventually at any rate
        """
        self.operror = False
        if self.not_yet_initialised:
            return

        names = [
            "ITC",
            "ILM",
            "IPS",
            "LakeShore350",
            "Keithley2182_1",
            "Keithley2182_2",
            "Keithley2182_3",
            "Keithley6220_1",
            "Keithley6220_2",
            "SR830",
        ]

        self.connected = self.connectdb(self.conf["general"]["logfile_location"])
        if not self.connected:
            self.sig_assertion.emit("no connection, storing locally")
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


class main_Logger_adaptable(main_Logger):
    """This is a the logging worker thread"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        self.interval = 1

    @pyqtSlot(dict)
    def store_data(self, data):
        """storing logging data
        what data should be logged is set in self.conf
        or will be set there eventually at any rate
        """
        self._logger.debug("storing data in sqlite!")
        self.operror = False
        if self.not_yet_initialised:
            return

        names = data.keys()

        self.connected = self.connectdb(self.conf["logfile_location"])
        if not self.connected:
            self.sig_assertion.emit("no connection, storing locally")
            self._logger.debug("no connection to database, storing locally")
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
            self._logger.exception(e)
        except sqlite3.Error as er:
            if not self.operror:
                self.local_list.append(data)
            self.sig_assertion.emit(er.args[0])
            self._logger.exception(er)
            print(er)
        self._logger.debug("done storing data in sqlite!")
        # data.update(timedict)

    def update_conf(self, conf):
        """
        - update the configuration with one being sent.
        - set the configuration done bool to True,
            so that self.running will actually log
        - set self.conf_done_layer2 to False,
            so that the configuring thread will be quit.

        """
        self.conf = conf
        self.interval = self.conf["interval"]
        self.configuration_done = True
        self.conf_done_layer2 = False


class live_Logger_bare:
    """docstring for live_Logger"""

    def __init__(self, mainthread=None, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.mainthread = mainthread
        self.interval = 1
        self.length_list = 60
        self.data = mainthread.data
        self.dataLock = mainthread.dataLock
        self.dataLock_live = mainthread.dataLock_live

        self.calculations = {
            "ar_mean": lambda time, value: np.nanmean(value),
            # 'stddev': lambda time, value: np.nanstd(value),
            "stderr": lambda time, value: np.nanstd(value) / np.sqrt(len(value)),
            "stddev_rel": lambda time, value: np.nanstd(value) / np.nanmean(value),
            "stderr_rel": lambda time, value: np.nanstd(value)
            / (np.nanmean(value) * np.sqrt(len(value))),
            # 'test': lambda time, value: print(time),
            "slope": lambda time, value: nppolyfit(time, value, deg=1, full=True),
            # 'slope_of_mean': lambda time, value: nppolyfit(time, value, deg=1)[1] * 60
        }

        start_http_server(8000)

        self.slopes = {
            "slope": lambda value, mean: value[0][1] * 60,  # minutes,
            # minutes,
            "slope_rel": lambda value, mean: value[0][1] / mean * 60,
            "slope_residuals": lambda value, mean: value[1][0][0] * 60
            if len(value[1][0]) > 0
            else np.nan,
        }
        self.noCalc = [
            "time",
            "Time",
            "logging",
            "band",
            "Loop",
            "Range",
            "Setup",
            "calc",
        ]

        self.pre_init()
        # self.initialisation() # this is done by starting this new thread
        # anyways!
        mainthread.sig_logging_newconf.connect(self.update_conf)

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
                        timedict = dict(
                            logging_timeseconds=time.time() - self.startingtime,
                            # logging_ReadableTime=convert_time(
                            # time.time()),
                            # logging_SearchableTime=convert_time_searchable(time.time())
                        )
                        dic = deepcopy(self.data[instr])
                        dic.update(timedict)
                        try:
                            timediff = (
                                datetime.strptime(
                                    dic["realtime"], "%Y-%m-%d %H:%M:%S.%f"
                                )
                                - datetime.now()
                            ).total_seconds()
                        except ValueError as err:
                            self._logger.error(f"problem parsing time in {dic}")
                            if "does not match format" in err.args[0]:
                                try:
                                    timediff = (
                                        datetime.strptime(
                                            dic["realtime"], "%Y-%m-%d %H:%M:%S"
                                        )
                                        - datetime.now()
                                    ).total_seconds()
                                except ValueError as e:
                                    raise e
                            else:
                                self._logger.exception(err)
                                timediff = 0
                        except TypeError:
                            timediff = (
                                dic["realtime"] - datetime.now()
                            ).total_seconds()
                        uptodate = abs(timediff) < 10

                        # print(times[0])
                        for varkey in dic:
                            # print(instr, varkey)
                            self.data_live[instr][varkey].append(dic[varkey])
                            # print(instr, varkey)
                            # print(self.Gauges)
                            if uptodate:
                                try:
                                    self.Gauges[instr][varkey].set(dic[varkey])
                                except TypeError as err:
                                    if not err.args[0].startswith(
                                        "float() argument must be a string or a number"
                                    ):
                                        self._logger.exception(err.args[0])
                                    else:
                                        # self._logger.debug(err.args[0] + f'instr:
                                        # {instr}, varkey: {varkey}')
                                        pass
                                except ValueError as err:
                                    if not err.args[0].startswith(
                                        "could not convert string to float"
                                    ):
                                        self._logger.exception(err.args[0])
                                    else:
                                        # self._logger.debug(err.args[0] + f'instr:
                                        # {instr}, varkey: {varkey}')
                                        pass
                            else:
                                self.Gauges[instr][varkey].set(0)

                        if self.time_init:
                            times = [
                                float(x)
                                for x in self.data_live[instr]["logging_timeseconds"]
                            ]
                        else:
                            times = [0]
                for instr in self.data_live:
                    for varkey in self.data_live[instr]:
                        for calc in self.calculations:
                            if all((x not in varkey for x in self.noCalc)):
                                if self.time_init:
                                    self.calculations_perform(
                                        instr, varkey, calc, times
                                    )
                        if self.count > self.length_list:
                            self.counting = False
                            self.data_live[instr][varkey].pop(0)

        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
            self._logger.exception(assertion)
        except KeyError as key:
            self.sig_assertion.emit("live logger: " + key.args[0])
            self._logger.exception(key)
        self.time_init = True
        if self.counting:
            self.count += 1

    def calculations_perform(self, instr, varkey, calc, times):
        """
        perform one specified calculation on all corresponding datasets

        return: None
        """
        if calc == "slope":
            fit = self.calculations[calc](times, self.data_live[instr][varkey])
            for name, calc_slope in zip(self.slopes.keys(), self.slopes.values()):
                self.data_live[instr][
                    "{key}_calc_{c}".format(key=varkey, c=name)
                ].append(
                    calc_slope(
                        fit,
                        self.data_live[instr][
                            "{key}_calc_{c}".format(key=varkey, c="ar_mean")
                        ][-1],
                    )
                )
        elif calc == "slope_of_mean":
            times_spec = deepcopy(times)
            while len(times_spec) > len(
                self.data_live[instr]["{key}_calc_{c}".format(key=varkey, c="ar_mean")]
            ):
                times_spec.pop(0)
            fit = self.data_live[instr][
                "{key}_calc_{c}".format(key=varkey, c=calc)
            ].append(
                self.calculations[calc](
                    times_spec,
                    self.data_live[instr][
                        "{key}_calc_{c}".format(key=varkey, c="ar_mean")
                    ],
                )
            )
        else:
            try:
                self.data_live[instr][
                    "{key}_calc_{c}".format(key=varkey, c=calc)
                ].append(self.calculations[calc](times, self.data_live[instr][varkey]))
            except TypeError as e:
                # raise AssertionError(e_type.args[0])
                # print('TYPE CALC')
                self._logger.exception(e)
            except ValueError as e_val:
                self._logger.exception(e_val)
                # raise AssertionError(e_val.args[0])

    def pre_init(self):
        self.initialised = False

    def initialisation(self):
        """
        copy the current data-dict,
        update for logging times,
        insert empty lists in all values
        """
        self.startingtime = time.time()
        timedict = dict(
            logging_timeseconds=0,
        )
        self.time_init = False
        self.count = 0
        self.counting = True
        try:
            self.Gauges["ITC"]
        except AttributeError:
            self.Gauges = {}
        except KeyError:
            pass
        with self.dataLock:
            with self.dataLock_live:
                self.mainthread.data_live = deepcopy(self.data)
                self.data_live = self.mainthread.data_live
                for instrument in self.data:
                    # print(self.Gauges)
                    dic = self.data[instrument]
                    dic.update(timedict)
                    if instrument not in self.Gauges.keys():
                        self.Gauges[instrument] = {}
                    self.data_live[instrument].update(timedict)
                    for variablekey in dic:
                        self.data_live[instrument][variablekey] = []
                        try:
                            # print(instrument, variablekey)
                            if variablekey not in self.Gauges[instrument].keys():
                                self.Gauges[instrument][variablekey] = Gauge(
                                    "CryoGUI_{}_{}".format(instrument, variablekey), ""
                                )
                                # print(self.Gauges)
                        except ValueError:
                            # print('sth went wrong', instrument, variablekey)
                            self._logger.info(
                                "sth went wrong with registering prometheus Gauges"
                            )
                        if all((x not in variablekey for x in self.noCalc)):
                            for calc in self.calculations:
                                self.data_live[instrument][
                                    "{key}_calc_{c}".format(key=variablekey, c=calc)
                                ] = []
                            for calc in self.slopes:
                                self.data_live[instrument][
                                    "{key}_calc_{c}".format(key=variablekey, c=calc)
                                ] = []
        self.initialised = True

    def setLength(self, length):
        """set the number of measurements the calculation should be conducted over"""

        if self.length_list > length:
            with self.dataLock_live:
                for instr in self.data_live:
                    for varkey in self.data_live[instr]:
                        self.data_live[instr][varkey] = self.data_live[instr][varkey][
                            (self.length_list - length) :
                        ]
        elif self.length_list < length:
            with self.dataLock_live:
                for instr in self.data_live:
                    for varkey in self.data_live[instr]:
                        self.data_live[instr][varkey] = [np.nan] * (
                            length - self.length_list
                        ) + self.data_live[instr][varkey]
        self.length_list = length

    def update_conf(self, conf):
        """
        - update the configuration with one being sent.
        """
        self.interval = conf["interval_live"]


class live_Logger(live_Logger_bare, AbstractLoopThread):
    """docstring for live_Logger"""

    def __init__(self, mainthread=None, **kwargs):
        super().__init__(mainthread=mainthread, **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        mainthread.sig_running_new_thread.connect(self.pre_init)
        mainthread.sig_running_new_thread.connect(self.initialisation)

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
            self._logger.exception(assertion)
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
            self._logger.exception(assertion)
        finally:
            QTimer.singleShot(self.interval * 1e3, self.worker)


class live_zmqDataStoreLogger(live_Logger_bare, AbstractLoopThreadDataStore):
    """docstring for live_Logger"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        del self.initialised

    def zmq_handle(self):
        try:
            self.initialised
            super().zmq_handle()
        except AttributeError:
            # time.sleep(0.02)
            self.initialisation()

    def running(self):
        try:
            self.initialised
            super().running()
        except AttributeError:
            time.sleep(0.02)
            self.initialisation()
        # TODO: NOT FINISHED !!!

    def store_data(self, ID, data):
        timedict = {
            "timeseconds": time.time(),
            "ReadableTime": convert_time(time.time()),
            "SearchableTime": convert_time_searchable(time.time()),
        }
        data.update(timedict)
        with self.dataLock:
            self.data[ID] = data
        present = True
        with self.dataLock_live:
            if ID not in self.data_live:
                present = False
        if not present:
            self.initialisation()

    def get_answer(self, qdict):
        self._logger.debug(f"getting answer for {qdict}")
        adict = {}
        live = qdict["live"]
        try:
            if live:
                data = self.data_live[qdict["instr"]][qdict["value"]][-1]
            else:
                data = self.data[qdict["instr"]][qdict["value"]]
            timediff = (
                datetime.strptime(
                    self.data[qdict["instr"]]["realtime"], "%Y-%m-%d %H:%M:%S.%f"
                )
                - datetime.now()
            ).total_seconds()
            uptodate = abs(timediff) < 3
        except KeyError as e:
            return dict(
                ERROR="KeyError",
                ERROR_message=e.args[0],
                info="the data you requested is seemingly not present in the data",
            )
        adict["data"] = data
        adict["uptodate"] = uptodate
        adict["timediff"] = timediff
        self._logger.debug(f"answer: {adict}")
        return adict


class LoggingGUI(AbstractMainApp, Window_trayService_ui):
    """docstring for LoggingGUI"""

    sig_logging = pyqtSignal(dict)
    sig_logging_newconf = pyqtSignal(dict)
    # sig_send_conf = pyqtSignal(dict)

    data = {}
    data_live = {}

    def __init__(self, **kwargs):
        self.kwargs = deepcopy(kwargs)
        del kwargs["identity"]
        self._identity = self.kwargs["identity"]
        super().__init__(
            ui_file=".\\..\\loggingFunctionality\\Logging_main.ui", **kwargs
        )
        self.softwarecontrol_timer.stop()
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        # start thread 1: main_logger
        # start thread 2: newLiveLogger with zmq capability

        logger_main = self.running_thread_control(
            main_Logger_adaptable(mainthread=self), "logger"
        )
        # logger.sig_log.connect(self.logging_send_all)
        logger_main.sig_log.connect(lambda: self.sig_logging.emit(deepcopy(self.data)))

        # ------------- main Logging configuration initialisation -------------
        self.read_configuration()

        self.general_spinSetInterval.valueChanged.connect(
            lambda value: self.setValue("interval", value)
        )
        self.general_spinSetInterval_Live.valueChanged.connect(
            lambda value: self.setValue("interval_live", value)
        )

        self.pushBrowseFileLocation.clicked.connect(self.window_FileDialogSave)
        self.lineFilelocation.textEdited.connect(
            lambda value: self.setValue("logfile_location", value)
        )

        self.pushApply.clicked.connect(self.applyConf)
        QTimer.singleShot(
            0, lambda: self.restore_window(QtWidgets.QSystemTrayIcon.DoubleClick)
        )

        # ----------------------------------------------------------------------

        # ------------- live Logging configuration initialisation -------------
        self.dataLock = Lock()
        self.dataLock_live = Lock()
        # logger_live =
        self.running_thread_control(
            live_zmqDataStoreLogger(mainthread=self), "zmq_liveLogger"
        )
        # ----------------------------------------------------------------------

    def applyConf(self):
        """save the configuration dict to a file, close the window afterwards"""
        self.sig_logging_newconf.emit(self.conf)
        with open("./../configurations/log_conf.pickle", "wb") as handle:
            pickle.dump(self.conf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        # self.close()

    def setValue(self, value, bools):
        self.conf[value] = bools

    def read_configuration(self):
        """
        search for configuration file,
        load it if found,
        initialise new dict if not found
        """
        configurations = os.listdir(r".\\..\\configurations")
        if "log_conf.pickle" in configurations:
            with open("./../configurations/log_conf.pickle", "rb") as handle:
                self.conf = pickle.load(handle)
                # if 'general' in self.conf:
                if "interval" not in self.conf:
                    self.conf["interval"] = 5
                self.general_spinSetInterval.setValue(self.conf["interval"])
                if "interval_live" not in self.conf:
                    self.conf["interval_live"] = 1
                self.general_spinSetInterval_Live.setValue(self.conf["interval_live"])
                if "logfile_location" not in self.conf:
                    string = "C:/Users/Lab-user/Documents/GitHub/Cryostat-GUI/CryostatGUI/Logs/Log{}.db"
                    self.conf["logfile_location"] = string.format(
                        convert_time_date(time.time())
                    )
                self.lineFilelocation.setText(self.conf["logfile_location"])
        else:
            self.conf = dict(logfile_location="", interval=2, interval_live=1)

    def window_FileDialogSave(self):
        dbname, __ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Choose Database File Location",
            "c:\\",
            "Database Files - SQLite3 (*.db)",
        )
        self.lineFilelocation.setText(dbname)
        self.setValue("logfile_location", dbname)


class Logger_measurement_configuration(Window_ui):
    """docstring for Logger_configuration"""

    sig_send_conf = pyqtSignal(dict)

    def __init__(self, **kwargs):
        super().__init__(ui_file=".\\configurations\\Log_meas_conf.ui", **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

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
        conf = dict(datafile="")
        return conf

    def window_FileDialogSave(self):
        dbname, __ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose Datafile Location", "c:\\", "Data Files (*.dat)"
        )
        self.lineFilelocation.setText(dbname)
        self.setValue("datafile", dbname)


class measurement_Logger(AbstractEventhandlingThread):
    """This is the datasaving thread"""

    # sig_configuring = pyqtSignal(bool)
    sig_log = pyqtSignal()

    def __init__(self, mainthread, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.mainthread = mainthread
        self.mainthread.sig_log_measurement.connect(self.store_data)

        self.starttime = time.time()

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
        # if isinstance(data, dict):
        if data["type"] == "multichannel":

            datastring = ""
            temperatures = [
                "{{{mean}:.5E}} {{{std}:.5E}} ".format(mean=mean, std=std)
                for mean, std in zip(data["T_mean_K"], data["T_std_K"])
            ]
            for t in temperatures:
                datastring += t
            datastring = datastring.format(**data["T_mean_K"], **data["T_std_K"])

            for instrument in data["resistances"]:
                res_instr = [
                    "{{{name}:.10E}} ".format(name=key)
                    for key in data["resistances"][instrument]
                ]
                for r in res_instr:
                    datastring += r
                datastring = datastring.format(**data["resistances"][instrument])

            for instrument in data["voltages"]:
                voltages = [
                    "{{{num}:.5E}} ".format(num=ct)
                    for ct, value in enumerate(data["voltages"][instrument])
                ]
                datastring += "{} ".format(len(voltages))
                for v in voltages:
                    datastring += v
                datastring = datastring.format(*data["voltages"][instrument])

            for instrument in data["currents"]:
                currents = [
                    "{{{num}:.5E}} ".format(num=ct)
                    for ct, value in enumerate(data["currents"][instrument])
                ]
                datastring += "{} ".format(len(currents))
                for v in currents:
                    datastring += v
                datastring = datastring.format(*data["currents"][instrument])

            datastring = "\n{ReadableTime} ".format(**data) + datastring
            # print(datastring)

            headerstring = """\
# Measurement started on {date}
#
# date,Sensor_1_(A)_[K]_arithmetic_mean,Sensor_1_(A)_[K]_uncertainty,Sensor_2_(B)_[K]_arithmetic_mean,Sensor_2_(B)_[K]_uncertainty,Sensor_3_(C)_[K]_arithmetic_mean,Sensor_3_(C)_[K]_uncertainty,Sensor_4_(D)_[K]_arithmetic_mean,Sensor_4_(D)_[K]_uncertainty,Keith1:_resistance_[Ohm]_(slope_of_4_points),Keith1:_residuals_(of_fit_for_slope),Keith1:_non-ohmicity:_0_if_ohmic_1_if_nonohmic,Keith2:_resistance_[Ohm]_(slope_of_4_points),Keith2:_residuals_(of_fit_for_slope),Keith2:_non-ohmicity:_0_if_ohmic_1_if_nonohmic,descr1,Keith1_voltage_1,Keith1_voltage_2,Keith1_voltage_3,Keith1_voltage_4,descr2,Keith2_voltage_1,Keith2_voltage_2,Keith2_voltage_3,Keith2_voltage_4,descr3,Keith1_current_1,Keith1_current_2,Keith1_current_3,Keith1_current_4,descr4,Keith2_current_1,Keith2_current_2,Keith2_current_3,Keith2_current_4,
# columns -1 based / zero based / one based
#
# -1 / 0 /  1 date
#
#   -- temperatures
#  0 /  1 /  2 Sensor 1 (A) [K] arithmetic mean
#  1 /  2 /  3 Sensor 1 (A) [K] uncertainty
#  2 /  3 /  4 Sensor 2 (B) [K] arithmetic mean
#  3 /  4 /  5 Sensor 2 (B) [K] uncertainty
#  4 /  5 /  6 Sensor 3 (C) [K] arithmetic mean
#  5 /  6 /  7 Sensor 3 (C) [K] uncertainty
#  6 /  7 /  8 Sensor 4 (D) [K] arithmetic mean
#  7 /  8 /  9 Sensor 4 (D) [K] uncertainty
#
#   -- resistances Keithley2182_1
#  8 /  9 / 10 resistance [Ohm] (slope of 4 points)
#  9 / 10 / 11 residuals (of fit for slope)
# 10 / 11 / 12 non-ohmicity: 0 if ohmic, 1 if nonohmic
#
#   -- resistances Keithley2182_2
# 11 / 12 / 13 resistance [Ohm] (slope of 4 points)
# 12 / 13 / 14 residuals (of fit for slope)
# 13 / 14 / 15 non-ohmicity: 0 if ohmic, 1 if nonohmic
#
#   the following numbers only apply if the number of points for the iv-fit is 4

#   -- voltages Keithley2182_1
# 14 / 15 / 16 number of voltages
# 15 / 16 / 17 voltage 1
# 16 / 17 / 18 voltage 2
# 17 / 18 / 19 voltage 3
# 18 / 19 / 20 voltage 4

#   -- voltages Keithley2182_2
# 19 / 20 / 21 number of voltages
# 20 / 21 / 22 voltage 1
# 21 / 22 / 23 voltage 2
# 22 / 23 / 24 voltage 3
# 23 / 24 / 25 voltage 4

#   -- currents Keithley6221_1
# 24 / 25 / 26 number of currents
# 25 / 26 / 27 current 1
# 26 / 27 / 28 current 2
# 27 / 28 / 29 current 3
# 28 / 29 / 30 current 4

#   -- currents Keithley6221_2
# 29 / 30 / 31 number of currents
# 30 / 31 / 32 current 1
# 31 / 32 / 33 current 2
# 32 / 33 / 34 current 3
# 33 / 34 / 35 current 4
# 34 / 35 / 36 unused
# 35 / 36 / 37 unused
# 36 / 37 / 38 unused
# 37 / 38 / 39 unused
# 38 / 39 / 40 unused
# 39 / 40 / 41 unused
# 40 / 41 / 42 unused
# 41 / 42 / 43 unused
# 42 / 43 / 44 unused
# 43 / 44 / 45 unused
# 44 / 45 / 46 unused
# 45 / 46 / 47 unused
# 46 / 47 / 48 unused
# 47 / 48 / 49 unused
# 48 / 49 / 50 unused
# 49 / 50 / 51 unused
# 50 / 51 / 52 unused
# 51 / 52 / 53 unused
# 52 / 53 / 54 unused
# 53 / 54 / 55 unused
# 54 / 55 / 56 unused
# 55 / 56 / 57 unused
# 56 / 57 / 58 unused
# 57 / 58 / 59 unused
# 58 / 59 / 60 unused
# 59 / 60 / 61 unused
# 60 / 61 / 62 unused
# 61 / 62 / 63 unused
# 62 / 63 / 64 unused
# 63 / 64 / 65 unused
# 64 / 65 / 66 unused
# 65 / 66 / 67 unused
# 66 / 67 / 68 unused
# 67 / 68 / 69 unused
# 68 /
""".format(
                date=convert_time(self.starttime)
            )

        else:
            datastring = "\n {T_mean_K:.3E} {T_std_K:.3E} {R_mean_Ohm:.14E} {R_std_Ohm:.14E} {timeseconds} {ReadableTime}".format(
                **data
            )
            headerstring = str(
                "# Measurement started on {date} \n".format(
                    date=convert_time(self.starttime)
                )
                + "# temp_sample [K], T_std [K], resistance [Ohm], R_std [Ohm], time [s], date \n"
            )

        if os.path.isfile(data["datafile"]):
            try:
                with open(data["datafile"], "a") as f:
                    f.write(datastring)
            except IOError as err:
                self.sig_assertion.emit("DataSaver: " + err.args[0])
                self._logger.exception(err)
        else:
            try:
                with open(data["datafile"], "w") as f:
                    f.write(headerstring)
                    f.write(datastring)
            except IOError as err:
                self.sig_assertion.emit("DataSaver: " + err.args[0])
                self._logger.exception(err)

        # try:
        #     with open(data['datafile'][:-3]+'csv', 'a') as f:
        #         data['df'].to_csv(f)  # , header=False)
        # except KeyError:
        #     pass


if __name__ == "__main__":
    # dbname = 'He_first_cooldown.db'
    # conn = sqlite3.connect(dbname)
    # mycursor = conn.cursor()
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
    form = LoggingGUI(Name="Logger", identity="log")
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
