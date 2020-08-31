"""Module containing a class to interface with a LakeShore 350 Cryogenic Temperature Controller

Attributes:
    logger: a python logger object

Classes:
    LakeShore350: a class for interfacing with a LakeShore350 temperature controller
            inherits from AbstractGPIBDeviceDriver where the low-level visa
            communications are defined.
"""
import logging
from itertools import combinations

from drivers import AbstractGPIBDeviceDriver
from drivers import AbstractEthernetDeviceDriver

# create a logger object for this module
logger = logging.getLogger(__name__)
# added so that log messages show up in Jupyter notebooks
logger.addHandler(logging.StreamHandler())

# try:
#     # the pyvisa manager we'll use to connect to the GPIB resources
#     resource_manager = visa.ResourceManager(
#         'C:\\Windows\\System32\\agvisa32.dll')
# except OSError:
#     logger.exception(
#         "\n\tCould not find the VISA library. Is the National Instruments / Agilent VISA driver installed?\n\n")


class LakeShore350_bare(object):
    """class to interface with a LakeShore350

    in order to change the self.go() and self.query() commands,
    use inheritance injection:
    class TCPLakeShore(LakeShore350, TCPInstrument):
        pass
    where in TCPInstrument you must define
        self.go()
        self.query()
        self.__init__()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # def go(self, command):
    #     """write a command to the instrument"""
    #     return super().go(command)

    # def query(self, command):
    #     """write a command to the instrument and return its answer"""
    #     return super().query(command)

    def ClearInterfaceCommand(self):
        """Clears the bits in the Status Register, Standard Event Status Register, and Operation Event Register,
        and terminates all pending operations. Clears the interface, but not the controller. The related
        controller command is *RST.
        """
        self.go("*CLS")

    def EventStatusEnableRegisterCommand(self, bit_weighting):
        """Each bit is assigned a bit weighting and represents the enable/disable mask of the corresponding
        event flag bit in the Standard Event Status Register. Refer to section 6.2.5 for a list of event flags.
            Bit     Bit Weighting       Event Name
            0       1                   OPC
            2       4                   QXE
            4       16                  EXE
            5       32                  CME
            7       128                 PON
            Total:  181

        :param bit_weighting: sum of the bit weighting for each desired bit
        :type bit_weighting: int
        """
        weighting_list = [1, 4, 16, 32, 128]
        sum_list = sum(
            [
                map(list, combinations(weighting_list, i))
                for i in range(len(weighting_list) + 1)
            ],
            [],
        )
        map_list = map(sum, sum_list)  # creates list of all possible sums

        if bit_weighting not in map_list:
            raise AssertionError(
                "Bit_Weighting parameter must be a sum of elements of [0,1,4,16,32,128]."
            )

        self.go("*ESE " + "{0:3d}".format(bit_weighting))

    def EventStatusEnableRegisterQuery(self):
        """Refer to EventStatusEnableRegisterCommand for description.

        :return: sum of the bit weighting for each bit
        """
        return self.query("*ESE?")

    def StandardEventStatusRegisterQuery(self):
        """The integer returned represents the sum of the bit weighting of the event flag bits in the
        Standard Event Status Register. Refer to section 6.2.5 for a list of event flags.

        :return: sum of the bit weighting for each desired bit
        """
        return self.query("*ESR?")

    def IdentificationQuery(self):
        """Returns information about the device

        :return: ['<manufacturer>','<model>','<instrument serial>','<option serial>','<firmware version>']
            <manufacturer>          Manufacturer ID
            <model>                 Instrument model number
            <instrument serial>     Instrument serial number
            <option card serial>    Option card serial number
            <firmware version>      Instrument firmware version
        """
        return self.query("*IDN?")

    def OperationCompleteCommand(self):
        """Generates an Operation Complete event in the Event Status Register upon
        completion of all pending selected device operations.
        Send it as the last command in a command string.
        """
        self.go("*OPC")

    def OperationCompleteQuery(self):
        """Places a 1 in the controller output queue upon completion of all pending selected device
        operations. Send as the last command in a command string. Not the same as *OPC.

        :return: 1
        """
        return self.go("*OPC?")

    def ResetInstrumentCommand(self):
        """Sets controller parameters to power-up settings.
        """
        self.go("*RST")

    def ServiceRequestEnableRegisterCommand(self, bit_weighting):
        """Each bit has a bit weighting and represents the enable/disable mask of the corresponding
        status flag bit in the Status Byte Register. To enable a status flag bit, send the command *SRE with
        the sum of the bit weighting for each desired bit. Refer to section 6.2.6 for a list of status flags.
            Bit     Bit Weighting       Event Name
            4       16                  MAV
            5       64                  ESB
            7       128                 OSB
            Total:  208

        :param bit_weighting: sum of the bit weighting for each desired bit
        :type bit_weighting: int
        """
        weighting_list = [16, 64, 128]
        sum_list = sum(
            [
                map(list, combinations(weighting_list, i))
                for i in range(len(weighting_list) + 1)
            ],
            [],
        )
        map_list = map(sum, sum_list)  # creates list of all possible sums

        if bit_weighting not in map_list:
            raise AssertionError(
                "Bit_Weighting parameter must be an Integer in [16,64,128]."
            )

        self.go("*SRE " + "{0:3d}".format(bit_weighting))

    def ServiceRequestEnableRegisterQuery(self):
        """Refer to ServiceRequestEnableRegisterCommand for description.

        :return: <bit weighting>
        """
        return self.query("*SRE?")

    def StatusByteQuery(self):
        """Acts like a serial poll, but does not reset the register to all zeros. The integer returned
        represents the sum of the bit weighting of the status flag bits that are set in the Status Byte Register.
        Refer to section 6.2.6 for a list of status flags.

        :return: <bit weighting>
        """
        return self.query("*STB?")

    def SelfTestQuery(self):
        """The Model 350 reports status based on test done at power up.

        :return: 0 = 'no errors found' OR 1 = 'errors found'
        """
        return self.query("*TST?")

    def WaitToContinueCommand(self):
        """Causes the IEEE-488 interface to hold off until all pending operations have been completed.
        This is the same function as the *OPC command, except that it does not set the Operation Complete event
        bit in the Event Status Register.
        """
        self.go("*WAI*")

    def InputAlarmParameterCommand(
        self,
        input_value,
        check_state=1,
        set_high=450,
        set_low=0,
        deadband=0,
        latch_enable=1,
        audible=1,
        visible=1,
    ):
        """Configures the alarm parameters for an input_value.

        :param input_value: Specifies which input to configure: A - D (D1 - D5 for 3062 option).
        :type input_value: str
        :param check_state: Determines whether the instrument checks the alarm for this input, where 0 = off and 1 = on.
        :type check_state: int
        :param set_high: Sets the value the source is checked against to activate the high alarm.
        :type set_high: float
        :param set_low: Sets the value the source is checked against to activate low alarm.
        :type set_low: float
        :param deadband: Sets the value that the source must change outside of an alarm condition to deactivate an unlatched alarm.
        :type deadband: int
        :param latch_enable: Specifies a latched alarm (remains active after alarm condition correction) where 0 = off(no latch) and 1 = on.
        :type latch_enable: int
        :param audible: Specifies if the internal speaker will beep when an alarm condition occurs. Valid entries: 0 = off, 1 = on.
        :type audible: int
        :param visible: Specifies if the Alarm LED on the instrument front panel will blink when an alarm condition occurs. Valid entries: 0 = off, 1 = on.
        :type visible: int

        Default:
            check_state = 1, set_high = 450, set_low = 0, deadband = 0, latch_enable = 1, audible = 1, visible = 1

        Example:
        ALARM A,0[term] — turns off alarm checking for input_value A.
        ALARM B,1,270.0,0,0,1,1,1[term] — turns on alarm checking for input B, activates high alarm if Kelvin reading is
        over 270, and latches the alarm when Kelvin reading falls below 270. Alarm condition will cause instrument to
        beep and the front panel Alarm LED to blink.
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        if check_state not in [0, 1]:
            raise AssertionError(
                "Check_State parameter must be an integer in [0,1.].")

        if set_high < 0.0:
            raise AssertionError(
                "Set_High parameter must be a float greater than 0.")

        if set_low < 0.0:
            raise AssertionError(
                "Set_Low parameter must be a float greater than 0.")

        if deadband < 0:
            raise AssertionError(
                "Deadband parameter must be a float greater than 0.")

        if latch_enable not in [0, 1]:
            raise AssertionError(
                "Latch_Enable parameter must be an integer in [0,1].")

        if audible not in [0, 1]:
            raise AssertionError(
                "Audible parameter must be an integer in [0,1.].")

        if visible not in [0, 1]:
            raise AssertionError(
                "LakeShore: Visible parameter must be an integer in [0,1]."
            )

        if check_state == 0:
            self.go("ALARM " + "{0:1},{1:1d}".format(input_value, check_state))

        if check_state == 1:
            self.go(
                "ALARM "
                + "{0:1},{1:1d},{2:4.2f},{3:4.2f},{4:4.2f},{5:1d},{6:1d},{7:1d}".format(
                    input_value,
                    check_state,
                    set_high,
                    set_low,
                    deadband,
                    latch_enable,
                    audible,
                    visible,
                )
            )

    def InputAlarmParameterQuery(self, input_value):
        """Refer to InputAlarmParameterCommand for description.

        :param input_value: Specifies which input to read: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: ['<off/on>','<high value>','<low value>','<deadband>','<latch enable>','<audible>','<visible>']
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("ALARM? " + "{0:1}".format(input_value))

    def InputAlarmStatusQuery(self, input_value):
        """Returns alarm status whereas 0 = Off and 1 = On.

        :param input_value:  A - D (D1 - D5 for 3062 option)
        :type input_value: str

        :return: ['<high state>','<low state>']
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("ALARMST? " + "{0:1}".format(input_value))

    def ResetAlarmStatusCommand(self):
        """Clears both the high and low status of all alarms, including latching items.
        """
        self.go("ALMRST")

    def MonitorOutParameterCommand(
        self, output, input_value, high_value, low_value, polarity, units=1
    ):
        """Use the OUTMODE command to set the output mode to Monitor Out. The <input_value> parameter in the ANALOG
        command is the same as the <input_value> parameter in the OUTMODE command. It is included in the ANALOG command
        for backward compatibility with previous Lake Shore temperature monitors and controllers. The ANALOG com-
        mand name is also named as such for backward compatibility.

        :param output:  Unpowered analog output to configure: 3 or 4
        :type output: int
        :param input_value: Specifies which input_value to monitor. 0 = none, 1 = input_value A, 2 = input_value B, 3 = input_value C,
            4 = input_value D (5 = input_value D2, 6 = input_value D3, 7 = input_value D4,8 = input_value D5 for 3062 option)
        :type input_value: int
        :param units: Specifies the units on which to base the output voltage: 1 = Kelvin, 2 = Celsius, 3 = Sensor units
        :type units: int
        :param high_value: If output mode is Monitor Out, this parameter represents the data at which the
            Monitor Out reaches +100% output. Entered in the units designated by the <units>
            parameter. Refer to OUTMODE command.
        :type high_value: float
        :param low_value: If output mode is Monitor Out,this parameter represents the data at which the analog
            output reaches -100% output if bipolar, or 0% output if positive only. Entered in the
            units designated by the <units> parameter.
        :type low_value: float
        :param polarity: Specifies output voltage is 0 = unipolar (positive output only) or 1 = bipolar (positive
            or negative output)
        :type polarity: int

        Default:
            units = 1

        Example:
            ANALOG 4,1,1,100.0,0.0,0[term] — sets output 4 to monitor input_value A kelvin reading with 100.0 K at
            +100% output (+10.0 V) and 0.0 K at 0% output (0.0 V).
        """
        if output not in [3, 4]:
            raise AssertionError(
                "Output parameter must be an integer in [3,4].")

        if input_value not in [0, 1, 3, 4]:
            raise AssertionError(
                "Input_Value Parameter must be an integer in [0,1,3,4]."
            )

        if units not in [1, 2, 3]:
            raise AssertionError(
                "Units parameter must be an integer in [1,2,3].")

        if units == 1:
            if high_value < 0.0:
                raise AssertionError(
                    "High_Value parameter is given in Kelvin and must be a float greater than 0."
                )

            if low_value < 0.0:
                raise AssertionError(
                    "Low_Value parameter is given in Kelvin and must be a float greater than 0."
                )

        if units == 2:
            if not isinstance(high_value, float):
                raise AssertionError(
                    "High_Value parameter is given in Celsius and must be a float."
                )

            if not isinstance(low_value, float):
                raise AssertionError(
                    "Low_Value parameter is given in Celsius and must be a float."
                )

        if units == 3:
            if not isinstance(high_value, float):
                raise AssertionError(
                    "High_Value parameter is given in Sensor Units. Check your sensor for valid floats."
                )

            if not isinstance(low_value, float):
                raise AssertionError(
                    "Low_Value parameter is given in Sensor Units. Check your sensor for valid floats."
                )

        if polarity not in [0, 1]:
            raise AssertionError(
                "Poalrity parameter must be an integer in [0,1].")

        self.go(
            "ANALOG "
            + "{0:1d},{1:1d},{2:1d},{3:4.2f},{4:4.2f},{5:1d}".format(
                output, input_value, units, high_value, low_value, polarity
            )
        )

    def MonitorOutParameterQuery(self, output):
        """Refer to MonitorOutParameterCommand for description.

        :param output: Specifies which unpowered analog output to query the Monitor Out parameters for: 3 or 4.
        :type output: int

        :return: ['<input_value>','<units>','<high value>','<low value>','<polarity>']
        """
        if output not in [3, 4]:
            raise AssertionError(
                "Output parameter must be an integer in [3,4].")

        return self.query("ANALOG? " + "{0:1d}".format(output))

    def AnalogOutputDataQuery(self, output):
        """Returns the output percentage of the unpowered analog output.

        :param output: Specifies which unpowered analog output to query: 3 or 4.
        :type output: int

        :return: <output percentage>
        """
        if output not in [3, 4]:
            raise AssertionError(
                "Output parameter must be an integer in [3,4].")

        return self.query("AOUT? " + "{0:1d}".format(output))

    def AutotuneCommand(self, output, mode):
        """If initial conditions required to Autotune the specified loop are not met, an Autotune
        initialization error will occur and the Autotune process will not be performed. The TUNEST? query can be
        used to check if an Autotune error occurred.

        :param output: Specifies the output associated with the loop to be Autotuned: 1–4.
        :type output: int
        :param mode: Specifies the Autotune mode. Valid entries: 0 = P Only, 1 = P and I, 2 = P, I, and D.
        :type mode: int

        Example:
            AT  UNE 2,1 [term] — initiates Autotuning of control loop associated with output 2, in P and I mode.
        """
        if output not in [1, 2, 3, 4]:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if output not in [3, 4]:
            raise AssertionError(
                "Mode parameter must be an integer in [0,1,2].")

        self.go("ATUNE " + "{0:1d},{1:1d}".format(output, mode))

    def DisplayContrastCommand(self, contrast_value):
        """Sets the display contrast for the front panel LCD.

        :param contrast_value: 1 - 32
        :type contrast_value: int
        """
        if 1 > contrast_value > 32:
            raise AssertionError(
                "Contrast_Value parameter must be an integer in between 1 - 32."
            )

        # with or without leading zero?
        self.go("BRIGT " + "{0:2d}".format(contrast_value))

    def DisplayContrastQuery(self):
        """Refer to DisplayContrastCommand for description.

        :return: <contrast value>
        """
        return self.query("BRIGT?")

    def CelsiusReadingQuery(self, input_value):
        """Returns the Celsius reading for a single input_value or all input_values.
        <input_value> specifies which input(s) to query. 0 = all input.Also see the RDGST? command.

        :param input_value: Specifies input_value to query: A-D (D1–D5 for 3062 option)
        :type input_value: int or str

        :return: <temp value> Or if all input_values are queried: ['<A value>','<B value>','<C value>','<D value>']
        """
        if input_value not in [0, "A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value parameter must be a string in ['A','B','C','D'] or an integer with the value 0."
            )

        if input_value in ["A", "B", "C", "D"]:
            return self.query("CRDG? " + "{0:1}".format(input_value))

        if input_value == 0:
            return self.query("CRDG? " + "{0:1d}".format(input_value))

    def CurveDeleteCommand(self, curve):
        """
        :param curve: Specifies a user curve to delete. Vaild entries 21-59.
        :type curve: int

        Example:
            CRVDEL 21[term] — deletes User Curve 21.
        """
        if 21 > curve > 59:
            raise AssertionError(
                "Curve parameter is not an integer in between 21 - 59."
            )

        self.go("CRVDEL " + "{0:2d}".format(curve))

    def CurveHeaderCommand(
        self, curve, name, sn, format_value, coefficient, limit_value=375
    ):
        """Configures the user curve header. The coefficient parameter will be calculated auto-
        matically based on the first 2 curve datapoints. It is included as a parameter for com-
        patability with the CRVHDR? query.

        :param curve: int
            Specifies which curve to configure. Valid entries: 21–59.
        :type curve: int
        :param name: Specifies curve name. Limited to 15 characters.
        :type name: str
        :param sn: Specifies the curve serial number. Limited to 10 characters.
        :type sn: str
        :param format_value: Specifies the curve data format. Valid entries: 1 = mV/K, 2 = V/K, 3 = Ohm/K, 4 = log Ohm/K.
        :type format_value: int
        :param limit_value: Specifies the curve temperature limit in kelvin.
        :type limit_value: float
        :param coefficient: Specifies the curves temperature coefficient. Valid entries: 1 = negative, 2 = positive.
        :type coefficient: int

        Default:
            limit_value = 375

        Example:
            CRVHDR 21,DT-470,00011134,2,325.0,1[term]—configures User Curve 21 with a
            name of DT-470, serial number of 00011134, data format of volts versus kelvin, upper
            temperature limit of 325 K, and negative coefficient.
        """
        if 21 > curve > 59:
            raise AssertionError(
                "Curve parameter must be an integer in between 21 - 59."
            )

        if len(name) > 15:
            raise AssertionError(
                "Name parameter must be a string with a maximum of 15 characters."
            )

        if len(sn) > 10:
            raise AssertionError(
                "SN parameter must be a string with a maximum of 10 characters."
            )

        if format not in [1, 2, 3, 4]:
            raise AssertionError(
                "Format_Value parameter must be an integer in [1,2,3,4]."
            )

        if limit_value < 0:
            raise AssertionError(
                "Limit_Value parameter must be a positive float.")

        if coefficient not in [1, 2]:
            raise AssertionError(
                "Coefficient parameter must be an integer in [1,2].")

        self.go(
            "CRVHDR"
            + "{0:2d},{1:15},{2:10},{3:1d},{4:4.2f},{5:1d}".format(
                curve, name, sn, format, limit_value, coefficient
            )
        )

    def CurveHeaderQuery(self, curve):
        """Refer to CurveHeaderCommand for description.

        :param curve: Valid entries: 1–59.
        :type curve: int

        :return: ['<name>','<SN>','<format>','<limit value>','<coefficient>']
        """
        if not isinstance(curve, int) or 1 > curve > 59:
            raise AssertionError(
                "Curve parameter must be an integer in between 1 - 59."
            )

        return self.query("CRVHDR?" + "{0:2d}".format(curve))

    def CurveDataPointCommand(self, curve, index, units_value, temp_value):
        """Configures a user curve data point.

        :param curve: Specifies which curve to configure. Valid entries: 21–59.
        :type curve: int
        :param index: Specifies the points index in the curve. Valid entries: 1–200.
        :type index: int
        :param units_value: Specifies sensor units for this point to 6 digits.
        :type units_value: float
        :param temp_value: Specifies the corresponding temperature in kelvin for this point to 6 digits.
        :type temp_value: float

        Example:
            CRVPT 21,2,0.10191,470.000,N[term] — sets User Curve 21 second data point to 0.10191 sensor units and 470.000 K.
        """
        if not 21 > curve > 59:
            raise AssertionError(
                "Curve parameter must be an integer in between 21 - 59."
            )

        if not 1 > index > 200:
            raise AssertionError(
                "Curve parameter must be an integer in between 1 - 200."
            )

        if not isinstance(units_value, float):  # can be improved?
            raise AssertionError(
                "Units_Value parameter must be a float with up to 6 digits."
            )

        if not isinstance(temp_value, float):  # can be improved?
            raise AssertionError(
                "Temp_Value parameter must be a float with up to 6 digits."
            )

        self.go(
            "CRVPT "
            + "{0:2d},{1:3d},{2:7.3f},{3:7.3f}".format(
                curve, index, units_value, temp_value
            )
        )  # improve formatting?

    def CurveDataPointQuery(self, curve, index):
        """Returns a standard or user curve data point.

        :param curve: Specifies which curve to query: 1–59.
        :type curve: int
        :param index: Specifies the points index in the curve: 1–200.
        :type index: int

        :return: ['<units value>','<temp value>']
        """
        if 1 > curve > 59:
            raise AssertionError(
                "Curve parameter must be an integer in between 1 - 59."
            )

        if 1 > index > 200:
            raise AssertionError(
                "Curve parameter must be an integer in between 1 - 200."
            )

        return self.query("CRVPT? " + "{0:2d},{1:3d}".format(curve, index))

    def FactoryDefaultsCommand(self):
        """Sets all configuration values to factory defaults and resets the instrument.
        The “99” is included to prevent accidentally setting the unit to defaults.

        Refer to LakeShore 350 Manual for more information.
        """
        raise NotImplementedError

    def DiodeExcitationCurrentParameterCommand(self, input_value, excitation):
        """The 10 μA excitation current is the only calibrated excitation current, and is used in almost
        all applications. Therefore the Model 350 will default the 10 μA current setting any time the input_value
        sensor type is changed in order to prevent an accidental change. If using a current that is not 10 μA,
        the input_value sensor type must first be configured to Diode (INTYPE command). If the sensor type is not
        set to Diode when the DIOCUR command is sent, the command will be ignored.

        :param input_value: Specifies which input to configure: D2–D5 (only for the 3062 card).
        :type input_value: str
        :param excitation: Specifies the Diode excitation current: 0 = 10 μA, 1 = 1 mA.
        :type excitation: int
        """
        if input_value not in ["D2", "D3", "D4", "D5"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in ['D2','D3','D4','D5']."
            )

        if excitation not in [0, 1]:
            raise AssertionError(
                "Excitation parameter must be an integer in [0,1].")

        self.go("DIOCUR " + "{0:2},{1:1d}".format(input_value, excitation))

    def CustomModeDisplayFieldCommand(self, field, input_value, units):
        """This command only applies to the readings displayed in the Custom display mode. All other display
        modes have predefined readings in predefined locations, and will use the Preferred Units parameter to
        determine which units to display for each sensor input. Refer to section 4.3 for details on display setup.

        :param field: Specifies field (display location) to configure: 1–8.
        :type field: int
        :param input_value: Specifies item to display in the field: 0 = None, 1 = Input A, 2 = Input B, 3 = Input C,
            4 = Input D (5 = Input D2, 6 = Input D3, 7 = Input D4, 8 = Input D5 for 3062 option)
        :type input_value: int
        :param units: Valid entries: 1 = kelvin, 2 = Celsius, 3 = sensor units, 4 = minimum data, and 5 = maximum data.
        :type units: int

        Example:
            DISPFLD 2,1,1[term] — displays kelvin reading for input_value A in display field 2 when display mode is set to Custom.
        """
        if 8 < field < 1:
            raise AssertionError(
                "Field parameter must be an integer in between 1 - 8.")

        if 8 < input_value < 0:
            raise AssertionError(
                "Input_Value Parameter must be an integer in between 0 - 8."
            )

        if 5 < units < 1:
            raise AssertionError(
                "Units parameter must be an integer in between 1 - 5.")

        self.go("DISPFLD " +
                "{0:1d},{1:1d},{2:1d}".format(field, input_value, units))

    def CustomModeDisplayFieldQuery(self, field):
        """Refer to CustomModeDisplayFieldCommand for description.

        :param field: Specifies field (display location) to query: 1–8.
        :type field: int

        :return: ['<input_value>','<units>']
        """
        if 8 < field < 1:
            raise AssertionError(
                "Field parameter must be an integer in between 1 - 8.")

        return self.query("ISPFLD? " + "{0:1d}".format(field))

    def DisplaySetupCommand(self, mode, num_fields=2, output_source=1):
        """The <num fields> and <displayed output> commands are ignored in all display modes except for Custom.

        :param mode: Specifies display mode: 0 = input A, 1 = input B, 2 = input C, 3 = input D, 4 = Custom,
            5 = Four Loop, 6 = All inputs, (7 = input D2, 8 = input D3, 9 = input D4, 10 = input D5 for 3062 option)
        :type mode: int
        :param num_fields: When mode is set to Custom, specifies number of fields (display locations) to display:
            0 = 2 large, 1 = 4 large, 2 = 8 small. When mode is set to All inputs, specifies size of readings:
            0 = small with input names, 1 = large without input names
        :type num_fields: int
        :param output_source: Specifies which output, and associated loop information, to display in the bottom
            half of the custom display screen: 1 = Output 1, 2 = Output 2, 3 = Output 3, 4 = Output 4
        :type output_source: int

        Default:
            num_fields = 2, output_source = 1

        Example:
            DISPLAY 4,0,1[term] — set display mode to Custom with 2 large display fields, and set custom output display source to Output 1.
        """
        if 10 < mode < 0:
            raise AssertionError(
                "Mode parameter must be an integer in between 0 - 10.")

        if mode == 4:
            if 2 < num_fields < 0:
                raise AssertionError(
                    "Num_Fields parameter must be an integer in between 0 - 2."
                )
            if 4 < output_source < 1:
                raise AssertionError(
                    "Output_Source parameter must be an integer in between 1 - 4."
                )

        if mode == 6:
            if 1 < num_fields < 0:
                raise AssertionError(
                    "Num_Fields parameter must be an integer in [0,1]."
                )

        self.go(
            "DISPLAY" +
            "{0:1d},{1:1d},{2:1d}".format(mode, num_fields, output_source)
        )

    def DisplaySetupQuery(self):
        """Refer to DisplaySetupCommand for description.

        :return: ['<mode>','<num fields>','<output source>']
        """
        return self.query("DISPLAY?")

    def InputFilterParameterCommand(self, input_value, check_state, points, window):
        """
        :param input_value: Specifies input_value to configure: A - D (D1 - D5 for 3062 option).
        :type input_value: str
        :param check_state: Specifies whether the filter function is 0 = Off or 1 = On.
        :type check_state: int
        :param points: Specifies how many data points the filtering function uses.  Valid range = 2 to 64.
        :type points: int
        :param window: Specifies what percent of full scale reading limits the filtering function.
            Reading changes greater than this percentage reset the filter. Valid range = 1 to 10 (%).
        :type window: int

        Example:
            FILTER B,1,10,2[term] — filter input_value B data through 10 readings with 2% of full scale window.
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        if check_state not in [0, 1]:
            raise AssertionError(
                "Check_State parameter must be an integer in [0,1].")

        if 64 < points < 2:
            raise AssertionError(
                "Points parameter must be an integer in between 2 - 64."
            )

        if 10 < window < 1:
            raise AssertionError(
                "Window parameter must be an integer in between 1 - 10."
            )

        self.go(
            "FILTER "
            + "{0:1},{1:1d},{2:2d},{3:2d}".format(
                input_value, check_state, points, window
            )
        )

    def InputFilterParameterQuery(self, input_value):
        """Refer to Command for description.

        :param input_value: Specifies input_value to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: ['<off/on>','<points>','<window>']
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("FILTER?" + "{0:1}".format(input_value))

    def HeaterOutputQuery(self, output):
        """HTR? is for the Heater Outputs, 1 and 2, only. Use AOUT? for Outputs 3 and 4.

        :param output: Heater output to query: 1 = Output 1, 2 = Output 2
        :type output: int

        :return: <heater value> Heater output in percent (%).
        """
        if output not in [1, 2]:
            raise AssertionError(
                "Output parameter must be an integer in [1,2].")

        answer = self.query("HTR? " + "{0:1d}".format(output))
        return float(answer[0].strip("+"))

    def HeaterSetupCommand(
        self, output, heater_resistance, max_current, max_usercurrent, current_or_power
    ):  # set default value
        """
        :param output: Specifies which heater output to configure: 1 or 2.
        :type output: int
        :param heater_resistance: Heater Resistance Setting (output 1 only): 1 = 25 Ohm, 2 = 50 Ohm.
        :type heater_resistance: int
        :param max_current: Specifies the maximum heater output current (output 1 only):
            0 = User Specified, 1 = 0.707A, 2 = 1A, 3 = 1.141A, 4 = 2A
        :type max_current: int
        :param max_usercurrent: Specifies the maximum heater output current if max current
            is set to User Specified (output 1 only).
        :type max_usercurrent: float
        :param current_or_power: Specifies whether the heater output displays in current or power. Valid entries:
            1 = current, 2 = power.
        :type current_or_power: int

        Example:
            HTRSET 1,1,2,0,1[term] — Heater output 1 will use the 25 Ohm heater setting, has a maximum current
            of 1 A, the maximum user current is set to 0 A because it is not going to be used since a discrete value
            has been chosen, and the heater output will be displayed in units of current.
        """
        if output not in [1, 2]:
            raise AssertionError(
                "Output parameter must be an integer in [1,2].")

        if heater_resistance not in [1, 2]:
            raise AssertionError(
                "Heater_Resistance parameter must be an integer in [1,2]."
            )

        if 4 < max_current < 0:
            raise AssertionError(
                "Max_Current parameter must be an integer in between 0 - 4."
            )

        if max_usercurrent < 0:
            raise AssertionError(
                "Max_Usercurrent parameter must be a float greater than or equal to 0.."
            )

        if current_or_power not in [1, 2]:
            raise AssertionError(
                "Current_Or_Power parameter must be an integer in [1,2]."
            )

        cmd = "HTRSET {0:1d},{1:1d},{2:1d},{3:3.3f},{4:1d}".format(
            output, heater_resistance, max_current, max_usercurrent, current_or_power
        )

        self.go(cmd)  # 3:3.2f correct format?

    def HeaterSetupQuery(self, output):
        """Refer to HeaterSetupCommand for description.

        :param output: Specifies which heater output to query: 1 or 2.
        :type output: int

        :return: ['<htr resistance>','<max current>','<max user current>','<current/power>']
        """
        if output not in [1, 2]:
            raise AssertionError("Output  must be an integer in [1,2].")

        return self.query("HTRSET? " + "{0:1d}".format(output))

    def HeaterStatusQuery(self, output):
        """Error condition is cleared upon querying the heater status, except for the heater compliance
        error for output 2 which does not latch querying the heater status, will also clear the
        front panel error message for heater open or heater short error messages.

        :param output: Specifies which heater output to query: 1 or 2.
        :type output: int

        :return: <error code> Heater error code: 0 = no error, 1 = heater open load, 2 = heater short for
            output 1, or heater compliance for output 2.

        """
        if output not in [1, 2]:
            raise AssertionError(
                "Output parameter must be an integer in [1,2].")

        return self.query("HTRST? " + "{0:1d}".format(output))

    def IEEE488InterfaceParameterCommand(self, address):
        """
        :param address: Specifies the IEEE address: 1–30. (Address 0 and 31 are reserved.)
        :type address: int

        Example:
            IEEE 4[term] — after receipt of the current terminator, the instrument responds to address 4.
        """
        if 30 < address < 1:
            raise AssertionError(
                "Address parameter must be an integer in between 1 - 30."
            )

        self.go("IEEE " + "{0:2d}".format(address))

    def IEEE488InterfaceQuery(self):
        """
        :return: <address>
        """
        return self.query("IEEE?")

    def InputCurveNumberCommand(self, input_value, curve_number):
        """Specifies the curve an input uses for temperature conversion.

        :param input_value: Specifies which input to configure: A - D (D1 - D5 for 3062 option).
        :type input_value: str
        :param curve_number: Specifies which curve the input uses. If specified curve type does notmatch the
            configured input type, the curve number defaults to 0. Valid entries:
            0 = none, 1–20 = standard curves, 21–59 = user curves
        :type curve_number: int

        Example:
            INCRV A,23[term] — input_value A uses User Curve 23 for temperature conversion.
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        if 59 < curve_number < 0:
            raise AssertionError(
                "Check_State parameter must be an integer in between 0 - 59."
            )

        self.go("INCRV " + "{0:1},{1:2d}".format(input_value, curve_number))

    def InputCurveNumberQuery(self, input_value):
        """
        :param input_value: Specifies which input_value to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: <curve number>
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("INRCV? " + "{0:1}".format(input_value))

    def SensorInputNameCommand(self, input_value, name):
        """Be sure to use quotes when sending strings, otherwise characters such as spaces, and other
        non alpha-numeric characters, will be interpreted as a delimiter and the full string will not be accepted.
        It is not recommended to use commas or semi-colons in sensor input_value names as these characters are used
        as delimiters for query responses.

        :param input_value: Specifies input_value to configure: A - D (D1 - D5 for 3062 option).
        :type input_value: str
        :param name: Specifies the name to associate with the sensor input_value.
        :type name: str

        Example:
            INNAME A, “Sample Space”[term] — the string “Sample Space” will appear on the front panel
            display when possible to identify the sensor information being displayed.
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "LakeShore: Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        if not isinstance(name, str) or len(name) > 15:
            raise AssertionError(
                "LakeShore: Name parameter must be a string with a maximum of 15 characters."
            )

        self.go("INNAME " + "{0:1},{1:15}".format(input_value, name))

    def SensorInputNameQuery(self, input_value):
        """Refer to SensorInputNameCommand for description.

        :param input_value: Specifies input_value to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: <name>
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("INNAME? " + "{0:1}".format(input_value))

    def InterfaceSelectCommand(self, interface):
        """The Ethernet interface will attempt to configure itself based on the current configu-
        ration parameters, which can be set using the NET command. Configuring the Ether-
        net interface parameters prior to enabling the interface is recommended.

        :param interface: Specifies the remote interface to enable:
            0 = USB
            1 = Ethernet
            2 = IEEE-488.
        :type interface: int
        """
        if interface not in [0, 1, 2]:
            raise AssertionError(
                "Interface parameter must be an integer in [0,1,2].")

        self.go("INTSEL " + "{0:1}".format(interface))

    def InterfaceSelectQuery(self):
        """Refer to InterfaceSelectCommand for description.

        :return: <interface>
        """
        return self.query("INTSEL?")

    def InputTypeParameterCommand(
        self,
        input_value,
        sensor_type,
        autorange,
        range_value,
        compensation=0,
        units=0,
        sensor_excitation=0,
    ):
        """The <autorange> parameter does not apply to diode, thermocouple, or capacitance sensor types,
        the <range_value> parameter does not apply to the thermocouple sensor type, the <compensation> parameter
        does not apply to the diode sensor type, and the <sensor excitation> parameter only applies to
        the NTC RTD sensor type. When configuring sensor inputs, all parameters must be included, but
        non-applicable parameters are ignored. A setting of 0 for each is recommended in this case.

        :param input_value: Specifies input to configure: A - D (D1 - D5 for 3062 option)
        :type input_value: str
        :param sensor_type: Specifies input sensor type:
            0 = Disabled
            1 = Diode (3062 option only)
            2 = Platinum RTD
            3 = NTC RTD
            4 = Thermocouple (3060 option only)
            5 = Capacitance (3061 option only)
        :type sensor_type: int
        :param autorange: Specifies autoranging: 0 = off and 1 = on.
        :type autorange: int
        :param range_value: Specifies input range when autorange is off:
            Sensor Type     Sensor excitation       Range
            Diode           na                      0 = 2.5 V
                            na                      1 = 10 V
            PTC RTD         10 mV                   0 = 10 Ohm
                            10 mV                   1 = 30 Ohm
                            10 mV                   2 = 100 Ohm
                            10 mV                   3 = 300 Ohm
                            10 mV                   4 = 1 kOhm
                            10 mV                   5 = 3 kOhm
                            10 mV                   6 = 10 kOhm
            NTC RTD         10 mV or 1 mV           0 = 10 Ohm
                            10 mV or 1 mV           1 = 30 Ohm
                            10 mV or 1 mV           2 = 100 Ohm
                            10 mV or 1 mV           3 = 300 Ohm
                            10 mV or 1 mV           4 = 1 kOhm
                            10 mV or 1 mV           5 = 3 kOhm
                            10 mV or 1 mV           6 = 10 kOhm
                            10 mV or 1 mV           7 = 30 kOhm
                            10 mV or 1 mV           8 = 100 kOhm
                            10 mV                   9 = 300 kOhm
            Thermocouple    na                      0 = 50 mV
            Capacitance     na                      0 = 15nF
        :type range_value: int
        :param compensation: Specifies input compensation where 0 = off and 1 = on. Reversal for thermal EMF
            compensation if input is resistive, room compensation if input is thermocouple. Also used to set
            temperature coefficient for capacitance sensors where 0 = negative and 1 = positive.
            Always 0 if input is a diode. (3062 option only)
        :type compensation: int
        :param units: Specifies the preferred units parameter for sensor readings and for the control setpoint: 1 = Kelvin, 2 = Celsius, 3 = Sensor
        :type units: int
        :param sensor_excitation: Specifies the sensor excitation voltage level to maintain for the NTC RTD sensor type.
            0 = 1 mV and 1 = 10 mV
        :type sensor_excitation: int

        Default:
            compensation = 1, units = 0, sensor_excitation = 0

        Example:
            INTYPE A,3,1,0,1,1,1[term]—sets input_value A sensor type to NTC RTD, autorange on, thermal compensation on, preferred units to kelvin, and sensor excitation to 1 mV.
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        if 5 > sensor_type > 0:
            raise AssertionError(
                "Sensor_Type parameter must be an integer in [0,1,2,3,4,5]."
            )

        if sensor_type == 1:
            if range_value not in [0, 1]:
                raise AssertionError(
                    "For Diode (Sensor_Type == 1) the Range_Value parameter must be an integer in [0,1]."
                )

        if sensor_type == 2:
            if sensor_excitation != 1:
                raise AssertionError(
                    "For PTC RTD (Sensor_Type == 2) the Sensor_Excitation parameter must be an integer with the value 0."
                )
            if 6 > range_value > 0:
                raise AssertionError(
                    "For PTC RTD (Sensor_Type == 2) the Range_Value parameter must be an integer in between 0 - 6."
                )

        if sensor_type == 3:
            if sensor_excitation not in [0, 1]:
                raise AssertionError(
                    "For NTC RTD (Sensor_Type == 3) Sensor_Excitation parameter must be an integer in [0,1]."
                )
            if sensor_excitation == 0 and 0 > range_value > 8:
                raise AssertionError(
                    "For NTC RTD (Sensor_Type == 3) and 1 mV (Sensor_Excitation == 0) the Range_Value parameter must be an integer in between 0 - 8."
                )
            if sensor_excitation == 1 and 0 > range_value > 9:
                raise AssertionError(
                    "For NTC RTD (Sensor_Type == 3) and 10 mV (Sensor_Excitation == 1) the Range_Value parameter must be an integer in between 0 - 9."
                )

        if sensor_type == 4:
            if range_value != 0:
                raise AssertionError(
                    "For Thermocouple (Sensor_Type == 4) the Range_Value parameter must be an integer with value 0."
                )

        if sensor_type == 5:
            if range_value not in [0, 1]:
                raise AssertionError(
                    "For Capacitance (Sensor_Type == 5) the Range_Value parameter must be an integer in [0,1]."
                )

        if autorange not in [0, 1]:
            raise AssertionError(
                "Autorange parameter must be an integer in [0,1].")

        if compensation not in [0, 1]:
            raise AssertionError(
                "Compensation parameter must be an integer in [0,1].")

        if units not in [1, 2, 3]:
            raise AssertionError(
                "Units parameter must be an integer in [1,2,3].")

        self.go(
            "INTYPE "
            + "{0:1},{1:1d},{2:1d},{3:1d},{4:1d},{5:1d},{6:1d}".format(
                input_value,
                sensor_type,
                autorange,
                range_value,
                compensation,
                units,
                sensor_excitation,
            )
        )

    def InputTypeParameterQuery(self, input_value):
        """If autorange is on, the returned range parameter is the currently auto-selected range. Refer to InputTypeParameterCommand for description.

        :param input_value: Specifies input to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: ['<sensor type>','<autorange>','<range>','<compensation>','<units>','<sensor excitation>']
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A','B','C','D']."
            )

        return self.query("INTYPE? " + "{0:1}".format(input_value))

    def KelvinReadingQuery(self, input_value):
        """Returns the Kelvin reading for a single input or all input_values. <input_value> specifies which input(s) to query. 0 = all input.
            Also see the RDGST? command.

        :param input_value: Specifies input to query: A-D (D1–D5 for 3062 option)
        :type input_value: int or str

        :return: <temp value>
            Or if all input are queried:
            ['<A value>','<B value>','<C value>','<D value>']
        """
        if input_value not in [0, "A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be the integer 0 or a string in  ['A', 'B', 'C', 'D']."
            )

        # necessary to implement if-else for A,B,C,D or 0?

        answer = self.query("KRDG? " + "{0:1d}".format(input_value))

        try:
            answer = [float(x) for x in answer]
        except TypeError as e:
            raise AssertionError("{}".format(e))
        return answer

    def FrontPanelLEDSCommand(self, check_state):
        """If set to 0, front panel LEDs will not be functional. Function can be used when display brightness is a problem.

        :param check_state: <off/on> 0 = LEDs Off, 1 = LEDs On
        :type check_state: int

        Example:
            LED 0[term] — turns all front panel LED functionality off.
        """
        if check_state not in [0, 1]:
            raise AssertionError(
                "Check_State parameter must be an integer in [0,1].")

        self.go("LEDS " + "{0:1d}".format(check_state))  # LEDS or LED ?

    def FrontPanelLEDSQuery(self):
        """Refer to FrontPanelLEDSCommand for description.

        :return: <off/on>
        """
        return self.query("LEDS?")

    def FrontPanelKeyboardLockCommand(self, state, code):
        """Locks out all front panel entries except pressing the All Off key to immediately turn off all heater outputs. Refer to section 4.7.

        :param state: 0 = Unlocked, 1 = Locked
        :type state: int
        :param code: Specifies lock-out code. Valid entries are 000 – 999.
        :type code: int

        Example:
            LOCK 1,123[term] — enables keypad lock and sets the code to 123.
        """
        if state not in [0, 1]:
            raise AssertionError(
                "State parameter must be an integer in [0,1].")

        if 999 < code < 000:
            raise AssertionError(
                "Code parameter must be an integer in between 0 - 999."
            )

        self.go("LOCK " + "{0:1d},{1:03d}".format(state, code))

    def FrontPanelKeyboardLockQuery(self):
        """Refer to FrontPanelKeyboardLockCommand for description.

        :return: ['<state>','<code>']
        """
        return self.query("LOCK?")

    def MinimumMaximumDataQuery(self, input_value):
        """Returns the minimum and maximum input data. Also see the RDGST? command.

        :param input_value: Specifies which input to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: ['<min value>','<max value>']
        """
        if not isinstance(input_value, str) or input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("MDAT? " + "{0:1}".format(input_value))

    def MinimumMaximumFunctionResetCommand(self):
        """Resets the minimum and maximum data for all inputs.
        """
        self.go("MNMXRST")

    def RemoteInterfaceModeCommand(self, mode):
        """
        :param mode: 0 = local, 1 = remote, 2 = remote with local lockout.
        :type mode: int

        Example:
            MODE 2[term] — places the Model 350 into remote mode with local lockout.
        """
        if not isinstance(mode, int) or mode not in [0, 1, 2]:
            raise AssertionError(
                "Mode parameter must be an integer in [0,1,2].")

        self.go("MODE " + "{0:1d}".format(mode))

    def RemoteInterfaceModeQuery(self):
        """Refer to RemoteInterfaceModeCommand for description.

        :return: <mode>[term]
        """
        return self.query("MODE?")

    def ManualOutputCommand(self, output, value):
        """Manual output only applies to outputs in Closed Loop PID, Zone, or Open Loop modes.

        :param output: Specifies output to configure: 1–4.
        :type output: int
        :param value: Specifies value for manual output in percent.
        :type value: float

        Example:
            MOUT 1,22.45[term] — Output 1 manual output is 22.45%.
        """
        if output not in [1, 2, 3, 4]:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if 0.0 > value > 100.0:
            raise AssertionError(
                "Value parameter must be a float in between 0 - 100.")

        self.go("MOUT " + "{0:1},{1:3.2f}".format(output, value))

    def ManualOutputQuery(self, input_value):
        """Refer to ManualOutputCommand for description.

        :param input_value: Specifies which output to query: 1 - 4.
        :type input_value: int

        :return: <value>
        """
        if input_value not in [1, 2, 3, 4]:
            raise AssertionError(
                "Input_Value Parameter must be an integer in [1,2,3,4]."
            )

        return self.query("MOUT? " + "{0:1d}".format(input_value))

    def NetworkSettingsCommand(
        self,
        dhcp,
        auto_ip,
        ip,
        sub_mask,
        gateway,
        pri_dns,
        sec_dns,
        pref_host,
        pref_domain,
        description,
    ):
        """Network Settings Command
        :param dhcp: 0 = DHCP off, 1 = DHCP on.
        :type dhcp: int
        :param auto_ip: 0 = Dynamically configured link-local addressing (Auto IP) off, 1 = On
        :type auto_ip: int
        :param ip: IP address for static configuration.
        :type ip: ## which type?
        :param sub_mask: Subnet mask for static configuration.
        :type sub_mask: ## which type?
        :param gateway: Gateway address for static configuration.
        :type gateway: ## which type?
        :param pri_dns: Primary DNS address for static configuration.
        :type pri_dns:## which type?
        :param sec_dns: Secondary DNS address for static configuration.
        :type sec_dns: ## which type?
        :param pref_host: Preferred Hostname (15 character maximum)
        :type pref_host: str
        :param pref_domain: Preferred Domain name (64 character maximum)
        :type pref_domain: str
        :param description: Instrument description (32 character maximum)
        :type description: str

        input_value:
            NET <DHCP>,<AUTO IP>,<IP>,<Sub Mask>,<Gateway>,<Pri DNS>,<Sec DNS>,<Pref Host>,<Pref Domain>,<Description>[term]
        Format:
            n,n,dd,dd,dd,dd,dd,s[15],s[64],s[32],
            <DHCP>
            <AUTO IP>
            <IP>                IP address for static configuration.
            <Sub Mask>          Subnet mask for static configuration.
            <Gateway>           Gateway address for static configuration.
            <Pri DNS>           Primary DNS address for static configuration.
            <Sec DNS>           Secondary DNS address for static configuration.
            <Pref Host>         Preferred Hostname (15 character maximum)
            <Pref Domain>       Preferred Domain name (64 character maximum)
            <Description>       Instrument description (32 character maximum)
        """
        if not isinstance(dhcp, int) or dhcp not in [0, 1]:
            raise AssertionError(
                "LakeShore: DHCP parameter must be an integer in [0,1]."
            )

        if not isinstance(auto_ip, int) or auto_ip not in [0, 1]:
            raise AssertionError(
                "LakeShore: Auto_IP parameter must be an integer in [0,1]."
            )

        # ADD assertion errors for ip variables

        if not isinstance(pref_host, str) or len(pref_host) > 15:
            raise AssertionError(
                "LakeShore: Pref_Host parameter must be a string with a maximum of 15 characters."
            )

        if not isinstance(pref_domain, str) or len(pref_domain) > 64:
            raise AssertionError(
                "LakeShore: Pref_Domain parameter must be a string with a maximum of 64 characters."
            )

        if not isinstance(description, str) or len(description) > 32:
            raise AssertionError(
                "LakeShore: Description parameter must be a string with a maximum of 32 characters."
            )

        self.go(
            "NET "
            + "{0:1},{1:1},{2},{3},{4},{5},{6},{7:15},{8:64},{9:32}".format(
                dhcp,
                auto_ip,
                ip,
                sub_mask,
                gateway,
                pri_dns,
                sec_dns,
                pref_host,
                pref_domain,
                description,
            )
        )

    def NetworkSettingsQuery(self):
        """Refer to NetworkSettingsCommand for description.

        :return: ['<DHCP>','<AUTO IP>','<IP>','<Sub Mask>','<Gateway>','<Pri DNS>','<Sec DNS>','<Pref Host>','<Pref Domain>','<Description>']

        """
        return self.query("NET?")

    def NetworkConfigurationQuery(self):
        """This query returns the configured Ethernet parameters. If the Ethernet interface is not configured then IP,
        subnet mask, gateway, primary DNS and secondary DNS parameters will be 0.0.0.0.

        :return: ['<lan status>','<IP>','<sub mask>','<gateway>','<pri DNS>','<sec DNS>','<mac addr>','<actual hostname>','<actual domain>']
            <lan status>           Current status of Ethernet connection:
                                        0 = Connected Using Static IP,
                                        1 = Connected Using DHCP,
                                        2 = Connected Using  Auto IP,
                                        3 = Address Not Acquired Error,
                                        4 = Duplicate Initial  IP Address Error,
                                        5 = Duplicate Ongoing IP Address Error, 
                                        6 = Cable Unplugged,
                                        7 = Module Error,
                                        8 = Acquiring Address,
                                        9 = Ethernet Disabled.
                                        Refer to section 6.4.2.1 for details on lan status.
            <IP>                    Configured IP address
            <sub mask>              Configured subnet mask
            <gateway>               Configured gateway address
            <pri DNS>               Configured primary DNS address
            <sec DNS>               Configured secondary DNS address
            <actual hostname>       Assigned hostname
            <actual domain>         Assigned domain
            <mac addr>              Module MAC address.
        """
        return self.query("NETID?")

    def OperationalStatusQuery(self):
        """The integer returned represents the sum of the bit weighting of the operational status bits.
        Refer to section 6.2.5.2 for a list of operational status bits.

        :return: <bit weighting>
        """
        return self.query("OPST?")

    def OperationalStatusEnableCommand(self, bit_weighting):
        """Each bit has a bit weighting and represents the enable/disable mask of the corresponding operational
        status bit in the Operational Status Register. This determines which status bits can set the corresponding
        summary bit in the Status Byte Register. To enable a status bit, send the command OPSTE with the sum of
        the bit weighting for each desired bit. Refer to section 6.2.5.2 for a list of operational status bits.
            Bit     Bit Weighting       Event Name
            0       1                   COM
            1       2                   CAL
            2       4                   ATUNE
            3       8                   NRDG
            4       16                  RAMP1
            5       32                  RAMP2
            6       64                  OVLD
            7       128                 ALARM
            Total:  255

        :param bit_weighting: <bit weighting>
        :type bit_weighting: int
        """
        weighting_list = [1, 2, 4, 8, 16, 32, 64, 128]
        sum_list = sum(
            [
                map(list, combinations(weighting_list, i))
                for i in range(len(weighting_list) + 1)
            ],
            [],
        )
        map_list = map(sum, sum_list)  # creates list of all possible sums

        if bit_weighting not in map_list:
            raise AssertionError(
                "Bit_Weighting parameter must be a sum of elements of [0,1,2,4,8,16,32,64,128]."
            )

        self.go("OPSTE " + "{0:3d}".format(bit_weighting))

    def OperationalStatusEnableQuery(self):
        """Refer to OperationalStatusEnableCommand for description.

        :return: <bit weighting>
        """
        return self.query("OPSTE?")

    def OperationalStatusRegisterQuery(self):
        """The integers returned represent the sum of the bit weighting of the operational status bits.
        These status bits are latched when the condition is detected. This register is cleared when it is read.
        Refer to section 6.2.5.2 for a list of operational status bits. Or refer to OperationalStatusEnableCommand.

        :return: <bit weighting>
        """
        return self.query("OPSTR?")

    def OutputModeCommand(self, output, mode, input_value, powerup_enable):
        """Modes 4 and 5 are only valid for Analog Outputs (3 and 4).

        :param output: Specifies which output to configure: 1 – 4.
        :type output: int
        :param mode: Specifies the control mode. Valid entries:     0 = Off,
                                                                    1 = Closed Loop PID,
                                                                    2 = Zone,
                                                                    3 = Open Loop,
                                                                    4 = Monitor out, 
                                                                    5 = Warmup Supply
        :type mode:int
        :param input_value: Specifies which input to use for control:   0 = None,
                                                                        1 = A,
                                                                        2 = B,
                                                                        3 = C,
                                                                        4 = D
                                                                        (5 = input_value D2,
                                                                        6 = input_value D3,
                                                                        7 = input_value D4,
                                                                        8 = input_value D5 for 3062 option)
        :type input_value: int
        :param powerup_enable: Specifies whether the output remains on or shuts off after power cycle.
                                Valid entries:  0 = powerup enable off,
                                                1 = powerup enable on.
        :type powerup_enable: int

        Example:
            OUTMODE 1,2,1,0[term] — Output 1 configured for Zone control mode, using input A for the control input sensor, and will turn the output off when power is cycled.
        """

        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if 0 > mode > 5:
            raise AssertionError(
                "Mode parameter must be an integer in [0,1,2,3,4,5].")

        if 0 > input_value > 8:
            raise AssertionError(
                "Input_Value Parameter must be an integer in [0,1,2,3,4,5,6,7,8]."
            )

        if powerup_enable not in [0, 1]:
            raise AssertionError(
                "Powerup_Enable parameter must be an integer in [0,1]."
            )

        self.go(
            "OUTMODE "
            + "{0:1d},{1:1d},{2:1d},{3:1d}".format(
                output, mode, input_value, powerup_enable
            )
        )

    def OutputModeQuery(self, output):
        """Refer to OutputModeCommand for description.

        :param output: Specifies which output to query: 1 – 4.
        :type output: int

        :return: ['<mode>','<input_value>','<powerup enable>']
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        answer = self.query("OUTMODE? " + "{0:1d}".format(output))
        return [int(x) for x in answer]

    def ControlLoopPIDValuesCommand(self, output, p_value, i_value, d_value):
        """Control settings, (P, I, D, and Setpoint) are assigned to outputs, which results in the settings being
        applied to any loop formed by the output and its control input_value.

        :param output: Specifies which output's control loop to configure: 1 - 4.
        :type output: int
        :param p_value: The value for output Proportional (gain): 0.1 to 1000.
        :type p_value: float
        :param i_value: The value for output Integral (reset): 0.1 to 1000.
        :type i_value: float
        :param d_value: The value for output Derivative (rate): 0 to 200
        :type d_value: int

        Example:
            PID 1,10,50,0[term] — Output 1 P is 10, I is 50, and D is 0%.
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if 0.1 > p_value > 1000.0:
            raise AssertionError(
                "P_Value parameter must be a float in between 0.1 - 1000."
            )

        if 0.1 > i_value > 1000.0:
            raise AssertionError(
                "I_Value parameter must be a float in between 0.1 - 1000."
            )

        if 0 > d_value > 200:
            raise AssertionError(
                "D_Value parameter must be an integer in between 0 - 200."
            )

        self.go(
            "PID "
            + "{0:1d},{1:4.1f},{2:4.1f},{3:3d}".format(
                output, p_value, i_value, d_value
            )
        )

    def ControlLoopPIDValuesQuery(self, output):
        """Refer to ControlLoopPIDValuesCommand for description.

        :param output: Specifies which output’s control loop to query: 1 – 4.>
        :type output: int

        :return: ['<P value>','<I value>','<D value>']
        """
        if 1 > output > 4:  # is this faster than not in?
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")
        answer = self.query("PID? " + "{0:1d}".format(output))
        return [float(x) for x in answer]

    def ControlSetpointRampParameterCommand(self, output, check_state, rate_value):
        """Control loop settings are assigned to outputs, which results in the settings being applied to
        the control loop formed by the output and its control input.

        :param output: Specifies which output’s control loop to configure: 1 – 4.
        :type output: int
        :param check_state: Specifies whether ramping is 0 = Off or 1 = On.
        :type check_state: int
        :param rate_value: Specifies setpoint ramp rate in kelvin per minute from 0.001 to 100 K/min.
            The rate is always positive, but will respond to ramps up or down.
            A rate of 0 is interpreted as infinite, and will therefore respond as if
            setpoint ramping were off.
        :type rate_value: float

        Example:
            RAMP 1,1,10.5[term] — when Output 1 setpoint is changed, ramp the current setpoint to the target setpoint at 10.5 K/minute.
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if 0 > check_state > 1:
            raise AssertionError(
                "Check_State parameter must be an integer in [0,1].")

        if 0.001 > rate_value > 100.0:
            raise AssertionError(
                "I_Value parameter must be a float in between 0.001 - 100."
            )

        self.go(
            "RAMP " +
            "{0:1d},{1:1d},{2:3.2f}".format(output, check_state, rate_value)
        )  # :3.2f properly fromatted?

    def ControlSetpointRampParameterQuery(self, output):
        """Refer to ControlSetpointRampParameterCommand for description.

        :param output: Specifies which output’s control loop to query: 1 – 4.
        :type output: int

        :return: ['<off/on>','<rate value>']
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        answer = self.query("RAMP? " + "{0:1d}".format(output))
        # print(answer, type(answer), type(answer[0]))
        return [float(x) for x in answer]

    def ControlSetpointRampStatusQuery(self, output):
        """Refer to ControlSetpointRampParameterCommand for description.

        :param output: Specifies which output’s control loop to query: 1 – 4.
        :type output: int

        :return: <ramp status> 0 = Not ramping, 1 = Setpoint is ramping.
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        return self.query("RAMPST? " + "{0:1d}".format(output))

    def HeaterRangeCommand(self, output, range_value):
        """The range setting has no effect if an output is in the Off mode, and does not apply to
        an output in Monitor Out mode. An output in Monitor Out mode is always on.

        :param output: Specifies which output to configure: 1–4.
        :type output: int
        :param range: For outputs 1 and 2:  0 = Off,
                                            1 = Range 1,
                                            2 = Range 2,
                                            3 = Range 3,
                                            4 = Range 4,
                                            5 = Range 5
                      For outputs 3 and 4:  0 = Off,
                                            1 = On
        :type range: int
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if 0 > range_value > 5 and 0 < output < 3:
            raise AssertionError(
                "For Output 1 or 2 the Range_Value parameter must be an integer in between 0 - 5."
            )

        if 0 > range_value > 1 and 2 < output < 5:
            raise AssertionError(
                "For Output 3 or 4 Range_Value parameter must be an integer in [0,1]."
            )

        self.go("RANGE " + "{0:1d},{1:1d}".format(output, range_value))

    def HeaterRangeQuery(self, output):
        """Refer to HeaterRangeCommand for Description.

        :param output: Specifies which output to query: 1–4.
        :type output: int

        :return: <range>
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")
        answer = self.query("RANGE? " + "{0:1d}".format(output))
        return int(answer[0])

    def InputReadingStatusQuery(self, input_value):
        """The integer returned represents the sum of the bit weighting of the input_value status flag bits.
            A “000” response indicates a valid reading is present.
                Bit     Bit Weighting       Status Indicator
                0           1                   invalid reading
                4           16                  temp underrange
                5           32                  temp overrange
                6           64                  sensor units zero
                7           128                 sensor units overrange

        :param input_value: Specifies which input_value to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :return: <bit weighting>
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in ['A','B','C','D']."
            )

        return self.query("RDGST? " + "{0:1}".format(input_value))

    def RelayControlParameterCommand(self, relay_number, mode, input_alarm, alarm_type):
        """
        :param relay_number: Specifies which relay to configure: 1 or 2.
        :type relay_number: int
        :param mode: Specifies relay mode. 0 = Off, 1 = On, 2 = Alarms.
        :type mode: int
        :param input_alarm: Specifies which input_value alarm activates the relay when the
            relay is in alarm mode: A - D (D1 - D5 for 3062 option).
        :type input_alarm: str
        :param alarm_type: Specifies the input_value alarm type that activates the relay when
            the relay is in alarm mode. 0 = Low alarm, 1 = High Alarm,
            2 = Both Alarms.
        :type alarm_type: int

        Example:
            RELAY 1,2,B,0[term] – relay 1 activates when input_value B low alarm activates.
        """
        if 1 > relay_number > 2:
            raise AssertionError(
                "Relay_Number parameter must be an integer in [1,2].")

        if 0 > mode > 2:
            raise AssertionError(
                "Mode parameter must be an integer in [0,1,2].")

        if input_alarm not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Alarm parameter must be a string in  ['A','B','C','D']."
            )

        if 0 > alarm_type > 1:
            raise AssertionError(
                "Alarm_Type parameter must be an integer in [0,1].")

        self.go(
            "RELAY "
            + "{0:1d},{1:1d},{2:1},{3:1d}".format(
                relay_number, mode, input_alarm, alarm_type
            )
        )

    def RelayControlParameterQuery(self, relay_number):
        """Refer to RelayControlParameterCommand for description.

        :param relay_number: Specifies which relay to query: 1 or 2.
        :type relay_number: int

        :return: ['<mode>','<input_value alarm>','<alarm type>']
        """
        if 1 > relay_number > 2:
            raise AssertionError(
                "Relay_Number parameter must be an integer in [1,2].")

        return self.query("RELAY? " + "{0:1}".format(relay_number))

    def RelayStatusQuery(self, relay_number):
        """
        :param relay_number: Specifies which relay to query: 1 or 2.
        :type relay_number: int

        :return: <status> 0 = Off, 1 = On.
        """
        if 1 > relay_number > 2:
            raise AssertionError(
                "Relay_Number parameter must be an integer in [1,2].")

        return self.query("RELAYST? " + "{0:1}".format(relay_number))

    def GeneratSofCalCurveCommand(
        self, std, dest, sn, t1_value, u1_value, t2_value, u2_value, t3_value, u3_value
    ):
        """Generates a SoftCalTM curve. Refer to Paragraph 5.3.

        :param std: Specifies the standard curve from which to generate a SoftCalTM curve. Valid entries: 1, 6, 7.
        :type std: int
        :param dest: Specifies the user curve to store the SoftCalTM curve. Valid entries: 21–59.
        :type dest: int
        :param sn: Specifies the curve serial number. Limited to 10 characters.
        :type sn: str
        :param t1_value: Specifies first temperature point in kelvin.
        :type t1_value: float
        :param u1_value: Specifies first sensors units point.
        :type u1_value: float
        :param t2_value: Specifies second temperature point in kelvin.
        :type t2_value: float
        :param u2_value: Specifies second sensor units point.
        :type u2_value: float
        :param t3_value: Specifies third temperature point in kelvin.
        :type t3_value: float
        :param u3_value: Specifies third sensor units point.
        :type u3_value: float

        Example:
            SCAL 1,21,1234567890,4.2,1.6260,77.32,1.0205,300.0,0.5189[term] – generates a
            three-point SoftCalTM curve from standard curve 1 and saves it in user curve 21.
        """
        if std not in [1, 6, 7]:
            raise AssertionError(
                "Std parameter must be an integer in [1,6,7].")

        if 21 > dest > 59:
            raise AssertionError(
                "Dest parameter must be an integer in [0,1,2].")

        if not isinstance(sn, str) or len(sn) > 10:
            raise AssertionError(
                "Sn parameter must be a string with a maximum of 10 characters."
            )

        if t1_value < 0.0:
            raise AssertionError(
                "T1_Value parameter must be a float greater than 0.")

        if not isinstance(u1_value, float):
            raise AssertionError(
                "LakeShore:GeneratSofCalCurveCommand U1_Value parameter must be a float"
            )

        if t2_value < 0.0:
            raise AssertionError(
                "T1_Value parameter must be a float greater than 0.")

        if not isinstance(u2_value, float):
            raise AssertionError(
                "LakeShore:GeneratSofCalCurveCommand U2_Value parameter must be a float"
            )

        if t3_value < 0.0:
            raise AssertionError(
                "T1_Value parameter must be a float greater than 0.")

        if not isinstance(u3_value, float):
            raise AssertionError(
                "LakeShore:GeneratSofCalCurveCommand U3_Value parameter must be a float"
            )

        self.go(
            "SCAL "
            + "{0:1d},{1:2d},{2:10},{3:4.2f},{4:7},{5:4.2f},{6:7},{7:4.2f},{8:7}".format(
                std,
                dest,
                sn,
                t1_value,
                u1_value,
                t2_value,
                u2_value,
                t3_value,
                u3_value,
            )
        )

    def ControlSetpointCommand(self, output, value):
        """For outputs 3 and 4, setpoint is only valid in Warmup mode. Control settings, that is,
        P, I, D, and Setpoint, are assigned to outputs, which results in the settings being
        applied to the control loop formed by the output and its control input.

        :param output: Specifies which output’s control loop to configure: 1–4.
        :type output: int
        :param value: The value for the setpoint (in the preferred units of the control loop sensor).
        :type value: float

        Example:
            SETP 1,122.5[term] — Output 1 setpoint is now 122.5 (based on its units).
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if not isinstance(value, (int, float)):
            raise AssertionError(
                "Value Parameter must be an integer or float.")

        # string formatting
        self.go("SETP " + "{0:1},{1:4.2f}".format(output, value))

    def ControlSetpointQuery(self, output):
        """Refer to ControlSetpointCommand for description

        :param output: Specifies which output to query: 1–4.
        :type output: int

        :return: <value>
        """
        if 1 > output > 4:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        answer = self.query("SETP? " + "{0:1d}".format(output))

        return float(answer[0])

    def SensorUnitsInputReadingQuery(self, input_value):
        """Returns the sensor input reading for a single input or all input. <input_value> specifies
        which input(s) to query. 0 = all input_values.
        Also see the RDGST? command.

        :param input_value: Specifies input to query: A - D (D1–D5 for 3062 option)
        :type input_value: str

        :return: <temp value>
            Or if all input are queried:
            <A value>,<B value>,<C value>,<D value>
        """
        if input_value not in ["A", "B", "C", "D", 0]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

<< << << < HEAD:
    CryostatGUI / LakeShore / LakeShore350.py
    answer = self.query('SRDG? ' + '{0:1}'.format(input_value))
    try:
        return [float(x) for x in answer]
    except TypeError:
        return float(answer)
== == == =
    answer = self.query("SRDG? " + "{0:1}".format(input_value))
    return [float(x) for x in answer]
>>>>>> > master:
    LakeShore / LakeShore350.py

    def ThermocoupleJunctionTemperatureQuery(self):
        """Temperature is in kelvin. This query returns the temperature of the ceramic thermo-
        couple block used in the room temperature compensation calculation

        :return: <junction temperature>
        """
        return self.query("TEMP?")

    def TemperatureLimitCommand(self, input_value, limit):
        """A temperature limit setting of 0 K turns the temperature limit feature off.

        :param input_value:  Specifies which input to configure: A - D (D1 - D5 for 3062 option).
        :type input_value: str
        :param limit: The temperature limit in kelvin for which to shut down all
            control outputs when exceeded. A temperature limit of zero
            turns the temperature limit feature off for the given
            sensor input.
        :type limit: float

        Example:
            TLIMIT B,450[term] — if the temperature of the sensor on input B exceeds 450 K, all
            control outputs will be turned off.
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        if limit < 0.0:
            raise AssertionError(
                "Limit parameter must be a float greater than 0.")

        # string formatting
        self.go("TLIMIT " + "{0:1},{1:3.2f}".format(input_value, limit))

    def TemperatureLimitQuery(self, input_value):
        """Refer to TemperatureLimitCommand for description.

        :param input_value: Specifies which input_value to query: A - D (D1 - D5 for 3062 option).
        :type input_value: str

        :retun: <limit>
        """
        if input_value not in ["A", "B", "C", "D"]:
            raise AssertionError(
                "Input_Value Parameter must be a string in  ['A', 'B', 'C', 'D']."
            )

        return self.query("LIMIT? " + "{0:1}".format(input_value))

    def ControlTuningStatusQuery(self):
        """If initial conditions are not met when starting the autotune procedure, causing the
        autotuning process to never actually begin, then the error status will be set to 1 and
        the stage status will be stage 00.

        :return: ['<tuning status>','<output>','<error status>','<stage status>']
            <tuning status>         0 = no active tuning,
                                    1 = active tuning.
            <output>                Heater output of the control loop being tuned (if tuning): 
                                    1 = output 1,
                                    2 = output 2,
                                    3 = output 3,
                                    4 = output 4
            <error status>          0 = no tuning error,
                                    1 = tuning error
            <stage status>          Specifies the current stage in the Autotune process. 
                                    If tuning error occurred, stage status represents stage 
                                    that failed.
        """
        return self.query("UNEST?")

    def WarmupSupplyParameterCommand(self, output, control, percentage):
        """The Output Mode parameter and the Control Input Parameter must be configured
        using the OUTMODE command.

        :param output: Specifies which analog output to configure: 3 or 4
        :type output: int
        :param control: Specifies the type of control used: 0 = Auto Off, 1 = Continuous
        :type control: int
        :param percentage: Specifies the percentage of full scale (10 V) Monitor Out 
            voltage to apply to turn on the external power supply.
        :type percentage: float

        Example:
            WARMUP 3,1,50[term] — Output 3 will use the Continuous control mode, with a 5 V
            (50%) output voltage for activating the external power supply.
        """
        if 4 < output < 3:
            raise AssertionError(
                "Output parameter must be an integer in [3,4]")

        if 1 < control < 0:
            raise AssertionError(
                "Control parameter must be an integer in [0,1].")

        if 100.0 < percentage < 0.0:
            raise AssertionError(
                "Percentage parameter must be a float in between 0 - 100"
            )

        self.go(
            "WARUMP " +
            "{0:1d},{1:2d},{2:3.2f}".format(output, control, percentage)
        )

    def WarmupSupplyParameterQuery(self, output):
        """Refer to WarmupSupplyParameterCommand for description.

        :param output: Specifies which analog output to query: 3 or 4.
        :type output: int

        :return: ['<control>','<percentage>']
        """
        if 4 < output < 3:
            raise AssertionError(
                "Output parameter must be an integer in [3,4]")

        return self.query("WARUMP? " + "{0:1d}".format(output))

    def WebsiteLoginParameters(self, username, password):
        """Strings can be sent with or without quotation marks, but to send a string that con-
        tains spaces, commas, or semi-colons quotation marks must be used to differentiate
        the actual parameter separator.

        :param username: 15 character string representing the website username.
        :type username: str
        :param password: 15 character string representing the website password.
        :type password: str

        Example:
            WEBLOG “user”, “pass” —sets the username to user and the password to pass.
        """
        if not isinstance(username, str) or len(username) > 15:
            raise AssertionError(
                "Username parameter must be a string with a maximum of 15 characters."
            )

        if not isinstance(password, str) or len(password) > 15:
            raise AssertionError(
                "Password parameter must be a string with a maximum of 15 characters."
            )

        self.go("WEBLOG " + "{0:15},{1:15}".format(username, password))

    def WebsiteLoginParameterQuery(self):
        """Note that all strings returned by the Model 350 will be padded with spaces to main-
        tain a constant number of characters. Refer to WebsiteLoginParameters for description.

        :return: ['<username>,<password>]
        """
        return self.query("WEBLOG?")

    def ControlLoopZoneTableParameterCommand(
        self,
        output,
        zone,
        upper_bound,
        p_value,
        i_value,
        d_value,
        mout_value,
        range_value,
        input_value,
        rate,
    ):
        """Configures the output zone parameters. Refer to Paragraph 2.9.

        :param output: Specifies which heater output to configure: 1 – 4.
        :type output: int
        :param zone: Specifies which zone in the table to configure. Valid entries are: 1–10.
        :type zone: int
        :param upper_bound: Specifies the upper Setpoint boundary of this zone in kelvin.
        :type upper_bound: float
        :param p_value: Specifies the P for this zone: 0.1 to 1000.
        :type p_value: float
        :param i_value: Specifies the I for this zone: 0.1 to 1000.
        :type i_value: float
        :param d_value: Specifies the D for this zone: 0 to 200%.
        :type d_value: float
        :param mout_value: Specifies the manual output for this zone: 0 to 100%.
        :type mout_value: float
        :param range_value: Specifies the heater range for this zone. Valid entries:
                                    0 = Off,
                                    1 = Low,
                                    2 = Med,
                                    3 = High.
        :type range_value: int
        :param input_value: Specifies the sensor input_value to use for this zone.
                                    0 = Default (Use previously assigned sensor),
                                    1 = Input A,
                                    2 = Input B, 
                                    3 = Input C,
                                    4 = Input D
                                    (5 = Input D2, 6 = Input D3,7 = Input D4, 8 = Input D5 for 3062 option)
        :type input_value: int
        :param rate: Specifies the ramp rate for this zone: 0.001 to 100 K/min
        :type rate: float

        Example:
            ZONE 1,1,25.0,10,20,0,0,2,2,10[term] — Output 1 zone 1 is valid to 25.0 K with 
            P = 10, I = 20, D = 0, a heater range of medium, sensor input B, and aramp rate of 10 K/min.
        """
        if 4 < output < 1:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4].")

        if 10 < zone < 1:
            raise AssertionError(
                "Zone parameter must be an integer in between 1 - 10.")

        if upper_bound < 0.0:
            raise AssertionError(
                "Upper_Bound parameter must be a float greater than 0."
            )

        if 1000 < p_value < 0.1:
            raise AssertionError(
                "P_Value parameter must be a float greater than 0.1 .")

        if 1000 < i_value < 0.1:
            raise AssertionError(
                "I_Value parameter must be a float greater than 0.1 .")

        if 200.0 < d_value < 0.0:
            raise AssertionError(
                "D_Value parameter must be a float in between 0 - 200 ."
            )

        if 100.0 < mout_value < 0.0:
            raise AssertionError(
                "Mout_Value parameter must be a float in between 0 - 100."
            )

        if 3 < range_value < 0:
            raise AssertionError(
                "Range_Value parameter must be an integer in [0,1,2,3]."
            )

        if 4 < input_value < 0:
            raise AssertionError(
                "Input_Value parameter must be an integer in [0,1,2,3,4]."
            )

        if 100.0 < rate < 0.0:
            raise AssertionError(
                "Rate parameter must be a float in between 0.001 - 100."
            )

        self.go(
            "ZONE "
            + "{0:1d},{1:2d},{2:3.2f},{3:3.2f},{4:3.2f},{5:3.2f},{6:3.2f},{7:1d},{8:1d},{9:3.2f}".format(
                output,
                zone,
                upper_bound,
                p_value,
                i_value,
                d_value,
                mout_value,
                range_value,
                input_value,
                rate,
            )
        )  # string formatting

    def OutputZoneTableParameterQuery(self, output, zone):
        """Refer to ControlLoopZoneTableParameterCommand for description.

        :param output: Specifies which heater output to query: 1 – 4
        :type output: int
        :param zone: Specifies which zone in the table to query. Valid entries: 1–10.
        :type zone: int

        :return: ['<upper boundary>','<P value>','<I value>','<D value>','<mout value>','<range>','<input_value>','<rate>']
        """
        if 4 < output < 1:
            raise AssertionError(
                "Output parameter must be an integer in [1,2,3,4]")

        if 10 < zone < 1:
            raise AssertionError(
                "Zone parameter must be an integer in between 1 - 10.")

<< << << < HEAD:
    CryostatGUI / LakeShore / LakeShore350.py
    return self.query('ZONE? ' + '{0:1d},{1:2d}'.format(output, zone))


class LakeShore350(AbstractGPIBDeviceDriver, LakeShore350_bare):
    """docstring for LakeShore350"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class LakeShore350_ethernet(AbstractEthernetDeviceDriver, LakeShore350_bare):
    """docstring for LakeShore350"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
== == == =
    return self.query("ZONE? " + "{0:1d},{1:2d}".format(output, zone))
>>>>>> > master:
    LakeShore / LakeShore350.py
