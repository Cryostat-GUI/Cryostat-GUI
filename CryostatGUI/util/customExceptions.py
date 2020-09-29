class BlockedError(Exception):
    """raised by the contextmanager noblopckLock when a LoopThread is paused"""


class problemAbort(Exception):
    """raised in Sequences, aborting them if an unsolvable problem occurrs"""


class ApplicationExit(Exception):
    """should never be handled, but if raised, crash the application
    this is intended for use with a service,
    which will be restarted upon uncontrolled exit
    Windows:
        - service
    Ubuntu:
        - systemd service

    used primarily by hardware drivers,
    when the hardware is not available
    """


class genericAnswer(Exception):
    """zmq Exception for when a generic answer is generated
    by a function handling the message
    deprecated
    """


class successExit(Exception):
    """zmq: when waiting for an answer, trials are repeated without blocking
    however once the answer was received, we want to move on
    """
