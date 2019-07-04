"""Module for controlling a Stanford Research SR830 Lock-In Amplifier
    for use as control device for pressure as well as measuring
    resistivity

Author(s):
    bklebel (Benjamin Klebel)
    Wojtek
"""
from pymeasure.instruments.srs import SR830

import sys
# import os
import time
import numpy as np
# from parse import *

import argparse

filename = 'EUG27A_He4-06.dat'

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--inlet', '-p', type=int, required=True,
                    help='pressure of the inlet')

args = parser.parse_args()

inlet_pressure = args.inlet  # bar
# goal_pressure = 5 # bar, this is max pressure we want to achieve

for goal_pressure in range(6, 7, 1):

    volt = goal_pressure / 1.7898
    volt_max = inlet_pressure / 1.7898

    if inlet_pressure < goal_pressure:
        sys.exit('Goal prressure exceeds the limit, bitch!!')

    ramp1 = np.linspace(0, volt, int(volt / 0.1))
    ramp2 = np.linspace(volt, 0, int(volt / 0.1))
    print(ramp1)

    lockin1 = SR830('GPIB::9')

    print(lockin1.frequency)
    lockin1.frequency = 11.425
    print(lockin1.frequency)

    for no_cycle in range(1):

        CNT = 0
        for ramp in [ramp1, ramp2]:
            for set_voltage in ramp:

                lockin1.auxv3 = set_voltage
                time.sleep(1)

                for no_mes in range(50):

                    read_voltage = lockin1.get_AUXin(3)
                    read_pressure = (read_voltage - 1.008) / 0.3924

                    set_pressure = lockin1.auxv3 * 1.7898
                    data = [set_pressure, read_pressure, lockin1.auxv3, read_voltage,
                            lockin1.x, lockin1.y, lockin1.frequency, lockin1.sine_voltage]
                    print(no_mes, data)

                    with open(filename, 'a') as f:
                        f.write('{} {} {} {} {} {} {} {} {} {} \n'.format(data[0], data[1], data[
                                2], data[3], data[4], data[5], data[6], data[7], CNT, no_cycle))

                    time.sleep(0.2)

                time.sleep(2)
                CNT += 1
