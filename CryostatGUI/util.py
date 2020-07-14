"""
Utility module for the Cryostat-GUI


Classes:
    AbstractThread: a class which sets up QT's QThread instance, as well as the assertion signal

    AbstractLoopThread: a thread-class, inheriting from AbstractThread,
        which implements Thread-Loop behaviour, continuously running the class method self.running

    AbstractEventhandlingThread: a thread class, inheriting from AbstractThread,
        which is designed to be used for handling signal-events, not continuous loops

    Window_ui: a window class, which loads the UI definitions from a specified .ui file,
        emits a signal upon closing

    Window_plotting: a window class, which enables an unsuspecting user to
        plot data, with continuous updates to the plot

Author(s):
    bklebel (Benjamin Klebel)
"""

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec


import functools
# import inspect
import sys
import time
import numpy as np
import json
import os
import logging


# from contextlib import suppress
from copy import deepcopy
from datetime import datetime as dt
from datetime import timedelta as td
from visa import VisaIOError
from threading import Lock

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot

from PyQt5 import QtCore
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QSizePolicy

from zmqcomms import zmqClient
# from zmqcomms import enc

from loggingFunctionality.sqlBaseFunctions import SQLiteHandler


logger = logging.getLogger('CryostatGUI.utility')


class BlockedError(Exception):
    pass


def convert_time_date(ts):
    """converts timestamps from time.time() into date string"""
    return dt.fromtimestamp(ts).strftime('%d%m%Y')


def convert_time(ts):
    """converts timestamps from time.time() into reasonable string format"""
    return dt.fromtimestamp(ts).strftime('%Y-%m-%d::%H:%M:%S')


def convert_time_reverse(tstr):
    """convert time-string into datetime object"""
    return dt.strptime(tstr, '%Y-%m-%d::%H:%M:%S')


def convert_time_searchable(ts):
    """converts timestamps from time.time() into reasonably searchable string format"""
    return dt.fromtimestamp(ts).strftime('%Y%m%d%H%M%S')


def convert_time_searchable_reverse(tstr):
    """convert the time string into datetime object"""
    return dt.strptime(tstr, '%Y%m%d%H%M%S')


def convert_time_realtime_reverse(tstr):
    """convert the realtime entry in the database back to a datetime object
    Timezones are for now ignored, apart from the note in the database entry"""
    # var = 'UTC' + '{:+05.0f} '.format(self.houroffset) + var.strftime('%Y-%m-%d  %H:%M:%S.%f')
    utcoffset = td(hours=float(tstr[3:8]))
    var = dt.strptime(tstr[8:], '%Y-%m-%d  %H:%M:%S.%f')
    return var
    pass


def shaping(entry):
    """adjust the shape of data-arrays given to matplotlib,
        to prevent mismatches
        possibly this could be avoided with intelligent use of 'zip'
    """
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

    # ent0, ent1 = zip(entry)
    return ent0, ent1


def shaping_m(entry):
    """adjust the shape of data-arrays given to matplotlib,
        to prevent mismatches
        possibly this could be avoided with intelligent use of 'zip'
    """
    ent = [deepcopy(np.array(entry[i])) for i in range(len(entry))]

    # ent0 = deepcopy(np.array(entry[0]))
    # ent1 = deepcopy(np.array(entry[1]))
    for i in range(len(entry)):

        if ent[i].shape > ent[i - 1].shape:
            # print('bad shape: ', ent0.shape, ent1.shape, self.legend[ct])
            ent[i - 1] = ent[i - 1][:len(ent[i])]
            # print('corrected: ', ent0.shape, ent1.shape)
        elif ent[i].shape < ent[i - 1].shape:
            # print('bad shape: ', ent0.shape, ent1.shape, self.legend[ct])
            ent[i] = ent[i][:len(ent[i - 1])]
            # print('corrected: ', ent0.shape, ent1.shape)

    return tuple(ent)


def running_thread(worker, info=None, **kwargs):
    """Set up a new Thread, and insert the worker class, which runs in the new thread
        Args:
            worker - the class (as a class instance) which should run inside
            dataname - the name for which a dict entry should be made in the self.data dict,
                    in case the Thread is passing data (e.g. sensors, instrument status...)
            threadname - the name as which the thread will be listed in self.threads,
                    to be used for e.g. signals
                    listing the thread in self.threads is also important to protect it
                    from garbage collection!
        Returns:
            the worker class instance, useful for connecting signals directly
    """

    thread = QThread()
    worker.moveToThread(thread)

    thread.started.connect(worker.work)
    thread.start()
    return worker, thread


def ExceptionSignal(thread, func, e_type, err):
    """Emit assertion-signal with relevant information"""
    string = '{}: {}: {}: {}'.format(
        thread.__name__,
        func.__name__,
        e_type,
        err.args[0])

    # thread.sig_assertion.emit(string)
    return string


def ExceptionHandling(func):

    @functools.wraps(func)
    def wrapper_ExceptionHandling(*args, **kwargs):
        # if inspect.isclass(type(args[0])):
        # thread = args[0]
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            s = ExceptionSignal(args[0], func, 'Assertion', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)

        except TypeError as e:
            s = ExceptionSignal(args[0], func, 'Type', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)

        except KeyError as e:
            s = ExceptionSignal(args[0], func, 'Key', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)

        except IndexError as e:
            s = ExceptionSignal(args[0], func, 'Index', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)

        except ValueError as e:
            s = ExceptionSignal(args[0], func, 'Value', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)

        except AttributeError as e:
            s = ExceptionSignal(args[0], func, 'Attribute', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)

        except NotImplementedError as e:
            s = ExceptionSignal(args[0], func, 'NotImplemented', e)
            # thread.logger.exception(s)
            args[0].logger.exception(s)
            # e.args = [str(e)]

        except VisaIOError as e:
            if isinstance(e, type(args[0].timeouterror)) and \
                    e.args == args[0].timeouterror.args:
                args[0].sig_visatimeout.emit()
            else:
                s = ExceptionSignal(args[0], func, 'VisaIO', e)
                # thread.logger.exception(s)
                args[0].logger.exception(s)

        except OSError as e:
            s = ExceptionSignal(args[0], func, 'OSError', e)
            args[0].logger.exception(e)
        # else:
        #     logger.warning('There is a bug!! ' + func.__name__)
    return wrapper_ExceptionHandling


def noKeyError(func):
    @functools.wraps(func)
    def wrapper_noKeyError(*args, **kwargs):
        # if inspect.isclass(type(args[0])):
        try:
            return func(*args, **kwargs)

        except KeyError:
            pass
    return wrapper_noKeyError


def readPID_fromFile(filename):
    """read PID values from file"""
    arr = np.loadtxt(filename)
    list_T = arr[:, 0]
    listPID = [dict(p=arr[x, 1], i=arr[x, 2], d=arr[x, 3])
               for x in range(arr.shape[0])]
    return list_T, listPID


class dummy:
    """dummy context manager doing nothing at all"""

    def __init__(self):
        pass

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self, *args, **kwargs):
        pass


class loops_off:
    """Context manager for disabling all AbstractLoopThread loops"""

    def __init__(self, threads):
        self._threads = [threads[thread][0] for thread in threads.keys()
                         if not isinstance(threads[thread], type(Lock())) and
                         'control' not in thread]
        self.lock = threads['Lock']

    def __enter__(self, *args, **kwargs):
        self.lock.acquire()
        for thread in self._threads:
            thread.lock.acquire()
        # loopcontrol_threads(self._threads, False)
        # time.sleep(0.1)

    def __exit__(self, *args, **kwargs):
        # loopcontrol_threads(self._threads, True)
        self.lock.release()
        for thread in self._threads:
            thread.lock.release()


class noblockLock(object):
    """docstring for noblockLock"""

    def __init__(self, lock):
        super().__init__()
        self._lock = lock

    def __enter__(self, *args, **kwargs):
        if not self._lock.acquire(blocking=False):
            raise BlockedError

    def __exit__(self, *args, **kwargs):
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


class AbstractApp(QtWidgets.QMainWindow):
    """docstring for AbstractApp"""

    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)
    sig_Infodata = pyqtSignal(dict)

    def __init__(self, ui_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        if ui_file is not None:
            loadUi(ui_file, self)


class AbstractLoopApp(AbstractApp):
    """Abstract application class to be used with instruments 

    this needs to be used in conjunction with a zmqClass!
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 0.5  # second
        self.lock = Lock()

        QTimer.singleShot(0, self.work)

    @pyqtSlot()  # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        try:
            self.zmq_handle()  # inherited later from zmqClient
            with noblockLock(self.lock):
                self.running()
                self.send_data_upstream()
        except BlockedError:
            pass
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval * 1e3, self.work)

    def running(self):
        """class method to be overriden for periodic tasks"""
        raise NotImplementedError

    @pyqtSlot(float)
    def setInterval(self, interval):
        """set the interval between running events in seconds"""
        self.interval = interval


class AbstractMainApp(AbstractApp):
    """docstring for AbstractMainApp"""
    data = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.softwarecontrol_timer = QTimer()
        self.softwarecontrol_timer.timeout.connect(self.softwarecontrol_check)
        self.softwarecontrol_timer.start(100)

    def setup_logging_base(self):
        self.logger_all = logging.getLogger()
        self.logger_personal = logging.getLogger('CryostatGUI.main')

        self.Log_DBhandler = SQLiteHandler(
            db='Errors\\' + dt.datetime.now().strftime('%Y%m%d') + '_dblog.db')
        self.Log_DBhandler.setLevel(logging.DEBUG)

        self.logger_personal.setLevel(logging.DEBUG)
        self.logger_all.setLevel(logging.ERROR)
        # self.logger_personal.addHandler(self.Log_DBhandler)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger_personal.addHandler(handler)
        self.logger_all.addHandler(handler)

    def setup_logging(self):
        """set up the logger, handler, for now in DEBUG
        TODO: connect logging levels with GUI preferences"""

        self.logger_all.setLevel(logging.INFO)

        self.logger_all.addHandler(self.Log_DBhandler)

    # def load_settings(self):
    #     """load all settings store in the QSettings
    #     set corresponding values in the 'Global Settings' window"""
    #     settings = QSettings("TUW", "CryostatGUI")
    #     try:
    #         self.window_settings.temp_ITC_useAutoPID = bool(
    #             settings.value('ITC_useAutoPID', int))
    #         self.window_settings.temp_ITC_PIDFile = settings.value(
    #             'ITC_PIDFile', str)
    #     except KeyError as e:
    #         QTimer.singleShot(20 * 1e3, self.load_settings)
    #         self.show_error_general(f'could not find a key: {e}')
    #         self.logger_personal.warning(f'key {e} was not found in the settings')
    #     del settings

    #     self.window_settings.checkUseAuto.setChecked(
    #         self.window_settings.temp_ITC_useAutoPID)
    #     if isinstance(self.window_settings.temp_ITC_PIDFile, str):
    #         text = self.window_settings.temp_ITC_PIDFile
    #     else:
    #         text = ''
    #     self.window_settings.lineConfFile.setText(text)

    def softwarecontrol_toggle_locking(self, value):
        """acquire/release the controls Lock
        this is used to control the disabling/enabling of GUI elements,
        in case of a running sequence/measurement"""
        if value:
            self.controls_Lock.acquire()
        else:
            self.controls_Lock.release()

    def softwarecontrol_check(self):
        """disable all respective GUI elements in case
            the controls_lock is locked
            thus prevent interference of the user
                with a running sequence/measurement
        """
        # try:
        if self.controls_Lock.locked():
            for c in self.controls:
                c.setEnabled(False)
        else:
            for c in self.controls:
                c.setEnabled(True)

    def running_thread_control(self, worker, threadname, **kwargs):
        """
            run a specified worker class in a thread
                this should be a device controlling thread
            add a corresponding entry in the data dictionary
            add the thread and worker-class instances to the threads dictionary

            return: the worker-class instance
        """
        worker, thread = running_thread(worker)

        with self.threads['Lock']:
            # this needs to be locked when a new thread is added, as otherwise
            # the thread locking context manager would try to unlock the new thread
            # before it was ever locked, resulting in a crash
            #
            # threads need to be saved somewhere, since otherwise garbage collection
            # will throw them away, they die
            self.threads[threadname] = (worker, thread)

        return worker


class AbstractLoopClient(AbstractLoopApp, zmqClient):
    """docstring for AbstractLoopClient"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AbstractThread(QObject):
    """Abstract thread class to be used with instruments """

    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)
    sig_Infodata = pyqtSignal(dict)

    def __init__(self, **kwargs):
        QThread.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

    @pyqtSlot()
    def work(self):
        """class method which is usually started when starting the thread. """
        raise NotImplementedError

    def running(self):
        """class method to be overriden """
        raise NotImplementedError


class AbstractLoopThread_old(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 0.5  # second
        # self.__isRunning = True
        self.loop = True
        self.lock = Lock()

    @pyqtSlot()  # int
    # @ExceptionHandling  # this is being done with all functions again, still...
    def work(self):
        """class method which is working all the time while the thread is running. """
        # while self.__isRunning:
        try:

            while not self.loop:
                time.sleep(0.05)
            with self.lock:
                self.running()

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


class AbstractLoopThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 0.5  # second
        # self.__isRunning = True
        self.loop = True
        self.lock = Lock()

    @pyqtSlot()  # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        try:
            self.zmq_handle()  # inherited later from zmqClient
            with noblockLock(self.lock):
                self.running()
                self.send_data_upstream()
        except BlockedError:
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


class AbstractLoopThreadClient(AbstractLoopThread, zmqClient):
    """docstring for AbstractLoopThreadClient"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AbstractEventhandlingThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 500
        self.lock = Lock()

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
        super().__init__(**kwargs)
        self.workfunction = workfunction
        self.args = args
        self.kwargs = kwargs
        self.logger = logging.getLogger(__name__)

    def work(self):
        """run the passed function"""
        self.workfunction(*self.args, **self.kwargs)


class Window_ui(QtWidgets.QWidget):
    """Class for a small window, the UI of which is loaded from the .ui file

    emits a signal when being closed
    """

    sig_closing = pyqtSignal()
    sig_error = pyqtSignal(str)

    def __init__(self, ui_file=None, **kwargs):
        self.logger = logging.getLogger(__name__)
        if 'lock' in kwargs:
            del kwargs['lock']
        super().__init__(**kwargs)
        if ui_file is not None:
            loadUi(ui_file, self)
        self.setWindowIcon(QtGui.QIcon('TU-Signet.png'))

    def closeEvent(self, event):
        """emit signal that the window is going to be closed and hand event to parent class method"""
        self.sig_closing.emit()
        # event.accept()  # let the window close
        super().closeEvent(event)


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):

    def __init__(self, icon, parent=None):
        super(SystemTrayIcon, self).__init__(icon, parent)
        parent.pyqt_trayMenu = QtWidgets.QMenu(parent)
        exitAction = parent.pyqt_trayMenu.addAction("Exit")
        exitAction.triggered.connect(parent.close)
        self.setContextMenu(parent.pyqt_trayMenu)


class Window_trayService_ui(QtWidgets.QWidget):
    """Class for a small window, the UI of which is loaded from the .ui file

    emits a signal when being closed
    """

    sig_closing = pyqtSignal()
    sig_error = pyqtSignal(str)

    def __init__(self, ui_file=None, Name=None, **kwargs):
        self.logger = logging.getLogger(__name__)
        super().__init__(**kwargs)

        icon = QtGui.QIcon('./../TU-Signet.png')
        self.pyqt_sysTray = SystemTrayIcon(icon, self)
        self.setWindowIcon(QtGui.QIcon(icon))

        self.pyqt_sysTray.activated.connect(self.restore_window)
        if Name is not None:
            self.pyqt_sysTray.setToolTip(u'{}'.format(Name))
            self.setToolTipDuration(-1)
            self.setWindowTitle(Name)

        QTimer.singleShot(0, self.initialise_minimized)

    def initialise_minimized(self):
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.Tool)
        self.pyqt_sysTray.show()
        self.hide()

    def event(self, event):
        if (event.type() == QtCore.QEvent.WindowStateChange and
                self.isMinimized()):
            # take out of taskbar
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.Tool)
            self.pyqt_sysTray.show()
            return True
        else:
            return super().event(event)

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(
            self,
            'Message', "Are you sure to quit this application?\n\n" +
            "'Yes'    will kill me (if I am a service, I might restart immediately)\n" +
            "'No'     will minimize me to the Tray\n" +
            "'Cancel' will do....nothing",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Cancel)

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        elif reply == QtWidgets.QMessageBox.Cancel:
            event.ignore()
        else:
            self.pyqt_sysTray.show()
            self.hide()
            event.ignore()

    def restore_window(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.pyqt_sysTray.hide()
            self.showNormal()


class Window_plotting_m(Window_ui):
    """Small window containing a plot, which updates itself regularly"""
    sig_closing = pyqtSignal()

    def __init__(self, data, labels_x, labels_y, legend_labels, number, title='your advertisment could be here!', multiple=False, updateinterval=2, linestyle='*-', navtoolbar=False, **kwargs):
        """storing data, building the window layout, starting timer to update"""
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.data = data
        self.labels_x = labels_x
        self.labels_y = labels_y
        self.title = title
        self.legend = legend_labels
        self.linestyle = linestyle

        self.number = number
        if 'lock' in kwargs:
            self.lock = kwargs['lock']
        else:
            self.lock = dummy()

        self.interval = updateinterval

        # a figure instance to plot on
        self.fig = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.fig)

        FigureCanvas.setSizePolicy(self.canvas,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self.canvas)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        if navtoolbar:
            self.toolbar = NavigationToolbar(self.canvas, self)

        # self.setGeometry(100, 100, 800, 600)

        # set the layout
        layout = QtWidgets.QGridLayout()
        # layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        # layout.addWidget(self.button)
        self.setLayout(layout)
        self.lines = []
        if not multiple:
            self.plot_base_single()
        else:
            self.plot_base_multiple()

        self.timer = QTimer()
        self.timer.timeout.connect(self.plot)
        self.timer.start(self.interval * 1e3)

    def plot_base_single(self):
        """create the first plot"""

        self.ax = self.fig.add_subplot(111)
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

    def plot_base_multiple(self):
        """create the first plot"""
        n = len(self.data)
        if n != len(self.legend):
            raise AssertionError('number of plots and legends mismatches!')

        # self.axes = self.fig.subplots(nrows=n, ncols=1)
        # if not isinstance(self.axes, type(np.zeros(1))):
        #     self.axes = [self.axes]
        # self.fig.canvas.set_window_title(self.title)

        self.axes = []
        self.subplotgrid = gridspec.GridSpec(n, 1)
        for i in range(n):
            self.axes.append(self.fig.add_subplot(self.subplotgrid[i]))

        with self.lock:
            for ct, entry in enumerate(zip(self.data, self.legend, self.labels_x, self.labels_y)):
                data = entry[0]
                if not isinstance(data, list):
                    data = [data]
                legend = entry[1]
                label_x = entry[2]
                label_y = entry[3]
                self.lines.append([])
                self.axes[ct].set_xlabel(label_x)
                self.axes[ct].set_ylabel(label_y)
                # print(data)
                for curve, label in zip(data, legend):
                    c1, c2 = shaping(curve)
                    # print(c)
                    self.lines[-1].append(self.axes[ct].plot(
                        c1, c2, self.linestyle, label=label)[0])
                self.axes[ct].legend()
        # plt.tight_layout(w_pad=10, pad=5)
        self.subplotgrid.tight_layout(self.fig)

        # discards the old graph

        # self.ax.clear()
        # print(self.data)
        # with self.lock:
        #     for entry, label in zip(self.data, self.legend):
        #         ent0, ent1 = shaping(entry)
        #         self.lines.append(self.ax.plot(
        #             ent0, ent1, '*-', label=label)[0])
        # self.ax.legend()

    def plot(self):
        ''' update the plotted data in-place '''
        try:
            with self.lock:
                for axindex, entry_data in enumerate(self.data):
                    for cindex, curve in enumerate(entry_data):
                        c1, c2 = shaping(curve)
                        self.lines[axindex][cindex].set_xdata(c1)
                        self.lines[axindex][cindex].set_ydata(c2)
                    self.axes[axindex].relim()
                    self.axes[axindex].autoscale_view()
            self.canvas.draw_idle()
        except ValueError as e_val:
            print('ValueError: ', e_val.args[0])
        # FigureCanvas.updateGeometry(self.canvas)

    def closeEvent(self, event):
        """stop the timer for updating the plot, super to parent class method"""
        self.timer.stop()
        super().closeEvent(event)
    #     del self


class Window_plotting_specification(Window_ui):
    """docstring for Window_plotting_specification"""
    sig_plotnow = pyqtSignal()
    sig_success = pyqtSignal()

    def __init__(self, mainthread, ui_file='.\\configurations\\Data_display_selection_live_multiple.ui', **kwargs):
        super().__init__(ui_file, **kwargs)
        self.logger = logging.getLogger(__name__)

        self.ui_file_plotselection = '.\\configurations\\Data_display_selection_presetempty.ui'
        self.presets_path = './configurations/plotting_presets/'

        self.selection = []
        self.mainthread = mainthread

        self.axesnames = ['X', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5']

        if not hasattr(mainthread, "data_live"):
            self.sig_error.emit('no live data to plot!')

            self.sig_error.emit(
                'If you want to see live data, start the live logger!')
            logger.warning('no live data to plot!')
            self.close()
            return
        self.show()

        self.tablist = []
        self.pushAddPlot.clicked.connect(self.adding_selectiontab)
        self.adding_selectiontab()

        self.lineEdit_savingpreset.textEdited.connect(self.store_filenamevalue)
        self.lineEdit_savingpreset.returnPressed.connect(self.saving)
        self.combo_loadingpreset.activated[
            'QString'].connect(self.restoring_preset)

        self.parse_presets()

        # self.combo_loadingpreset.currentIndexChanged[
        #     'QString'].connect(self.restoring_preset)

        self.buttonBox.clicked.connect(self.displaying)

        self.sig_success.connect(self.close)
        self.buttonCancel.clicked.connect(self.close)

    def store_filenamevalue(self, value):
        '''store a filename for future use when saving a preset'''
        self.filenamevalue = value

    def saving(self):
        '''save the current configuration (self.selection) as a preset'''
        with open('.\\configurations\\plotting_presets\\{}.json'.format(self.filenamevalue), 'w') as output:
            output.write(json.dumps(self.selection))

    def restoring_preset(self, filename):
        '''restore a preset from a json file'''
        if filename == '-':
            return
        filename = os.path.join(self.presets_path, str(filename) + '.json')
        # print(filename)
        try:
            with open(filename) as f:
                self.selection_int = json.load(f)
        except FileNotFoundError:
            self.sig_error.emit(f'Plotting: The preset file you wanted ({filename}) was not found!')
            logger.warning(f'The preset file you wanted ({filename}) was not found!')
            return
        # print(len(self.selection_int))
        self.tablist = []
        self.tabW_selection.clear()

        for plot_entry in self.selection_int:
            # print('adding a tab')
            self.adding_selectiontab()
            # print('added a tab')
            tabw = self.tablist[-1]

            instrumentGUI = [tabw.comboInstr_X, tabw.comboInstr_Y1, tabw.comboInstr_Y2,
                             tabw.comboInstr_Y3, tabw.comboInstr_Y4, tabw.comboInstr_Y5]
            valueGUI = [tabw.comboValue_X, tabw.comboValue_Y1, tabw.comboValue_Y2,
                        tabw.comboValue_Y3, tabw.comboValue_Y4, tabw.comboInstr_Y5]

            for inst, value, axname in zip(instrumentGUI, valueGUI, self.axesnames):
                try:
                    index1 = inst.findText(
                        plot_entry[axname]['instrument'], QtCore.Qt.MatchFixedString)
                    if index1 >= 0:
                        inst.setCurrentIndex(index1)
                    index2 = value.findText(
                        plot_entry[axname]['value'], QtCore.Qt.MatchFixedString)

                    if index2 >= 0:
                        value.setCurrentIndex(index2)
                except KeyError:
                    # this axis was not chosen, it may seem
                    pass
        self.selection = deepcopy(self.selection_int)

    # def function(self, val):
    #     pass
    #     print('called with ', val)

    def parse_presets(self):
        '''read in all previously saved presets, add it to the combobox'''
        os.makedirs(self.presets_path, exist_ok=True)
        files = [os.path.splitext(f)[0] for f in os.listdir(
            self.presets_path) if f.endswith('.json') and
            os.path.isfile(os.path.join(self.presets_path, f))]
        self.combo_loadingpreset.addItem('-')
        self.combo_loadingpreset.addItems(files)

    def adding_selectiontab(self):
        '''add a Tab for additional plot selections

        Create a widget, load the selection Ui, add it to the WTabWidget,
        prepare everything for the GUI elements to work
        '''
        tabw = QtWidgets.QWidget()
        loadUi(self.ui_file_plotselection, tabw)
        tabw.index = len(self.tablist)
        self.tablist.append(tabw)
        self.tabW_selection.addTab(tabw, 'Plot {}'.format(tabw.index))

        # self.data['axes'].append(dict())
        # self.data['data'].append(dict())
        # self.data['labels_x'].append('dummy')
        # self.data['labels_y'].append('dummy')
        # self.data['legend_labels'].append('dummy')

        self.selection.append(
            dict(X=dict(), Y1=dict(), Y2=dict(), Y3=dict(), Y4=dict(), Y5=dict()))

        with self.mainthread.dataLock_live:
            # all the dictionary keys
            instruments = list(self.mainthread.data_live)
        instruments.insert(0, "-")  # for no chosen value by default
        # tabw.comboInstr_X.clear()
        # tabw.comboInstr_Y1.clear()
        # tabw.comboInstr_Y2.clear()
        # tabw.comboInstr_Y3.clear()
        # tabw.comboInstr_Y4.clear()
        # tabw.comboInstr_Y5.clear()

        # for i in axis_instrument:  # filling the comboboxes for the instrument
        # print(i, type(i))
        tabw.comboInstr_X.addItems(instruments)
        tabw.comboInstr_Y1.addItems(instruments)
        tabw.comboInstr_Y2.addItems(instruments)
        tabw.comboInstr_Y3.addItems(instruments)
        tabw.comboInstr_Y4.addItems(instruments)
        tabw.comboInstr_Y5.addItems(instruments)
        # actions in case instruments are chosen in comboboxes
        xconf = dict(GUI_value=tabw.comboValue_X,
                     GUI_instr=tabw.comboInstr_X,
                     livevsdb="LIVE",
                     axis='X',
                     tab=tabw,
                     )
        y1conf = dict(GUI_value=tabw.comboValue_Y1,
                      GUI_instr=tabw.comboInstr_Y1,
                      livevsdb="LIVE",
                      axis='Y1',
                      tab=tabw,
                      )
        y2conf = dict(GUI_value=tabw.comboValue_Y2,
                      GUI_instr=tabw.comboInstr_Y2,
                      livevsdb="LIVE",
                      axis='Y2',
                      tab=tabw,
                      )
        y3conf = dict(GUI_value=tabw.comboValue_Y3,
                      GUI_instr=tabw.comboInstr_Y3,
                      livevsdb="LIVE",
                      axis='Y3',
                      tab=tabw,
                      )
        y4conf = dict(GUI_value=tabw.comboValue_Y4,
                      GUI_instr=tabw.comboInstr_Y4,
                      livevsdb="LIVE",
                      axis='Y4',
                      tab=tabw,
                      )
        y5conf = dict(GUI_value=tabw.comboValue_Y5,
                      GUI_instr=tabw.comboInstr_Y5,
                      livevsdb="LIVE",
                      axis='Y5',
                      tab=tabw,
                      )
        tabw.comboInstr_X.currentIndexChanged['int'].connect(
            lambda x: self.plot_sel_instr(**xconf))
        tabw.comboInstr_Y1.currentIndexChanged['int'].connect(
            lambda x: self.plot_sel_instr(**y1conf))
        tabw.comboInstr_Y2.currentIndexChanged['int'].connect(
            lambda x: self.plot_sel_instr(**y2conf))
        tabw.comboInstr_Y3.currentIndexChanged['int'].connect(
            lambda x: self.plot_sel_instr(**y3conf))
        tabw.comboInstr_Y4.currentIndexChanged['int'].connect(
            lambda x: self.plot_sel_instr(**y4conf))
        tabw.comboInstr_Y5.currentIndexChanged['int'].connect(
            lambda x: self.plot_sel_instr(**y5conf))

    def plot_sel_instr(self, livevsdb, GUI_instr, GUI_value, axis, tab):
        """
           filling the Value column combobox in case the corresponding
           element of the instrument column combobox was chosen
           thus:
                - check for the chosen instrument,
                - get the data for the new combobox
                - connect the corresponding second combobox action with
                    its choosing function
        """

        instrument_name = GUI_instr.currentText()
        if livevsdb == "LIVE":
            with self.mainthread.dataLock_live:
                try:
                    value_names = list(
                        self.mainthread.data_live[instrument_name])
                except KeyError:
                    self.sig_error.emit('plotting: do not choose "-" '
                                        'please, there is nothing behind it!')
                    logger.warning(
                        'do not choose "-" please, there is nothing behind it!')
                    return

        GUI_value.clear()
        GUI_value.addItems(("-",))
        GUI_value.addItems(value_names)
        GUI_value.activated.connect(lambda: self.plot_sel_val(GUI_instr=GUI_instr,
                                                              GUI_value=GUI_value,
                                                              livevsdb="LIVE",
                                                              axis=axis,
                                                              tab=tab))

    def plot_sel_val(self, GUI_instr, GUI_value, livevsdb, axis, tab):
        """get instrument and value of the chosen axis, and store it"""
        value_name = GUI_value.currentText()
        instrument_name = GUI_instr.currentText()
        self.selection[tab.index][axis]['instrument'] = instrument_name
        self.selection[tab.index][axis]['value'] = value_name

        # self.data['axes'][tab.index][axis] = '{}: {}'.format(
        #     instrument_name, value_name)

    def displaying(self):
        """retrieve all the data and plot it"""
        data = []
        labels_x = []
        labels_y = []
        labels_legend = []
        # print(self.selection)
        for plot_entry in self.selection:
            # try:
            # print('lenplotentry', len(plot_entry))
            with self.mainthread.dataLock_live:
                try:
                    x = self.mainthread.data_live[plot_entry['X'][
                        'instrument']][plot_entry['X']['value']]
                except KeyError:
                    self.sig_error.emit(
                        'Plotting: There was to be an empty plot - I ignored it....')
                    logger.warning(
                        'There was to be an empty plot - I ignored it....')
                    continue
                y = []
                # print(x)
                labels_l = []
                for ax in [name for name in self.axesnames if name != 'X']:
                    # print(plot_entry[ax])
                    if ('instrument' and 'value') in plot_entry[ax]:
                        # print('found something!')
                        try:
                            y.append(self.mainthread.data_live[plot_entry[ax][
                                     'instrument']][plot_entry[ax]['value']])
                            labels_l.append('{}: {}'.format(
                                plot_entry[ax]['instrument'], plot_entry[ax]['value']))
                        except KeyError:
                            logger.warning(
                                'some key was specified which is not present in the data!')

                # y = [entry_data[key] for key in entry_data if key != 'X']

            # except KeyError:
            #     self.sig_error.emit(
            #         'Plotting: Either you did not choose all adjoining axes '
            #         'together (to every instrument you chose also a value to '
            #         'plot), or you used a preset with which you tried to plot '
            #         'values which currently do not exist (possibly instruments'
            #         ' are not connected, or do not send the data you want to '
            #         'see), try again!')
            #     return

                # try:
                #     label_y = '{}: {}'.format(self.selection[tabindex]['Y1']['instrument'], self.selection[tabindex]['Y1']['value'])
                # except KeyError:
            labels_y.append('')

            labels_x.append('{}: {}'.format(
                plot_entry['X']['instrument'], plot_entry['X']['value']))
            labels_legend.append(labels_l)

            data.append([[x, yn] for yn in y])

        # print(data)

        self.mainthread.plotting_window_count += 1
        number = deepcopy(self.mainthread.plotting_window_count)
        window = Window_plotting_m(data=data,
                                   labels_x=labels_x,
                                   labels_y=labels_y,
                                   legend_labels=labels_legend,
                                   lock=self.mainthread.dataLock_live,
                                   number=number,
                                   multiple=True)
        # print(type(window))
        window.sig_closing.connect(lambda:
                                   self.mainthread.plotting_deleting_window(window, number))
        self.mainthread.windows_plotting.append(window)
        window.show()
        self.sig_success.emit()
