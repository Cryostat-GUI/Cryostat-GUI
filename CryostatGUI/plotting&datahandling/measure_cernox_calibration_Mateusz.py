from util.zmqcomms import zmqMainControl
from util.zmqcomms import dictdump
import sys


import pandas as pd

import time
import datetime
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


zmq_main_control = zmqMainControl(_ident="main_manual")

datafile = 'C:/Users/Lab-user/Dropbox/SPLITCOIL_data/calibrations/cal_cernox_X119873_X119802_to_X118100__9.dat'

id_lakeshore = "LakeShore350"

df_LS350 = pd.DataFrame(dict(datetime=[], sensor1_K=[], sensor1_Ohms=[], sensor2_K=[], sensor2_Ohms=[], sensor3_K=[], sensor3_Ohms=[], sensor4_K=[], sensor4_Ohms=[]))

while True:

    time.sleep(10)

    dt = datetime.datetime.now()

    sensor1_K = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_K": "Sensor_1_K"})["data_raw"]["Temperature_K"]))
    sensor1_Ohms = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_Ohm": "Sensor_1_Ohm"})["data_raw"]["Temperature_Ohm"]))

    sensor2_K = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_K": "Sensor_2_K"})["data_raw"]["Temperature_K"]))
    sensor2_Ohms = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_Ohm": "Sensor_2_Ohm"})["data_raw"]["Temperature_Ohm"]))

    sensor3_K = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_K": "Sensor_3_K"})["data_raw"]["Temperature_K"]))
    sensor3_Ohms = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_Ohm": "Sensor_3_Ohm"})["data_raw"]["Temperature_Ohm"]))

    sensor4_K = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_K": "Sensor_4_K"})["data_raw"]["Temperature_K"]))
    sensor4_Ohms = float("{0:.4f}".format(zmq_main_control.query_device_command(id_lakeshore, {"measure_Sensor_Ohm": "Sensor_4_Ohm"})["data_raw"]["Temperature_Ohm"]))

    df_LS350 = df_LS350.append(dict(datetime=dt, sensor1_K=sensor1_K, sensor1_Ohms=sensor1_Ohms, sensor2_K=sensor2_K, sensor2_Ohms=sensor2_Ohms,
        sensor3_K=sensor3_K, sensor3_Ohms=sensor3_Ohms, sensor4_K=sensor4_K, sensor4_Ohms=sensor4_Ohms), ignore_index=True)

    with open(datafile, "a", newline="") as f:
        df_LS350.tail(1).to_csv(f, header=f.tell() == 0, sep=" ")
