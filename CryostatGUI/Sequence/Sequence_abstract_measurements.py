from numpy.polynomial.polynomial import polyfit
from itertools import combinations_with_replacement as comb
from time import sleep

import logging

logger = logging.getLogger("CryostatGUI.Sequences")
logger_measure = logging.getLogger("CryostatGUI.measuring")


def AbstractMeasureResistance(
    channel_current,
    channel_voltage,
    exc_curr,
    iv_characteristic,
    current_reversal_time=0.06,
):
    """Abstract logic for resistance measurement"""
    # logger_measure.info("abstract resistance measurement")
    currents = []
    voltages = []
    resistance = {}
    first = True
    for currentfactor in [-1, 1]:
        if currentfactor == 1:
            iv_char = reversed(iv_characteristic)
        else:
            iv_char = iv_characteristic
        for current_base in iv_char:
            current = exc_curr * currentfactor * current_base
            currents.append(current)
            channel_current.current = current
            if first:
                channel_current.enabled = True
                first = False
            # waiting for current to stabilize
            sleep(current_reversal_time)
            voltage = channel_voltage.voltage
            voltages.append(voltage)
    channel_current.enabled = False
    c, stats = polyfit(currents, voltages, deg=1, full=True)
    resistance["coeff"] = c[1]
    resistance["residuals"] = stats[0][0]
    logger_measure.info(
        "Measured Resistance {} for ch current: {}, ch voltage: {}, iv_char: {}, excitation: {}".format(
            resistance, channel_current, channel_voltage, iv_characteristic, exc_curr
        )
    )
    return resistance, currents, voltages


def AbstractMeasureResistanceMultichannel(
    channels_current: list,
    channels_voltage: list,
    iv_characteristic: list,
    exc_currs: list,
):
    """Abstract logic for multichannel resistance measurement"""
    lengths = [len(channels_current), len(channels_voltage), len(exc_currs)]
    for c in comb(lengths, 2):
        if c[0] != c[1]:
            logger_measure.error(
                "number of excitation currents, current sources and voltmeters does not coincide!"
            )

    resistances = []
    excitations = []
    voltages = []
    for chC, chV, exc in zip(channels_current, channels_voltage, exc_currs):
        R, I, V = AbstractMeasureResistance(chC, chV, exc, iv_characteristic)
        resistances.append(R)
        excitations.append(I)
        voltages.append(V)

    return resistances, excitations, voltages
