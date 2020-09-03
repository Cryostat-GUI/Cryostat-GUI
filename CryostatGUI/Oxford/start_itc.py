import logging
from PyQt5 import QtWidgets
import sys

from ITC503_ControlClient import ITCGUI
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

    app = QtWidgets.QApplication(sys.argv)
    ITC_Instrumentadress = "ASRL6::INSTR"
    form = ITCGUI(
        ui_file="itc503_main.ui",
        Name="ITC 503",
        identity="ITC",
        InstrumentAddress=ITC_Instrumentadress,
        prometheus_port=8001,
    )
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
