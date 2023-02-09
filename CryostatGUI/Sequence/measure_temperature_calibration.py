"""Documentation for usable functions in measuring scripts, to be injected by a user"""
# from Sequence_abstract_measurements import AbstractMeasureResistance
from util.zmqcomms import loops_off_zmq
from datetime import datetime as dt

self._logger.info(
    "CAl MEAS - -------------   START  ---------------------------------------"
)


""" defining classes for channels for DC measurement  """

# ----------------------------------------------------------------------------------------
"""    USER     PREFERENCES    HERE   """

# defining which instruments are used for the resistance measurement

loop_stop_devices = [
    # "Keithley6221_1",
    # "Keithley2182_1",
    "LakeShore350",
]

# ----------------------------------------------------------------------------------------
stop_loops = loops_off_zmq(control=self, devices=loop_stop_devices)


with stop_loops:
    # self._logger.info("DC MEAS - measuring DC with %s and %s", k6221_1, k2182_1)
    data = self.query_device_command(
        "LakeShore350",
        command={
            "measure_calibration": None,
        },
    )


data = data["data_raw"]

self._logger.info("CAL MEAS {}".format(data))


# building the dictionary which contains all measurement data
d = dict(
    timestamp=dt.now().isoformat(),
)

for ct, (k, o) in enumerate(zip(data["kelvins"], data["ohms"])):
    d[f"sensor{ct+1}_K"] = k
    d[f"sensor{ct+1}_Ohms"] = o


self._logger.debug("Cal MEAS - storing data")
# last-second changes of the datafile to which the data is written:
# self.datafile = "C:/Users/Lab-user/Dropbox/SPLITCOIL_data/tests/second.csv"
# writing data to datafile (csv)
self.measuring_store_data(data=d, datafile=self.datafile)


# additional outputs, writing to other files, printing things to the console...
# with open(self.datafile, "a", newline="") as f:
#     df.tail(1).to_csv(f, header=f.tell() == 0, index=False)

# print("Temperature:", self.getTemperature_force(sensortype="sample"))

self._logger.info(
    "CAL MEAS - -------------   STOP  ---------------------------------------"
)
