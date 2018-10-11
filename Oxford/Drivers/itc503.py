"""Module containing a class to interface with an Oxford Instruments ITC 503.

Note: Our (Mason Group) laboratory does not have a working motorized needle
        valve, so the gas functions are not totally useful. However, if
        it somehow is fixed or if someone not from the group decides to use
        this module, then it may be of use.

This module requires a National Instruments VISA driver, which can be found at
https://www.ni.com/visa/

Attributes:
    resource_manager: the pyvisa resource manager which provides the visa
                      objects used for communicating over the GPIB interface

    logger: a python logger object


Classes:
    itc503: a class for interfacing with a ITC 503 temperature controller

"""
import logging
import threading

from Oxford.Drivers.driver import AbstractSerialDeviceDriver
import visa
from pyvisa.errors import VisaIOError

# create a logger object for this module
logger = logging.getLogger(__name__)
# added so that log messages show up in Jupyter notebooks
logger.addHandler(logging.StreamHandler())

try:
    # the pyvisa manager we'll use to connect to the GPIB resources
    resource_manager = visa.ResourceManager()
except OSError:
    logger.exception("\n\tCould not find the VISA library. Is the National Instruments VISA driver installed?\n\n")



class itc503(AbstractSerialDeviceDriver):
    """class for interfacing with a ITC 503 temperature controller"""
    

    def __init__(self, **kwargs):
        super(itc503, self).__init__(**kwargs)

        # set the heater voltage limit to be controlled dynamically according to the temperature
        self.write('$M0')
        self.delay = 0.06
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
            raise AssertionError('ITC: setTemperature: argument must be a number')

        command = '$T{}'.format(temperature)# + str(int(1000*temperature))
        self.write(command)

    def getValue(self, variable=0):
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
            raise AssertionError('ITC: getValue: argument must be integer')
        if variable not in range(0,11):
            raise AssertionError('ITC: getValue: Argument is not a valid number.')

        # clear any buffer by reading, ignoring all timeout errors
        self.clear_buffers()
        # retrieve value     
        value = self.query('R{}'.format(variable))
        # value = self._visa_resource.read()
        
        if value == "" or None:
            # raise AssertionError('ITC: getValue: bad reply: empty string')
            # print('ITC: Assertion: empty')
            try:
                self.read()
            except VisaIOError as e_visa:
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    pass
            return self.getValue(variable)
            # return None
        if value[0] != 'R':
            # raise AssertionError('ITC: getValue: bad reply: {}'.format(value))
            # print('ITC: Assertion: {}'.format(value))
            try:
                self.read()
            except VisaIOError as e_visa:
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    pass
            return self.getValue(variable)
            # return None
        # if value[0] == 'T':
        #     print('ITC: Assertion: T')
        #     self.read()
        #     value = self.getValue(variable)
        return float(value.strip('R+'))
        
    def setProportional(self, prop=0):
        """Sets the proportional band.
        
        Args:
            prop: Proportional band, in steps of 0.0001K.
        """
        self.write('$P{}'.format(prop))
        return None
        
    def setIntegral(self, integral=0):
        """Sets the integral action time.
        
        Args:
            integral: Integral action time, in steps of 0.1 minute.
                        Ranges from 0 to 140 minutes.
        """
        self.write('$I{}'.format(integral))
        return None
        
    def setDerivative(self, derivative=0):
        """Sets the derivative action time.
        
        Args:
            derivative: Derivative action time.
                        Ranges from 0 to 273 minutes.
        """
        self.write('$D{}'.format(derivative))
        return None
        
    def setHeaterSensor(self, sensor=1):
        """Selects the heater sensor.
        
        Args:
            sensor: Should be 1, 2, or 3, corresponding to
                    the heater on the front panel.
        """
        
        if sensor not in [1,2,3]:
            raise AssertionError('ITC: setHeaterSensor: Heater not on list.')
        
        self.write('$H{}'.format(sensor))
        return None
        
    def setHeaterOutput(self, heater_output=0):
        """Sets the heater output level.
        
        Args:
            heater_output: Sets the percent of the maximum
                        heater output in units of 0.1%.
                        Min: 0. Max: 999.
        """
        
        self.write('$O{}'.format(heater_output))
        return None

    def setGasOutput(self, gas_output=0):
        """Sets the gas (needle valve) output level.
        
        Args:
            gas_output: Sets the percent of the maximum gas
                    output in units of 0.1%.
                    Min: 0. Max: 999.
        """
        self.write('$G{}'.format(gas_output))
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
        self.write('$A{}'.format(auto_manual))

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
            raise AssertionError('ITC: setSweeps: Input should be a dict (of dicts)!')
        steps = range(1,17)
        parameters_keys = sweep_parameters.keys()
        null_parameter = {  'set_point' : 5,
                            'sweep_time': 0,
                            'hold_time' : 0  }

        for step in steps:
            if step in parameters_keys:
                self._setSweepStep(step, sweep_parameters[step])
            else:
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
        self.ComLock.acquire()
        step_setting = '$x{}'.format(sweep_step)
        self._visa_resource.write(step_setting)

        setpoint_setting = '$s{}'.format(
                            sweep_table['set_point'])
        sweeptime_setting = '$s{}'.format(
                            sweep_table['sweep_time'])
        holdtime_setting = '$s{}'.format(
                            sweep_table['hold_time'])

        self._visa_resource.write('$y1')
        self._visa_resource.write(setpoint_setting)

        self._visa_resource.write('$y2')
        self._visa_resource.write(sweeptime_setting)

        self._visa_resource.write('$y3')
        self._visa_resource.write(holdtime_setting)

        self._resetSweepTablePointers()
        self.ComLock.release()

    def _resetSweepTablePointers(self):
        """Resets the table pointers to x=0 and y=0 to prevent
           accidental sweep table changes.
        """
        self._visa_resource.write('$x0')
        self._visa_resource.write('$y0')

    def SweepStart(self):
        """start the sweep, beginning at the first step in the table"""
        self.write('$S1')

    def SweepStartAtPoint(self, point):
        """start walking through the sweep table at a specific point"""

        if 32 > point < 2: 
            raise AssertionError('ITC: SweepStartAtPoint: Sweep-Startpoint out of range (2-32)')
        self.write('$S{}'.format(point))

    def SweepStop(self):
        """Stop any sweep which is currently running"""
        self.write('$S0')