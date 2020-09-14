import logging
from PyQt5 import QtWidgets
import sys

from LakeShore350_ControlClient import LakeShoreGUI

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

    LakeShore_InstrumentAddress = "TCPIP::192.168.2.105::7777::SOCKET"
    app = QtWidgets.QApplication(sys.argv)
    form = LakeShoreGUI(
        ui_file="LakeShore_main.ui",
        Name="LakeShore350",
        identity="LakeShore350",
        InstrumentAddress=LakeShore_InstrumentAddress,
        prometheus_port=8004,
    )
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
