#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides support for the Keithley 6220 constant current supply
"""

# IMPORTS #####################################################################

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

    Example usage:

    >>> import quantities as pq
    >>> import instruments as ik
    >>> ccs = ik.keithley.Keithley6220.open_gpibusb("/dev/ttyUSB0", 10)
    >>> ccs.current = 10 * pq.milliamp # Sets current to 10mA
    >>> ccs.disable() # Turns off the output and sets the current to 0A
    """



    def bounded_unitful_property(command, units, min_fmt_str="{}:MIN?",
                                 max_fmt_str="{}:MAX?",
                                 valid_range=("query", "query"), **kwargs):
        """
        Called inside of SCPI classes to instantiate properties with unitful numeric
        values which have upper and lower bounds. This function in turn calls
        `unitful_property` where all kwargs for this function are passed on to.
        See `unitful_property` documentation for information about additional
        parameters that will be passed on.
    
        Compared to `unitful_property`, this function will return 3 properties:
        the one created by `unitful_property`, one for the minimum value, and one
        for the maximum value.
    
        :param str command: Name of the SCPI command corresponding to this property.
            If parameter set_cmd is not specified, then this parameter is also used
            for both getting and setting.
        :param str set_cmd: If not `None`, this parameter sets the command string
            to be used when sending commands with no return values to the
            instrument. This allows for non-symmetric properties that have different
            strings for getting vs setting a property.
        :param units: Units to assume in sending and receiving magnitudes to and
            from the instrument.
        :param str min_fmt_str: Specify the string format to use when sending a
            minimum value query. The default is ``"{}:MIN?"`` which will place
            the property name in before the colon. Eg: ``"MOCK:MIN?"``
        :param str max_fmt_str: Specify the string format to use when sending a
            maximum value query. The default is ``"{}:MAX?"`` which will place
            the property name in before the colon. Eg: ``"MOCK:MAX?"``
        :param valid_range: Tuple containing min & max values when setting
            the property. Index 0 is minimum value, index 1 is maximum value.
            Setting `None` in either disables bounds checking for that end of the
            range. The default of ``("query", "query")`` will query the instrument
            for min and max parameter values. The valid set is inclusive of
            the values provided.
        :type valid_range: `list` or `tuple` of `int`, `float`, `None`, or the
            string ``"query"``.
        :param kwargs: All other keyword arguments are passed onto
            `unitful_property`
        :return: Returns a `tuple` of 3 properties: first is as returned by
            `unitful_property`, second is a property representing the minimum
            value, and third is a property representing the maximum value
        """
    
        def _min_getter(self):
            if valid_range[0] == "query":
                return pq.Quantity(*split_unit_str(self.query(min_fmt_str.format(command)), units))
    
            return assume_units(valid_range[0], units).rescale(units)
    
        def _max_getter(self):
            if valid_range[1] == "query":
                return pq.Quantity(*split_unit_str(self.query(max_fmt_str.format(command)), units))
    
            return assume_units(valid_range[1], units).rescale(units)
    
        new_range = (
            None if valid_range[0] is None else _min_getter,
            None if valid_range[1] is None else _max_getter
        )
    
        return (
            unitful_property(command, units, valid_range=new_range, **kwargs),
            property(_min_getter) if valid_range[0] is not None else None,
            property(_max_getter) if valid_range[1] is not None else None
        )


        def go(self, command):
            with self.CommunicationLock:
                self.device.write(command)

    # PROPERTIES ##

    @property
    def channel(self):
        """
        For most power supplies, this would return a channel specific object.
        However, the 6220 only has a single channel, so this function simply
        returns a tuple containing itself. This is for compatibility reasons
        if a multichannel supply is replaced with the single-channel 6220.

        For example, the following commands are the same and both set the
        current to 10mA:

        >>> ccs.channel[0].current = 0.01
        >>> ccs.current = 0.01
        """
        return self,

    @property
    def voltage(self):
        """
        This property is not supported by the Keithley 6220.
        """
        raise NotImplementedError("The Keithley 6220 does not support voltage "
                                  "settings.")

    @voltage.setter
    def voltage(self, newval):
        raise NotImplementedError("The Keithley 6220 does not support voltage "
                                  "settings.")

    current, current_min, current_max = bounded_unitful_property(
        "SOUR:CURR",
        pq.amp,
        valid_range=(-105 * pq.milliamp, +105 * pq.milliamp),
        doc="""
        Gets/sets the output current of the source. Value must be between
        -105mA and +105mA.

        :units: As specified, or assumed to be :math:`\\text{A}` otherwise.
        :type: `float` or `~quantities.Quantity`
        """
    )

    # METHODS #

    def disable(self):
        """
        Set the output current to zero and disable the output.
        """
        self.go('SOUR:CLE:IMM')


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




























