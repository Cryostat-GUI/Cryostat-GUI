"""
Utility module for the Cryostat GUI


Classes: 
    AbstractThread: a class which sets up QT's QThread instance, as well as the assertion signal

    AbstractLoopThread: a thread-class, inheriting from AbstractThread, 
        which implements Thread-Loop behaviour, continuously running the class method self.running

    AbstractEventhandlingThread: a thread class, inheriting from AbstractThread, 
        which is designed to be used for handling signal-events, not continuous loops

"""






# from PyQt5 import QtWidgets,  
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot



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

    def __init__(self):
        super().__init__()
        self.__isRunning = True

    @pyqtSlot() # int
    def work(self):
        """class method which is working all the time while the thread is running. """
        while self.__isRunning:
            try: 
                self.running()
            except AssertionError as assertion: 
                self.sig_assertion.emit(assertion.args[0])          


    def running(self):
        """class method to be overriden """
        raise NotImplementedError

    @pyqtSlot()
    def stop(self):
        """stop the loop execution, sets self.__isRunning to False"""
        self.__isRunning = False


class AbstractEventhandlingThread(AbstractThread):
    """Abstract thread class to be used with instruments """

    def __init__(self):
        super().__init__()


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
        """just here so stopping the thread can be done as with all others"""
        pass
