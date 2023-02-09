import logging
from datetime import datetime as dt

import sys
from util.util_misc import CustomStreamHandler

from Sequence_zmq import Sequence_functionsPersonal
from Sequence_zmq import Sequence_comms_zmq

from tokenize import detect_encoding
import time


# with PidFile("MainControl"):
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logger_2 = logging.getLogger("pyvisa")
logger_2.setLevel(logging.DEBUG)
logger_3 = logging.getLogger("PyQt5")
logger_3.setLevel(logging.DEBUG)

# logger_4 = logging.getLogger("measureSequences")
# logger_4.setLevel(logging.DEBUG)

date = dt.now().strftime("%Y%m%d-%H%M%S")
handler_debug = logging.FileHandler(filename=f"Logs/Sequence_logs{date}.log", mode="a")
handler_debug.setLevel(logging.DEBUG)
formatter_debug = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
)
handler_debug.setFormatter(formatter_debug)

handler_info = CustomStreamHandler(logging.INFO, sys.stdout)
handler_info.setLevel(logging.INFO)
formatter_info = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler_info.setFormatter(formatter_info)

logger.addHandler(handler_debug)
logger.addHandler(handler_info)
logger_2.addHandler(handler_debug)
logger_3.addHandler(handler_debug)
# logger_4.addHandler(handler_debug)
# logger_4.addHandler(handler_info)


class from_Sequence_runner(object):
    """docstring for from_Sequence_runner"""

    # def __init__(self, arg):
    #     super(from_Sequence_runner, self).__init__()
    #     self.arg = arg

    def execute_python_single(self, file: str, **kwargs) -> None:
        """execute python code directly, changable during runtime

        DANGEROUS!

        Has the potential that whatsoever-code is inserted. In principle,
        after all, that is exactly its purpose. Be careful with it, it might
        give unpleasant surprises....

        using globals() and locals(), the python script is in the Namespace of
        'right here', in this function.
        checks file for encoding"""
        with open(self.python_default_path + file, "rb") as fe:
            try:
                enc = detect_encoding(fe.readline)[0]
            except SyntaxError:
                enc = "utf-8"

        with open(self.python_default_path + file, "r", encoding=enc) as f:
            fc = f.read()
        if not fc.endswith("\n"):
            fc += "\n"
        code = compile(fc, file, "exec")
        exec(code, globals(), locals())


class Together(Sequence_functionsPersonal, from_Sequence_runner, Sequence_comms_zmq):
    """docstring for Together"""


if __name__ == "__main__":
    d = Together(_ident="main_manual")
    filename = "cal_cernox_X119873_X119802_to_X118100__7.dat"
    d.datafile = "C:/Users/Lab-user/Dropbox/SPLITCOIL_data/calibrations/" + filename

    d.python_default_path = "Sequence/"

    while True:
        d.execute_python_single(file="measure_temperature_calibration.py")
        time.sleep(10)


