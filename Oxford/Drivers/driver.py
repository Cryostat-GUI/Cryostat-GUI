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



class AbstractSerialDeviceDriver(object):
    """Abstract Device driver class"""
    def __init__(self, InstrumentAddress=''):
        super(AbstractSerialDeviceDriver, self).__init__()
        self._visa_resource = resource_manager.open_resource(InstrumentAddress)
        self._visa_resource.read_termination = '\r'
        self.ComLock = threading.Lock()    
        self.delay = 0.2


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


    def query(self, command):
        """
            low-level communication wrapper for visa.query with Communication Lock, 
            to prevent multiple writes to serial adapter
        """
        with self.ComLock: 
            answer = self._visa_resource.query(command)
            time.sleep(self.delay)
        return answer
