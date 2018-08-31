
import sys
import time


# from labdrivers.oxford.itc503 import itc503 
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

from pyvisa.errors import VisaIOError

import ITCcontrol_ui 





class ITC_Updater(QObject):

    """This is the worker thread, which updates all instrument data of the self.ITC 503.

        For each self.ITC503 function (except collecting data), there is a wrapping method,
        which we can call by a signal, from the main thread. This wrapper sends
        the corresponding value to the device. 

        There is a second method for all wrappers, which accepts
        the corresponding value, and stores it, so it can be sent upon acknowledgment 

        The information from the device is collected in regular intervals (method "work"),
        and subsequently sent to the main thread. It is packed in a dict,
        the keys of which are displayed in the "sensors" dict in this class. 
    """

    sig_Infodata = pyqtSignal(dict)
    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)

    sensors = dict(
            set_temperature = 0,
            sensor_1_temperature = 1,
            sensor_2_temperature = 2,
            sensor_3_temperature = 3,
            temperature_error = 4,
            heater_output_as_percent = 5,
            heater_output_as_voltage = 6,
            gas_flow_output = 7,
            proportional_band = 8,
            integral_action_time = 9,
            derivative_action_time = 10)

    def __init__(self, ITC):
        QThread.__init__(self)

        # here the class instance of the ITC should be handed
        self.ITC = ITC
        self.__abort = False

        # TODO need initialisation for all the parameters!

        self.control_unlocked = 1
        self.control_remote = 1
        self.set_temperature = 0
        self.set_prop = 0
        self.set_integral = 0
        self.set_derivative = 0
        self.set_sensor = 1
        self.set_heater_output = 0
        self.set_gas_output = 0
        self.set_auto_manual = 0
        self.sweep_parameters = None

        self.delay1 = 1
        self.delay2 = 0.2
        self.setControl()
        self.__isRunning = True


    @pyqtSlot() # int
    def work(self):
        """class method which is working all the time while the thread is running
            
        """
        # app.processEvents()
        while self.__isRunning:
            # time.sleep(1)
            try: 
                data = dict()
                # get key-value pairs of the sensors dict, 
                # so I can then transmit one single dict
                for key, idx_sensor in self.sensors.items():
                    data[key] = self.ITC.getValue(idx_sensor)
                    time.sleep(self.delay2)
                self.sig_Infodata.emit(data)
                # time.sleep(self.delay1)
                # print(self.set_temperature)

            except VisaIOError as e_visa:
                if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args:
                    self.sig_visatimeout.emit()
                else: 
                    self.sig_visaerror.emit(e_visa.args[0])
            except AssertionError as assertion: 
                self.sig_assertion.emit(assertion.args[0])

    @pyqtSlot()
    def stop(self):
        self.__isRunning = False

    @pyqtSlot(int)
    def set_delay_sending(self, delay):
        self.delay1 = delay

    @pyqtSlot(int)
    def set_delay_measuring(self, delay):
        self.delay2 = delay



    @pyqtSlot()
    def setNeedle(self):
        """class method to be called to set Needle
            this is necessary, so it can be invoked by a signal
        """
        value = self.set_GasOutput
        try:
            if 0 <= value <= 100:
                self.ITC.setGasOutput(value)
            else:
                raise AssertionError('Gas output setting must be between 0 and 100%!')
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setControl(self):
        """class method to be called to set Control
            this is to be invoked by a signal
        """
        try:
            self.ITC.setControl(unlocked=self.control_unlocked, remote=self.control_remote)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setTemperature(self):
        """class method to be called to set Temperature
            this is to be invoked by a signal
        """
        try:
            self.ITC.setTemperature(self.set_temperature)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setProportional(self):
        """class method to be called to set Proportional
            this is to be invoked by a signal

            prop: Proportional band, in steps of 0.0001K.
        """
        try:
            self.ITC.setProportional(self.set_prop)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setIntegral(self):
        """class method to be called to set Integral
            this is to be invoked by a signal

            integral: Integral action time, in steps of 0.1 minute.
                        Ranges from 0 to 140 minutes.
        """
        try:
            self.ITC.setIntegral(self.set_integral)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setDerivative(self):
        """class method to be called to set Derivative
            this is to be invoked by a signal
            
            derivative: Derivative action time.
            Ranges from 0 to 273 minutes.
        """
        try:
            self.ITC.setDerivative(self.set_derivative)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setHeaterSensor(self, value):
        """class method to be called to set HeaterSensor
            this is to be invoked by a signal

            sensor: Should be 1, 2, or 3, corresponding to
            the heater on the front panel.
        """
        self.set_sensor = value
        try:
            self.ITC.setHeaterSensor(self.set_sensor)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setHeaterOutput(self):
        """class method to be called to set HeaterOutput
            this is to be invoked by a signal

            heater_output: Sets the percent of the maximum
                        heater output in units of 0.1%.
                        Min: 0. Max: 999.
        """
        try:
            self.ITC.setHeaterOutput(self.set_heater_output)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setGasOutput(self):
        """class method to be called to set GasOutput
            this is to be invoked by a signal

            gas_output: Sets the percent of the maximum gas
                    output in units of 1%.
                    Min: 0. Max: 99.            
        """
        try:
            self.ITC.setGasOutput(self.set_gas_output)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setAutoControl(self, value):
        """class method to be called to set AutoControl
            this is to be invoked by a signal

        Value:Status map
            0: heater manual, gas manual
            1: heater auto  , gas manual
            2: heater manual, gas auto
            3: heater auto  , gas auto

        """
        self.set_auto_manual = value
        try:
            self.ITC.setAutoControl(self.set_auto_manual)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])

    @pyqtSlot()
    def setSweeps(self):
        """class method to be called to set Sweeps
            this is to be invoked by a signal
        """
        try:
            self.ITC.setSweeps(self.sweep_parameters)
        except AssertionError as e_ass:
            self.sig_assertion.emit(e_ass.args[0])
        except VisaIOError as e_visa:
            if type(e_visa) is type(self.timeouterror) and e_visa.args == self.timeouterror.args: 
                self.sig_visatimeout.emit()
            else: 
                self.sig_visaerror.emit(e_visa.args[0])


    @pyqtSlot(float)
    def gettoset_Temperature(self, value):
        """class method to receive and store the value to set the temperature
            later on, when the command to enforce the value is sent
        """
        self.set_temperature = value
        # print('got it')

    @pyqtSlot()
    def gettoset_Proportional(self, value):
        """class method to receive and store the value to set the proportional (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_prop = value

    @pyqtSlot()
    def gettoset_Integral(self, value):
        """class method to receive and store the value to set the integral (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_integral = value

    @pyqtSlot()
    def gettoset_Derivative(self, value):
        """class method to receive and store the value to set the derivative (PID)
            later on, when the command to enforce the value is sent
        """
        self.set_derivative = value

    @pyqtSlot()
    def gettoset_HeaterOutput(self, value):
        """class method to receive and store the value to set the heater_output
            later on, when the command to enforce the value is sent
        """
        self.set_heater_output = value

    @pyqtSlot()
    def gettoset_GasOutput(self, value):
        """class method to receive and store the value to set the gas_output
            later on, when the command to enforce the value is sent
        """
        self.set_gas_output = value

    @pyqtSlot()
    def gettoset_Sweeps(self, value):
        """class method to receive and store the value to for the sweep_parameters
            to set them later on, when the command to enforce the value is sent
        """
        self.sweep_parameters = value


    # @pyqtSlot()
    # def gettoset_HeaterSensor(self, value):
    #     """class method to receive and store the value to set the sensor
    #         later on, when the command to enforce the value is sent
    #     """
    #     self.set_sensor = value

    # @pyqtSlot()
    # def gettoset_AutoControl(self, value):
    #     """class method to receive and store the value to set the auto_manual
    #         later on, when the command to enforce the value is sent
    #     """
    #     self.set_auto_manual = value

# class NeedleValve_Window(QtWidgets.QMainWindow): # , self.ITCcontrol_ui.Ui_ITCcontrol):
    
#     sig_arbitrary = pyqtSignal()

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         QThread.__init__(self)
#         # self.setupUi(self)
#         loadUi('ITC_control.ui')




#         # self.ITC = self.ITC503()
#         # self.liste = []
#         # self.getInfodata = self.ITC_Updater(ITC)
#         # self.thread = QThread()
#         # self.liste.append((self.getInfodata, self.thread))
#         # self.getInfodata.moveToThread(self.thread)

#         # self.getInfodata.sig_GasOutput.connect(self.setNeedleIndicator)

#         # self.thread.started.connect(self.getInfodata.work)
#         # self.thread.start()

#         # self.Slider_Needle.valueChanged['int'].connect(self.setNeedle)
    
#         # self.Something_temperature.valueChanged['int'].connect(self.send_data)

#     # this is meant as an example, which should be tested, and then possibly followed! 
#     def send_data(self, data:int):
#         self.sig_arbitrary.connect(self.getInfodata.gettoset_Temperature)
#         self.sig_arbitrary.emit(data)

        

#     # def setNeedle(self, value):
#     #   if (0 <= value <= 100):
#     #       self.ITC.setGasOutput(value)

#     # @pyqtSlot(int)
#     # def setNeedleIndicator(self, value):
#     #   self.NeedleValve_bar.setValue(value)



# if __name__ == '__main__':
#     app = QtWidgets.QApplication(sys.argv)
#     form = NeedleValve_Window()
#     form.show()
#     sys.exit(app.exec_())
