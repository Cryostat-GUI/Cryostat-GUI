#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides support for the Keithley 6220 constant current supply
"""

# IMPORTS #####################################################################

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

from __future__ import absolute_import
from __future__ import division

import quantities as pq

from Keithley.lib import PowerSupply
from Keithley.lib import SCPIInstrument

# CLASSES #####################################################################


class Keithley6220(SCPIInstrument, PowerSupply):

    """
    The Keithley 6220 is a single channel constant current supply.

    Because this is a constant current supply, most features that a regular
    power supply have are not present on the 6220.

    """
    def go(self, command):
        with self.CommunicationLock:
            self.device.write(command)


    # METHODS #

    def disable(self):
        """
        Set the output current to zero and disable the output.
        """
        self.go('SOUR:CLE:IMM')

    def SetCurrent(self, current_value):
    	"""Sets Current
    	"""
        if 0.105 < current_value < - 0.105:
            raise AssertionError("Keithley:InputAlarmParameterCommand: Current_Value parameter must be a float in between -0.105 and 0.105")
    	self.go('CURR ' + '{0:e}'.format(current_value))


    def ConfigSourceFunctions(self, bias_current = 1e-4, compliance = 1):
        """The bias current is the fixed current setting just prior to the start of the sweep.
        The current output will remain at the last point in the sweep after completion.
        The compliance setting limits the output voltage of the Model 622x. The voltage
        compliance limit can be set from 0.1V to 105V in 10mV steps. The output will
        not exceed the programmed compliance level.
        """
        self.go('*RST')
        self.go('SOUR:CURR ' + '{0:e}'.format(bias_current))
        self.go('SOUR:CURR:COMP ' + '{0:f}'.format(compliance))

    def SetupSweep(self, start_current, stop_current, step_current, delay):
        """Sets up the Sweep
        """
        self.go('OUR:SWE:SPAC LIN')
        self.go('OUR:CURR:STAR ' + '{0:e}'.format(start_current))
        self.go('OUR:CURR:STOP ' + '{0:e}'.format(stop_current))
        self.go('OUR:CURR:STEP ' + '{0:e}'.format(step_current))
        self.go('OUR:DEL ' + '{0:d}'.format(delay))
        self.go('OUR:SWE:RANG BEST')
        self.go('OUR:SWE:COUN 1')
        self.go('OUR:SWE:CAB OFF')

    def StartSweep(self):
        """Starts the Sweep
        """
        self.go('SOUR:SWE:ARM')
        self.go('INIT')




























