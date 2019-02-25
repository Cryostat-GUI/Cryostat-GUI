"""
Provides support for the Keithley 6221 constant current supply
"""

# IMPORTS #####################################################################

# import threading
# import visa

import logging

from drivers import AbstractGPIBDeviceDriver

# create a logger object for this module
logger = logging.getLogger(__name__)
# added so that log messages show up in Jupyter notebooks
logger.addHandler(logging.StreamHandler())

# try:
#     # the pyvisa manager we'll use to connect to the GPIB resources
#     resource_manager = visa.ResourceManager(
#         'C:\\Windows\\System32\\agvisa32.dll')
# except OSError:
#     logger.exception(
#         "\n\tCould not find the VISA library. Is the National Instruments VISA driver installed?\n\n")

#from __future__ import absolute_import
#from __future__ import division

#import quantities as pq

#from Keithley.lib import PowerSupply
#from Keithley.lib import SCPIInstrument

# CLASSES #####################################################################


class Keithley6221(AbstractGPIBDeviceDriver):

    """
    The Keithley 6221 is a single channel constant current supply.

    Because this is a constant current supply, most features that a regular
    power supply have are not present on the 6221.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def go(self, command):
        return super().go(command)

    def query(self, command):
        return super().query(command)

    # METHODS #
    def disable_fully(self):
        """
        Set the output current to zero and disable the output.
        """
        self.go('SOUR:CLE:IMM')

    def enable(self):
        self.go('OUTPUT:STATE ON')

    def disable(self):
        self.go('OUTPUT:STATE OFF')

    def getstatus(self):
        return self.query('OUTPUT:STATE?')

    def disable_frontpanel(self, text):
        self.go('DISPlay:TEXT:STATe on; DISPlay:TEXT "measuring..."')
        self.go(f'DISPlay:WINDow2TEXT:STATe on; DISPlay:WINDow2:TEXT "{text}"')
        self.go('DISPlay:ENABle off')

    def enable_frontpanel(self):
        self.go('DISPlay:ENABle on')
        self.go('DISPlay:TEXT:STATe off')
        self.go(f'DISPlay:WINDow2TEXT:STATe off')

    def setCurrent(self, current_value):
        """Sets Current
        """
        if -0.105 > current_value > 0.105:
            raise AssertionError(
                "Keithley:InputAlarmParameterCommand: Current_Value parameter must be a float in between -0.105 and 0.105")
        self.go('CURR {0:e}'.format(current_value))

    def configSourceFunctions(self, bias_current=1e-4, compliance=1):
        """The bias current is the fixed current setting just prior to the start of the sweep.
        The current output will remain at the last point in the sweep after completion.
        The compliance setting limits the output voltage of the Model 622x. The voltage
        compliance limit can be set from 0.1V to 105V in 10mV steps. The output will
        not exceed the programmed compliance level.
        """
        self.go('*RST')
        self.go('SOUR:CURR ' + '{0:e}'.format(bias_current))
        self.go('SOUR:CURR:COMP ' + '{0:f}'.format(compliance))

    def setupSweep(self, start_current, stop_current, step_current, delay):
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

    def startSweep(self):
        """Starts the Sweep
        """
        self.go('SOUR:SWE:ARM')
        self.go('INIT')

    def more(self):
        """
        OUTPut Source output control:
            [:STAT]? Turn output on or off (standby). default = OFF
            :LTE <b> Connect output low to earth ground (ON) or float output low (OFF). default = OFF
            :ISH <name> Connect triax inner shield to OLOW (output low) or cable GUAR. default = OLOW
            :RESP <name> Set the output response for 6221: FAST or SLOW. default = FAST
            :INT Interlock:
                :TRIP? Returns a “0” if interlock is tripped (open) or a “1”
        """

        pass

    def even_more(self):
        """
        STATus Commands status registers:                               Note 1
                :MEASurement Measurement event registers:
                    [:EVENt]? Read the event register.                  Note 2
                    :ENABle <NDN> or <NRf> Program the enable register. Note 3
                    :CONDition? Read the condition register.
                :OPERation Operation event registers:
                    [:EVENt]? Read the event register.                  Note 2
                    :ENABle <NDN> or <NRf> Program the enable register. Note 3
                    :CONDition? Read the condition register.
                :QUEStionable Questionable event registers:
                    [:EVENt]? Read the event register. Note 2
                    :ENABle <NDN> or <NRf> Program the enable register. Note 3
                    :CONDition? Read the condition register.
                :PRESet Return status registers to default states.
                :QUEue Read error queue:
                    [:NEXT]? Read the most recent error message.        Note 4
                    :ENABle <list> Specify error and status messages
                                for errorqueue: -999 to +999.
                    Note 5
                    :DISable <list> Specify error and status messages not to
                                be placed in error queue: -999 to +999
                    :CLEar Clears all messages from error queue.
        Notes:
        1. Commands in this subsystem are not affected
            by *RST or SYSTem:PRESet.
            The effects of cycling power, *CLS and STATus:PRESet,
            are explained by the following notes.
        2. Event registers — Power-up and *CLS clears all bits.
            STATus:PRESet has no effect.
        3. Enable registers — Power-up and STATus:PRESet clears all bits.
            *CLS has no effect.
        4. Error queue — Power-up and *CLS empties the error queue.
            STATus:PRESet has no effect.
        5. Error queue messages — Power-up enables error messages and disables
            status messages. *CLS and STATus:PRESet have no effect.
        """
        pass
