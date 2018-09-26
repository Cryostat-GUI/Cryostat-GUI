from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

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
    # def __init__(self, message, *args, **kwargs):
    #     super(BreakCondition, self).__init__(*args, **kwargs)
    #     self.message = message
        

class Sequence_Thread(AbstractEventhandlingThread):
    """docstring for Sequence_Thread"""

    sig_aborted = pyqtSignal()

    def __init__(self, mainthread, sequence):
        super(Sequence_Thread, self).__init__()
        self.__isRunning = True
        self.sequence = sequence
        self.dataLock = mainthread.dataLock

        self.threshold_Temp = 0.1
        self.threshold_Field = 0.1

    def running(self):
        try: 
            self.mainthread.ITC_window.widgetSetpoints.setEnabled(False)
            for entry in self.sequence:
                if entry['typ'] == 'scan_T':
                    pass
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
                



    def wait_for_Temp(self, Temp):
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
