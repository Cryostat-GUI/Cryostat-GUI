import pyvisa as visa
from pymeasure.instruments.srs import SR860

rm = visa.ResourceManager()
print(rm)
info = str(rm.list_resources())
info = info.replace("(", "")
info = info.replace(")", "")
info = info.split(", ")
print("Devices that are connected:")
numerator = 1
for inst in info:
    print(str(numerator) + ". " + inst)
    numerator += 1
print()

SR860 = SR860("GPIB::24::INSTR")
# SR860 = rm.open_resource('GPIB::24::INSTR')
print(SR860.query("*IDN?"))

# LS here is 5 or 6

print("Hello there")

"""
from pymeasure.instruments.srs import SR830
from Keithley2182 import Keithley2182
from datetime import datetime as dt
from time import sleep
import pyvisa as visa



# IEEE 488, SELECT PORT GPIB ADDR 06 COMMANDS FLUKE 45 (sophisticated) or 8842 (the raw fluke8846.read() works)

fluke8846a = rm.open_resource('GPIB::6::INSTR')
print(fluke8846a.query('*IDN?'))
fluke8846a.write('*RST; AAC; RANGE 1; RATE M; TRIGGER 1; *TRG')

Keithley_2182A_Nanovoltmeter = Keithley2182('GPIB::7::INSTR')
print(Keithley_2182A_Nanovoltmeter.query('*IDN?'))

Keithley_2002_Multimeter = rm.open_resource('GPIB::16::INSTR')
print(Keithley_2002_Multimeter.query('*IDN?'))
print(Keithley_2002_Multimeter.query(':FETCh?'))

SR830_DSP_Lockin_Amplifier = SR830('GPIB::8::INSTR')
print(SR830_DSP_Lockin_Amplifier.ask('*IDN?'))
# print(SR830_DSP_Lockin_Amplifier.x)

lakeshore = LakeShore331('GPIB::12::INSTR')
# print(lakeshore.ask('*IDN?'))

filename = './new_probe_april2022/431-7/431-7_006.dat'

with open(filename, "a") as file:
    file.write('T_Kth2182A[K] T_Kth2002[K] CNT Ux[V] Uy[V] f[Hz] SinVoltage[V] Current[A] Res[Ohm] %s\n' % dt.now())

indx = 1
while True:
    el_x = SR830_DSP_Lockin_Amplifier.x
    el_y = SR830_DSP_Lockin_Amplifier.y
    el_f = SR830_DSP_Lockin_Amplifier.frequency
    sine_volt = SR830_DSP_Lockin_Amplifier.sine_voltage

    ac_curr = float(fluke8846a.query('VAL1?'))
    ohm_res = float(el_x) / float(ac_curr)
    kth_2002_T = float(Keithley_2002_Multimeter.query(':READ?').split(',')[0][0:-2])
    temps = [Keithley_2182A_Nanovoltmeter.temperature, kth_2002_T]
    # LS_temps = [lakeshore.temperature_A, lakeshore.temperature_B]
    LS_temps = [0, 0]
    print(ac_curr)

    line_to_save = '%.4f %.4f %d %.8f %.8f %.4f %.4f %.8f %.8f %.4f %.4f\n' % (temps[0] + 273.15, temps[1] + 273.15, indx, el_x, el_y,
                                                                     el_f, sine_volt, ac_curr, ohm_res, LS_temps[0], LS_temps[1])
    print(line_to_save + str(dt.now()))
    with open(filename, "a") as fn:
        fn.write(line_to_save)

    indx += 1
    sleep(2)"""
