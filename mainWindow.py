
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

import sys
import time

import mainWindow_ui

from Oxford.ITC_control import ITC_Updater as cls_itc
from labdrivers.oxford.itc503 import itc503

from pyvisa.errors import VisaIOError


class main_Worker(QObject):

    """This is the worker thread, which updates all instrument data of the ITC 503.

        For each itc503 function (except collecting data), there is a wrapping method,
        which we can call by a signal, from the main thread. This wrapper sends
        the corresponding value to the device. 

        There is a second method for all wrappers, which accepts
        the corresponding value, and stores it, so it can be sent upon acknowledgment 

        The information from the device is collected in regular intervals (method "work"),
        and subsequently sent to the main thread. It is packed in a dict,
        the keys of which are displayed in the "sensors" dict in this class. 
    """

    sig_dict = pyqtSignal(dict)
    sig_str = pyqtSignal(str)
    sig_str = pyqtSignal(str)
    sig_ = pyqtSignal()


    def __init__(self):
        QThread.__init__(self)

    @pyqtSlot()
    def work(self):
        app.processEvents()

    def printing(self,b):
        print('a', b)
        time.sleep(2)
        print('b', b)

class mainWindow(QtWidgets.QMainWindow): #, mainWindow_ui.Ui_Cryostat_Main):
    
    sig_arbitrary = pyqtSignal()

    def __init__(self, **kwargs):
        super(mainWindow, self).__init__(**kwargs)
        loadUi('Cryostat GUI.ui', self)
        # self.setupUi(self)
        self.threads = dict()


        worker = main_Worker()
        thread = QThread()
        self.threads['mainworker'] = (worker, thread)
        worker.moveToThread(thread)
        thread.started.connect(worker.work)
        thread.start()

        self.action_run_ITC.triggered['bool'].connect(self.run_ITC)
        # self.action_run_ITC.triggered['bool'].connect(self.threads['mainworker'][0].printing)





    def run_ITC(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""

        if boolean:
            try:
                ITC = itc503()
                getInfodata = cls_itc(ITC)
                thread = QThread()
                self.threads['ITC'] = (getInfodata, thread)
                self.getInfodata.moveToThread(thread)

                getInfodata.sig_GasOutput.connect(self.setNeedleIndicator)

                thread.started.connect(getInfodata.work)
                thread.start()
                self.action_run_ITC.setChecked(True)
            except VisaIOError as e:
                self.action_run_ITC.setChecked(False)
                print(e)
                # return e

        else:
            self.action_run_ITC.setChecked(False)
            self.threads['ITC'][1].quit()
            self.threads['ITC'][1].wait()


# def main():
#         app = QtWidgets.QApplication(sys.argv)
#         form = mainWindow()
#         form.show()
#         sys.exit(app.exec_())

if __name__ == '__main__':
    # main()
    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow()
    form.show()
    sys.exit(app.exec_())

