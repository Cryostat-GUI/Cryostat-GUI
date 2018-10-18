from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot

# import sys
# import datetime
# import pickle
# import os
# import re
import time

from util import AbstractEventhandlingThread

class BreakCondition(Exception):
    """docstring for BreakCondition"""
    pass


class Sequence_Thread(AbstractEventhandlingThread):
    """docstring for Sequence_Thread"""

    sig_aborted = pyqtSignal()

    def __init__(self, mainthread, sequence):
        super(Sequence_Thread, self).__init__()
        self.__isRunning = True
        self.sequence = sequence
        self.mainthread = mainthread
        self.dataLock = mainthread.dataLock

        self.threshold_Temp = 0.1
        self.threshold_Field = 0.1

    def running(self):
        try:
            self.mainthread.ITC_window.widgetSetpoints.setEnabled(False)
            self.mainthread.ILM_window.widgetSetpoints.setEnabled(False)
            self.mainthread.IPS_window.widgetSetpoints.setEnabled(False)
            self.mainthread.LakeShore350_window.widgetSetpoints.setEnabled(False)
            for entry in self.sequence:
                if entry['typ'] == 'scan_T':
                    for temp_setpoint_sample in entry['sequence_temperature']:
                        temp_setpoint_VTI = temp_setpoint_sample - 5
                        temp_setpoint_VTI =  4.3 if temp_setpoint_VTI < 4.3 else temp_setpoint_VTI

                        self.mainthread.threads['control_ITC'][0].gettoset_Temperature(temp_setpoint_VTI)
                        self.mainthread.threads['control_ITC'][0].setTemperature()

                        self.mainthread.threads['control_LakeShore350'][0].gettoset_Temp_K(temp_setpoint_sample)
                        self.mainthread.threads['control_LakeShore350'][0].setTemp_K()

                        self.check_Temp_in_Scan(temp_setpoint_sample)

                    # always use the sweep option, so the rate can be controlled!
                    # in case stabilisation is needed, just sweep to the respective point (let's try this...)
                if entry['typ'] == 'Wait':
                    self.wait_for_Temp(entry['Temp'])
                    self.wait_for_Field(entry['Field'])
                    time.sleep(entry['Delay'])
        except BreakCondition:
            self.sig_aborted.emit()
            return 'Aborted!'
        finally:
            self.mainthread.ITC_window.widgetSetpoints.setEnabled(True)
            self.mainthread.ILM_window.widgetSetpoints.setEnabled(True)
            self.mainthread.IPS_window.widgetSetpoints.setEnabled(True)
            self.mainthread.LakeShore350_window.widgetSetpoints.setEnabled(True)


    def check_Temp_in_Scan(self, Temp, direction=0):
        pass


    def wait_for_Temp(self, Temp_target, threshold=0.01):
        """repeatedly check whether the temperature was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        with self.dataLock:
            # check for value
            # check for break condition
            if not self.__isRunning:
                raise BreakCondition
            Temp_now = self.mainthread.data['LakeShore350']['Sensor_1_K']
            if abs(Temp_now-Temp_target) < threshold:
                return

        # sleep for short time OUTSIDE of Lock
        time.sleep(0.1)

    def wait_for_Field(self, Field):
        """repeatedly check whether the field was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        with self.dataLock:
            # check for value
            # check for break condition
            if not self.__isRunning:
                raise BreakCondition

        # sleep for short time OUTSIDE of Lock
        time.sleep(0.1)



    def stop(self):
        """stop the sequence execution by setting self.__isRunning to False"""
        self.__isRunning = False
