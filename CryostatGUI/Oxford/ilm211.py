"""Module containing a class to interface with an Oxford Instruments ILM211.

Classes:
    itc503: a class for interfacing with a ILM 211 level meter
            inherits from AbstractSerialDeviceDriver where the low-level visa
            communications are defined.
Author(s):
    bklebel (Benjamin Klebel)
"""

from pyvisa.errors import VisaIOError

from drivers import AbstractSerialDeviceDriver
import logging


class ilm211(AbstractSerialDeviceDriver):
    """docstring for ilm200"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    def setControl(self, state=3):
        """Set the LOCAL / REMOTE control state of the Oxford controller

        0 - Local & Locked (default state)
        1 - Remote & Locked
        2 - Local & Unlocked
        3 - Remote & Unlocked

        Locked = Front panel is disabled
        Unlocked = Front panel usable

        Args:
            state(int): the state in which to place the Oxford controller
        """
        # state_bit = str(remote) + str(unlocked)
        # state = int(state_bit, 2)

        self.write("$C{}".format(state))

    def getValue(self, variable=2):
        """Read the variable defined by the index.

        There are values 11-13 but useless for
        general use. These are omitted.

        1: CHANNEL 1 LEVEL           6: CHANNEL 1 WIRE CURRENT
        2: CHANNEL 2 LEVEL           7: CHANNEL 2 WIRE CURRENT
        3: CHANNEL 3 LEVEL           8: not in use
        4:  not in use               9: not in use
        5:  not in use              10: NEEDLE VALVE POSITION
        5:  not in use

        Args:
            variable: Index of variable to read.
        """
        if not isinstance(variable, int):
            raise AssertionError("ILM: getValue: Argument must be integer")
        if variable not in range(0, 11):
            raise AssertionError("ILM: getValue: Argument is not a valid number.")

        # self.clear_buffers()

        value = self.query("R{}".format(variable))
        # value = self._visa_resource.read()
        try:
            if value[0] != "R":
                try:
                    self.read()
                except VisaIOError as e_visa:
                    if (
                        isinstance(e_visa, type(self.timeouterror))
                        and e_visa.args == self.timeouterror.args
                    ):
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

    @staticmethod
    def _converting_status_channel(i):
        i = int(i)
        if i == 0:
            return "not in use"
        elif i == 1:
            return "Nitrogen"
        elif i == 2:
            return "Helium pulsed"
        elif i == 3:
            return "Helium continuous"
        elif i == 9:
            return "Error - probe unplugged"

    def getStatus(self):
        """query status of the machine,
        interprete it, and return it
        """

        status = self.query("X")
        stat_channel = []
        stat_channel.append(status[5:6])
        stat_channel.append(status[7:8])
        stat_channel.append(status[9:10])
        # TODO: extract information from the hexadecimal numbers

        return [
            self._converting_status_channel(status[1]),
            self._converting_status_channel(status[2]),
            stat_channel[0],
            stat_channel[1],
            stat_channel[2],
        ]

    def setSlow(self, channel):
        """put channel 'channel' into slow sample rate"""
        if not isinstance(channel, int):
            raise AssertionError("ILM: setSlow: Argument must be integer")
        if channel not in [1, 2]:
            raise AssertionError("ILM: setSlow: Argument is not a valid number.")

        self.write("$S{}".format(channel))

    def setFast(self, channel):
        """put channel 'channel' into fast sample rate"""
        if not isinstance(channel, int):
            raise AssertionError("ILM: setFast: Argument must be integer")
        if channel not in [1, 2]:
            raise AssertionError("ILM: setFast: Argument is not a valid number.")

        self.write("$T{}".format(channel))
