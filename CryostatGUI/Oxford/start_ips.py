import logging
import sys

from ips120 import ips120

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


Addr = "ASRL4::INSTR"


instr = ips120(Addr)
