import threading

import visa
from pyvisa.errors import VisaIOError


from Oxford.Drivers.driver import AbstractSerialDeviceDriver


class ilm211(AbstractSerialDeviceDriver):
    """docstring for ilm200"""
    def __init__(self, **kwargs):
        super(ilm211, self).__init__(**kwargs)

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
            raise AssertionError('ILM: getValue: Argument must be integer')
        if variable not in range(0,11):
            raise AssertionError('ILM: getValue: Argument is not a valid number.')
        
        # self.clear_buffers()

        value = self.query('R{}'.format(variable))
        # value = self._visa_resource.read()
        
        if value == "" or None:
            # raise AssertionError('ILM: getValue: bad reply: empty string')
            # print('ILM: Assertion: empty')
            try:
                self.read()
            except VisaIOError as e_visa:
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    pass
            return self.getValue(variable)
            # return None
        if value[0] != 'R':
            # raise AssertionError('ILM: getValue: bad reply: {}'.format(value))
            # print('ILM: Assertion: {}'.format(value))
            try:
                self.read()
            except VisaIOError as e_visa:
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    pass
            return self.getValue(variable)

        return float(value.strip('R+'))

    def _converting_status_channel(self, i):
        i = int(i)
        if i == 0: 
            return 'not in use'
        elif i == 1: 
            return 'Nitrogen'
        elif i == 2: 
            return 'Helium pulsed'
        elif i == 3: 
            return 'Helium continuous'
        elif i == 9:
            return 'Error - probe unplugged' 

    def getStatus(self):
        """query status of the machine, 
            interprete it, and return it
        """


        status = self.query('X')
        stat_channel = []
        stat_channel.append(status[5:6])
        stat_channel.append(status[7:8])
        stat_channel.append(status[9:10])
        # TODO: extract information from the hexadecimal numbers 

        return [self._converting_status_channel(status[1]), self._converting_status_channel(status[2]), 
                stat_channel[0], stat_channel[1], stat_channel[2]]


    def setSlow(self, channel):
        """put channel 'channel' into slow sample rate"""
        if not isinstance(channel, int): 
            raise AssertionError('ILM: setSlow: Argument must be integer')
        if channel not in [1,2]:
            raise AssertionError('ILM: setSlow: Argument is not a valid number.')         

        self.write('$S{}'.format(channel))

    def setFast(self, channel):
        """put channel 'channel' into fast sample rate"""
        if not isinstance(channel, int): 
            raise AssertionError('ILM: setFast: Argument must be integer')
        if channel not in [1,2]:
            raise AssertionError('ILM: setFast: Argument is not a valid number.')         

        self.write('$T{}'.format(channel))       
        
