# -*- coding: utf-8 -*-
"""
Driver for the Keithley 2182 Nano-Voltmeter
"""

import threading, visa

import logging

# create a logger object for this module
logger = logging.getLogger(__name__)
# added so that log messages show up in Jupyter notebooks
logger.addHandler(logging.StreamHandler())

try:
    # the pyvisa manager we'll use to connect to the GPIB resources
    resource_manager = visa.ResourceManager('C:\\Windows\\System32\\agvisa32.dll')
except OSError:
    logger.exception("\n\tCould not find the VISA library. Is the National Instruments VISA driver installed?\n\n")


class Keithley2182(object):

    """
    The Keithley 2182 is a nano-voltmeter. You can find the full specifications
    list in the `user's guide`_.

    Example usage:

    >>> import instruments as ik
    >>> meter = ik.keithley.Keithley2182.open_gpibusb("/dev/ttyUSB0", 10)
    >>> print meter.measure(meter.Mode.voltage_dc)
    """
    def __init__(self, InstrumentAddress = 'GPIB0::12::INSTR'):



        self._visa_resource = resource_manager.open_resource(InstrumentAddress)
        # self._visa_resource.read_termination = '\r'
        self.CommunicationLock = threading.Lock()
        self.device = self._visa_resource



    def measureTemperature(self):
        self.sendcmd("SENS:CHAN 1")
        self.sendcmd("SENS:FUNC 'VOLT:DC'")
        return self.query("SENS:DATA:FRES?")[0]

    def measureVoltage(self):

        self.sendcmd("SENS:CHAN 2")
        self.sendcmd("SENS:FUNC 'TEMP'")
        return self.query("SENS:DATA:FRES?")[0]