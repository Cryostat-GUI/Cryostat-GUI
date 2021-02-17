import logging
from PyQt5 import QtWidgets

# from PyQt5.QtCore import QTimer
import sys

# import time
# from threading import Event

from pid import PidFile
from pid import PidFileError

from Keithley6221_ControlClient import Keithley6221GUI

if __name__ == "__main__":

    try:
        prometheus_startport = 8006  # one below the first Keithley 6221
        if len(sys.argv) > 1:
            n = int(sys.argv[1]) if sys.argv[1] != 0 else 1
        else:
            n = 1
        # Keithley6221_adress = f"TCPIP::192.168.1.10{6+n-1}::1394::SOCKET"
        # f"TCPIP::192.168.1.106::1394::SOCKET"
        # f"GPIB0::{n+1}::INSTR"
        Keithley6221_adress = f"GPIB0::{5+n-1}::INSTR"
        prometheus_port = prometheus_startport + n

        with PidFile(f"Keithley6221_{n}"):
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

            app = QtWidgets.QApplication(sys.argv)
            logger.debug(Keithley6221_adress)
            form = Keithley6221GUI(
                ui_file="K6221_main.ui",
                Name=f"Keithley6221_{n}",
                identity=f"Keithley6221_{n}",
                InstrumentAddress=Keithley6221_adress,
                prometheus_port=prometheus_port,
            )
            form.show()
            # print('date: ', dt.datetime.now(),
            #       '\nstartup time: ', time.time() - a)
            sys.exit(app.exec_())
    except PidFileError:
        print("Program already running! \nShutting down now!\n")
        sys.exit()
