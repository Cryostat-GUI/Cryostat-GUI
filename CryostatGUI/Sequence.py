"""Module containing the class and possible helperfunctions to run a measuring sequence

Author(s):
    bklebel (Benjamin Klebel)

"""


from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

# import sys
import datetime as dt
# import pickle
# import os
# import re
import time
from copy import deepcopy
import pandas as pd
import numpy as np
from numpy.polynomial.polynomial import polyfit
from itertools import combinations_with_replacement as comb


from util import AbstractThread
from util import AbstractEventhandlingThread
from util import loops_off
from util import ExceptionHandling
from util import convert_time
from util import convert_time_searchable

import measureSequences as mS

# from qlistmodel import ScanningN


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
                                    iv_characteristic,
                                    threadname_Temp='control_LakeShore350',
                                    # temperature_sensor='Sensor_1_K',
                                    # n_measurements=1,
                                    current_reversal_time=0.08,

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
            resistances, voltages, currents:
                dicts with corresponding values for all measurement channels
            timeseconds: pythons time.time()
            ReadableTime: Time in %Y-%m-%d %H:%M:%S
            SearchableTime: Time in %Y%m%d%H%M%S
    """
    # measured current reversal = 40ms.
    # reversal measured with a DMM 7510 of a 6221 Source (both Keithley)
    lengths = [len(threadnames_CURR),
               len(threadnames_RES),
               len(excitation_currents_A)]
    for c in comb(lengths, 2):
        if c[0] != c[1]:
            raise AssertionError(
                'number of excitation currents, current sources and voltmeters does not coincide!')
    data = dict()
    resistances = {key: dict(coeff=0, residuals=0, nonohmic=0)
                   for key in threadnames_RES}
    voltages = {key: [] for key in threadnames_RES}
    currents = {key: [] for key in threadnames_CURR}

    with loops_off(threads):

        temp1 = threads[threadname_Temp][0].read_Temperatures()
        temps = {key: [val] for key, val in zip(temp1.keys(), temp1.values())}

        for ct, (name_curr, exc_curr, name_volt) in enumerate(zip(threadnames_CURR, excitation_currents_A, threadnames_RES)):
            threshold_residuals = 1e4
            # threshold_coefficients = 1e4

            threads[name_curr][0].enable()

            for current_base in iv_characteristic:
                for currentfactor in [-1,  1]:
                    current = exc_curr * currentfactor * current_base
                    # print(current)
                    currents[name_curr].append(current)
                    threads[name_curr][0].gettoset_Current_A(current)
                    threads[name_curr][0].setCurrent_A()
                    # wait for the current to be changed:
                    time.sleep(current_reversal_time)
                    voltage = threads[name_volt][0].read_Voltage()
                    voltages[name_volt].append(voltage)
            c, stats = polyfit(currents[name_curr], voltages[
                               name_volt], deg=1, full=True)
            resistances[name_volt]['coeff'] = c[1]
            resistances[name_volt]['residuals'] = stats[0][0]
            # c_wrong = polyfit(currents[name_curr], voltages[
            #                   name_volt], deg=4)
            # print(stats[0], c_wrong)

            if stats[0] > threshold_residuals:
                resistances[name_volt]['nonohmic'] = 1
            # if np.any(np.array([x > threshold_coefficients for x in stats[2:]])):
            #     resistances[name_volt]['nonohmic'] = 1

            threads[name_curr][0].disable()

        temp2 = threads[threadname_Temp][0].read_Temperatures()
        for key in temps:
            temps[key].append(temp2[key])

    data['T_mean_K'] = {key + '_mean': np.mean(temps[key]) for key in temps}
    data['T_std_K'] = {
        key + '_std': np.std(temps[key], ddof=1) for key in temps}

    data['resistances'] = {key.strip('control_'): value
                           for key, value in zip(
        resistances.keys(), resistances.values())}
    data['voltages'] = {key.strip('control_'): value
                        for key, value in zip(
        voltages.keys(), voltages.values())}
    data['currents'] = {key.strip('control_'): value
                        for key, value in zip(
        currents.keys(), currents.values())}

    df = pd.DataFrame.from_dict(data)
    data['datafile'] = kwargs['datafile']
    timedict = {'timeseconds': time.time(),
                'ReadableTime': convert_time(time.time()),
                'SearchableTime': convert_time_searchable(time.time())}
    data.update(timedict)

    data['df'] = df
    # print(data)
    # for x in data: print(x)
    # df = pd.DataFrame.from_dict(data)
    return data


class Sequence_Functions(object):
    """docstring for Functions"""

    sig_message = pyqtSignal(str)

    def __init__(self, device_signals, **kwargs):
        super().__init__(**kwargs)
        self.devices = device_signals
        # self.temp_VTI_offset = probe_Toffset

    def setTemperature(self, temperature: float) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a
            certain temperature directly
            needs to be implemented.
            TODO: override method
        """
        self.devices['ITC']['setTemp'].emit(dict(isSweep=False,
                                                 isSweepStartCurrent=False,
                                                 setTemp=temperature,))
        print('setTemperature :: temp = {}'.format(temperature))

    def setField(self, field: float, EndMode: str) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a certain field directly
            needs to be implemented.
            TODO: override method
        """
        self.devices['IPS']['setField'].emit(
            dict(field=field, EndMode=EndMode))
        print(f'setField :: field = {field}, EndMode = {EndMode}')

    def setPosition(self, position: float, speedindex: float) -> None:
        """
            Method to be overridden/injected by a child class
            here, all logic which is needed to go to a
            certain position directly
            needs to be implemented.
            TODO: override method
        """
        print(f'setPosition :: pos = {position}, speedindex = {speedindex}')

    def message_to_user(self, message: str) -> None:
        """deliver a message to a user in some way

        default is printing to the command line
        may be overriden!
        """
        # super().message_to_user(message)
        # print(message)
        # self.devices['general']['message_to_user'].emit(message)
        self.sig_message.emit(message)
        print(f'message_to_user :: message = {message}')


class Sequence_Thread(mS.Sequence_runner, AbstractThread, Sequence_Functions):
    """docstring for Sequence_Thread"""

    sig_aborted = pyqtSignal()
    sig_finished = pyqtSignal(str)
    sig_message = pyqtSignal(str)

    def __init__(self, sequence: list, data: list, datalock, dataLive: list, data_LiveLock, device_signals: dict, thresholdsconf: dict, tempdefinition: list, controlsLock, **kwargs):
        super().__init__(sequence=sequence, device_signals=device_signals, **kwargs)

        self.__name__ = 'runSequence'

        self.devices = device_signals
        self.data = data
        self.dataLock = datalock
        self.data_Live = dataLive
        self.data_LiveLock = data_LiveLock
        self.tempdefinition = tempdefinition
        self.thresholdsconf = thresholdsconf
        self.controlsLock = controlsLock

    @ExceptionHandling
    def work(self):
        '''run the sequence, emit the finish-line'''
        # print('I will now start to work!')
        with self.controlsLock:
            fin = self.running()
        self.sig_finished.emit(fin)

    def scan_T_programSweep(self, start: float, end: float, Nsteps: float, temperatures: list, SweepRate: float, SpacingCode: str = 'uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep of temperatures
        """
        self.devices['ITC']['setTemp'].emit(dict(isSweep=False,
                                                 isSweepStartCurrent=False,
                                                 setTemp=start,))
        self.checkStable_Temp(temp=start, direction=0, ApproachMode='Fast')
        self.devices['ITC']['setTemp'].emit(dict(isSweep=True,
                                                 isSweepStartCurrent=True,
                                                 # setTemp=setTemp,
                                                 start=start,
                                                 end=end,
                                                 SweepRate=SweepRate))
        print(f'scan_T_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, temps: {temperatures}, Rate: {SweepRate}, SpacingCode: {SpacingCode}')

    def scan_H_programSweep(self, start: float, end: float, Nsteps: float, fields: list, SweepRate: float, EndMode: str, SpacingCode: str = 'uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep for field values
        """
        print(f'scan_H_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, fields: {fields}, Rate: {SweepRate}, SpacingCode: {SpacingCode}, EndMode: {EndMode}')

    def scan_P_programSweep(self, start: float, end: float, Nsteps: float, positions: list, speedindex: float, SpacingCode: str = 'uniform'):
        """
            Method to be overriden by a child class
            here, the devices should be programmed to start
            the respective Sweep of positions
        """
        print(f'scan_T_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, positions: {positions}, speedindex: {speedindex}, SpacingCode: {SpacingCode}')

    def setFieldEndMode(self, EndMode: str) -> bool:
        """Method to be overridden by a child class
        return bool stating success or failure (optional)
        """
        print(f'setFieldEndMode :: EndMode = {EndMode}')

    def getTemperature(self) -> float:
        """Read the temperature

        Method to be overriden by child class
        implement measuring the temperature used for control
        returns: temperature as a float
        """
        return self.readDataFromList(dataind1=self.tempdefinition[0], dataind2=self.tempdefinition[1])

    def readDataFromList(self, dataind1: str, dataind2: str, Live: bool = False) -> float:
        """retrieve a datapoint from the central list"""
        gotit = False
        uptodate = False
        datalock = self.data_LiveLock if Live else self.dataLock
        data = self.data_Live if Live else self.data
        # print('reading from list')
        try:
            while not uptodate:
                self.check_running()
                with datalock:
                    # print('locked onto the (Live=', Live, f'data: {dataind1}, {dataind2}')
                    dateentry = data[dataind1]['realtime']
                    if Live:
                        dateentry = dateentry[-1]
                    # print('time: ', dateentry)
                    # print('timediff: ', (dt.datetime.now() - dateentry).total_seconds())
                    uptodate = (dt.datetime.now() -
                                dateentry).total_seconds() < 10
                    # print('uptodate:', uptodate)
                    if not uptodate:
                        # print('not up to date')
                        self.sig_assertion.emit(
                            f'Sequence: readData: data not sufficiently up to date. ({dataind1})')
                        time.sleep(0.02)
        except KeyError as err:
            # print('KeyErr')
            self.sig_assertion.emit(
                'Sequence: readData: no data: {}'.format(err.args[0]))
            self.check_running()
            time.sleep(1)
            temp = self.readDataFromList(
                dataind1=dataind1, dataind2=dataind2, Live=Live)
            gotit = True

        # print('came through')
        if not gotit:
            temp = data[dataind1][dataind2]
        if Live:
            temp = temp[-1]
        self.sig_assertion.emit(f'Sequence: readData :: got a datum: {temp}')
        return temp

    def getPosition(self) -> float:
        """
            Method to be overriden by child class
            implement checking the position

            returns: position as a float
        """
        val = np.random.rand() * 360
        print(f'getPosition :: returning random value: {val}')
        return val

    def getField(self) -> float:
        """Read the Field

        Method to be overriden by child class
        implement measuring the field
        returns: Field as a float
        """
        val = np.random.rand() * 9
        print(f'getField :: returning random value: {val}')
        return val

    def getChamber(self):
        """Read the Chamber status

        Method to be overriden by child class
        implement measuring whether the chamber is ready
        returns: chamber status
        """
        val = np.random.rand() * 4
        print(f'getChamber :: returning random value: {val}')
        return val

    def checkStable_Temp(self, temp: float, direction: int = 0, ApproachMode: str = 'Sweep') -> bool:
        """wait for the temperature to stabilize

        param: Temp:
            the temperature which needs to be arrived to continue
            function must block until the temperature has reached this value!
            (apart from checking whether the sequence qas aborted)

        param: direction:
            indicates whether the 'Temp' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        # print('checking for stable temp')
        if direction == 0 or ApproachMode != 'Sweep':
            # no information, temp should really stabilize

            if ApproachMode == 'Sweep':
                self.sig_assertion.emit(
                    'Sequence: checkStable_Temp: no direction information available in Sweep, cannot check!')
                self.stop()
                self.check_running()

            stable = False
            while not stable:
                # print('waiting for stabilized temp')
                self.check_running()
                count = 0

                temperature = self.getTemperature()
                mean = self.readDataFromList(dataind1=self.tempdefinition[0],
                                             dataind2=self.tempdefinition[
                                                 1] + '_calc_ar_mean',
                                             Live=True)
                stderr_rel = self.readDataFromList(dataind1=self.tempdefinition[0],
                                                   dataind2=self.tempdefinition[
                                                       1] + '_calc_stderr_rel',
                                                   Live=True)
                slope_rel = self.readDataFromList(dataind1=self.tempdefinition[0],
                                                  dataind2=self.tempdefinition[
                                                      1] + '_calc_slope_rel',
                                                  Live=True)
                slope_residuals = self.readDataFromList(dataind1=self.tempdefinition[0],
                                                        dataind2=self.tempdefinition[
                                                            1] + '_calc_slope_residuals',
                                                        Live=True)

                if abs(temperature - temp) < self.thresholdsconf['threshold_temp']:
                    count += 1
                if abs(mean - temp) < self.thresholdsconf['threshold_mean']:
                    count += 1
                if abs(stderr_rel) < self.thresholdsconf['threshold_stderr_rel']:
                    count += 1
                if abs(slope_rel) < self.thresholdsconf['threshold_slope_rel']:
                    count += 1
                if abs(slope_residuals) < self.thresholdsconf['threshold_slope_residuals']:
                    count += 1

                if count >= 5:
                    stable = True
                else:
                    time.sleep(1)

        elif direction == 1:
            # temp should be rising, all temps above 'temp' are fine
            while self.getTemperature() < temp:
                self.check_running()
                # print(f'temp not yet above {temp}!')
                time.sleep(1)
        elif direction == -1:
            # temp should be falling, all temps below 'temp' are fine
            while self.getTemperature() > temp:
                self.check_running()
                # print(f'temp not yet below {temp}!')
                time.sleep(1)

        print(f'checkstable_Temp :: Temp: {temp} is stable!, ApproachMode = {ApproachMode}, direction = {direction}')

    def checkField(self, Field: float, direction: int = 0, ApproachMode: str = 'Sweep') -> bool:
        """check whether the Field has passed a certain value

        param: Field:
            the field which needs to be arrived to continue
            function must block until the field has reached this value!
            (apart from checking whether the sequence qas aborted)

        param: direction:
            indicates whether the 'Field' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        print(f'checkField :: Field: {Field} is stable!, ApproachMode = {ApproachMode}, direction = {direction}')

    def checkPosition(self, position: float, direction: int = 0, ApproachMode: str = 'Sweep') -> bool:
        """check whether the Field has passed a certain value

        param: position:
            the field which needs to be arrived to continue
            function must block until the field has reached this value!
            (apart from checking whether the sequence qas aborted)

        param: direction:
            indicates whether the 'Field' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: temperature should be rising
                direction = -1: temperature should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        print(f'checkPosition :: position: {position} is stable!, ApproachMode = {ApproachMode}, direction = {direction}')

    def Shutdown(self):
        """Shut down instruments to a safe standby-configuration"""
        print(f'Shutdown :: going into safe shutdown mode')

    def chamber_purge(self):
        """purge the chamber

        must block until the chamber is purged
        """
        print(f'chamber_purge :: purging chamber')

    def chamber_vent(self):
        """vent the chamber

        must block until the chamber is vented
        """
        print(f'chamber_vent :: venting chamber')

    def chamber_seal(self):
        """seal the chamber

        must block until the chamber is sealed
        """
        print(f'chamber_seal :: sealing chamber')

    def chamber_continuous(self, action):
        """pump or vent the chamber continuously"""
        if action == 'pumping':
            print(f'chamber_continuous :: pumping continuously')
        if action == 'venting':
            print(f'chamber_continuous :: venting continuously')

    def chamber_high_vacuum(self):
        """pump the chamber to high vacuum

        must block until the chamber is  at high vacuum
        """
        print(f'chamber_high_vacuum :: bringing the chamber to HV')

    def res_measure(self, dataflags: dict, bridge_conf: dict) -> dict:
        """Measure resistivity
            Must be overridden!
            return dict with all data according to the set dataflags
        """
        print(f'res_measure :: measuring the resistivity with the following dataflags: {dataflags} and the following bridge configuration: {bridge_conf}')
        return dict(res1=5, exc1=10, res2=8, exc2=10)

    def measuring_store_data(self, data: dict, datafile: str) -> None:
        """Store measured data
            Must be overridden!
        """
        print(f'measuring_store_data :: store the measured data: {data} in the file: {datafile}.')

    def res_datafilecomment(self, comment: str, datafile: str) -> None:
        """write a comment to the datafile
            Must be overridden!
        """
        print(f'res_datafilecomment :: write a comment: {comment} in the datafile: {datafile}.')

    def res_change_datafile(self, datafile: str, mode: str) -> None:
        """change the datafile (location)
            Must be overridden!
            mode ('a' or 'w') determines whether data should be
                'a': appended
                'w': written over
            (to) the new datafile
        """
        print(f'res_change_datafile :: change the datafile to: {datafile}, with mode {mode}.')

    @pyqtSlot()
    def setTempVTIOffset(self, offset):
        self.temp_VTI_offset = offset


class OneShot_Thread(AbstractEventhandlingThread):
    """docstring for OneShot_Thread"""

    def __init__(self, mainthread, **kwargs):
        super().__init__(**kwargs)
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
            with self.mainthread.controls_Lock:
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

        self.mainthread.sig_measure_oneshot.connect(self.measure_oneshot_once)
        # self.mainthread.sig_measure_oneshot_start.connect(self.series_start)
        # self.mainthread.sig_measure_oneshot_stop.connect(self.series_stop)
        self.iv_specs = [0.5, 1, 2]  # start/stop/nsteps
        self.iv_curve = list(reversed(np.linspace(
            self.iv_specs[0], self.iv_specs[1], self.iv_specs[2])))
        # print('iv default:', self.iv_curve)

        self.current_revtime = 0.08  # default waiting value

        self.conf = dict(threads=self.mainthread.threads,
                         threadname_Temp='control_LakeShore350',
                         threadnames_RES=[
                             'control_Keithley2182_1', 'control_Keithley2182_2'],
                         threadnames_CURR=[
                             'control_Keithley6221_1', 'control_Keithley6221_2'],
                         # [A] needs to be set - thus communicated!
                         excitation_currents_A=[0.0005, 0.0005],
                         iv_characteristic=self.iv_curve,
                         current_reversal_time=self.current_revtime,
                         interval=10)
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.measure_oneshot_once)
        self.__name__ = 'OneShot_Thread_multichannel'

    def update_conf(self, key, value):
        self.conf[key] = value

    def update_exc(self, channel, value):
        """update the excitation current for a specific channel"""
        self.conf['excitation_currents_A'][channel - 1] = value

    def update_iv(self, spec, value):
        self.iv_specs[spec] = value
        self.iv_curve = np.linspace(
            self.iv_specs[0], self.iv_specs[1], self.iv_specs[2])
        self.update_conf('iv_characteristic', self.iv_curve)

    # @pyqtSlot()
    # def series_start(self):
    #     """start the timer for the series, with the current interval"""
    #     self.timer.start(self.conf['interval']*1e3)

    # @pyqtSlot()
    # def series_stop(self):
    #     """stop the timer for the series"""
    #     self.timer.stop()

    @pyqtSlot()
    @ExceptionHandling
    def measure_oneshot_once(self):
        """invoke a single measurement and send it to saving the data"""
        with self.mainthread.controls_Lock:
            data = measure_resistance_multichannel(**self.conf)
            data['type'] = 'multichannel'
        self.sig_storing.emit(deepcopy(data))

    @pyqtSlot()
    # @ExceptionHandling
    def measure_oneshot(self):
        """invoke a single measurement and send it to saving the data"""
        try:
            # print('measuring', convert_time(time.time()), 'entering')
            self.measure_oneshot_once()

        # except AttributeError as e_arr:
        #     print(e_arr)
        finally:
            QTimer.singleShot(
                self.conf['interval'] * 1e3, lambda: self.measure_oneshot())
