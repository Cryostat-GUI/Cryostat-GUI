"""
Utility module for the Cryostat GUI


Classes:
    AbstractThread: a class which sets up QT's QThread instance, as well as the assertion signal

    AbstractLoopThread: a thread-class, inheriting from AbstractThread,
        which implements Thread-Loop behaviour, continuously running the class method self.running

    AbstractEventhandlingThread: a thread class, inheriting from AbstractThread,
        which is designed to be used for handling signal-events, not continuous loops

    Window_ui: a window class, which loads the UI definitions from a spcified .ui file,
        emits a signal upon closing
"""







from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi


class AbstractThread(QObject):
    """Abstract thread class to be used with instruments """

    sig_assertion = pyqtSignal(str)

    def __init__(self):
        QThread.__init__(self)

    @pyqtSlot()
    def work(self):
        """class method which is usually started when starting the thread. """
        raise NotImplementedError

    def running(self):
        """class method to be overriden """
        raise NotImplementedError


class AbstractLoopThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 2 # second
        # self.__isRunning = True
        self.loop = True

    @pyqtSlot()  # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        # while self.__isRunning:
        try:
            if self.loop:
                self.running()
            else:
                pass
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval*1e3, self.work)

    def running(self):
        """class method to be overriden """
        raise NotImplementedError


    @pyqtSlot(float)
    def setInterval(self, interval):
        """set the interval between running events in seconds"""
        self.interval = interval



    # @pyqtSlot()
    # def stop(self):
    #     """stop the loop execution, sets self.__isRunning to False"""
    #     self.__isRunning = False


class AbstractEventhandlingThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    @pyqtSlot() # int
    def work(self):
        """class method which is here so something runs, and starting behaviour is not broken
        """
        # while self.__isRunning:
        try:
            self.running()
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval*1e3, self.work)

    def running(self):
        """class method to be overrriden """
        pass
        # raise NotImplementedError

    @pyqtSlot()
    def stop(self):
        """just here so stopping the thread can be done as with all others
            can be overriden for "last second actions"
        """
        pass


class Window_ui(QtWidgets.QWidget):
    """Class for a small window, the UI of which is loaded from the .ui file
        emits a signal when being closed
    """

    sig_closing = pyqtSignal()

    def __init__(self, ui_file=None, parent=None,**kwargs):
        super().__init__(**kwargs)
        loadUi(ui_file, self)

    def closeEvent(self, event):
        # do stuff
        self.sig_closing.emit()
        event.accept() # let the window close



class sequence_listwidget(QtWidgets.QListWidget):
    """docstring for Sequence_ListWidget"""
    sig_dropped = pyqtSignal()
    def __init__(self, **kwargs):
        super(Sequence_ListWidget, self).__init__(**kwargs)

    def dropEvent(self, event):
        self.sig_dropped.emit(event)
        event.accept()


def calculate_resistance(Voltage, Current):
    return (Voltage*(10**9)/Current)


