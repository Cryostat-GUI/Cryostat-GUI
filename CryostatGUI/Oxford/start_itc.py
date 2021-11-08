import logging
from PyQt5 import QtWidgets

# from PyQt5.QtCore import QTimer
import sys
import time

from threading import Event

from pid import PidFile
from pid import PidFileError

from ITC503_ControlClient import ITCGUI
from ITC503_ControlClient_pythreading import ITC503_ControlClient_pythreading

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
        if len(sys.argv) > 1:
            with PidFile("CryoGUI/itc503"):
                # logger = logging.getLogger()
                # logger.setLevel(logging.DEBUG)

                # logger_2 = logging.getLogger("pyvisa")
                # logger_2.setLevel(logging.INFO)
                # logger_3 = logging.getLogger("PyQt5")
                # logger_3.setLevel(logging.INFO)

                # handler = logging.StreamHandler(sys.stdout)
                # handler.setLevel(logging.DEBUG)
                # formatter = logging.Formatter(
                #     "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
                # )
                # handler.setFormatter(formatter)

                # logger.addHandler(handler)
                # logger_2.addHandler(handler)
                # logger_3.addHandler(handler)

                ITC_Instrumentadress = "ASRL6::INSTR"
                stopEvent = Event()
                workingThread = ITC503_ControlClient_pythreading(
                    event=stopEvent,
                    # Name="ITC 503",
                    identity="ITC",
                    InstrumentAddress=ITC_Instrumentadress,
                    prometheus_port=8001,
                    prometheus_name="ITC",
                    # daemon=True,
                )
                workingThread.start()

                try:
                    while workingThread.is_alive():
                        # workingThread.join(0.01)
                        time.sleep(0.01)
                finally:
                    logger.warning(f"exception occured, trying to shut down gracefully")
                    stopEvent.set()
                    # logger.info("just set the event, trying to join now")
                    workingThread.join(2)
                logger.info("shutting down now")
                sys.exit(-1)

        else:
            with PidFile("CryoGUI/itc503"):
                # logger = logging.getLogger()
                # logger.setLevel(logging.DEBUG)

                # logger_2 = logging.getLogger("pyvisa")
                # logger_2.setLevel(logging.INFO)
                # logger_3 = logging.getLogger("PyQt5")
                # logger_3.setLevel(logging.INFO)

                # handler = logging.StreamHandler(sys.stdout)
                # handler.setLevel(logging.DEBUG)
                # formatter = logging.Formatter(
                #     "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
                # )
                # handler.setFormatter(formatter)

                # logger.addHandler(handler)
                # logger_2.addHandler(handler)
                # logger_3.addHandler(handler)

                app = QtWidgets.QApplication(sys.argv)
                ITC_Instrumentadress = "ASRL6::INSTR"
                form = ITCGUI(
                    ui_file="itc503_main.ui",
                    Name="ITC 503",
                    identity="ITC",
                    InstrumentAddress=ITC_Instrumentadress,
                    prometheus_port=8001,
                )
                # try:
                if len(sys.argv) == 1:
                    form.show()
                # print('date: ', dt.datetime.now(),
                #       '\nstartup time: ', time.time() - a)
                exit = app.exec_()
                sys.exit(exit)
                # except KeyboardInterrupt:
                #     print("shutting down due to Ctrl+C")
                #     sys.exit()

    except PidFileError:
        logger.error("Program already running! \nShutting down now!\n")
        sys.exit(0)
