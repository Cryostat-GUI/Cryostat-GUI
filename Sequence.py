"""Module containing the class and possible helperfunctions to run a measuring sequence



    Author(s): bklebel (Benjamin Klebel)

"""


from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

# import sys
# import datetime
# import pickle
# import os
# import re
import time
from copy import deepcopy
import numpy as np
from itertools import combinations_with_replacement as comb


from util import AbstractEventhandlingThread
from util import loops_off
from util import locking
# from util import controls_software_disabled
from util import ExceptionHandling
from util import convert_time
from util import convert_time_searchable

from qlistmodel import ScanningN


class BreakCondition(Exception):
    """docstring for BreakCondition"""
    pass


def measure_resistance_singlechannel(threads,
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


def measure_resistance_multichannel(threads,
                                    excitation_currents_A,
                                    threadnames_RES,
                                    threadnames_CURR,
                                    threadname_Temp='control_LakeShore350',
                                    # temperature_sensor='Sensor_1_K',
                                    n_measurements=1,
                                    **kwargs):
    """conduct one 'full' measurement of resistance:
        arguments: dict conf
            threads = dict of threads running of the mainWindow class
            threadname_Temp  = name of the (LakeShore) Temperature thread
            threadnames_RES  = list of names of the (Keithley) Voltage measure threads 
            threadnames_CURR  = list of names of the (Keithley) Current set threads 
            n_measurements  = number of measurements (dual polarity) to be averaged over
                            default = 1 (no reason to do much more)
            excitation_currents_A = list of excitations currents for the measurement 
        returns: dict data
            T_mean_K : dict of means of temperature readings
                    before and after measurement [K]
            T_std_K : dict of stds of temperature readings
                    before and after measurement [K]
            R_mean_Ohm : dict of means of all n_measurements resistance measurements [Ohm]
            R_std_Ohm : dict of stds of all n_measurements resistance measurements [Ohm]
            timeseconds: pythons time.time()
            ReadableTime: Time in %Y-%m-%d %H:%M:%S
            SearchableTime: Time in %Y%m%d%H%M%S
    """
    # measured current reversal = 40ms.
    # reversal measured with a DMM 7510 of a 6221 Source (both Keithley)

    lengths = [len(threadnames_CURR), len(
        threadnames_RES), len(excitation_currents_A)]
    for c in comb(lengths, 2):
        if c[1] != c[2]:
            raise AssertionError(
                'number of excitation currents, current sources and voltmeters does not coincide!')

    current_reversal_time = 0.06

    data = dict()
    resistances = {key: [] for key in threadnames_CURR}

    with loops_off(threads):

        temp1 = threads[threadname_Temp][0].read_Temperatures()
        temps = {key: [val] for key, val in zip(temp1.keys(), temp1.values())}

        for ct, (name_curr, exc_curr, name_volt) in enumerate(zip(threadnames_CURR, excitation_currents_A, threadnames_RES)):

            for idx in range(n_measurements):
                # as first time, apply positive current --> pos voltage
                # (correct)
                for currentfactor in [1, -1]:
                    threads[name_curr][0].enable()
                    threads[name_curr][0].gettoset_Current_A(
                        exc_curr * currentfactor)
                    threads[name_curr][0].setCurrent_A()
                    # wait for the current to be changed:
                    time.sleep(current_reversal_time)
                    voltage = threads[name_volt][
                        0].read_Voltage() * currentfactor
                    # pure V/I, I hope that is fine.
                    resistances[name_curr].append(
                        voltage / (exc_curr * currentfactor))
                    threads[name_curr][0].disable()

        temp2 = threads[threadname_Temp][0].read_Temperatures()
        for key in temps:
            temps[key].append(temp2[key])

    data['T_mean_K'] = {key: np.mean(temps[key]) for key in temps}
    data['T_std_K'] = {key: np.std(temps[key]) for key in temps}

    data['R_mean_Ohm'] = {key: np.mean(resistances[key])
                          for key in resistances}
    data['R_std_Ohm'] = {key: np.std(resistances[key]) for key in resistances}

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

        self.sensor_control = None  # needs to be set!
        self.sensor_sample = None   # needs to be set!

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
            self.scan_T_execute(**entry)

        if entry['typ'] == 'Wait':
            self.wait_for_Temp(entry['Temp'])
            self.wait_for_Field(entry['Field'])
            time.sleep(entry['Delay'])

    def scan_T_execute(self, start, end, Nsteps, SweepRate, SpacingCode, ApproachMode, commands, **kwargs):

        temperatures, stepsize = ScanningN(start=start,
                                           end=end,
                                           N=Nsteps)
        try:
            if ApproachMode == 0:
                mode_scan = 'Fast Settle - Set Temps'
            elif ApproachMode == 1:
                mode_scan = "No o'shoot"
                raise NotImplementedError(
                    "No o'shoot is not yet implemented - highly device specific!")
            elif ApproachMode == 2:
                mode_scan = 'Sweep'
            else:
                raise AssertionError('bad Temperature ApproachMode variable!')
        except NotImplementedError:
            mode_scan = 'Fast Settle - Set Temps'
            self.sig_assertion.emit(
                'Sequence: Tscan: Mode not impelemented yet! \n I am using Fast Settle instead!')

        if mode_scan == 'Fast Settle - Set Temps':
            for temp_setpoint_sample in temperatures:
                temp_setpoint_VTI = temp_setpoint_sample - self.temp_VTI_offset
                temp_setpoint_VTI = 4.3 if temp_setpoint_VTI < 4.3 else temp_setpoint_VTI

                self.setTemperatures_hard(VTI=temp_setpoint_VTI,
                                          Sample=temp_setpoint_sample)

                self.check_Temp_in_Scan(temp_setpoint_sample)

                for entry in commands:
                    self.scan_runCommand(entry)

        elif mode_scan == 'Sweep':
            pass
            # program VTI sweep, in accordance to the VTI Offset
            # set temp and RampRate for Lakeshore
            # if T_sweepentry is arrived: do stuff

    def setTemperatures_hard(self, VTI, Sample):
        self.mainthread.threads['control_ITC'][0].gettoset_Temperature(VTI)
        self.mainthread.threads['control_ITC'][0].setTemperature()

        self.mainthread.threads['control_LakeShore350'][
            0].gettoset_Temp_K(Sample)
        self.mainthread.threads['control_LakeShore350'][0].setTemp_K()
        self.mainthread.threads['control_LakeShore350'][0].setStatusRamp(False)

    def scan_T_programSweep(self, temperatures, SweepRate):
        """
            program sweep for VTI
            program sweep for LakeShore
        """
        pass

    def scan_T_checkTemp(self, Temp, direction=0):
        # must block until the temperature has arrived at the specified point!
        pass

    def scan_runCommand(self, command):
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
        try:
            with controls_software_disabled(self.mainthread.controls, self.mainthread.controls_Lock):
                conf['store_signal'].emit(
                    deepcopy(measure_resistance_singlechannel(**conf)))
                print('measuring', convert_time(time.time()))
        finally:
            QTimer.singleShot(
                30 * 1e3, lambda: self.measure_oneshot(self.conf))


class OneShot_Thread_multichannel(AbstractEventhandlingThread):
    """docstring for OneShot_Thread"""

    sig_storing = pyqtSignal(dict)

    def __init__(self, mainthread):
        super().__init__()
        self.mainthread = mainthread

        self.mainthread.sig_measure_oneshot.connect(
            lambda: self.measure_oneshot(self.conf))
        self.conf = dict(threads=self.mainthread.threads,
                         threadname_Temp='control_LakeShore350',
                         threadname_RES=[
                             'control_Keithley2182_1', 'control_Keithley2182_2'],
                         threadname_CURR=[
                             'control_Keithley6221_1', 'control_Keithley6221_2'],
                         excitation_current_A=[0.004, 0.004])  # [A] needs to be set - thus communicated!
        self.__name__ = 'OneShot_Thread_multichannel'

    def update_conf(self, key, value):
        self.conf[key] = value

    @pyqtSlot(dict)
    @ExceptionHandling
    def measure_oneshot(self, conf):
        """invoke a single measurement and send it to saving the data"""
        try:
            print('measuring', convert_time(time.time()), '-------------')
            with locking(self.mainthread.controls_Lock):
                data = measure_resistance_singlechannel(**conf)
            self.sig_storing.emit(deepcopy(data))
                
        finally:
            QTimer.singleShot(
                10 * 1e3, lambda: self.measure_oneshot(self.conf))
