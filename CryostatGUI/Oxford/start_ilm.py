import logging
from PyQt5 import QtWidgets
import sys

from pid import PidFile
from pid import PidFileError

from ILM_ControlClient import DeviceGUI

if __name__ == "__main__":

    try:
        with PidFile("ilm211"):
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
            form = DeviceGUI(
                ui_file="ILM_main.ui",
                Name="ILM 211",
                identity="ILM",
                InstrumentAddress="ASRL5::INSTR",
                prometheus_port=8002,
            )
            try:
                form.show()
                # print('date: ', dt.datetime.now(),
                #       '\nstartup time: ', time.time() - a)
                exit = app.exec_()
            except KeyboardInterrupt:
                print("shutting down: ", exit)
                # sys.exit(-500)
            # sys.exit(exit)
    except PidFileError:
        print("Program already running! \nShutting down now!\n")
        sys.exit()
