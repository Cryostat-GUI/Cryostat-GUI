# -*- coding: utf-8 -*-
"""
Driver for the Keithley 2182 Nano-Voltmeter
"""

# import threading
import visa

import logging

from drivers import AbstractGPIBDeviceDriver

# create a logger object for this module
logger = logging.getLogger(__name__)
# added so that log messages show up in Jupyter notebooks
logger.addHandler(logging.StreamHandler())

try:
    # the pyvisa manager we'll use to connect to the GPIB resources
    resource_manager = visa.ResourceManager(
        'C:\\Windows\\System32\\agvisa32.dll')
except OSError:
    logger.exception(
        "\n\tCould not find the VISA library. Is the National Instruments VISA driver installed?\n\n")


class Keithley2182(AbstractGPIBDeviceDriver):

    """
    The Keithley 2182 is a nano-voltmeter.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def measureVoltage(self):
        """measure voltage
        :return: voltage in V
        :return type: float
        """
       # self.sendcmd("SENS:CHAN 1")
       # self.sendcmd("SENS:FUNC 'VOLT:DC'")
       # return self.query("SENS:DATA:FRES?")[0]
        self.go(':TRIGger:COUNt 1')
        answer = self.query(':READ?')[0]
        if answer[0:2] == '--':
            answer = answer[1:]
        return float(answer)

    def DisplayOn(self):
        self.go(':DISPlay:ENABle ON')

    def DisplayOff(self):
        self.go(':DISPlay:ENABle OFF')

    def setRate(self, value='MED', num=None):
        """
        Change the measuring rate

        :SENSe SENSe Subsystem:
            :VOLTage DCV1 and DCV2:
                :NPLCycles <n>
                    Specify integration rate in PLCs:
                       [0.01 to 60 (60Hz)]
                       [0.01 to 50 (50Hz)]
                :APERture <n>
                    Specify integration rate in seconds:
                       [166.67μsec to 1 sec (60Hz)]
                       [200μsec to 1 sec (50Hz)]
            """
        if num is None:
            if value == 'FAS':
                self.go(':SENSe:VOLTage:DC:NPLC 0.1')
            if value == 'MED':
                self.go(':SENSe:VOLTage:DC:NPLC 1')
            if value == 'SLO':
                self.go(':SENSe:VOLTage:DC:NPLC 5')
        else:
            if 0.01 > num > 50:
                raise AssertionError('Keithley2182:setRate: The measuring rate'
                                     ' needs to be between 0.01 and 50 NPLCycles'
                                     ' - that is 200microseconds to 1 second '
                                     '(at a 50Hz powerline - europe)')
            self.go(':SENSe:VOLTage:DC:NPLC {}'.format(num))

    def FrontAutozeroOn(self):
        """
            With Front Autozero for the front-end amplifier enabled (which is the default setting), the
            Model 2182 performs two A/D measurement cycles for each reading. The first one is a normal
            measurement cycle, and the second one is performed with the polarity of the amplifier reversed.
            This two-cycle, polarity-reversal measurement technique is used to cancel internal offsets in the
            amplifier. With Front Autozero disabled, the second A/D measurement cycle is not performed.
        """
        self.go(':SYST:FAZ ON')

    def FrontAutozeroOff(self):
        """See FrontAutoZeroOn
        """
        self.go(':SYST:FAZ OFF')

    def AutozeroOn(self):
        """
            When Autozero for the second amplifier is disabled, the offset, gain, and internal reference
            temperature measurements are not performed. This increases measurement speed (a few % at 1PLC).
            However, the zero, gain, and temperature reference points will eventually drift resulting in
            inaccurate readings for the input signal. It is recommended that Autozero only be disabled for
            short periods of time.
            When Autozero is enabled after being off for a long period of time, the internal reference points
            will not be updated immediately. This will initially result in inaccurate measurements, especially
            if the ambient temperature has changed by several degrees. A faster update of reference points
            can be forced by setting a faster integration rate.
        """
        self.go(':SYST:AZER ON')

    def AutozeroOff(self):
        """See AutoZeroOn
        """
        self.go(':SYST:AZER OFF')

    def AutorangeOn(self):
        """
            To enable autoranging, press the AUTO key. The AUTO annunciator turns on when
            autoranging is selected. While autoranging is enabled, the instrument automatically selects the
            best range to measure the applied signal. Autoranging should not be used when optimum speed
            is required. Note that the AUTO key has no effect on temperature (TEMP1 and TEMP2).
            Up-ranging occurs at 120% of range, while down-ranging occurs at 10% of nominal range.
        """
        self.go(':SENS:VOLT:RANG:AUTO ON')

    def AutorangeOff(self):
        """See AutorangeOn"""
        self.go(':SENS:VOLT:RANG:AUTO OFF')

    def more_ACAL(self):
        """Commands Description Default
            For ACAL:
                :CALibration CALibration Subsystem:
                    :UNPRotected
                    :ACALibration ACAL:
                    :INITiate Prepare 2182 for ACAL.
                    :STEP1 Perform full ACAL (100V and 10mV).
                    :STEP2 Perform low level ACAL (10mV only).
                    :DONE Exit ACAL (see Note).
                    :TEMPerature? Read the internal temperature (in °C) at the time
                            of the last ACAL.
            :SENSe SENSe Subsystem:
                :TEMPerature
                    :RTEMperature? Measure the present internal temperature (in °C).
            For Front Autozero:
                :SYSTem SYSTem Subsystem:
                    :FAZero [state] <b> Enable or disable Front Autozero. ON
            For Autozero:
                :SYSTem SYSTem Subsystem:
                    :AZERo [state] <b> Enable or disable Autozero. ON
            For LYSNC:
                :SYSTem SYSTem Subsystem:
                    :LSYNc [state] <b> Enable or disable line cycle synchronization. OFF

            not necessarily necessary:
            For Low Charge Injection:
                :SENSe:VOLTage SENSe Subsystem:
                    :CHANnel2
                        :LQMode <b> Enable or disable Low Charge Injection Mode for
                            Channel 2 (see “Pumpout current (low charge injection
                            mode)” for details).
        """
        pass

    def more_Range(self):
        """Commands Description Default
        :SENSe: SENSe Subsystem:
            :VOLTage Volts function:
                [:CHANnel1] Channel 1 (DCV1):
                    :RANGe Range selection:
                        [:UPPer] <n> Specify expected reading: 0 to 120 (volts). 120
                        : AUTO <b> Enable or disable auto range.

        :CHANnel2 Channel 2 (DCV2):
            :RANGe Range selection:
                [:UPPer] <n> Specify expected reading: 0 to 12 (volts). 12
                : AUTO <b> Enable or disable auto range."""
        pass

    def more_device_operation(self):
        """implement LLO and GTL (local locked out & go to local)"""

        pass
