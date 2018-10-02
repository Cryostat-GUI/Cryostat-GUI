

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

import sys
import datetime
import pickle
import os
import sqlite3
import numpy as np
from copy import deepcopy


from util import AbstractLoopThread
from util import Window_ui



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
        

        self.buttonBox_finish.accepted.connect(lambda: self.sig_send_conf.emit(deepcopy(self.conf)))
        self.buttonBox_finish.accepted.connect(self.close_and_safe)
        self.buttonBox_finish.rejected.connect(self.close)


    def close_and_safe(self):
        """save the configuration dict to a file, close the window afterwards"""
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
        conf['general'] = dict(logfile_location='')
        return conf

    def read_configuration(self):
        '''search for configuration file, load it if found, initialise new dict if not found'''
        configurations = os.listdir(r'.\\configurations')
        if 'log_conf.pickle' in configurations:
            with open('configurations/log_conf.pickle', 'rb') as handle:
                self.conf = pickle.load(handle)
        else:
            self.conf = self.initialise_dicts()

class main_Logger(AbstractLoopThread):
    """This is a worker thread
    """

    sig_configuring = pyqtSignal(bool)
    sig_log = pyqtSignal()


    def __init__(self, mainthread, **kwargs):
        super().__init__(**kwargs)
        self.mainthread = mainthread

        self.interval = 3 # 60s interval for logging as initialisation

        self.mainthread.sig_logging.connect(self.store_data)
        self.mainthread.sig_logging_newconf.connect(self.update_conf)

        QTimer.singleShot(1e3, lambda: self.sig_configuring.emit(True))
        self.configuration_done = False
        self.conf_done_layer2 = False


        # QTimer.singleShot(1e3, self.initialise)
        self.not_yet_initialised = False





    # def initialise(self):
    #     self.connectdb('testdata')
    #     self.mycursor = self.conn.cursor()
    #     self.not_yet_initialised = False

        # self.test = test(ui_file='.\\configurations\\Logger_conf.ui')


    def running(self):
        try:
            # Do things
            # print('logging running')
            if self.configuration_done:
                self.sig_log.emit()
                if not self.conf_done_layer2:
                    self.sig_configuring.emit(False)
                    self.conf_done_layer2 = True
                # print('emitted signal')


        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        # finally:
        #     QTimer.singleShot(self.interval*1e3, self.running)

    # @pyqtSlot()
    # def stop(self):
    #     self.__isRunning = False

    def update_conf(self, conf):
        """
            - update the configuration with one being sent.
            - set the configuration done bool to True,
                so that self.running will actually log
            - set self.conf_done_layer2 to False,
                so that the configuring thread will be quit.

        """
        # print('updated conf for logging')
        self.conf = conf
        self.configuration_done = True
        self.conf_done_layer2 = False

    @pyqtSlot(int)
    def set_Interval(self, interval):
        """set the interval between logging events in seconds"""
        self.interval = interval



    def connectdb(self, dbname):
        try:
            # global conn
            self.conn= sqlite3.connect(dbname)
        except sqlite3.connect.Error as err:
            raise AssertionError("Logger: Couldn't establish connection {}".format(err))



    def createtable(self,tablename,dictname):

        def typeof(dictkey):
            if isinstance(dictkey,float):
                return "REAL"
            elif isinstance(dictkey,int):
                return "INTEGER"
            else:
                return "TEXT"


        sql="CREATE TABLE IF NOT EXISTS {} (id INTEGER PRIMARY KEY)".format(tablename)
        self.mycursor.execute(sql)

        #We should try to find a nicer a solution without try and except
        #try:
        for i in dictname.keys():
            try:
                sql="ALTER TABLE  {} ADD COLUMN {} {}".format(tablename,i,typeof(i))
                self.mycursor.execute(sql)
            except sqlite3.OperationalError as err:
                pass # Logger: probably the column already exists, no problem.
                # self.sig_assertion.emit("Logger: probably the column already exists, no problem. ({})".format(err))


    def updatetable(self,  tablename,dictname):
        if not dictname: 
            raise AssertionError('Logger: dict does not yet exist')
        # print('list',dictname)

        sql="INSERT INTO {} ({}) VALUES ({})".format(tablename,'CurrentTime',dictname['CurrentTime'])
        # print(sql)
        self.mycursor.execute(sql)

        for i in range(len(dictname)):
            sql="UPDATE {} SET {}='{}' WHERE {}='{}'".format(tablename,list(dictname.keys())[i],list(dictname.values())[i],'CurrentTime',dictname['CurrentTime'])
            # print(sql)
            self.mycursor.execute(sql)

        self.conn.commit()



    def printtable(self,tablename,dictname,date1,date2):

        for colnames in dictname.keys():
            print(colnames, end=',', flush=True)
        print('\n')

        sql="SELECT * from {} WHERE CurrentTime BETWEEN {} AND {}".format(tablename,date1,date2)
        self.mycursor.execute(sql)

        data = self.mycursor.fetchall()
        for row in data:
            print(row)




    def exportdatatoarr(self, tablename,colnamelist):

        array=[]

        sql="SELECT {},{},{} from {} ".format(*colnamelist,tablename)
        self.mycursor.execute(sql)
        data = self.mycursor.fetchall()

        for row in data:
            array.append(list(row))

        nparray=np.asarray(array)
        # print("the numpy array:")
        # print(nparray)
        return nparray


    @pyqtSlot(dict)
    def store_data(self, data):
        if self.not_yet_initialised: 
            return
        self.connectdb('testdata.db')
        self.mycursor = self.conn.cursor() 

        """storing logging data
            into database or logfile - to be decided!
            what data should be logged is set in self.conf
        # """
        # dbname='test'
        # tablename='measured_data'
        # # colnamelist=['Voltage', 'Current','CurrentTime']


        # #test dict:
        # testdict={
        #     "Voltage":"10",
        #     "Current" :"20",
        #     "Temperature":"0",
        #     "Testcol1":10,
        #     "Testcol2":100,
        #     "testcol3":3.1415
        # }


        timedict={"CurrentTime":datetime.datetime.now().strftime("%Y%m%d%H%M%S")} #it was the only way i could implement date and time and still select them
        # testdict={**timedict,**testdict}

        #Creating the readable time value and then appending it to the dictionary:
        timestr=str(timedict["CurrentTime"])
        ReadableTime="'"+timestr[0:4]+'-'+timestr[4:6]+'-'+timestr[6:8]+' '+timestr[8:10]+':'+timestr[10:12]+':'+timestr[12:14]+"'"
        # testdict['ReadableTime']=ReadableTime
        data['ReadableTime']=ReadableTime



        #cursor setup:

        #Optional command to delete a table, must be commented out
        #mycursor.execute("DROP TABLE measured_data")

        #initializing a table with a primary key as first column:

        names = ['ITC', 'ILM']
        for name in names: 
            try: 
                data[name].update(timedict)

                # print('creating table')
                self.createtable(name, data[name])
                #inserting in the measured values:

                # print('updating table')
                self.updatetable(name,data[name])

                # print('printing table')
                # self.printtable('ITC',data,20181001000000,20191005000000)
            except AssertionError as assertion:
                self.sig_assertion.emit(assertion.args[0])
            except KeyError as key: 
                self.sig_assertion.emit(key.args[0])

        # self.exportdatatoarr('ITC',colnamelist)

    # store_data(0,0)
    # def logging_read_configuration(self):
    #     """method to establish the configuration of
    #         what shall be logged from a respective file

    #         open window to let the user choose.

    #         Return: dictionary holding bools
    #     """
    #     return None
