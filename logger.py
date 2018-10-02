

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

import sys
import datetime
import pickle
import os
import sqlite3
import numpy as np

from util import AbstractEventhandlingThread
from util import Window_ui



class Logger_configuration(Window_ui):
    """docstring for Logger_configuration"""

    sig_send_conf = pyqtSignal(dict)

    def __init__(self, **kwargs):
        super(Logger_configuration, self).__init__(**kwargs)

        self.read_configuration()

        self.general_threads_ITC.toggled.connect(lambda value: self.setValue('ITC', 'thread', value))
        self.general_threads_ITC.toggled.connect(lambda: self.ITC_thread_running.setChecked)
        self.general_threads_ILM.toggled.connect(lambda value: self.setValue('ILM', 'thread', value))
        self.general_threads_ILM.toggled.connect(lambda: self.ILM_thread_running.setChecked)
        self.general_threads_PS.toggled.connect(lambda value: self.setValue('PS', 'thread', value))
        self.general_threads_PS.toggled.connect(lambda: self.PS_thread_running.setChecked)
        self.general_threads_Lakeshore350.toggled.connect(lambda value: self.setValue('Lakeshore350', 'thread', value))
        self.general_threads_Lakeshore350.toggled.connect(lambda: self.Lakeshore350_thread_running.setChecked)

        # self.general_threads_Current1.toggled.connect(lambda value: self.setValue('Current1', 'thread', value))
        # self.general_threads_Current1.toggled.connect(lambda: self.Current1_thread_running.setChecked)
        # self.general_threads_Current2.toggled.connect(lambda value: self.setValue('Current2', 'thread', value))
        # self.general_threads_Current2.toggled.connect(lambda: self.Current2_thread_running.setChecked)
        # self.general_threads_Nano1.toggled.connect(lambda value: self.setValue('Nano1', 'thread', value))
        # self.general_threads_Nano1.toggled.connect(lambda: self.Nano1_thread_running.setChecked)
        # self.general_threads_Nano2.toggled.connect(lambda value: self.setValue('Nano2', 'thread', value))
        # self.general_threads_Nano2.toggled.connect(lambda: self.Nano2_thread_running.setChecked)
        # self.general_threads_Nano3.toggled.connect(lambda value: self.setValue('Nano3', 'thread', value))
        # self.general_threads_Nano3.toggled.connect(lambda: self.Nano3_thread_running.setChecked)


        self.buttonBox_finish.accepted.connect(lambda: self.sig_send_conf.emit(self.conf))
        self.buttonBox_finish.accepted.connect(self.close_and_safe)
        self.buttonBox_finish.rejected.connect(self.close)
        # print(self.conf)
        # self.show()
        # MAINTHREAD crashes when showing this window!
        # TODO: FIND THE BUG!
        print('bug')


    def close_and_safe(self):
        """save the configuration dict to a file, close the window afterwards"""
        with open('configurations/log_conf.pickle', 'wb') as handle:
            pickle.dump(self.conf, handle, protocol=pickle.HIGHEST_PROTOCOL)
        self.close()


    def setValue(self, instrument, value, bools):
        self.conf[instrument][value] = bools

    def initialise_dicts(self):
        """initialise the conf dict, in case it was not handed down
            return the empty conf dict
        """
        conf = dict()
        conf['ITC'] = dict()
        conf['ILM'] = dict()
        conf['PS'] = dict()
        conf['Lakeshore350'] = dict()
        conf['Keithley Current']  = dict()
        conf['Keithley Volt']   = dict()
        return conf

    def read_configuration(self):
        '''search for configuration file, load it if found, initialise new dict if not found'''
        configurations = os.listdir(r'.\\configurations')
        if 'log_conf.pickle' in configurations:
            with open('configurations/log_conf.pickle', 'rb') as handle:
                self.conf = pickle.load(handle)
        else:
            self.conf = self.initialise_dicts()


class test(Window_ui):
    """docstring for test"""
    def __init__(self, **kwargs):
        super(test, self).__init__(**kwargs)
        # self.arg = arg
        self.show()



class Log_config_windowthread(AbstractEventhandlingThread):
    """class to handle the logging configuration window.

    """

    def __init__(self, mainthread, **kwargs):
        super(Log_config_windowthread, self).__init__(**kwargs)
        self.mainthread = mainthread


    def running(self):
        """instantiate the Logger configuration window-class,
            connect its signals, so configurations are sent properly
        """
        self.logger_conf = Logger_configuration(ui_file='.\\configurations\\Logger_conf.ui')
        # if window is closed, uncheck the menu-bar option in "show"
        self.logger_conf.sig_closing.connect(lambda: self.mainthread.action_Logging_configuration.setChecked(False))
        # if the button to accept configuration is pressed, emit signal with dict, sending it to the logger thread
        self.logger_conf.sig_send_conf.connect(lambda conf: self.mainthread.sig_logging_newconf.emit(conf))
        # self.logger_conf.show()
        # print('run log config thread')
        # print(self.mainthread.threads['logger_confwindow'])




class main_Logger(AbstractEventhandlingThread):

    """This is a worker thread
    """

    sig_configuring = pyqtSignal(bool)
    sig_log = pyqtSignal()


    def __init__(self, mainthread, **kwargs):
        super().__init__(**kwargs)
        self.mainthread = mainthread

        self.interval = 2 # 60s interval for logging as initialisation

        self.mainthread.sig_logging.connect(self.store_data)
        self.mainthread.sig_logging_newconf.connect(self.update_conf)

        QTimer.singleShot(1e3, lambda: self.sig_configuring.emit(True))
        self.configuration_done = False
        self.conf_done_layer2 = False


        self.connectdb('testdata')
        self.mycursor = self.conn.cursor()



        # self.test = test(ui_file='.\\configurations\\Logger_conf.ui')


    def running(self):
        try:
            # Do things
            print('logging running')
            if self.configuration_done:
                self.sig_log.emit()
                if not self.conf_done_layer2:
                    self.sig_configuring.emit(False)
                    self.conf_done_layer2 = True
                print('emitted signal')


        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval*1e3, self.running)

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
        print('updated conf for logging')
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
            rase AssertionError("Logger: Couldn't establish connection {}".format(err))



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
                raise AssertionError("Logger: prabably the column already exists, no problem. ({})".format(err))


    def updatetable(self,  tablename,dictname):

        sql="INSERT INTO {} ({}) VALUES ({})".format(tablename,list(dictname.keys())[0],list(dictname.values())[0])
        self.mycursor.execute(sql)

        for i in range(len(dictname)):
            sql="UPDATE {} SET {}={} WHERE {}={}".format(tablename,list(dictname.keys())[i],list(dictname.values())[i],list(dictname.keys())[0],list(dictname.values())[0])
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
        print("the numpy array:")
        print(nparray)


    @pyqtSlot(dict)
    def store_data(self, data):
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
        data.update(timedict)



        #cursor setup:

        #Optional command to delete a table, must be commented out
        #mycursor.execute("DROP TABLE measured_data")

        #initializing a table with a primary key as first column:


        createtable('ITC', data['ITC'])

        #inserting in the measured values:


        updatetable('ITC',data['ITC'])


        printtable('ITC',data,20181001000000,20181005000000)


        exportdatatoarr(tablename,colnamelist)

    # store_data(0,0)
    # def logging_read_configuration(self):
    #     """method to establish the configuration of
    #         what shall be logged from a respective file

    #         open window to let the user choose.

    #         Return: dictionary holding bools
    #     """
    #     return None