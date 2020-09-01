"""Module containing a class to interface with an Oxford Instruments IPS 120-10.

Classes:
    ips120: a class for interfacing with a IPS 120-10 magnet power supply
            inherits from AbstractSerialDeviceDriver where the low-level visa
            communications are defined.
Author(s):
    bklebel (Benjamin Klebel)
"""
from datetime import datetime
import time
import logging

from drivers import AbstractSerialDeviceDriver
from pyvisa.errors import VisaIOError


class ips120(AbstractSerialDeviceDriver):
    """Driver class for the Intelligent Power Supply 120-10 from Oxford Instruments. """

    def __init__(self, **kwargs):
        """Connect to an IPS 120-10 at the specified RS232 address

        Args:
            adress(str): RS232 address of the IPS 120-10 (at the local machine)
        """
        super().__init__(**kwargs)
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)
        self.setControl()

    def read_buffer(self):
        return self.read()

    def setControl(self, state=3):
        """Set the LOCAL / REMOTE control state of the IPS 120-10

        0 - Local & Locked (default state)
        1 - Remote & Locked
        2 - Local & Unlocked
        3 - Remote & Unlocked

        Args:
            state(int): the state in which to place the IPS 120-10
        """
        if not isinstance(state, int):
            raise AssertionError("IPS: setControl: Argument must be integer")
        if state not in [0, 1, 2, 3]:
            raise AssertionError(
                "IPS: setControl: Argument must be one of [0,1,2,3]")

        self.write("$C{}".format(state))

    def getValue(self, variable=0):
        """Read the variable defined by the index.

         0: Demand Current to PSU (Output Current)
         1: Measured Power supply voltage
         2: measured magnet current
         3: ----- unused -----
         4: demand current (dublicate of 0)
         5: CURRENT set point (Target) -  [A]
         6: CURRENT sweep rate            [A/min]
         7: Demand Field (Output Field)
         8: FIELD set point (Target) -    [T]
         9: FIELD sweep rate              [T/min]
        10: Lead resistance               [milli Ohm]
        11: channel 1 Freq/4
        12: channel 2 Freq/4
        13: channel 3 Freq/4
        14: DACZ (PSU zero correction as a hexadecimal number)
        15: software voltage limit
        16: persistent magnet current
        17: trip current
        18: persistent magnet field
        19: trip field
        20: IDAC (demand current as a hexadecimal number)
        21: safe current limit, most negative
        22: safe current limit, most positive

        Args:
            variable: Index of variable to read.
        """
        if not isinstance(variable, int):
            raise AssertionError("IPS: getValue: argument must be integer")
        if variable not in range(0, 23):
            raise AssertionError(
                "IPS: getValue: Argument is not a valid number.")

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
                if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
                    pass
            return self.getValue(variable)
        return float(value.strip("R+"))

    def getStatus(self):
        value = self.query("X")

        if value == "" or None:
            raise AssertionError("IPS: getValue: bad reply: empty string")
        if value[0] != "X":
            raise AssertionError("IPS: getStatus: Bad reply: {}".format(value))
        return value

    def readField(self):
        """Read the current magnetic field in Tesla

        Returns:
            field(float): current magnetic field in Tesla
        """
        return self.getValue(7)

    def readFieldSetpoint(self):
        """Read the current set point for the magnetic field in Tesla

        Returns:
            setpoint(float): current set point for the magnetic field in Tesla
        """
        return self.getValue(8)

    def readFieldSweepRate(self):
        """Read the current magnetic field sweep rate in Tesla/min

        Returns:
            sweep_rate(float): current magnetic field sweep rate in Tesla/min
        """
        return self.getValue(9)

    def setActivity(self, state=1):
        """Set the field activation method

        0 - Hold
        1 - To Set Point
        2 - To Zero
        3 - Clamp (clamp the power supply output)

        Args:
            state(int): the field activation method
        """

        if not isinstance(state, int):
            raise AssertionError("IPS: setActivity: Argument must be integer")
        if state not in [0, 1, 2, 3]:
            raise AssertionError(
                "IPS: setActivity: Argument must be one of [0,1,2,3]")

        self.write("$A{}".format(state))

    def setSwitchHeater(self, state=1):
        """Set the switch heater activation state

        0 - Heater Off              (close switch)
        1 - Heater On if PSU=Magnet (open switch)
        2 - Heater On, no checks    (open switch)

        Args:
            state(int): the switch heater activation state
        """
        if not isinstance(state, int):
            raise AssertionError(
                "IPS: setSwitchHeater: Argument must be integer")
        if state not in [0, 1, 2]:
            raise AssertionError(
                "IPS: setSwitchHeater: Argument must be one of [0,1,2]"
            )
        self.write("$H{}".format(state))

        # TODO: add timer to account for time it takes for switch to activate

    def setFieldSetpoint(self, field):
        """Set the magnetic field set point, in Tesla

        Args:
            field(float): the magnetic field set point, in Tesla

        TODO: check for sanity:
        - manual says field is set in mT (0.001 T)
        - plarity is set manually, NOT by setting negative field setpoint
        """
        MAX_FIELD = 8
        if not abs(field) < MAX_FIELD:
            raise AssertionError(
                "IPS: setFieldSetpoint: Field must be less than {}".format(
                    MAX_FIELD)
            )

        self.write("$J{}".format(field))

    def setFieldSweepRate(self, rate):
        """Set the magnetic field sweep rate, in Tesla/min

        Args:
            rate(float): the magnetic field sweep rate, in Tesla/min

        TODO: check for sanity:
        - manual: field rate in units of mT/min
        - look up the maximum rate and implement a check
        """
        self.write("$T{}".format(rate))

    def setDisplay(self, display):
        """Set the display to show amps or tesla

        Args:
            display(str): One of ['amps','tesla']
        """
        if display not in ["amps", "tesla"]:
            raise AssertionError(
                "IPS: setDisplay: Argument must be one of ['amps','tesla']"
            )

        mode_dict = {"amps": 8, "tesla": 9}

        self.write("$M{}".format(mode_dict[display]))

    def waitForField(self, timeout=600, error_margin=0.01):
        """Wait for the field to reach the set point

        Args:
            timeout(int): maximum time to wait, in seconds
            error_margin(float): how close the field needs to be to the set point, in tesla

        Returns:
            (bool): whether the field set point was reached
        """

        start_time = datetime.now()
        stop_time = start_time + datetime.timedelta(seconds=timeout)

        while datetime.now() < stop_time:
            field = self.readField()
            set_point = self.readFieldSetpoint()

            if abs(field - set_point) < error_margin:
                return True

            time.sleep(5)

        return False
