from util.zmqcomms import zmqMainControl
from util.zmqcomms import loops_off_zmq
from util.zmqcomms import dictdump
import sys

# import numpy as np
import pandas as pd


import time
import logging


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logger_2 = logging.getLogger("pyvisa")
logger_2.setLevel(logging.INFO)
logger_3 = logging.getLogger("PyQt5")
logger_3.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
)
handler.setFormatter(formatter)

logger.addHandler(handler)
logger_2.addHandler(handler)
logger_3.addHandler(handler)


c = zmqMainControl(_ident="main_manual")

datafile = './CERNOX-June2022/calibrate_cernox_001.csv'

shunt_Resistance = 1 * 1e3
contact_Resistance = 150

sr_sr860 = "SR860_1"
sr_sr830 = "SR830_1"
id_lakeshore = "LakeShore350"
# ct, x, y, theta
df_sr860 = pd.DataFrame(
    dict(X_V=[], Y_V=[], Theta_Deg=[], R_V=[], Voltage_V=[], Frequency_Hz=[])
)

df = pd.DataFrame(
    dict(
        X_V=[],
        Y_V=[],
        Theta_Deg=[],
        R_V=[],
        Voltage_V=[],
        Frequency_Hz=[],
        SampleCurrent_A=[],
        SampleResistance_Ohm=[],
        Temperature_sample_K=[],
        Temperature_holder_K=[],
    )
)


set_freq = 11.1111
input_voltage = 2.0

c.commanding(ID=sr_sr860, message=dictdump({"setFrequency": set_freq}))
c.commanding(ID=sr_sr860, message=dictdump({"setVoltage": input_voltage}))


while True:

    time.sleep(12)

    data = c.query_device_command(sr_sr860, {"measure_raw": 0})["data_raw"]

    SampleCurrent_A = data["Voltage_V"] / (shunt_Resistance + contact_Resistance + 50)

    data["SampleCurrent_A"] = SampleCurrent_A
    data["SampleResistance_Ohm"] = data["X_V"] / SampleCurrent_A

    print(data)

    temperature_1_K = c.query_device_command(
        id_lakeshore, {"measure_Sensor_K": "Sensor_1_K"}
    )["data_raw"]["Temperature_K"]

    temperature_4_K = c.query_device_command(
        id_lakeshore, {"measure_Sensor_K": "Sensor_4_K"}
    )["data_raw"]["Temperature_K"]

    data["Temperature_sample_K"] = temperature_1_K
    data["Temperature_holder_K"] = temperature_4_K

    df = df.append(data, ignore_index=True)

    with open(datafile, "a", newline="") as f:
        df.tail(1).to_csv(f, header=f.tell() == 0, sep=" ", index_label="Ct")
