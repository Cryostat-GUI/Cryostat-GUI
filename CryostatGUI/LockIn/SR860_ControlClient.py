from SR830_ControlClient import SR830GUI
import sys
from PyQt5 import QtWidgets
from pymeasure.instruments.srs import SR860

if __name__ == "__main__":
    # Sr860_InstrumentAddress = 'GPIB::4::INSTR'
    # Sr860_InstrumentAddress = 'TCPIP::192.168.2.104::1865::SOCKET'
    Sr860_InstrumentAddress = "TCPIP::192.168.2.104::INSTR"

    app = QtWidgets.QApplication(sys.argv)
    form = SR830GUI(
        ui_file="LockIn_main.ui",
        Name="LockinSR860",
        identity="SR860_1",
        InstrumentAddress=Sr860_InstrumentAddress,
        Lockin=SR860,
    )
    form.show()
    # print('date: ', dt.datetime.now(),
    #       '\nstartup time: ', time.time() - a)
    sys.exit(app.exec_())
