"""
Provides support for the Keithley 6221 constant current supply
"""

# IMPORTS #####################################################################

import logging
from drivers import AbstractGPIBDeviceDriver
from drivers import AbstractEthernetDeviceDriver


# CLASSES #####################################################################


class Keithley6221_bare(object):

    """
    The Keithley 6221 is a single channel constant current supply.

    Because this is a constant current supply, most features that a regular
    power supply have are not present on the 6221.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    # def go(self, command):
    #     return super().go(command)

    # def query(self, command):
    #     return super().query(command)

    # METHODS #
    def disable_fully(self):
        """
        Set the output current to zero and disable the output.
        """
        self.go("SOUR:CLE:IMM")

    def enable(self):
        self._logger.debug("output state enable")
        self.go("OUTPUT:STATE ON")

    def disable(self):
        self._logger.debug("output state disable")
        self.go("OUTPUT:STATE OFF")

    def getstatus(self):
        return self.query("OUTPUT:STATE?")

    def disable_frontpanel(self, text):
        self._logger.debug("disabling frontpanel, setting to %s", text)
        self.go('DISPlay:TEXT:STATe on; DISPlay:TEXT "measuring..."')
        self.go(f'DISPlay:WINDow2TEXT:STATe on; DISPlay:WINDow2:TEXT "{text}"')
        self.go("DISPlay:ENABle off")

    def enable_frontpanel(self):
        self._logger.debug("enabling frontpanel")
        self.go("DISPlay:ENABle on")
        self.go("DISPlay:TEXT:STATe off")
        self.go("DISPlay:WINDow2TEXT:STATe off")

    def setCurrent(self, current_value):
        """Sets Current"""
        if -0.105 > current_value > 0.105:
            raise AssertionError(
                "Keithley:InputAlarmParameterCommand: Current_Value parameter must be a float in between -0.105 and 0.105"
            )
        self._logger.debug("setting current to %f", current_value)
        self.go("CURR {0:e}".format(current_value))

    def configSourceFunctions(self, bias_current=1e-4, compliance=1):
        """The bias current is the fixed current setting just prior to the start of the sweep.
        The current output will remain at the last point in the sweep after completion.
        The compliance setting limits the output voltage of the Model 622x. The voltage
        compliance limit can be set from 0.1V to 105V in 10mV steps. The output will
        not exceed the programmed compliance level.
        """
        self.go("*RST")
        self.go("SOUR:CURR " + "{0:e}".format(bias_current))
        self.go("SOUR:CURR:COMP " + "{0:f}".format(compliance))

    def setupSweep(self, start_current, stop_current, step_current, delay):
        """Sets up the Sweep"""
        self.go("OUR:SWE:SPAC LIN")
        self.go("OUR:CURR:STAR " + "{0:e}".format(start_current))
        self.go("OUR:CURR:STOP " + "{0:e}".format(stop_current))
        self.go("OUR:CURR:STEP " + "{0:e}".format(step_current))
        self.go("OUR:DEL " + "{0:d}".format(delay))
        self.go("OUR:SWE:RANG BEST")
        self.go("OUR:SWE:COUN 1")
        self.go("OUR:SWE:CAB OFF")

    def startSweep(self):
        """Starts the Sweep"""
        self.go("SOUR:SWE:ARM")
        self.go("INIT")

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

    def query_error(self):
        """Query error status messages from device

        As error and status messages occur, they are placed in the Error Queue. This query command
        is used to read those messages. The Error Queue is a first-in, first-out (FIFO) register that can
        hold up to ten messages. Each time you read the queue, the “oldest” message is read, and that
        message is then removed from the queue.
        If the queue becomes full, the “350, Queue Overflow” message occupies the last memory
        location in the register. On power-up, the queue is empty. When the Error Queue is empty, the
        “0, No error” message is placed in the Error Queue.
        The messages in the queue are preceded by a number. Negative (–) numbers are used for SCPI
        defined messages, and positive (+) numbers are used for Keithley defined messages.
        Appendix B lists the messages."""
        return self.query(":SYST:ERR?")

    def error_gen(self):
        """wrap self.query_error() in a generator"""
        while True:
            a = self.query_error()
            yield a
            if a[0] == "0":
                break


class Keithley6221(AbstractGPIBDeviceDriver, Keithley6221_bare):
    """docstring for Keithley6221"""

    pass


class Keithley6221_ethernet(AbstractEthernetDeviceDriver, Keithley6221_bare):
    """docstring for Keithley6221"""

    def __init__(self, InstrumentAddress, **kwargs):
        super().__init__(
            InstrumentAddress,
            **kwargs,
            read_termination="\n",
            write_termination="\r",
        )
