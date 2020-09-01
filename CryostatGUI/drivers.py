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
import functools

import sys

# create a logger object for this module
logger = logging.getLogger('CryoGUI.'+__name__)

# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
# handler = logging.StreamHandler(sys.stderr)
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter(
#     '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)


# keysight = False
# ni = False


def get_rm(visalib='ks'):
    try:
        # the pyvisa manager we'll use to connect to the GPIB resources
        NI_RESOURCE_MANAGER = visa.ResourceManager()
    #        'C:\\Windows\\System32\\visa32.dll')
        ni = True
        # print('     made resource manager')
    except OSError:
        logger.exception(
            "\n\tCould not find the NI VISA library. Is the National Instruments VISA driver installed?\n\n")
    # try:
    #     KEYSIGHT_RESOURCE_MANAGER = visa.ResourceManager(
    #         'C:\\Windows\\System32\\agvisa32.dll')
    #     keysight = True
    # except OSError:
    #     logger.exception(
    #         "\n\tCould not find the keysight VISA library. Is it installed?\n\n")

    # if not (ni or keysight):
    #     logger.exception('I could not find any VISA library! \n\n')
    #     return None
    # if visalib == 'ni':
    #     rm = NI_RESOURCE_MANAGER
    #     KEYSIGHT_RESOURCE_MANAGER.close()
    #     KEYSIGHT_RESOURCE_MANAGER.visalib._registry.clear()
    #     del KEYSIGHT_RESOURCE_MANAGER.visalib
    #     del KEYSIGHT_RESOURCE_MANAGER
    # else:
    #     rm = KEYSIGHT_RESOURCE_MANAGER
    #     NI_RESOURCE_MANAGER.close()
    #     NI_RESOURCE_MANAGER.visalib._registry.clear()
    #     del NI_RESOURCE_MANAGER.visalib
    #     del NI_RESOURCE_MANAGER
    return NI_RESOURCE_MANAGER
    # return rm


def HandleVisaException(func):

    @functools.wraps(func)
    def wrapper_HandleVisaException(*args, timeoutcounter=0, **kwargs):
        # if inspect.isclass(type(args[0])):
        # thread = args[0]
        try:
            se = args[0]
            return func(*args, **kwargs)

        except VisaIOError as e:
            if isinstance(e, type(se.timeouterror)) and \
                    e.args == se.timeouterror.args:
                try:
                    se.sig_visatimeout.emit()
                except AttributeError:
                    pass
                se._logger.exception(e)
                time.sleep(0.01)
                # this is not fully tested ---- In ---------------------------
                if timeoutcounter < 5:
                    timeoutcounter += 1
                    return wrapper_HandleVisaException(*args, timeoutcounter=timeoutcounter, **kwargs)
                else:
                    return -1
                # this is not fully tested ---- Out --------------------------
            elif isinstance(e, type(se.connError)) and \
                    e.args == se.connError.args:
                se._logger.exception(e)
                se._logger.error('Connection lost, trying to reconnect')
                notyetthereagain = True
                se.res_close()
                while notyetthereagain:
                    try:
                        time.sleep(1)
                        try:
                            se.res_close()
                        except AttributeError:
                            pass
                        se.res_open()
                        q = se._visa_resource.query('*IDN?')
                        notyetthereagain = False
                    except VisaIOError:
                        se._logger.debug('trying to reactivate the connection!')
                se._logger.info('Exception of lost connection resolved! (I hope)')
            elif isinstance(e, type(se.visaIOError)) and \
                    e.args == se.visaIOError.args:
                se._logger.exception(e)
                se._logger.error('Visa I/O Error, trying to reconnect')
                notyetthereagain = True
                se.res_close()
                while notyetthereagain:
                    try:
                        time.sleep(1)
                        try:
                            se.res_close()
                        except AttributeError:
                            pass
                        se.res_open()
                        q = se._visa_resource.query('*IDN?')
                        notyetthereagain = False
                    except VisaIOError:
                        se._logger.debug('trying to reactivate the connection!')
                se._logger.info('Exception of I/O error resolved! (I hope)')
            else:
                se._logger.exception(e)
            try:
                q
                return wrapper_HandleVisaException(*args, **kwargs)
            except NameError:
                return -1

    return wrapper_HandleVisaException


class AbstractVISADriver(object):
    """Abstract VISA Device Driver

    visalib: 'ni' or 'ks' (national instruments/keysight)
    """

    connError = VisaIOError(-1073807194)
    timeouterror = VisaIOError(-1073807339)
    visaIOError = VisaIOError(-1073807298)

    def __init__(self, InstrumentAddress, visalib='ni', **kwargs):
        super(AbstractVISADriver, self).__init__(**kwargs)
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)

        self._comLock = threading.Lock()
        self.delay = 0
        self.delay_force = 0
        self._instrumentaddress = InstrumentAddress
        self.visalib_kw = visalib

        # if visalib.strip() == 'ni' and not ni:
        #     raise NameError('The VISA library was not found!')
        # if visalib.strip() == 'ks' and not keysight:
        #     raise NameError('The Keysight VISA library was not found!')

        # self._resource_manager = KEYSIGHT_RESOURCE_MANAGER if visalib.strip(
        # ) == 'ks' else NI_RESOURCE_MANAGER
        # self._resource_manager = get_rm(visalib=self.visalib_kw)
        #        resource_manager = NI_RESOURCE_MANAGER
        # self._visa_resource = self._resource_manager.open_resource(InstrumentAddress)
        self.res_open()

    def res_close(self):
        self._visa_resource.close()
        self._resource_manager.close()
        self._resource_manager.visalib._registry.clear()
        del self._resource_manager.visalib
        del self._resource_manager
        del self._visa_resource

    def res_open(self):
        self._resource_manager = get_rm(visalib=self.visalib_kw)
        try:
            self._visa_resource = self._resource_manager.open_resource(
                self._instrumentaddress)
        except VisaIOError:
            self._visa_resource = self._resource_manager.open_resource(
                self._instrumentaddress)
        self.initialise_device_specifics(**self._device_specifics)

        # time.sleep(2)
        # self._visa_resource.query('*IDN?')

    def initialise_device_specifics(self, **kwargs):
        # self._visa_resource.query_delay = 0.
        if 'timeout' in kwargs:
            self._visa_resource.timeout = kwargs['timeout']
        if 'read_termination' in kwargs:
            self._visa_resource.read_termination = kwargs['read_termination']
        if 'write_termination' in kwargs:
            self._visa_resource.write_termination = kwargs['write_termination']
        if 'baud_rate' in kwargs:
            self._visa_resource.baud_rate = kwargs['baud_rate']
        if 'data_bits' in kwargs:
            self._visa_resource.data_bits = kwargs['data_bits']
        if 'stop_bits' in kwargs:
            self._visa_resource.stop_bits = kwargs[
                'stop_bits']  # vconst.StopBits.two
        if 'parity' in kwargs:
            self._visa_resource.parity = kwargs['parity']  # vconst.Parity.none

    @HandleVisaException
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

    @HandleVisaException
    def query(self, command):
        """Sends commands as strings to the device and receives strings from the device

        low-level communication wrapper for visa.query with Communication Lock,
        to prevent multiple writes to serial adapter
        """
        with self._comLock:
            answer = self._visa_resource.query(command)
            time.sleep(self.delay)
        return answer

    @HandleVisaException
    def read(self):
        with self._comLock:
            answer = self._visa_resource.read()
            # time.sleep(self.delay)
        return answer


class AbstractSerialDeviceDriver(AbstractVISADriver):
    """Abstract Device driver class
    """

    def __init__(self, InstrumentAddress=None, timeout=500, read_termination='\r', write_termination='\r', baud_rate=9600, data_bits=8, *args, **kwargs):
        self._device_specifics = dict(timeout=timeout,
                                      read_termination=read_termination,
                                      write_termination=write_termination,
                                      baud_rate=baud_rate,
                                      data_bits=data_bits,
                                      stop_bits=vconst.StopBits.two,
                                      parity=vconst.Parity.none)
        super().__init__(*args, InstrumentAddress=InstrumentAddress, **kwargs)
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)

        # self.initialise_device_specifics(**self._device_specifics)

    def initialise_device_specifics(self, **kwargs):
        # self._visa_resource.query_delay = 0.
        super().initialise_device_specifics(**kwargs)

        self.delay = 0.1
        self.delay_force = 0.1

    @HandleVisaException
    def clear_buffers(self):
        # self._visa_resource.timeout = 5
        try:
            with self._comLock:
                self._visa_resource.read()
        except VisaIOError as e_visa:
            if isinstance(e_visa, type(self.timeouterror)) and e_visa.args == self.timeouterror.args:
                pass
            else:
                raise e_visa
        # self._visa_resource.timeout = 500


class AbstractModernVISADriver(AbstractVISADriver):
    """docstring for Instrument_GPIB"""

    def __init__(self, comLock=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)
        if comLock is not None:
            self._comLock = comLock

    def query(self, command):
        """Sends commands as strings to the device and receives strings from the device

        :param command: string generated by a given function, whom will be sent to the device
        :type command: str

        :return: answer from the device
        """
        q = super().query(command)
        try:
            return q.strip().split(',')
        except AttributeError:
            return [q] * 50

    def go(self, command):
        """Sends commands as strings to the device

        :param command: string generated by a given function, whom will be sent to the device
        :type command: str

        """
        super().write(command)


class AbstractGPIBDeviceDriver(AbstractModernVISADriver):
    """docstring for Instrument_GPIB"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AbstractEthernetDeviceDriver(AbstractModernVISADriver):
    """docstring for Instrument_GPIB"""

    def __init__(self, InstrumentAddress, read_termination='\r\n', write_termination='\n', *args, **kwargs):
        self._device_specifics = dict(
            read_termination=read_termination,
            write_termination=write_termination)
        super().__init__(*args, InstrumentAddress=InstrumentAddress, **kwargs)


if __name__ == '__main__':
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    # handler = logging.StreamHandler(sys.stderr)
    # handler.setLevel(logging.DEBUG)
    # formatter = logging.Formatter(
    #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # handler.setFormatter(formatter)
    # logger.addHandler(handler)

    # print('     opening device')
    # a = AbstractSerialDeviceDriver('ASRL5::INSTR')
    # print('     opened device')

    print('     opening device')
    a = AbstractEthernetDeviceDriver('TCPIP::192.168.2.105::7777::SOCKET')
    print('     opened device')

    print(a.query('*IDN?'))
    # print('     closing device')
    # a.res_close()
    # print('     device closed')
    # a.res_open()
    # print('     device reopened')
    # try:
    #     print(a.query('IDN?'))
    # except VisaIOError:
    #     a.clear_buffers()
    # # time.sleep(4)
    # print(a.query('IDN?'))
