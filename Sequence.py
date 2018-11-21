"""Module containing the class and possible helperfunctions to run a measuring sequence



    Author(s): bklebel (Benjamin Klebel)

"""


from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot

# import sys
# import datetime
# import pickle
# import os
# import re
import time
from copy import deepcopy
import numpy as np


from util import AbstractEventhandlingThread
from util import loops_off, controls_software_disabled
from util import ExceptionHandling
from util import convert_time, convert_time_searchable


class BreakCondition(Exception):
    """docstring for BreakCondition"""
    pass


def measure_resistance(threads,
                       excitation_current_A,
                       threadname_RES,
                       threadname_CURR,
                       threadname_Temp='control_LakeShore350',
                       temperature_sensor='Sensor_1_K',
                       n_measurements=1,
                       **kwargs):
    """conduct one 'full' measurement of resistance:
        arguments: dict conf
            threads = dict of threads running of the mainWindow class
            threadname_Temp  = name of the (LakeShore) Temperature thread
            threadname_RES  = name of the (Keithley) Voltage measure thread
            threadname_CURR  = name of the (Keithley) Current set thread
            n_measurements  = number of measurements (dual polarity) to be averaged over
                            default = 1 (no reason to do much more)
            excitation_current_A = excitation current for the measurement
        returns: dict data
            T_mean_K : mean of temperature readings
                    before and after measurement [K]
            T_std_K : std of temperature readings
                    before and after measurement [K]
            R_mean_Ohm : mean of all n_measurements resistance measurements [Ohm]
            R_std_Ohm : std of all n_measurements resistance measurements [Ohm]


    """
    # measured current reversal = 40ms.
    # reversal measured with a DMM 7510 of a 6221 Source (both Keithley)
    current_reversal_time = 0.06

    data = dict()
    temps = []
    resistances = []  # pos & neg

    with loops_off(threads):
        threads[threadname_CURR][0].enable()
        temps.append(threads[threadname_Temp][
                     0].read_Temperatures()[temperature_sensor])

        for idx in range(n_measurements):
            # as first time, apply positive current --> pos voltage (correct)
            for currentfactor in [1, -1]:
                threads[threadname_CURR][0].gettoset_Current_A(
                    excitation_current_A * currentfactor)
                threads[threadname_CURR][0].setCurrent_A()
                # wait for the current to be changed:
                time.sleep(current_reversal_time)
                voltage = threads[threadname_RES][
                    0].read_Voltage() * currentfactor
                # pure V/I, I hope that is fine.
                resistances.append(
                    voltage / (excitation_current_A * currentfactor))

        temps.append(threads[threadname_Temp][
                     0].read_Temperatures()[temperature_sensor])

    data['T_mean_K'] = np.mean(temps)
    data['T_std_K'] = np.std(temps)

    data['R_mean_Ohm'] = np.mean(resistances)
    data['R_std_Ohm'] = np.std(resistances)
    data['datafile'] = kwargs['datafile']
    timedict = {'timeseconds': time.time(),
                'ReadableTime': convert_time(time.time()),
                'SearchableTime': convert_time_searchable(time.time())}
    data.update(timedict)
    return data


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

        self.temp_VTI_offset = 5

    def running(self):
        with controls_software_disabled(self.mainthread.controls, self.mainthread.controls_lock):
            try:
                for entry in self.sequence:
                    self.execute_sequence_entry(entry)
            except BreakCondition:
                self.sig_aborted.emit()
                return 'Aborted!'

    def execute_sequence_entry(self, entry):
        if entry['typ'] == 'scan_T':
            self.execute_scan_T(entry)

        if entry['typ'] == 'Wait':
            self.wait_for_Temp(entry['Temp'])
            self.wait_for_Field(entry['Field'])
            time.sleep(entry['Delay'])

    def execute_scan_T(self, entry):
        for temp_setpoint_sample in entry['sequence_temperature']:
            temp_setpoint_VTI = temp_setpoint_sample - self.temp_VTI_offset
            temp_setpoint_VTI = 4.3 if temp_setpoint_VTI < 4.3 else temp_setpoint_VTI

            self.mainthread.threads['control_ITC'][
                0].gettoset_Temperature(temp_setpoint_VTI)
            self.mainthread.threads['control_ITC'][0].setTemperature()

            self.mainthread.threads['control_LakeShore350'][
                0].gettoset_Temp_K(temp_setpoint_sample)
            self.mainthread.threads['control_LakeShore350'][0].setTemp_K()

            self.check_Temp_in_Scan(temp_setpoint_sample)

        # always use the sweep option, so the rate can be controlled!
        # in case stabilisation is needed, just sweep to the respective point
        # (let's try this...)

    def check_Temp_in_Scan(self, Temp, direction=0):
        pass

    def wait_for_Temp(self, Temp_target, threshold=0.01):
        """repeatedly check whether the temperature was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        # check for break condition
        if not self.__isRunning:
            raise BreakCondition
        with self.dataLock:
            Temp_now = self.mainthread.data['LakeShore350']['Sensor_1_K']
        while abs(Temp_now - Temp_target) > threshold:
            with self.dataLock:
                # check for value
                Temp_now = self.mainthread.data['LakeShore350']['Sensor_1_K']
            # sleep for short time OUTSIDE of Lock
            time.sleep(0.1)

    def wait_for_Field(self, Field):
        """repeatedly check whether the field was reached,
            given the respective threshold, return once it has
            produce a possibility to abort the sequence, through
            repeated check for value, for breaking condition, and sleeping
        """
        # check for break condition
        if not self.__isRunning:
            raise BreakCondition
        with self.dataLock:
            # check for value
            pass

        # sleep for short time OUTSIDE of Lock
        time.sleep(0.1)

    def stop(self):
        """stop the sequence execution by setting self.__isRunning to False"""
        self.__isRunning = False

    @pyqtSlot()
    def setTempVTIOffset(self, offset):
        self.temp_VTI_offset = offset


class OneShot_Thread(AbstractEventhandlingThread):
    """docstring for OneShot_Thread"""

    def __init__(self, mainthread):
        super(OneShot_Thread, self).__init__()
        self.mainthread = mainthread

        self.mainthread.sig_measure_oneshot.connect(
            lambda: self.measure_oneshot(self.conf))
        self.conf = dict(store_signal=self.mainthread.sig_log_measurement,
                         threads=self.mainthread.threads,
                         threadname_Temp='control_LakeShore350',
                         threadname_RES=None,
                         threadname_CURR=None,
                         excitation_current_A=None)  # needs to be set - thus communicated!
        self.__name__ = 'OneShot_Thread'

    def update_conf(self, key, value):
        self.conf[key] = value

    @pyqtSlot(dict)
    @ExceptionHandling
    def measure_oneshot(self, conf):
        """invoke a single measurement and send it to saving the data"""
        with controls_software_disabled(self.mainthread.controls, self.mainthread.controls_Lock):
            conf['store_signal'].emit(deepcopy(measure_resistance(**conf)))
