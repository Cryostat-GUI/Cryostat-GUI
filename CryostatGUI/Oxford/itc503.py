"""Module containing a class to interface with an Oxford Instruments ITC 503.

Classes:
    itc503: a class for interfacing with a ITC 503 temperature controller
            inherits from AbstractSerialDeviceDriver where the low-level visa
            communications are defined.
Author(s):
    bklebel (Benjamin Klebel)
"""

from drivers import AbstractSerialDeviceDriver
from pyvisa.errors import VisaIOError
import logging


class itc503(AbstractSerialDeviceDriver):
    """class for interfacing with a ITC 503 temperature controller"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)

        # set the heater voltage limit to be controlled dynamically according to the temperature
        # self.write('$M0')
        self.delay = 0.06
        self.delay_force = 5e-3

        # self.setControl() # done in thread

    def setControl(self, state=3):
        """Set the LOCAL / REMOTE control state of the ITC 503

        0 - Local & Locked (default state)
        1 - Remote & Locked
        2 - Local & Unlocked
        3 - Remote & Unlocked

        Locked = Front panel is disabled
        Unlocked = Front panel usable

        Args:
            state(int): the state in which to place the ITC 503
        """
        # state_bit = str(remote) + str(unlocked)
        # state = int(state_bit, 2)

        self.write("$C{}".format(state))

    def setTemperature(self, temperature=0.010):
        """Change the temperature set point.

        Args:
            temperature(float): temperature to move to in Kelvin.
                Default: 0.010 K (10 mK) for default no heating
                above base temperature for any system.
        """
        if not isinstance(temperature, (int, float)):
            raise AssertionError("ITC: setTemperature: argument must be a number")

        command = "$T{}".format(temperature)  # + str(int(1000*temperature))
        self.write(command)

    def getStatus(self, run=True) -> dict:
        """read a general status from the itc 503"""
        answer = self.query("X")
        # print(answer, run)

        autoanswer = [
            "heater man, gas man",
            "heater auto, gas man",
            "heater man, gas auto",
            "heater auto, gas auto",
        ]
        locanswer = [
            "local locked",
            "remote locked",
            "local unlocked",
            "remote unlocked",
        ]

        a = dict(
            auto=autoanswer[int(answer[3])],
            auto_int=answer[3],
            loc_rem=locanswer[int(answer[5])],
            sweep=answer[7],
            sensor_control=answer[9],
            autopid=answer[11],
        )
        # print(a)
        return a

    def getValue(self, variable=0) -> float:
        """Read the variable defined by the index.

        There are values 11-13 but generally useless for
        general use. These are omitted.

        0: SET TEMPERATURE           6: HEATER O/P (as V)
        1: SENSOR 1 TEMPERATURE      7: GAS FLOW O/P (a.u.)
        2: SENSOR 2 TEMPERATURE      8: PROPORTIONAL BAND
        3: SENSOR 3 TEMPERATURE      9: INTEGRAL ACTION TIME
        4: TEMPERATURE ERROR        10: DERIVATIVE ACTION TIME
        5: HEATER O/P (as %)

        Args:
            variable: Index of variable to read.
        """
        if not isinstance(variable, int):
            raise AssertionError("ITC: getValue: argument must be integer")
        if variable not in range(0, 11):
            raise AssertionError("ITC: getValue: Argument is not a valid number.")

        # clear any buffer by reading, ignoring all timeout errors
        # self.clear_buffers()
        # retrieve value
        value = self.query("R{}".format(variable))
        # value = self._visa_resource.read()

        try:
            if value[0] != "R":
                try:
                    self.read()
                except VisaIOError as e_visa:
                    if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
                        pass
                return self.getValue(variable)
        except TypeError:
            try:
                self.read()
            except VisaIOError as e_visa:
                if (
                    isinstance(e_visa, type(self.timeouterror))
                    and e_visa.args == self.timeouterror.args
                ):
                    pass
            return self.getValue(variable)
        return float(value.strip("R+"))

    def setProportional(self, prop=0):
        """Sets the proportional band.

        Args:
            prop: Proportional band, in steps of 0.0001K.
        """
        self.write("$P{}".format(prop))
        return None

    def setIntegral(self, integral=0):
        """Sets the integral action time.

        Args:
            integral: Integral action time, in steps of 0.1 minute.
                        Ranges from 0 to 140 minutes.
        """
        self.write("$I{}".format(integral))
        return None

    def setDerivative(self, derivative=0):
        """Sets the derivative action time.

        Args:
            derivative: Derivative action time.
                        Ranges from 0 to 273 minutes.
        """
        self.write("$D{}".format(derivative))
        return None

    def setHeaterSensor(self, sensor=1):
        """Selects the heater sensor.

        Args:
            sensor: Should be 1, 2, or 3, corresponding to
                    the heater on the front panel.
        """

        if sensor not in [1, 2, 3]:
            raise AssertionError("ITC: setHeaterSensor: Heater not on list.")

        self.write("$H{}".format(sensor))
        return None

    def setHeaterOutput(self, heater_output=0):
        """Sets the heater output level.

        Args:
            heater_output: Sets the percent of the maximum
                        heater output in units of 0.1%.
                        Min: 0. Max: 999.
        """

        self.write("$O{}".format(heater_output))
        return None

    def setGasOutput(self, gas_output=0):
        """Sets the gas (needle valve) output level.

        Args:
            gas_output: Sets the percent of the maximum gas
                    output in units of 0.1%.
                    Min: 0. Max: 999.
        """
        self.write("$G{}".format(gas_output))
        return None

    def setAutoControl(self, auto_manual=0):
        """Sets automatic control for heater/gas(needle valve).

        Value:Status map
            0: heater manual, gas manual
            1: heater auto  , gas manual
            2: heater manual, gas auto
            3: heater auto  , gas auto

        Args:
            auto_manual: Index for gas/manual.
        """
        self.write("$A{}".format(auto_manual))

    def setSweeps(self, sweep_parameters):
        """Sets the parameters for all sweeps.

        This fills up a dictionary with all the possible steps in
        a sweep. If a step number is not found in the sweep_parameters
        dictionary, then it will create the sweep step with sweep_time and
        hold_time set to 0 - thus this step will be bypassed by the machine.
        The 16th step will nevertheless control the temperature setpoint after
        the sweep is completed, it should thus NOT be set to 0,
        because this would actually set the temperature setpoint to 0.
        Therefore all non-used steps have a low but reachable set point in T(K)

        Args:
            sweep_parameters: A dictionary whose keys are the step
                numbers (keys: 1-16). The value of each key is a
                dictionary whose keys are the parameters in the
                sweep table (see _setSweepStep).
        """
        if not isinstance(sweep_parameters, dict):
            raise AssertionError("ITC: setSweeps: Input should be a dict (of dicts)!")
        steps = [str(x) for x in range(1, 17)]
        parameters_keys = sweep_parameters.keys()
        null_parameter = {"set_point": 2, "sweep_time": 0, "hold_time": 0}
        for step in steps:
            if str(step) in parameters_keys:
                print("changing step: ", step, "to ", sweep_parameters[step])
                self._setSweepStep(step, sweep_parameters[step])
            else:
                print("setting step to null_parameter: ", step)
                self._setSweepStep(step, null_parameter)

    def _setSweepStep(self, sweep_step, sweep_table):
        """Sets the parameters for a sweep step.

        This sets the step pointer (x) to the proper step.
        Then this sets the step parameters (y1, y2, y3) to
        the values dictated by the sweep_table. Finally, this
        resets the x and y pointers to 0.

        Args:
            sweep_step: The sweep step to be modified (values: 1-16)
            sweep_table: A dictionary of parameters describing the
                sweep. Keys: set_point, sweep_time, hold_time.
        """
        with self._comLock:
            step_setting = "$x{}".format(sweep_step)
            self.write(step_setting, f=True)

            setpoint_setting = "$s{}".format(sweep_table["set_point"])
            sweeptime_setting = "$s{}".format(sweep_table["sweep_time"])
            holdtime_setting = "$s{}".format(sweep_table["hold_time"])
            self.write(step_setting, f=True)
            self.write("$y1", f=True)
            self.write(setpoint_setting, f=True)

            self.write(step_setting, f=True)
            self.write("$y2", f=True)
            self.write(sweeptime_setting, f=True)

            self.write(step_setting, f=True)
            self.write("$y3", f=True)
            self.write(holdtime_setting, f=True)

            self._resetSweepTablePointers()

    def _resetSweepTablePointers(self):
        """Resets the table pointers to x=0 and y=0 to prevent
           accidental sweep table changes.
        """
        self.write("$x0", f=True)
        self.write("$y0", f=True)

    def SweepStart(self):
        """start the sweep, beginning at the first step in the table"""
        self.write("$S1")

    def SweepStartAtPoint(self, point):
        """start walking through the sweep table at a specific point"""

        if 32 < point < 2:
            raise AssertionError(
                "ITC: SweepStartAtPoint: Sweep-Startpoint out of range (2-32)"
            )
        self.write("$S{}".format(point))

    def SweepJumpToLast(self):
        """Stop any sweep which is currently running
        meaning to jump to the last part of the sweep"""
        self.write('$S31')

    def readSweepTable(self):
        """read the Sweep Table which is stored in the device
            Not WORKING CURRENTLY

        """
        raise NotImplementedError
        steps = [str(i) for i in range(1, 17)]
        stepdict = {
            key: dict(set_point="not read", sweep_time="not read", hold_time="not read")
            for key in steps
        }
        with self._comLock:
            for step in steps:
                step_setting = "$x{}".format(step)
                self.write(step_setting, f=True)
                self.write("$y1", f=True)
                print("written1")
                try:
                    stepdict[step]["set_point"] = self.query("r", f=True)
                except Exception as e:
                    print(e)
                print("received 1")

                self.write(step_setting)  # just in cas, f=Truee
                self.write("$y2", f=True)
                stepdict[step]["sweep_time"] = self.query("r", f=True)

                self.write(step_setting)  # just in cas, f=Truee
                self.write("$y3", f=True)
                stepdict[step]["hold_time"] = self.query("r", f=True)
        print(stepdict)
        return stepdict
