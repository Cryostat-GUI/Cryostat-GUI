import random as s
import datetime as datetime
from util import AbstractLoopThreadClient
from util import ExceptionHandling
import time as t
from datetime import datetime 
import datetime
from util import running_thread
from util import AbstractMainApp
from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTimer
import sys
import os
class time(AbstractLoopThreadClient):
    data={}
    def __init__(self, mainthread=None, comLock=None, InstrumentAddress="", Lockin=None, **kwargs):
        super().__init__(**kwargs)
        print("time is running")
        self.__name__ = "Keithley6221_1_updater "
    @ExceptionHandling
    def running(self):
        self.run_finished = False
        self.data['time']=datetime.datetime.now()-datetime.timedelta(minutes=6)
        self.data["Frequency_Hz"] = s.randint(1,10)
        self.data["Voltage_V"] = s.randint(1,10)
        self.data["X_V"] = s.randint(1,10)
        self.data["Y_V"] = s.randint(1,10)
        self.data["R_V"] = s.randint(1,10)
        self.data["Theta_Deg"] = s.randint(1,10)
        self.data["ShuntResistance_user_Ohm"] = s.randint(1,10)
        self.data["ContactResistance_user_Ohm"] = s.randint(1,10)

        #print(self.data)
        t.sleep(1)
        #print(self.data)
        self.run_finished = True
    def act_on_command(self, command):
        """execute commands sent on downstream"""
        # -------------------------------------------------------------------------------------------------------------------------
        # commands, like for adjusting a set temperature on the device
        # commands are received via zmq downstream, and executed here
        if "setFrequency" in command:
            print(command)
        if "setVoltage" in command:
            print(command)
        if "set_Output" in command:
            print(command)
            self.data["set_Output"]=command["set_Output"]
        if "Display_1" in command:
            print(command)
class main_app_time(AbstractMainApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        QTimer.singleShot(0, self.run_Hardware)	
    
    def run_Hardware(self):
        self.running_thread_control(time(                  
                    InstrumentAddress='self._InstrumentAddress',
                    mainthread=None,
                    identity='Keithley6221_1',
                    Lockin='self._Lockin',
                    prometheus_port=8006,
                    prometheus_name='sr830_test'
                
                ), "tesst")





if __name__ == "__main__":





    Sr830_InstrumentAddress = "GPIB::9::INSTR"
            # Sr860_InstrumentAddress: 'filler'

    app = QtWidgets.QApplication(sys.argv)
    form = main_app_time(

            )
    form.show()
    sys.exit(app.exec_())
