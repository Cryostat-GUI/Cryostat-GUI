import logging
import sys
from PyQt5 import QtWidgets
from pymeasure.instruments.srs import SR860

from pid import PidFile
from pid import PidFileError

from SR830_ControlClient import SR830GUI

if __name__ == "__main__":
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

    try:
        with PidFile("CryoGUI/SR860"):

            # Sr860_InstrumentAddress = 'GPIB::4::INSTR'
            # Sr860_InstrumentAddress = 'TCPIP::192.168.2.104::1865::SOCKET'
            # Sr860_InstrumentAddress = "TCPIP::192.168.2.104::INSTR"
            Sr860_InstrumentAddress = "TCPIP::192.168.1.104::INSTR"

            app = QtWidgets.QApplication(sys.argv)
            form = SR830GUI(
                ui_file="LockIn_main.ui",
                Name="LockinSR860",
                identity="SR860_1",
                InstrumentAddress=Sr860_InstrumentAddress,
                Lockin=SR860,
                prometheus_port=8005,
            )
            form.show()
            # print('date: ', dt.datetime.now(),
            #       '\nstartup time: ', time.time() - a)
            sys.exit(app.exec_())
    except PidFileError:
        logger.error("Program already running! \nShutting down now!\n")
        sys.exit()
