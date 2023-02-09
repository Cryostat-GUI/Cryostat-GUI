import logging
import sys
from pid import PidFile
from pid import PidFileError
from PyQt5 import QtWidgets

from logger import LoggingGUI

try:
    with PidFile("zmqLogger"):
        # dbname = 'He_first_cooldown.db'
        # conn = sqlite3.connect(dbname)
        # mycursor = conn.cursor()
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
        form = LoggingGUI(Name="Logger", identity="log")
        form.show()
        # print('date: ', dt.datetime.now(),
        #       '\nstartup time: ', time.time() - a)
        sys.exit(app.exec_())
except PidFileError:
    print("Program already running! \nShutting down now!\n")
    sys.exit()
