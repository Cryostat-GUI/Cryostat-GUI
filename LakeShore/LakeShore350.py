# Commands for dealing with the LAKESHORE 350

import Gpib, time, socket, threading
import os, string
import numpy as np

from console_out import *

import logging

# create a logger object for this module
logger = logging.getLogger(__name__)
# added so that log messages show up in Jupyter notebooks
logger.addHandler(logging.StreamHandler())


class LAKESHORE350:
    def __init__(self):
        self.host = 'lakeshore'  # GPIB mnemonic for Lakeshore temp controller
        self.timeout = 30
        self.status = ''
        self.identity = ''
        self.connected = False
        self.input_num = 'A'
        self.curve_num = 21
        self.selected_curve = ''
        self.style = '\033[7;95m'
        self.temp = ''
        self.text = Text()
        self.communicationLock = threading.Lock()

    def connect(self):
        try:
            self.device = Gpib.Gpib(self.host)
            self.identity = self.go('*IDN?')
            self.text.show(self.identity, 'message')
            self.status = 'connected'
            self.connected = True
            self.initialize()
            self.get_curves()

        except socket.timeout:
            self.status = "socket timeout"
            self.identity = 'none'
            self.connected = False
        return self.identity

    def initialize(self):
        """ Input Type Parameter Command
        INTYPE  <input>,
                <sensor type>, 3 = NTC RTD
                <autorange>, 1 = on
                <range>, 0 = 10ohm with NTC RTD
                <compensation>, 1 = on
                <units>, 1 = kelvin
                <sensor excitation> 0 = 1mV [term]

        """


        for a in ['A', 'B', 'C', 'D']:
            cmd = 'INTYPE %c,3,1,0,1,1,0' % (a)
            self.text.show(cmd, 'blue')
            self.communicationLock.acquire()
            self.device.write(cmd + '\n')
            self.communicationLock.release()

    def go(self, command):
        # writes command to device & stores show received data
        self.communicationLock.acquire()
        self.device.write(command)
        received = self.device.read(100).split('\r\n')[0]
        self.communicationLock.release()
        self.text.show(command + '    ' + received[:10].strip() + '...', 'blue')
        return received.strip()

    def clear(self):
        self.go('*CLS')

    def get_curves(self):
        self.curves = []
        self.curve_mnemonics = []
        try:
            for a in range(1, 30):
                curve = self.go('CRVHDR? ' + str(a)).split(',')
                data_id = curve[1].strip()  # The unique ID of the calibration data
                if data_id != '':
                    self.curves.append([data_id, a, curve[0]])
                    self.curve_mnemonics.append(data_id + ' - ' + curve[0][:10])
        except:
            print 'Couldnt load all curves'
        print self.curves
        return self.curves

    def load_parameters(self):
        cmd = 'INCRV ' + str(self.input_num) + ',' + str(self.curve_num)
        self.communicationLock.acquire()
        self.device.write(cmd + '\n')
        self.text.show(cmd, 'blue')
        self.communicationLock.release()
        print 'Selected Input ', self.input_num, ' and loaded curve ', self.curve_num, self.selected_curve
        return 'Temp route : ' + self.input_num + ' ' + self.selected_curve

    def get_temp(self):
        # print self.input_num,len(self.input_num)
        self.temp = self.go('KRDG? ' + str(self.input_num))
        return self.temp

    def set_temp(self):
        pass


