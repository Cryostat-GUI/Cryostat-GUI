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

import functools
import inspect
from datetime import datetime
import time
from visa import VisaIOError
import numpy as np

from contextlib import suppress
from copy import deepcopy

from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtWidgets
from PyQt5.uic import loadUi


def convert_time_date(ts):
    """converts timestamps from time.time() into date string"""
    return datetime.fromtimestamp(ts).strftime('%d%m%Y')


def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def convert_time_searchable(ts):
    """converts timestamps from time.time() into reasonably searchable string format"""
    return datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M%S')


def loopcontrol_threads(threads, loopcondition):
    """
        temporarily turn off the loop function of
        an AbstractLoopThread class instance
    """
    for thread in threads:
        with suppress(AttributeError):  # eventhandlingThread somewhere....
            while bool(thread[0].loop) is bool(loopcondition):
                time.sleep(0.2)  # wait
            thread[0].loop = loopcondition


def shaping(entry):
    ent0 = deepcopy(np.array(entry[0]))
    ent1 = deepcopy(np.array(entry[1]))
    if ent0.shape > ent1.shape:
        # print('bad shape: ', ent0.shape, ent1.shape, self.legend[ct])
        ent0 = ent0[:len(ent1)]
        # print('corrected: ', ent0.shape, ent1.shape)
    elif ent0.shape < ent1.shape:
        # print('bad shape: ', ent0.shape, ent1.shape, self.legend[ct])
        ent1 = ent1[:len(ent0)]
        # print('corrected: ', ent0.shape, ent1.shape)
    return ent0, ent1


class dummy:
    """docstring for dummy"""
    def __init__(self):
        pass

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self, *args, **kwargs):
        pass


class loops_off:
    """Context manager for disabling all AbstractLoopThread loops"""

    def __init__(self, threads):
        self._threads = threads

    def __enter__(self, *args, **kwargs):
        loopcontrol_threads(self._threads, False)
        time.sleep(0.1)

    def __exit__(self, *args, **kwargs):
        loopcontrol_threads(self._threads, True)


class controls_software_disabled:
    """Context manager for disabling all controls in GUI"""

    def __init__(self, controls, lock):
        self._controls = controls
        self._lock = lock

    def __enter__(self, *args, **kwargs):
        self._lock.acquire()
        for control in self._controls:
            control.setEnabled(False)

    def __exit__(self, *args, **kwargs):
        for control in self._controls:
            control.setEnabled(True)
        self._lock.release()


class controls_hardware_disabled:
    """Context manager for disabling all Front panel controls
        on instruments
    """

    def __init__(self, threads, lock):
        self._lock = lock
        self._threads = threads

    def __enter__(self, *args, **kwargs):
        self._lock.acquire()
        for thread in self._threads:
            self._threads[thread][0].toggle_frontpanel(False)

    def __exit__(self, *args, **kwargs):
        for thread in self._threads:
            self._threads[thread][0].toggle_frontpanel(True)
        self._lock.release()


def ExceptionHandling(func):
    @functools.wraps(func)
    def wrapper_ExceptionHandling(*args, **kwargs):
        if inspect.isclass(type(args[0])):
            try:
                return func(*args, **kwargs)
            except AssertionError as e_ass:
                args[0].sig_assertion.emit('{}: {}: {}: {}'.format(
                    args[0].__name__,
                    func.__name__,
                    'Assertion',
                    e_ass.args[0]))
            except TypeError as e_type:
                args[0].sig_assertion.emit('{}: {}: {}: {}'.format(
                    args[0].__name__,
                    func.__name__,
                    'Type',
                    e_type.args[0]))
            except KeyError as e_key:
                args[0].sig_assertion.emit('{}: {}: {}: {}'.format(
                    args[0].__name__,
                    func.__name__,
                    'Key',
                    e_key.args[0]))
            except ValueError as e_val:
                args[0].sig_assertion.emit('{}: {}: {}: {}'.format(
                    args[0].__name__,
                    func.__name__,
                    'Value',
                    e_val.args[0]))
            except AttributeError as e_attr:
                args[0].sig_assertion.emit('{}: {}: {}: {}'.format(
                    args[0].__name__,
                    func.__name__,
                    'Attribute',
                    e_attr.args[0]))
            except NotImplementedError as e_implement:
                args[0].sig_assertion.emit('{}: {}: {}: {}'.format(
                    args[0].__name__, func.__name__,
                    'NotImplemented',
                    e_implement.args[0]))
            except VisaIOError as e_visa:
                if isinstance(e_visa, type(args[0].timeouterror)) and e_visa.args == args[0].timeouterror.args:
                    args[0].sig_visatimeout.emit()
                else:
                    args[0].sig_visaerror.emit('{}: {}: {}: {}'.format(
                        args[0].__name__,
                        func.__name__,
                        'VisaIO',
                        e_visa.args[0]))
        else:
            print('There is a bug!! ' + func.__name__)
    return wrapper_ExceptionHandling


class AbstractThread(QObject):
    """Abstract thread class to be used with instruments """

    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)
    sig_Infodata = pyqtSignal(dict)

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
        self.interval = 0.5  # second
        # self.__isRunning = True
        self.loop = True

    @pyqtSlot()  # int
    # @ExceptionHandling  # this is being done with all functions again, still...
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
            QTimer.singleShot(self.interval * 1e3, self.work)

    def running(self):
        """class method to be overriden """
        raise NotImplementedError

    @pyqtSlot(float)
    def setInterval(self, interval):
        """set the interval between running events in seconds"""
        self.interval = interval

    # @pyqtSlot()
    # def looping(self, loop):
    #     """start/stop the loop execution, by setting the bool self._loop"""
    #     self._loop = loop


class AbstractEventhandlingThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 500

    @pyqtSlot()
    def work(self):
        """class method which is here so something runs, and starting behaviour is not broken
        """
        try:
            self.running()
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval * 1e3, self.work)

    def running(self):
        """empty method to keep thread alive (there is surely a better solution) """
        pass


class Workerclass(QObject):
    """tiny class for performing one single task ()"""
    def __init__(self, workfunction, *args, **kwargs):
        super(Workerclass, self).__init__()
        self.workfunction = workfunction
        self.args = args
        self.kwargs = kwargs

    def work(self):
        self.workfunction(*self.args, **self.kwargs)
        

class Window_ui(QtWidgets.QWidget):
    """Class for a small window, the UI of which is loaded from the .ui file
        emits a signal when being closed
    """

    sig_closing = pyqtSignal()

    def __init__(self, ui_file=None, **kwargs):
        super().__init__(**kwargs)
        if ui_file is not None:
            loadUi(ui_file, self)

    def closeEvent(self, event):
        # do stuff
        self.sig_closing.emit()
        event.accept()  # let the window close


class Window_plotting(QtWidgets.QDialog, Window_ui):
    """Small window containing a plot, which can be udpated every so often"""
    sig_closing = pyqtSignal()

    def __init__(self, data, label_x, label_y, legend_labels, number, title='your advertisment could be here!', **kwargs):
        super().__init__()
        self.data = data
        self.label_x = label_x
        self.label_y = label_y
        self.title = title
        self.legend = legend_labels
        self.number = number
        if 'lock' in kwargs:
            self.lock = kwargs['lock']
        else:
            self.lock = dummy()

        self.interval = 2

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
        # create an axis
        self.ax = self.figure.add_subplot(111)

        self.ax.set_title(self.title)
        self.ax.set_xlabel(self.label_x)
        self.ax.set_ylabel(self.label_y)

        # discards the old graph
        if not isinstance(self.data, list):
            self.data = [self.data]
        self.ax.clear()
        # print(self.data)
        with self.lock:
            for entry, label in zip(self.data, self.legend):
                ent0, ent1 = shaping(entry)
                self.lines.append(self.ax.plot(
                    ent0, ent1, '*-', label=label)[0])
        self.ax.legend()

    def plot(self):
        ''' plot some not so random stuff '''
        try:
            with self.lock:
                for ct, entry in enumerate(self.data):
                    ent0, ent1 = shaping(entry)
                    self.lines[ct].set_xdata(ent0)
                    self.lines[ct].set_ydata(ent1)

            self.ax.relim()
            self.ax.autoscale_view()

            # refresh canvas
            self.canvas.draw()
        except ValueError as e_val:
            print('ValueError: ', e_val.args[0])
            # for x in self.data:
                # print(x)
        finally:
            QTimer.singleShot(self.interval * 1e3, self.plot)

    # def closeEvent(self, event):
    #     super().closeEvent(event)
    #     del self
