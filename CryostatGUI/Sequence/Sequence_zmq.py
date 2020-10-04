from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot

# from PyQt5.QtCore import QTimer

import sys

# import datetime as dt
# import zmq
import time

# from copy import deepcopy
import pandas as pd

# import numpy as np
# from numpy.polynomial.polynomial import polyfit
# from itertools import combinations_with_replacement as comb


# from datetime import datetime as dt
# from datetime import timedelta as dtdelta
from threading import Lock


from util import AbstractThread

# from util import AbstractEventhandlingThread
# from util import loops_off
# from util import ExceptionHandling
# from util import convert_time
# from util import convert_time_searchable
from util.zmqcomms import dictdump
from json import loads

# from util.zmqcomms import enc
# from util.zmqcomms import successExit
from util.zmqcomms import raiseProblemAbort
from util.zmqcomms import zmqMainControl

from util.util_misc import CustomStreamHandler

import measureSequences as mS

# from qlistmodel import ScanningN

from Sequence import problemAbort

# from Sequence import AbstractMeasureResistance
# from Sequence import AbstractMeasureResistanceMultichannel

from pid import PidFile
from pid import PidFileError

import logging

logger = logging.getLogger("CryostatGUI.Sequences_zmq")


class Sequence_comms_zmq(zmqMainControl):
    """docstring for Sequence_comms_zmq"""

    @raiseProblemAbort(raising=True)
    def readDataFromList(
        self, dataindicator1: str, dataindicator2: str, Live: bool = False
    ) -> float:
        return super()._bare_readDataFromList(dataindicator1, dataindicator2, Live)

    @raiseProblemAbort(raising=True)
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
        self.thresholdsconf = thresholdsconf

    @pyqtSlot(dict)
    def storing_thresholds(self, thresholds: dict):
        self.thresholdsconf = thresholds

    def checkStable_Temp(
        self, temp: float, direction: int = 0, ApproachMode: str = "Sweep"
    ) -> bool:
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
            ApproachMode = Sweep: only for sweeps

        method should be overriden - possibly some convenience functionality
            will be added in the future
        """
        self._logger.debug(f"checking for stable temp: {temp}K")
        if direction == 0 or ApproachMode != "Sweep":
            # no information, temp should really stabilize

            stable = False
            # count = None
            temperature = 0
            stable_values = []
            while not stable:
                self._logger.info(f"waiting for temp: {temp} (current: {temperature:.3f}), indicators ({len(stable_values):d}/5): {stable_values}")
                stable_values = []
                self.check_running()

                temperature = self.getTemperature()
                mean = self.readDataFromList(
                    dataindicator1=self.tempdefinition[0],
                    dataindicator2=self.tempdefinition[1] + "_calc_ar_mean",
                    Live=True,
                )
                stderr_rel = self.readDataFromList(
                    dataindicator1=self.tempdefinition[0],
                    dataindicator2=self.tempdefinition[1] + "_calc_stderr_rel",
                    Live=True,
                )
                slope_rel = self.readDataFromList(
                    dataindicator1=self.tempdefinition[0],
                    dataindicator2=self.tempdefinition[1] + "_calc_slope_rel",
                    Live=True,
                )
                slope_residuals = self.readDataFromList(
                    dataindicator1=self.tempdefinition[0],
                    dataindicator2=self.tempdefinition[1] + "_calc_slope_residuals",
                    Live=True,
                )

                if abs(temperature - temp) < self.thresholdsconf["threshold_T_K"]:
                    stable_values.append("T_K")
                if abs(mean - temp) < self.thresholdsconf["threshold_Tmean_K"]:
                    stable_values.append("Tmean_K")
                if abs(stderr_rel) < self.thresholdsconf["threshold_stderr_rel"]:
                    stable_values.append("stderr_rel")
                if abs(slope_rel) < self.thresholdsconf["threshold_relslope_Kpmin"]:
                    stable_values.append("relslope_Kpmin")
                if (
                    abs(slope_residuals)
                    < self.thresholdsconf["threshold_slope_residuals"]
                ):
                    stable_values.append("slope_residuals")

                if len(stable_values) >= 5:
                    stable = True
                else:
                    time.sleep(1)

        elif direction == 1:
            # temp should be rising, all temps above 'temp' are fine
            while self.getTemperature() < temp:
                self.check_running()
                self._logger.debug(f"temp not yet above {temp} (current: {temperature:.3f})")
                time.sleep(1)
        elif direction == -1:
            # temp should be falling, all temps below 'temp' are fine
            while self.getTemperature() > temp:
                self.check_running()
                self._logger.debug(f"temp not yet below {temp} (current: {temperature:.3f})")
                time.sleep(1)

        self._logger.info(
            f"Temperature {temp} is stable!, ApproachMode = {ApproachMode}, direction = {direction}"
        )


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
            ID=self.tempdefinition[0],
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
            ID=self.tempdefinition[0],
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
        print(
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
        return self.readDataFromList(
            dataindicator1=self.tempdefinition[0],
            dataindicator2=self.tempdefinition[1],
            Live=False,
        )

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
            df = pd.DataFrame({key: [data[key]] for key in data})
        else:
            df = pd.DataFrame(data)

        with open(datafile, "a", newline="") as f:
            df.tail(1).to_csv(f, header=f.tell() == 0)

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
                f.write("\n")
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
    Sequence_logic,
    Sequence_comms_zmq,
    AbstractThread,
):
    """docstring for Sequence_Thread"""

    # sig_aborted = pyqtSignal()
    sig_finished = pyqtSignal(str)
    sig_message = pyqtSignal(str)

    def __init__(
        self,
        controlsLock=None,
        # comms_downstream,
        # comms_data,
        **kwargs,
    ):
        super().__init__(**kwargs)
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

    try:
        with PidFile("MainControl"):
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)

            logger_2 = logging.getLogger("pyvisa")
            logger_2.setLevel(logging.INFO)
            logger_3 = logging.getLogger("PyQt5")
            logger_3.setLevel(logging.INFO)

            logger_4 = logging.getLogger("measureSequences")
            logger_4.setLevel(logging.DEBUG)

            handler_debug = logging.FileHandler(filename='Logs/Sequence_logs.log', mode='a')
            handler_debug.setLevel(logging.DEBUG)
            formatter_debug = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
            )
            handler_debug.setFormatter(formatter_debug)

            handler_info = CustomStreamHandler(logging.INFO, sys.stdout)
            handler_info.setLevel(logging.INFO)
            formatter_info = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )
            handler_info.setFormatter(formatter_info)

            logger.addHandler(handler_debug)
            logger.addHandler(handler_info)
            logger_2.addHandler(handler_debug)
            logger_3.addHandler(handler_debug)
            logger_4.addHandler(handler_debug)
            logger_4.addHandler(handler_info)

            filename = "seqfiles/testing_setTemp.json"
            thresholdsconf = dict(
                threshold_T_K=0.1,
                threshold_Tmean_K=0.2,
                threshold_stderr_rel=5e-4,
                threshold_relslope_Kpmin=1e-3,
                threshold_slope_residuals=30,
            )
            tempdefinition = ["ITC", "Sensor_1_calerr_K"]
            parsed = True
            if not parsed:
                parser = mS.Sequence_parser(sequence_file=filename)
                sequence = parser.data
            else:
                with open(filename, "r") as f:
                    sequence = loads(f.read())
            runner = Sequence_Thread_zmq(
                sequence=sequence,
                thresholdsconf=thresholdsconf,
                tempdefinition=tempdefinition,
                python_default_path="Sequence/",
            )

            runner.work()
    except PidFileError:
        print("Program already running! \nShutting down now!\n")
        sys.exit()
