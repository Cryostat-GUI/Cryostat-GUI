"""Documentation for usable functions in measuring scripts, to be injected by a user"""

""" defining classes for channels for DC measurement  """


class Keithley_Source_Channel:
    """docstring for Keithley_Source_Channel"""

    def __init__(self, control, device_id="Keithley6221_1"):
        self.id = device_id
        self.control = control

    def setCurrent(self, current):
        self.control.query_device_command(
            self.id,
            command={"set_Current_A": current},
        )

    def __repr__(self):
        return f"current source: {self.id}"


class Keithley_Voltage_Channel(object):
    """docstring for Keithley_Source_Channel"""

    def __init__(self, control, device_id="Keithley2182_1"):
        # super().__init__()
        self.id = device_id
        self.control = control

    def readVoltage(self):
        return self.control.query_device_command(
            self.id,
            command={"measure_Voltage": None},
        )["Voltage_V"]

    def __repr__(self):
        return f"nanovoltmeter: {self.id}"


# ----------------------------------------------------------------------------------------
"""    USER     PREFERENCES    HERE   """

# defining which instruments are used for the resistance measurement
k6221_1 = Keithley_Source_Channel(control=self, device_id="Keithley6221_1")
k2182_1 = Keithley_Voltage_Channel(control=self, device_id="Keithley2182_1")


"""defining the dc resistance characteristic.
    With exc_curr = 5, and iv_characteristic = [1, 0.5],
    the excitation currents in use are:
        -5, -2.5, 2.5, 5
"""
exc_curr = 5e-3
iv_characteristic = [1, 0.5]
# ----------------------------------------------------------------------------------------


self._logger.info("measuring DC with %s and %s", k6221_1, k2182_1)

# first temperature measurement, before measuring
t1 = self.getTemperature_force(sensortype="sample")

# dc measurement as defined in the called function
# in sublime text editor, klick on the function and press F12 to see the code
rho, currents, voltages = AbstractMeasureResistance(
    channel_current=k6221_1,
    channel_voltage=k2182_1,
    exc_curr=exc_curr,
    iv_characteristic=iv_characteristic,
)

# second temperature measurement, after measuring
t2 = self.getTemperature_force(sensortype="sample")


# mean and standard deviation of temperatures
t_mean = np.mean([t1, t2])
t_std = np.std([t1, t2])

# building the dictionary which contains all measurement data
d = dict(
    temperature=t_mean,
    temperature_std=t_std,
    rho=rho["coeff"],
    rho_residuals=rho["residuals"],
)
# updating the data dictionary with all the excitation currents and
# accordingly measured voltages
for ct, (c, v) in enumerate(zip(currents, voltages)):
    d.update({f"current_{ct}": c, f"voltage_{ct}": v})
# )

# last-second changes of the datafile to which the data is written:
# self.datafile = "C:/Users/Lab-user/Dropbox/SPLITCOIL_data/tests/second.csv"
# writing data to datafile (csv)
self.measuring_store_data(data=d, datafile=self.datafile)


# additional outputs, writing to other files, printing things to the console...
# with open(self.datafile, "a", newline="") as f:
#     df.tail(1).to_csv(f, header=f.tell() == 0, index=False)

# print("Temperature:", self.getTemperature_force(sensortype="sample"))
