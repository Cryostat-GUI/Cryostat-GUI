from PyQt5 import QtWidgets
import sys

from .mainWindow import mainWindow


# if __name__ == '__main__':
app = QtWidgets.QApplication(sys.argv)
form = mainWindow(app=app)
form.show()
# print('date: ', datetime.datetime.now(),
#       '\nstartup time: ', time.time() - a)
sys.exit(app.exec_())
