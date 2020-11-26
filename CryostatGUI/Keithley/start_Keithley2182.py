import logging
from PyQt5 import QtWidgets

# from PyQt5.QtCore import QTimer
import sys

# import time
# from threading import Event

from pid import PidFile
from pid import PidFileError

from Keithley2182_ControlClient import Keithley2182GUI

if __name__ == "__main__":

    try:
        if len(sys.argv) > 1:
            n = sys.argv[1] if sys.argv[1] != 0 else 1
            Keithley2182_adress = f"GPIB0::{int(n)+1}::INSTR"
        else:
            n = 1

        with PidFile(f"Keithley_{n}"):
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
            form = Keithley2182GUI(
                ui_file="Nanovolt_main.ui",
                Name=f"Keithley2182_{n}",
                identity=f"Keithley2182_{n}",
                InstrumentAddress=Keithley2182_adress,
                prometheus_port=None,
            )
            form.show()
            # print('date: ', dt.datetime.now(),
            #       '\nstartup time: ', time.time() - a)
            sys.exit(app.exec_())
    except PidFileError:
        print("Program already running! \nShutting down now!\n")
        sys.exit()
