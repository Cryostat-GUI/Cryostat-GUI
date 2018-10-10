import threading
import time
import visa
from pyvisa.errors import VisaIOError
from PyQt5.QtCore import pyqtSignal, pyqtSlot

try:
    # the pyvisa manager we'll use to connect to the GPIB resources
    resource_manager = visa.ResourceManager()
except OSError:
    logger.exception("\n\tCould not find the VISA library. Is the National Instruments VISA driver installed?\n\n")



import functools

# def do_check(func):
#     @functools.wraps(func)
#     def wrapper_do_check(*args, **kwargs):
#         value = func(*args, **kwargs)
#         if value == "" or None:
#             # raise AssertionError('SerialDriver: query: bad reply: empty string')
#             print('SerialDriver empty string')
#             value = wrapper_do_check(*args, **kwargs)
#         if value[0] == '?': 
#             print('serialDriver received "?": {}'.format(value))
#             value = wrapper_do_check(*args, **kwargs)
#         return value
#     return wrapper_do_check

class AbstractSerialDeviceDriver(object):
    """Abstract Device driver class"""
    timeouterror = VisaIOError(-1073807339)
    def __init__(self, InstrumentAddress):
        super(AbstractSerialDeviceDriver, self).__init__()
        self._visa_resource = resource_manager.open_resource(InstrumentAddress)
        # self._visa_resource.query_delay = 0.
        self._visa_resource.timeout = 500
        self._visa_resource.read_termination = '\r'
        self._visa_resource.write_termination = '\r'
        self.ComLock = threading.Lock()    
        self.delay = 0.0


    @pyqtSlot(float)
    def set_delay_measuring(self, delay):
        self.delay = delay

    def write(self, command):
        """
            low-level communication wrapper for visa.write with Communication Lock, 
            to prevent multiple writes to serial adapter
        """
        with self.ComLock: 
            self._visa_resource.write(command)
            time.sleep(self.delay)

    # @do_check
    def query(self, command):
        """
            low-level communication wrapper for visa.query with Communication Lock, 
            to prevent multiple writes to serial adapter
        """
        with self.ComLock: 
            answer = self._visa_resource.query(command)
            time.sleep(self.delay)
        return answer

    # def query(self, command):
    #     answer = self.query_wrap(command)
    #     # error handling for itc503
    #     if answer[0] == 'T':
    #         self.read()
    #         answer = self.query(command)
    #     return answer

    def read(self):
        with self.ComLock: 
            answer = self._visa_resource.read()
            # time.sleep(self.delay)
        return answer

    def clear_buffers(self):
        self._visa_resource.timeout = 5
        try:
            self.read()
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                pass
            else: 
                raise e_visa
        self._visa_resource.timeout = 500