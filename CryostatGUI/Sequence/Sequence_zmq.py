from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot

import sys
import time
import logging

from threading import Lock
from json import loads

from pid import PidFile
from pid import PidFileError

from datetime import datetime as dt


import pandas as pd
import numpy as np

from noconflict import classmaker

import measureSequences as mS

from util import AbstractThread
from util.zmqcomms import dictdump

# from util.zmqcomms import raiseProblemAbort
from util.zmqcomms import zmqMainControl
from util.util_misc import CustomStreamHandler
from util.util_misc import calculate_timediff
from util import problemAbort

from Sequence_abstract_measurements import AbstractMeasureResistance

# from Sequence import AbstractMeasureResistanceMultichannel


logger = logging.getLogger("CryostatGUI.Sequences_zmq")


class Sequence_comms_zmq(zmqMainControl):
    """docstring for Sequence_comms_zmq"""

    device_ids = dict(
        chan1=dict(V="Keithley2182_1", A="Keithley6221_1"),
        chan2=dict(V="Keithley2182_2", A="Keithley6221_2"),
    )

    # @raiseProblemAbort(raising=True)
    def readDataFromList(
        self, dataindicator1: str, dataindicator2: str, Live: bool = False
    ) -> float:
        return super()._bare_readDataFromList(dataindicator1, dataindicator2, Live)

    # @raiseProblemAbort(raising=True)
    def retrieveDataIndividual(self, dataindicator1, dataindicator2, Live=True):
        return super()._bare_retrieveDataIndividual(
            dataindicator1, dataindicator2, Live=True
        )


class Sequence_functionsConvenience:
    """docstring for Sequence_convenience
    Needs the following methods,
        implemented inside the class inheritance tree:
        self.getTemperature()
        self.readDataFromList()
    """

    def __init__(self, thresholdsconf: dict, tempdefinition: list, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.tempdefinition = tempdefinition
        # dict of two lists/tuples:
        #   'control'  &   'sample'
        # TODO: implement behavior
        self.thresholdsconf = thresholdsconf

    @pyqtSlot(dict)
    def storing_thresholds(self, thresholds: dict):
        self.thresholdsconf = thresholds

    def checkStable_Temp(
        self,
        temp: float,
        direction: int = 0,
        ApproachMode: str = "Sweep",
        weak: bool = False,
        sensortype="control",
        timeout: float = 0,
    ) -> bool:
        if sensortype == "both":
            r1 = self._checkStable_Temp(
                temp=temp,
                direction=direction,
                ApproachMode=ApproachMode,
                weak=weak,
                sensortype="control",
                timeout=timeout,
            )
            r2 = self._checkStable_Temp(
                temp=temp,
                direction=direction,
                ApproachMode=ApproachMode,
                weak=weak,
                sensortype="sample",
                timeout=timeout,
            )
            if r1 and r2:
                return True
            return False
        else:
            return self._checkStable_Temp(
                temp=temp,
                direction=direction,
                ApproachMode=ApproachMode,
                weak=weak,
                sensortype=sensortype,
                timeout=timeout,
            )

    def _checkStable_Temp(
        self,
        temp: float,
        direction: int = 0,
        ApproachMode: str = "Sweep",
        weak: bool = False,
        sensortype="control",
        timeout=0,
    ) -> bool:
        """wait for the temperature to stabilize

        param: temp:
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
            ApproachMode = Sweep: only for sweeps

        param: weak:
            TODO: implement behavior
            if True, do not check for distance to the temperature,
            bot only for slope and residuals and mean stderr

        param: sensortype:
            indicates which sensor from the tempdefinition to use:
                sensortype = 'control': self.tempdefinition['control']
                sensortype = 'sample': self.tempdefinition['sample']
                sensortype = 'both': check for stability in both values

        param: timeout:
            float [s]
            if timeout is exceeded, blocking behavior of the method is lifted,
                return value should be False if timeout is exceeded
                to be used with direction 0
                if set to 0, timeout is infinite, method blocks until stability
                is reached
        """
        return self._checkStable_Value(
            val=temp,
            direction=direction,
            ApproachMode=ApproachMode,
            weak=False,
            timeout=timeout,
            dataindicator1=self.tempdefinition[sensortype][0],
            dataindicator2=self.tempdefinition[sensortype][1],
            value_name="temperature",
            value_unit="K",
            getfunc=self.getTemperature,
            thresholdsconf=self.thresholdsconf["temperature"],
        )

    def _checkStable_Value(
        self,
        val: float,
        direction: int = 0,
        ApproachMode: str = "Sweep",
        weak: bool = False,
        timeout: float = 0,
        dataindicator1: str = None,
        dataindicator2: str = None,
        value_name: str = "tempearture",
        value_unit: str = "",
        getfunc=None,
        thresholdsconf=None,
    ) -> bool:
        """wait for a value to stabilize

        param: val:
            the temperature which needs to be arrived to continue
            function must block until the value has reached this value!
            (apart from checking whether the sequence has aborted)

        param: direction:
            indicates whether the 'val' should currently be
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: value should be rising
                direction = -1: value should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called
            ApproachMode = Sweep: only for sweeps

        param: weak:
            if True, do not check for distance to the specified value,
            but only for slope and residuals and mean stderr

        param: timeout:
            float [s]
            if timeout is exceeded, blocking behavior of the method is lifted,
                return value should be False if timeout is exceeded
                to be used with direction 0
                if set to 0, timeout is infinite, method blocks until stability
                is reached

        TODO: change thresholdsconf to variable thing for different values
        """

        if getfunc is None:

            def getfunc():
                return self.readDataFromList(
                    dataindicator1=dataindicator1,
                    dataindicator2=dataindicator2,
                    Live=False,
                )

        self._logger.debug(
            f"checking for stable {value_name}: {val} {value_unit} with mode {ApproachMode}"
        )

        starttime = dt.now()

        if direction == 0 or ApproachMode != "Sweep":
            # no information, temp should really stabilize

            stable = False
            # count = None
            value_now = 0
            stable_values = []
            while not stable:
                if timeout == 0:
                    pass
                else:
                    within_time_window, timediff = calculate_timediff(
                        starttime, float(timeout)
                    )
                    if not within_time_window:
                        return False

                stable_values = []
                self.check_running()

                value_now = getfunc()
                qdict = {
                    "mean": {
                        "instr": dataindicator1,
                        "value": dataindicator2 + "_calc_ar_mean",
                    },
                    "stderr_rel": {
                        "instr": dataindicator1,
                        "value": dataindicator2 + "_calc_stderr_rel",
                    },
                    "relslope_Xpmin": {
                        "instr": dataindicator1,
                        "value": dataindicator2 + "_calc_slope_rel",
                    },
                    "slope_residuals": {
                        "instr": dataindicator1,
                        "value": dataindicator2 + "_calc_slope_residuals",
                    },
                }
                all_data = self.retrieveDataMultiple(dataindicators=qdict, Live=True)
                all_data["data"].update({"value": value_now})

                all_values = [
                    "value",
                    "mean",
                    "stderr_rel",
                    "relslope_Xpmin",
                    "slope_residuals",
                ]
                for ct, label in enumerate(all_values):
                    try:
                        vn = all_data["data"][label]
                        if ct < 2:
                            compared_value = abs(vn - val)
                        else:
                            compared_value = abs(vn)
                        if compared_value < thresholdsconf[label]:
                            stable_values.append(label)
                    except TypeError as e_type:
                        # self._logger.warning("received wrong type (possibly None): ")
                        self._logger.exception(e_type)
                        continue

                missing_values = [
                    v_missing
                    for v_missing in all_values
                    if v_missing not in stable_values
                ]
                self._logger.info(
                    f"waiting for {value_name}: {val:.4f}, current: {value_now:.4f}{value_unit}, "
                    + f"indicators ({len(stable_values):d}/5): {stable_values}, "
                    + f"missing ({len(stable_values):d}/5): {missing_values}"
                )

                if len(stable_values) >= 5:
                    stable = True
                elif (
                    weak
                    and len(stable_values) >= 3
                    and all(
                        v_missing in missing_values for v_missing in ("value", "mean")
                    )
                ):
                    stable = True
                else:
                    time.sleep(1)

        elif direction == 1:
            # temp should be rising, all temps above 'temp' are fine
            value_now = getfunc()
            while value_now < val:
                value_now = getfunc()
                try:
                    float(value_now)
                except TypeError as e_type:
                    self._logger.exception(e_type)
                    value_now = -np.inf
                self.check_running()
                self._logger.debug(
                    f"{value_name} not yet above {val} (current: {value_now:.3f})"
                )
                time.sleep(1)
        elif direction == -1:
            # temp should be falling, all temps below 'temp' are fine
            value_now = getfunc()
            while value_now > val:
                value_now = getfunc()
                try:
                    float(value_now)
                except TypeError as e_type:
                    self._logger.exception(e_type)
                    value_now = np.inf
                self.check_running()
                self._logger.debug(
                    f"{value_name} not yet below {val} (current: {value_now:.3f})"
                )
                time.sleep(1)

        self._logger.info(
            f"{value_name} {val} is stable! ({value_now}), ApproachMode = {ApproachMode}, direction = {direction}"
        )
        return True


class Sequence_functionsPersonal:
    """docstring for Sequence_functionsPersonal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    def setTemperature(self, temperature: float) -> None:
        """set the system temperature to parameter temperature
        internal command dict for hardware drivers:
            dict(isSweep=isSweep,
                 isSweepStartCurrent=isSweepStartCurrent,
                 setTemp=setTemp,
                 start=start,
                 end=end,
                 SweepRate=SweepRate
            )
        """
        self._setpoint_temp = temperature
        self.commanding(
            ID=self.tempdefinition["control"][0],
            message=dictdump(
                {
                    "setTemp_K": dict(
                        isSweep=False,
                        isSweepStartCurrent=False,
                        setTemp=temperature,
                    )
                }
            ),
        )
        self._logger.debug("setting the temp to {}K, no sweep".format(temperature))

    def setField(self, field: float, EndMode: str) -> None:
        """
        Method to be overridden/injected by a child class
        here, all logic which is needed to go to a certain field directly
        needs to be implemented.
        TODO: override method
        """
        # self.devices["IPS"]["setField"].emit(dict(field=field, EndMode=EndMode))
        self._logger.debug(f"setting the field to {field}T, EndMode = {EndMode}")
        raise NotImplementedError

    def setPosition(self, position: float, speedindex: float) -> None:
        """
        Method to be overridden/injected by a child class
        here, all logic which is needed to go to a
        certain position directly
        needs to be implemented.
        TODO: override method
        """
        self._logger.debug(
            f"setting the position to {position}, speedindex = {speedindex}"
        )
        self._logger.debug("Not Implemented!")
        # raise NotImplementedError

    def scan_T_programSweep(
        self,
        start: float = None,
        isSweepStartCurrent: bool = False,
        end: float = None,
        Nsteps: float = None,
        temperatures: list = None,
        SweepRate: float = None,
        SpacingCode: str = "uniform",
    ):
        """
        Method to be overriden by a child class
        here, the devices should be programmed to start
        the respective Sweep of temperatures
        """
        if not isSweepStartCurrent:
            self.setTemperature(temperature=start)
            self.checkStable_Temp(temp=start, direction=0, ApproachMode="Fast")
        self.commanding(
            ID=self.tempdefinition["control"][0],
            message=dictdump(
                {
                    "setTemp_K": dict(
                        isSweep=True,
                        isSweepStartCurrent=True,
                        start=start,
                        end=end,
                        SweepRate=SweepRate,
                    )
                }
            ),
        )
        self._logger.debug(
            f"scan_T_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, temps: {temperatures}, Rate: {SweepRate}, SpacingCode: {SpacingCode}"
        )

    def scan_H_programSweep(
        self,
        start: float,
        end: float,
        Nsteps: float,
        fields: list,
        SweepRate: float,
        EndMode: str,
        SpacingCode: str = "uniform",
    ):
        """
        Method to be overriden by a child class
        here, the devices should be programmed to start
        the respective Sweep for field values
        TODO: implement for IPS
        """
        self._logger.debug(
            f"scan_H_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, fields: {fields}, Rate: {SweepRate}, SpacingCode: {SpacingCode}, EndMode: {EndMode}"
        )
        raise NotImplementedError

    def scan_P_programSweep(
        self,
        start: float,
        end: float,
        Nsteps: float,
        positions: list,
        speedindex: float,
        SpacingCode: str = "uniform",
    ):
        """
        Method to be overriden by a child class
        here, the devices should be programmed to start
        the respective Sweep of positions
        TODO: implement for pressure
        """
        self._logger.debug(
            f"scan_T_programSweep :: start: {start}, end: {end}, Nsteps: {Nsteps}, positions: {positions}, speedindex: {speedindex}, SpacingCode: {SpacingCode}"
        )
        raise NotImplementedError

    def setFieldEndMode(self, EndMode: str) -> bool:
        """Method to be overridden by a child class
        return bool stating success or failure (optional)
        TODO: implement for IPS
        """
        self._logger.debug(f"setFieldEndMode :: EndMode = {EndMode}")
        raise NotImplementedError

    def getPosition(self) -> float:
        """
        Method to be overriden by child class
        implement checking the position

        returns: position as a float
        TODO: implement for pressure
        """
        raise NotImplementedError
        # val = np.random.rand() * 360
        # self._logger.debug(f"getPosition :: returning random value: {val}")
        # return val

    def getField(self) -> float:
        """Read the Field

        Method to be overriden by child class
        implement measuring the field
        returns: Field as a float
        TODO: implement for IPS
        """
        raise NotImplementedError
        # val = np.random.rand() * 9
        # self._logger.debug(f"getField :: returning random value: {val}")
        # return val

    def getTemperature(self) -> float:
        """Read the temperature

        Method to be overriden by child class
        implement measuring the temperature used for control
        returns: temperature as a float
        """
        answer = self.readDataFromList(
            dataindicator1=self.tempdefinition["control"][0],
            dataindicator2=self.tempdefinition["control"][1],
            Live=False,
        )
        # self._logger.debug("received temperature: %s", answer)
        return answer

    def getTemperature_force(self, sensortype) -> float:
        """retrieve temperature from device directly"""
        device = self.tempdefinition[sensortype][0]

        answer_dict = self.query_device_command(
            device_id=device,
            command=dict(measure_Sensor_K=self.tempdefinition[sensortype][1]),
        )
        return answer_dict["Temperature_K"]

    def checkField(
        self, Field: float, direction: int = 0, ApproachMode: str = "Sweep"
    ) -> bool:
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
        TODO: implement for IPS
        """
        self._logger.debug(
            f"Field {Field} is stable!, ApproachMode = {ApproachMode}, direction = {direction}"
        )
        raise NotImplementedError

    def checkPosition(
        self, position: float, direction: int = 0, ApproachMode: str = "Sweep"
    ) -> bool:
        """check whether the Field has passed a certain value

        param: position:
            the position which needs to be arrived to continue
            function must block until the position has reached this value!
            (apart from checking whether the sequence was aborted)

        param: direction:
            indicates whether the 'position' should currently go in a certain direction
                rising or falling
                direction =  0: default, no information / non-sweeping
                direction =  1: values should be rising
                direction = -1: values should be falling

        param: ApproachMode:
            specifies the mode of approach in the scan this function is called

        method should be overriden - possibly some convenience functionality
            will be added in the future
        TODO: implement for pressure
        """
        self._logger.debug(
            f"checkPosition :: position: {position} is stable!, ApproachMode = {ApproachMode}, direction = {direction}"
        )
        raise NotImplementedError

    def Shutdown(self):
        """Shut down instruments to a safe standby-configuration"""
        self._logger.debug("going into safe shutdown mode")
        self._logger.warning(
            "no commands specified for shutdown mode, leaving everything 'as is'"
        )

    def res_measure(self, dataflags: dict, bridge_conf: dict) -> dict:
        """Measure resistivity
        Must be overridden!
        return dict with all data according to the set dataflags
        """
        self._logger.debug(
            f" measuring the resistivity with the following dataflags: {dataflags} and the following bridge configuration: {bridge_conf}"
        )
        raise NotImplementedError
        # return dict(res1=5, exc1=10, res2=8, exc2=10)

    def measuring_store_data(self, data: dict, datafile: str) -> None:
        """Store measured data"""
        if not all(isinstance(data[key], list) for key in data):
            df = pd.DataFrame(
                {key: [data[key]] for key in data if not isinstance(data[key], list)}
            )
        else:
            df = pd.DataFrame(data)

        with open(datafile, "a", newline="") as f:
            df.tail(1).to_csv(f, header=f.tell() == 0, index=False)

        self._logger.debug(f" store the measured data: {data} in the file: {datafile}.")

    def res_datafilecomment(self, comment: str, datafile: str) -> None:
        """write a comment to the datafile
        Must be overridden!
        TODO: implement
        """
        self._logger.debug(f" write a comment: {comment} in the datafile: {datafile}.")
        raise NotImplementedError

    def res_change_datafile(self, datafile: str, mode: str) -> None:
        """change the datafile (location)
        Must be overridden!
        mode ('a' or 'w') determines whether data should be
            'a': appended
            'w': written over
        (to) the new datafile
        """
        self.datafile = datafile
        if mode == "w":
            with open(datafile, "w") as f:
                f.write("")
        self._logger.debug(f" change the datafile to: {datafile}, with mode {mode}.")


class Sequence_functionsPersonal_chamberrelated:
    def getChamber(self):
        """Read the Chamber status

        Method to be overriden by child class
        implement measuring whether the chamber is ready
        returns: chamber status
        """
        raise NotImplementedError
        # val = np.random.rand() * 4
        # self._logger.debug(f'getChamber :: returning random value: {val}')
        # return val

    def chamber_purge(self):
        """purge the chamber

        must block until the chamber is purged
        """
        self._logger.debug("chamber_purge :: purging chamber")
        raise NotImplementedError

    def chamber_vent(self):
        """vent the chamber

        must block until the chamber is vented
        """
        self._logger.debug("chamber_vent :: venting chamber")
        raise NotImplementedError

    def chamber_seal(self):
        """seal the chamber

        must block until the chamber is sealed
        """
        self._logger.debug("chamber_seal :: sealing chamber")
        raise NotImplementedError

    def chamber_continuous(self, action):
        """pump or vent the chamber continuously"""
        if action == "pumping":
            self._logger.debug("chamber_continuous :: pumping continuously")
        if action == "venting":
            self._logger.debug("chamber_continuous :: venting continuously")
        raise NotImplementedError

    def chamber_high_vacuum(self):
        """pump the chamber to high vacuum

        must block until the chamber is  at high vacuum
        """
        self._logger.debug("chamber_high_vacuum :: bringing the chamber to HV")
        raise NotImplementedError


class Sequence_logic(
    Sequence_functionsConvenience,
    Sequence_functionsPersonal,
    mS.Sequence_runner,
):
    pass


class Sequence_Thread_zmq(
    Sequence_logic, Sequence_comms_zmq, AbstractThread, metaclass=classmaker()
):
    """docstring for Sequence_Thread"""

    # sig_aborted = pyqtSignal()
    sig_finished = pyqtSignal(str)
    sig_message = pyqtSignal(str)
    __name__ = "Sequence_now"

    def __init__(
        self,
        controlsLock=None,
        # comms_downstream,
        # comms_data,
        **kwargs,
    ):
        super().__init__(_ident="sequence", **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

        # self.devices = device_signals

        # self.comms_data = comms_data
        # self.comms_downstream = comms_downstream
        self.controlsLock = Lock() if controlsLock is None else controlsLock

        # self.devices["Sequence"]["newconf"].connect(self.storing_thresholds)

    # @ExceptionHandling
    def work(self):
        """run the sequence, emit the finish-line"""
        # print('I will now start to work!')
        # print('data from main:' ,zmqquery(self.zmq_sSeq, 'data'))
        try:
            with PidFile("zmqLogger"):
                msg = "zmqLogger is not running, no data available, aborting"
                self._logger.error(msg)
                self.sig_finished.emit(msg)
                return
        except PidFileError:
            pass

        try:
            with self.controlsLock:
                fin = self.running()
        except problemAbort as e:
            fin = f"Error occurred, aborting sequence! Error: {e}"
            self._logger.error(fin)

        finally:
            try:
                self.sig_finished.emit(fin)
            except NameError:
                self.sig_finished.emit(
                    "An Error occurred! Aborted sequence completely!"
                )
                self._logger.error("An Error occurred! Aborted sequence completely!")

    def message_to_user(self, message: str) -> None:
        """deliver a message to a user in some way

        default is printing to the command line
        may be overriden!
        """
        # super().message_to_user(message)
        # print(message)
        # self.devices['general']['message_to_user'].emit(message)
        self.sig_message.emit(message)
        self._logger.warning(f"A message to the user: {message}")

    def execute_remark(self, remark: str, **kwargs) -> None:
        """use the given remark

        shoud be overriden in case the remark means anything"""
        try:
            if remark.strip()[:5] == "scanT":
                self._logger.debug("scan T explicitly")
                temps = [float(x) for x in mS.searchf_number.findall(remark)]
                self.execute_scan_T(
                    start=temps[0],
                    end=temps[-1],
                    temperatures_forced=temps,
                    Nsteps=None,
                    SweepRate=None,
                    ApproachMode="No O'Shoot",
                    SpacingCode=None,
                    commands=[
                        {
                            "typ": "Wait",
                            "Temp": True,
                            "Field": False,
                            "Position": False,
                            "Chamber": False,
                            "Delay": 60.0,
                            "DisplayText": "   Wait for Temperature & 60.0 seconds more",
                        }
                    ],
                )
        except IndexError:
            pass

        self.message_to_user(f"remark: {remark}")

    @pyqtSlot()
    def setTempVTIOffset(self, offset):
        self.temp_VTI_offset = offset


if __name__ == "__main__":

    # try:
    # with PidFile("MainControl"):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    logger_2 = logging.getLogger("pyvisa")
    logger_2.setLevel(logging.DEBUG)
    logger_3 = logging.getLogger("PyQt5")
    logger_3.setLevel(logging.DEBUG)

    # logger_4 = logging.getLogger("measureSequences")
    # logger_4.setLevel(logging.DEBUG)

    date = dt.now().strftime("%Y%m%d-%H%M%S")
    handler_debug = logging.FileHandler(
        filename=f"Logs/Sequence_logs{date}.log", mode="a"
    )
    handler_debug.setLevel(logging.DEBUG)
    formatter_debug = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    )
    handler_debug.setFormatter(formatter_debug)

    handler_info = CustomStreamHandler(logging.INFO, sys.stdout)
    handler_info.setLevel(logging.INFO)
    formatter_info = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler_info.setFormatter(formatter_info)

    logger.addHandler(handler_debug)
    logger.addHandler(handler_info)
    logger_2.addHandler(handler_debug)
    logger_3.addHandler(handler_debug)
    # logger_4.addHandler(handler_debug)
    # logger_4.addHandler(handler_info)

    # filename = "seqfiles/testing_setTemp.json"
    # filename = "seqfiles/setTemp_300.json"
    # filename = "seqfiles/measure.json"
    # filename = "seqfiles/measuring_SR860_test2.json"
    # filename = "seqfiles/measuring_SR860_test3.json"
    filename = "seqfiles/measuring_DC_test1.json"
    thresholdsconf = dict(
        temperature=dict(
            value=0.3,  # 0.1, # 0.05,  T_K
            mean=10,  # 0.2,  # 0.05,   Tmean_K
            stderr_rel=1e-1,  # 1e-5,
            relslope_Xpmin=1e-0,  # 1e-3,  # _Kpmin
            slope_residuals=30e4,  # 30,
        ),
    )
    tempdefinition = dict(
        control=["ITC", "Sensor_1_calerr_K"],
        sample=["ITC", "Sensor_1_calerr_K"],
        # sample=["LakeShore350", "Sensor_4_K"],
    )
    parsed = True
    if not parsed:
        parser = mS.Sequence_parser(sequence_file=filename)
        sequence = parser.data
    else:
        with open(filename, "r") as f:
            sequence = loads(f.read())
    print(sequence)
    runner = Sequence_Thread_zmq(
        sequence=sequence,
        thresholdsconf=thresholdsconf,
        tempdefinition=tempdefinition,
        python_default_path="Sequence/",
    )

    runner.work()
    # except PidFileError:
    #     print("Program already running! \nShutting down now!\n")
    #     sys.exit()
