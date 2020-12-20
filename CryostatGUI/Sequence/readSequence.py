from PyQt5 import QtWidgets
import sys

from measureSequences import Sequence_builder


if __name__ == "__main__":

    file = "SEQ_20180914_Tscans.seq"
    file = "Tempscan.seq"
    file = None
    # file = 't.seq'

    app = QtWidgets.QApplication(sys.argv)
    form = Sequence_builder(file)
    form.show()
    sys.exit(app.exec_())
    