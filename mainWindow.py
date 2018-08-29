
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi

import sys
import time
import datetime

import mainWindow_ui

from Oxford.ITCcontrol_ui import Ui_ITCcontrol
from Oxford.ITC_control import ITC_Updater as cls_itc

from labdrivers.oxford.itc503 import itc503

from pyvisa.errors import VisaIOError


class main_Worker(QObject):

    """This is a worker thread
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
        """arbitrary exmple function"""
        print('a', b)
        time.sleep(2)
        print('b', b)


class mainWindow(QtWidgets.QMainWindow): #, mainWindow_ui.Ui_Cryostat_Main):
    """This is the main GUI Window"""
    
    sig_arbitrary = pyqtSignal()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        loadUi('Cryostat GUI.ui', self)
        # self.setupUi(self)
        self.threads = dict()
        self.data = dict()

        # initialize ITC Window
        self.ITC_ui = Ui_ITCcontrol()
        self.ITC_ui.setupUi(self.ITC_window)

        # worker = main_Worker()
        # thread = QThread()
        # self.threads['mainworker'] = (worker, thread)
        # worker.moveToThread(thread)
        # thread.started.connect(worker.work)
        # thread.start()

        self.action_run_ITC.triggered['bool'].connect(self.run_ITC)
        self.action_show_ITC.triggered['bool'].connect(self.show_ITC)

        # self.action_run_ITC.triggered['bool'].connect(self.threads['mainworker'][0].printing)

    @pyqtSlot(bool)
    def run_ITC(self, boolean):
        """method to start/stop the thread which controls the Oxford ITC"""

        if boolean:
            try:
                ITC = itc503('COM6')
                getInfodata = cls_itc(ITC)
                thread = QThread()
                self.threads['control_ITC'] = (getInfodata, thread)
                getInfodata.moveToThread(thread)
                if 'ITC' in self.data: 
                    pass
                else: 
                    self.data['ITC'] = list()

                getInfodata.sig_Infodata.connect(self.store_data_itc)
                getInfodata.sig_visaerror.connect(self.printing)

                thread.started.connect(getInfodata.work)
                thread.start()
                self.action_run_ITC.setChecked(True)
            except VisaIOError as e:
                self.action_run_ITC.setChecked(False)
                print(e) # open window displaying the error message

        else:
            self.action_run_ITC.setChecked(False)
            # possibly implement putting the instrument back to local operation
            self.threads['control_ITC'][1].quit()
            self.threads['control_ITC'][1].wait()


    def store_data_itc(self, data):
        """method to store ITC data in a central place"""
        self.data['ITC'].append(data.update(dict(time=convert_time(time.time()))))
        # self.ITC_ui.lcdTemp.display(self.data['ITC'][-1]['sensor_1_temperature'])


    # def test(self):
    #     while True: 
    #         time.sleep(1)
    #         if 'ITC' in self.data: print(self.data['ITC'])

    def show_ITC(self, boolean):
        """method which will eventually display the ITC window, one way or another
            (e.g. through a subwindow, or in a separate thread...)

        """

        if boolean:
            self.ITC_window.show()
            self.ITC_showing = True
            # self.threads['control_ITC'][0].sig_Infodata.connect()
        else:
            self.ITC_window.close()
            self.ITC_showing = False

    def printing(self,b):
        """arbitrary exmple function"""
        print(b)




def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = mainWindow()
    form.show()
    sys.exit(app.exec_())

