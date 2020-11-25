from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QThread
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.uic import loadUi

from threading import Thread
from threading import Event

from .util_misc import running_thread
from .util_misc import noblockLock
from .customExceptions import BlockedError

from .zmqcomms import zmqClient
from .zmqcomms import zmqDataStore
from .livedata import PrometheusGaugeClient

from datetime import datetime as dt
from datetime import timedelta


from visa import VisaIOError

import logging
from threading import Lock


def timediff(start, end):
    """return timediff of datetime objects in milliseconds"""
    return (end - start) / timedelta(milliseconds=1)


class Timerthread(Thread):
    def __init__(self, event=None, interval=0.5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.interval = interval
        self.interval_now = 0
        self.lock = Lock()
        if event is None:
            self.stopped = Event()
        else:
            self.stopped = event

    def run(self):
        self._logger.debug("entering the working loop")
        while not self.stopped.is_set():
            self.stopped.wait(self.interval_now)
            # self._logger.debug("not stopped, running")
            # print(f"my thread is working hard! {self.counter}")
            try:
                start = dt.now()
                self.work()
            except BlockedError:
                pass
            finally:
                end = dt.now()
                self.interval_now = self.calculate_timeToWait(start, end)

    def running(self):
        """to be implemented by child class!"""
        raise NotImplementedError

    def calculate_timeToWait(self, start, end):
        try:
            diff = timediff(start, end)
            timeToWait = self.interval * 1e0 - diff
            if timeToWait < 0:
                # self._logger.debug(
                #     "no wait for loop iteration, len(lastIt) = %f s > wait = %f",
                #     diff * 1e-3,
                #     self.interval,
                # )
                timeToWait = 0
        except NameError:
            timeToWait = 1e3
        # print("calculated time to wait:", timeToWait)
        return timeToWait

    def work(self):
        raise NotImplementedError


class Timerthread_Clients(zmqClient, PrometheusGaugeClient, Timerthread):
    """docstring for Timerthread_Clients"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.run_finished = False
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    def work(self):
        self.zmq_handle()  # inherited from zmqClient
        with noblockLock(self.lock):
            self.running()
            if self.run_finished:
                self.run_prometheus()  # inherited from PrometheusGaugeClient
                self.send_data_upstream()  # inherited from zmqClient


class AbstractApp(QtWidgets.QMainWindow):
    """docstring for AbstractApp"""

    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)
    sig_Infodata = pyqtSignal(dict)

    def __init__(self, *args, ui_file=None, **kwargs):
        # print('abstractApp pre')
        super().__init__(*args, **kwargs)
        # print('abstractApp post')
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        if ui_file is not None:
            loadUi(ui_file, self)

        # self.setup_logging_base()
        # self.setup_logging()
        self.sig_assertion.connect(lambda value: self._logger.exception(value))
        self.sig_visatimeout.connect(lambda value: self._logger.exception(value))

    # def setup_logging_base(self):
    #     self.logger_all = logging.getLogger()
    #     self.logger_personal = logging.getLogger(
    #         'CryostatGUI:' + __name__ + ':' + self.__class__.__name__)

    #     # self.Log_DBhandler = SQLiteHandler(
    #     #     db='Errors\\' + dt.datetime.now().strftime('%Y%m%d') + '_dblog.db')
    #     # self.Log_DBhandler.setLevel(logging.DEBUG)

    #     self.logger_personal.setLevel(logging.DEBUG)
    #     self.logger_all.setLevel(logging.INFO)
    #     # self.logger_personal.addHandler(self.Log_DBhandler)

    #     handler = logging.StreamHandler(sys.stderr)
    #     handler.setLevel(logging.DEBUG)
    #     formatter = logging.Formatter(
    #         '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #     handler.setFormatter(formatter)
    #     self.logger_personal.addHandler(handler)
    #     self.logger_all.addHandler(handler)

    #     self._logger = self.logger_personal

    # def setup_logging(self):
    #     """set up the logger, handler, for now in DEBUG
    #     TODO: connect logging levels with GUI preferences"""

    #     self.logger_all.setLevel(logging.DEBUG)

    # self.logger_all.addHandler(self.Log_DBhandler)


# class AbstractLoopApp(AbstractApp):
#     """Abstract application class to be used with instruments

#     this needs to be used in conjunction with a zmqClass!
#     """

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.interval = 0.5  # second
#         self.lock = Lock()

#         QTimer.singleShot(0, self.work)

#     @pyqtSlot()  # int
#     def work(self):
#         """class method which is working all the time while the thread is running. """
#         try:
#             self.zmq_handle()  # inherited later from zmqClient
#             with noblockLock(self.lock):
#                 self.running()
#                 if self.run_finished:
#                     self.send_data_upstream()
#         except BlockedError:
#             pass
#         except AssertionError as assertion:
#             self.sig_assertion.emit(assertion.args[0])
#         finally:
#             QTimer.singleShot(self.interval * 1e3, self.work)

#     def running(self):
#         """class method to be overriden for periodic tasks"""
#         raise NotImplementedError

#     @pyqtSlot(float)
#     def setInterval(self, interval):
#         """set the interval between running events in seconds"""
#         self.interval = interval


# class AbstractLoopClient(AbstractLoopApp, zmqClient):
#     """docstring for AbstractLoopClient"""

#     def __init__(self, *args, **kwargs):
#         # print('loopclient')
#         super().__init__(*args, **kwargs)


class AbstractMainApp(AbstractApp):
    """docstring for AbstractMainApp"""

    data = {}

    def __init__(self, **kwargs):
        # print('mainapp pre')
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        # print('mainapp post')

        self.softwarecontrol_timer = QTimer()
        self.softwarecontrol_timer.timeout.connect(self.softwarecontrol_check)
        self.softwarecontrol_timer.start(1000)

        self.controls_Lock = Lock()
        self.threads = dict(Lock=Lock())

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

        with self.threads["Lock"]:
            # this needs to be locked when a new thread is added, as otherwise
            # the thread locking context manager would try to unlock the new thread
            # before it was ever locked, resulting in a crash
            #
            # threads need to be saved somewhere, since otherwise garbage collection
            # will throw them away, they die
            self.threads[threadname] = (worker, thread)

        return worker


class AbstractThread(QObject):
    """Abstract thread class to be used with instruments """

    sig_assertion = pyqtSignal(str)
    sig_visaerror = pyqtSignal(str)
    sig_visatimeout = pyqtSignal()
    timeouterror = VisaIOError(-1073807339)
    sig_Infodata = pyqtSignal(dict)

    def __init__(self, **kwargs):
        QThread.__init__(self, **kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.sig_assertion.connect(lambda value: self._logger.exception(value))
        self.sig_visatimeout.connect(lambda value: self._logger.exception(value))

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
        self.interval = 0.2  # second
        self.lock = Lock()
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    @pyqtSlot()  # int
    # @ExceptionHandling  # this is being done with all functions again, still...
    def work(self):
        """class method which is working all the time while the thread is running. """
        try:
            start = dt.now()
            with noblockLock(self.lock):
                self.running()
        except BlockedError:
            pass
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            end = dt.now()
            timeToWait = self.calculate_timeToWait(start, end)
            QTimer.singleShot(timeToWait, self.work)

    def running(self):
        """class method to be overriden """
        raise NotImplementedError

    @pyqtSlot(float)
    def setInterval(self, interval):
        """set the interval between running events in seconds"""
        self.interval = interval

    def calculate_timeToWait(self, start, end):
        try:
            diff = timediff(start, end)
            timeToWait = self.interval * 1e3 - diff
            if timeToWait < 0:
                # self._logger.debug(
                #     "no wait for loop iteration, len(lastIt) = %f s > wait = %f",
                #     diff * 1e-3,
                #     self.interval,
                # )
                timeToWait = 0
        except NameError:
            timeToWait = 1e3
        return timeToWait


class AbstractLoopZmqThread(AbstractLoopThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.run_finished = False
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    @pyqtSlot()  # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        try:
            start = dt.now()
            self.zmq_handle()  # inherited later from zmqClient
            with noblockLock(self.lock):
                self.running()
                if self.run_finished:
                    # self._logger.debug("Hardware run finished, sending data upstream!")
                    self.send_data_upstream()
        except BlockedError:
            pass
        finally:
            end = dt.now()
            timeToWait = self.calculate_timeToWait(start, end)
            QTimer.singleShot(timeToWait, self.work)


class AbstractLoopThreadClient(AbstractLoopZmqThread, zmqClient, PrometheusGaugeClient):
    """docstring for AbstractLoopThreadClient"""

    @pyqtSlot()  # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        try:
            start = dt.now()
            self.zmq_handle()  # inherited later from zmqClient
            with noblockLock(self.lock):
                self.running()
                if self.run_finished:
                    self.run_prometheus()
                    self.send_data_upstream()
        except BlockedError:
            pass
        finally:
            end = dt.now()
            timeToWait = self.calculate_timeToWait(start, end)
            QTimer.singleShot(timeToWait, self.work)


class AbstractLoopThreadDataStore(AbstractLoopZmqThread, zmqDataStore):
    """docstring for AbstractLoopThreadDataStore"""


class AbstractEventhandlingThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interval = 500
        self.lock = Lock()
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )

    @pyqtSlot()
    def work(self):
        """class method which is here so something runs, and starting behaviour is not broken"""
        try:
            self.running()
        except AssertionError as assertion:
            self.sig_assertion.emit(assertion.args[0])
        finally:
            QTimer.singleShot(self.interval * 1e3, self.work)

    def running(self):
        """empty method to keep thread alive (there is surely a better solution) """
        pass
