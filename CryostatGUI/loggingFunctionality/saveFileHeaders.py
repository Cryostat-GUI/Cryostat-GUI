headerstring1 = """\
# Measurement started on {date}
#
# date,Sensor_1_(A)_[K]_arithmetic_mean,Sensor_1_(A)_[K]_uncertainty,Sensor_2_(B)_[K]_arithmetic_mean,Sensor_2_(B)_[K]_uncertainty,Sensor_3_(C)_[K]_arithmetic_mean,Sensor_3_(C)_[K]_uncertainty,Sensor_4_(D)_[K]_arithmetic_mean,Sensor_4_(D)_[K]_uncertainty,Keith1:_resistance_[Ohm]_(slope_of_4_points),Keith1:_residuals_(of_fit_for_slope),Keith1:_non-ohmicity:_0_if_ohmic_1_if_nonohmic,Keith2:_resistance_[Ohm]_(slope_of_4_points),Keith2:_residuals_(of_fit_for_slope),Keith2:_non-ohmicity:_0_if_ohmic_1_if_nonohmic,descr1,Keith1_voltage_1,Keith1_voltage_2,Keith1_voltage_3,Keith1_voltage_4,descr2,Keith2_voltage_1,Keith2_voltage_2,Keith2_voltage_3,Keith2_voltage_4,descr3,Keith1_current_1,Keith1_current_2,Keith1_current_3,Keith1_current_4,descr4,Keith2_current_1,Keith2_current_2,Keith2_current_3,Keith2_current_4,
# columns -1 based / zero based / one based
#
# -1 / 0 /  1 date
#
#   -- temperatures
#  0 /  1 /  2 Sensor 1 (A) [K] arithmetic mean
#  1 /  2 /  3 Sensor 1 (A) [K] uncertainty
#  2 /  3 /  4 Sensor 2 (B) [K] arithmetic mean
#  3 /  4 /  5 Sensor 2 (B) [K] uncertainty
#  4 /  5 /  6 Sensor 3 (C) [K] arithmetic mean
#  5 /  6 /  7 Sensor 3 (C) [K] uncertainty
#  6 /  7 /  8 Sensor 4 (D) [K] arithmetic mean
#  7 /  8 /  9 Sensor 4 (D) [K] uncertainty
#
#   -- resistances Keithley2182_1
#  8 /  9 / 10 resistance [Ohm] (slope of 4 points)
#  9 / 10 / 11 residuals (of fit for slope)
# 10 / 11 / 12 non-ohmicity: 0 if ohmic, 1 if nonohmic
#
#   -- resistances Keithley2182_2
# 11 / 12 / 13 resistance [Ohm] (slope of 4 points)
# 12 / 13 / 14 residuals (of fit for slope)
# 13 / 14 / 15 non-ohmicity: 0 if ohmic, 1 if nonohmic
#
#   the following numbers only apply if the number of points for the iv-fit is 4

#   -- voltages Keithley2182_1
# 14 / 15 / 16 number of voltages
# 15 / 16 / 17 voltage 1
# 16 / 17 / 18 voltage 2
# 17 / 18 / 19 voltage 3
# 18 / 19 / 20 voltage 4

#   -- voltages Keithley2182_2
# 19 / 20 / 21 number of voltages
# 20 / 21 / 22 voltage 1
# 21 / 22 / 23 voltage 2
# 22 / 23 / 24 voltage 3
# 23 / 24 / 25 voltage 4

#   -- currents Keithley6221_1
# 24 / 25 / 26 number of currents
# 25 / 26 / 27 current 1
# 26 / 27 / 28 current 2
# 27 / 28 / 29 current 3
# 28 / 29 / 30 current 4

#   -- currents Keithley6221_2
# 29 / 30 / 31 number of currents
# 30 / 31 / 32 current 1
# 31 / 32 / 33 current 2
# 32 / 33 / 34 current 3
# 33 / 34 / 35 current 4
# 34 / 35 / 36 unused
# 35 / 36 / 37 unused
# 36 / 37 / 38 unused
# 37 / 38 / 39 unused
# 38 / 39 / 40 unused
# 39 / 40 / 41 unused
# 40 / 41 / 42 unused
# 41 / 42 / 43 unused
# 42 / 43 / 44 unused
# 43 / 44 / 45 unused
# 44 / 45 / 46 unused
# 45 / 46 / 47 unused
# 46 / 47 / 48 unused
# 47 / 48 / 49 unused
# 48 / 49 / 50 unused
# 49 / 50 / 51 unused
# 50 / 51 / 52 unused
# 51 / 52 / 53 unused
# 52 / 53 / 54 unused
# 53 / 54 / 55 unused
# 54 / 55 / 56 unused
# 55 / 56 / 57 unused
# 56 / 57 / 58 unused
# 57 / 58 / 59 unused
# 58 / 59 / 60 unused
# 59 / 60 / 61 unused
# 60 / 61 / 62 unused
# 61 / 62 / 63 unused
# 62 / 63 / 64 unused
# 63 / 64 / 65 unused
# 64 / 65 / 66 unused
# 65 / 66 / 67 unused
# 66 / 67 / 68 unused
# 67 / 68 / 69 unused
# 68 /
"""
