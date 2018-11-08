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

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

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

    @pyqtSlot()  # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        # while self.__isRunning:
        try:
            self.running()
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

    def running(self):
        """class method to be overrriden """
        raise NotImplementedError

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

    def __init__(self, ui_file=None, parent=None, **kwargs):
        super().__init__(**kwargs)
        if ui_file is not None:
            loadUi(ui_file, self)

    def closeEvent(self, event):
        # do stuff
        self.sig_closing.emit()
        event.accept() # let the window close


# class sequence_listwidget(QtWidgets.QListWidget):
#     """docstring for Sequence_ListWidget"""
#     sig_dropped = pyqtSignal()

#     def __init__(self, **kwargs):
#         super(sequence_listwidget, self).__init__(**kwargs)

#     def dropEvent(self, event):
#         self.sig_dropped.emit(event)
#         event.accept()


class Window_plotting(QtWidgets.QDialog, Window_ui):
    """Small window containing a plot, which can be udpated every so often"""
    sig_closing = pyqtSignal()

    def __init__(self, data, label_x, label_y, title, parent=None):
        super().__init__()
        self.data = data
        self.label_x = label_x
        self.label_y = label_y
        self.title = title

        # a figure instance to plot on
        self.figure = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Just some button connected to `plot` method
        # self.button = QtWidgets.QPushButton('Plot')
        # self.button.clicked.connect(self.plot)

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        # layout.addWidget(self.button)
        self.setLayout(layout)
        self.lines = []
        self.plot_base()

        self.plot()

    def plot_base(self):
        self.ax = self.figure.add_subplot(111)

        self.ax.set_title(self.title)
        self.ax.set_xlabel(self.label_x)
        self.ax.set_ylabel(self.label_y)

        # discards the old graph
        if not isinstance(self.data, list):
            self.data = [self.data]
        self.ax.clear()
        for entry in self.data:
            self.lines.append(self.ax.plot(entry[0], entry[1], '*-')[0])

    def plot(self):
        ''' plot some not so random stuff '''
        # create an axis

        for ct, entry in enumerate(self.data):
            self.lines[ct].set_xdata(entry[0])
            self.lines[ct].set_ydata(entry[1])

        self.ax.relim()
        self.ax.autoscale_view()


        # refresh canvas
        self.canvas.draw()
        QTimer.singleShot(3*1e3, self.plot)
