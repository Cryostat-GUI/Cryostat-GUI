"""Module containing a classes to communicate with devices over a few distinct communication channels

This module requires a National Instruments VISA driver, which can be found at
https://www.ni.com/visa/
It also requires an Agilent VISA driver - if there is need for either one
(at least one VISA driver is required, may depend on your instrumentation)

Attributes:
    logger: a python logger object

Classes:
        AbstractSerialDeviceDriver: used for interactions with a serial connection
            the characteristics of the serial connection can be specified
            defaults are good for connections with "Oxford Instruments" devices
            over a serial connection

        AbstractGPIBDeviceDriver: used for interactions with a GPIB connection

Author(s):
    bklebel (Benjamin Klebel)
"""
# import sys
import threading
import logging
import time
import visa
from pyvisa.errors import VisaIOError
from visa import constants as vconst

# create a logger object for this module
logger = logging.getLogger(__name__)

keysight = False
ni = False
try:
    # the pyvisa manager we'll use to connect to the GPIB resources
    NI_RESOURCE_MANAGER = visa.ResourceManager()
    ni = True
except OSError:
    logger.exception(
        "\n\tCould not find the NI VISA library. Is the National Instruments VISA driver installed?\n\n")
try:
    KEYSIGHT_RESOURCE_MANAGER = visa.ResourceManager(
        'C:\\Windows\\System32\\agvisa32.dll')
    keysight = True
except OSError:
    logger.exception(
        "\n\tCould not find the keysight VISA library. Is it installed?\n\n")

# print(NI_RESOURCE_MANAGER)

if not (ni or keysight):
    logger.exception('I could not find any VISA library! \n\n')


class AbstractVISADriver(object):
    """Abstract VISA Device Driver

    visalib: 'ni' or 'ks' (national instruments/keysight)
    """

    def __init__(self, InstrumentAddress, visalib='ni', **kwargs):
        super(AbstractVISADriver, self).__init__(**kwargs)

        self._comLock = threading.Lock()
        self.delay = 0
        self.delay_force = 0

        if visalib.strip() == 'ni' and not ni:
            raise NameError('The VISA library was not found!')
        if visalib.strip() == 'ks' and not keysight:
            raise NameError('The Keysight VISA library was not found!')

        resource_manager = KEYSIGHT_RESOURCE_MANAGER if visalib.strip(
        ) == 'ks' else NI_RESOURCE_MANAGER
        self._visa_resource = resource_manager.open_resource(InstrumentAddress)

    def res_close(self):
        self._visa_resource.close()

    def write(self, command, f=False):
        """
            low-level communication wrapper for visa.write with Communication Lock,
            to prevent multiple writes to serial adapter
        """
        if not f:
            with self._comLock:
                self._visa_resource.write(command)
                time.sleep(self.delay)
        else:
            self._visa_resource.write(command)
            time.sleep(self.delay_force)

    def query(self, command):
        """Sends commands as strings to the device and receives strings from the device

        low-level communication wrapper for visa.query with Communication Lock,
        to prevent multiple writes to serial adapter
        """
        with self._comLock:
            answer = self._visa_resource.query(command)
            time.sleep(self.delay)
        return answer

    def read(self):
        with self._comLock:
            answer = self._visa_resource.read()
            # time.sleep(self.delay)
        return answer


class AbstractSerialDeviceDriver(AbstractVISADriver):
    """Abstract Device driver class
    """
    timeouterror = VisaIOError(-1073807339)

    def __init__(self, timeout=500, read_termination='\r', write_termination='\r', baud_rate=9600, data_bits=8, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self._visa_resource.query_delay = 0.
        self._visa_resource.timeout = timeout
        self._visa_resource.read_termination = read_termination
        self._visa_resource.write_termination = write_termination
        self._visa_resource.baud_rate = baud_rate
        self._visa_resource.data_bits = data_bits
        self._visa_resource.stop_bits = vconst.StopBits.two
        self._visa_resource.parity = vconst.Parity.none

        self.delay = 0.1
        self.delay_force = 0.1

    def clear_buffers(self):
        # self._visa_resource.timeout = 5
        try:
            # with self._comLock:
            self.read()
        except VisaIOError as e_visa:
            if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
                pass
            else:
                raise e_visa
        # self._visa_resource.timeout = 500


class AbstractGPIBDeviceDriver(AbstractVISADriver):
    """docstring for Instrument_GPIB"""

    def __init__(self, comLock=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if comLock is not None:
            self._comLock = comLock

    def query(self, command):
        """Sends commands as strings to the device and receives strings from the device

        :param command: string generated by a given function, whom will be sent to the device
        :type command: str

        :return: answer from the device
        """
        return super().query(command).strip().split(',')

    def go(self, command):
        """Sends commands as strings to the device

        :param command: string generated by a given function, whom will be sent to the device
        :type command: str

        """
        super().write(command)
