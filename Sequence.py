from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer

import sys
import datetime
import pickle
import os

from util import AbstractEventhandlingThread



class Sequence_Thread(AbstractEventhandlingThread):
	"""docstring for Sequence_Thread"""
	def __init__(self):
		super(Sequence_Thread, self).__init__()
		self.__isRunning = True

	def running(self):
		pass

	def stop(self):
		"""stop the sequence execution by setting self.__isRunning to False"""
		self.__isRunning = False
