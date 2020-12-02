import zmq
import logging
from json import loads as dictload
from json import dumps
from json import decoder
import functools
import time
from datetime import datetime as dt
from datetime import timedelta as dtdelta

from .customExceptions import problemAbort
from .customExceptions import successExit
from .customExceptions import genericAnswer

from .util_misc import ExceptionHandling

# from threading import Thread

# from util import ExceptionHandling

logger = logging.getLogger("CryostatGUI.zmqComm")


def enc(msg):
    return "{}".format(msg).encode("utf-8")


def dec(msg):
    return msg.decode("utf-8")


def dictdump(d):
    return dumps(d, indent=4, sort_keys=True, default=str)


def HandleJsonException(func):
    @functools.wraps(func)
    def wrapper_HandleJsonException(*args, **kwargs):
        # if inspect.isclass(type(args[0])):
        # thread = args[0]
        try:
            return func(*args, **kwargs)
        # except AssertionError as e:
        #     logger.exception(e)

        except TypeError as e:
            logger.exception(e)

        except decoder.JSONDecodeError as e:
            logger.exception(e)

        # except KeyError as e:
        #     logger.exception(e)

        # except IndexError as e:
        #     logger.exception(e)

        # except ValueError as e:
        #     logger.exception(e)

        # except AttributeError as e:
        #     logger.exception(e)

        # except NotImplementedError as e:
        #     logger.exception(e)

        # except OSError as e:
        #     logger.exception(e)

    return wrapper_HandleJsonException


def zmqquery_handle(socket, handlefun):
    # signal.signal(signal.SIGINT, signal.SIG_DFL)
    # context = zmq.Context()
    # socket = context.socket(zmq.REP)
    # socket.bind("tcp://*:{}".format(5556))
    try:
        while True:
            message = socket.recv(flags=zmq.NOBLOCK)
            logger.debug(f"received message: {message}")
            # print(f'received message: {message}')
            try:
                handlefun(message=message, socket=socket)
            except genericAnswer as gen:
                socket.send_string("{}".format(gen))
    except zmq.Again:
        pass
        # print('nothing to work')


def zmqquery(socket, query):
    # signal.signal(signal.SIGINT, signal.SIG_DFL);
    # context = zmq.Context()
    # socket = context.socket(zmq.REQ)
    # socket.connect("tcp://localhost:5556")
    try:
        socket.send_string(f"{query}")
        while True:
            try:
                message = socket.recv(flags=zmq.NOBLOCK)
                raise successExit
            except zmq.Again:
                time.sleep(0.2)
                logger.debug("no answer")

    except zmq.ZMQError as e:
        logger.exception(e)
        return -1
    except successExit:
        return message


def zmqquery_dict(socket, query):
    # signal.signal(signal.SIGINT, signal.SIG_DFL);
    # context = zmq.Context()
    # socket = context.socket(zmq.REQ)
    # socket.connect("tcp://localhost:5556")
    try:
        socket.send_string(f"{query}")
        while True:
            try:
                message = socket.recv_json(flags=zmq.NOBLOCK)
                raise successExit
            except zmq.Again:
                time.sleep(0.2)
                logger.debug("no answer")

    except zmq.ZMQError as e:
        logger.exception(e)
        return -1
    except successExit:
        return message


def raiseProblemAbort(_f=None, raising=False):
    # adapted from https://stackoverflow.com/questions/5929107/decorators-with-parameters#answer-60832711
    assert callable(_f) or _f is None

    def _decorator(func):
        """decorating functions which may raise an error internally,
        re-raising that error if necessary
        returns a single value if raising=True
        else it always returns message and error, either of which is None
        """

        @functools.wraps(func)
        def wrapper_raiseProblemAbort(*args, **kwargs):
            # if inspect.isclass(type(args[0])):
            message, error = func(*args, **kwargs)
            if raising:
                if error:
                    if isinstance(error, Exception):
                        raise error
                    else:
                        logger.warning(
                            "somehow a not-exception object ended up where it should not."
                        )
                return message
            else:
                return message, error

        return wrapper_raiseProblemAbort

    return _decorator(_f) if callable(_f) else _decorator


class zmqBare:
    """docstring for zmqBare"""

    pass


class zmqClient(zmqBare):
    """docstring for zmqDev"""

    def __init__(
        self,
        context=None,
        identity=None,
        ip_maincontrol="localhost",
        ip_data="localhost",
        port_reqp=5556,
        port_downstream=5557,
        port_upstream=5558,
        **kwargs,
    ):
        # print('zmqClient')
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.comms_name = identity
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.DEALER)
        self.comms_tcp.identity = "{}".format(identity).encode("ascii")  # id
        self.comms_tcp.connect(f"tcp://{ip_maincontrol}:{port_reqp}")

        self.comms_downstream = self._zctx.socket(zmq.SUB)
        self.comms_downstream.connect(f"tcp://{ip_maincontrol}:{port_downstream}")
        # subscribe to instrument specific commands
        self.comms_downstream.setsockopt(
            zmq.SUBSCRIBE,
            self.comms_name.encode("ascii"),
        )
        # subscribe to general commands
        self.comms_downstream.setsockopt(
            zmq.SUBSCRIBE,
            "general".encode("ascii"),
        )

        self.comms_upstream = self._zctx.socket(zmq.PUB)
        self.comms_upstream.connect(f"tcp://{ip_data}:{port_upstream}")

        self.poller = zmq.Poller()
        self.poller.register(self.comms_tcp, zmq.POLLIN)
        self.poller.register(self.comms_downstream, zmq.POLLIN)

        time.sleep(4)
        # needed for the PUB/SUB sockets to find each other!

        self.data = {}

    # def work_zmq(self):
    #     try:
    #         # self.comms_pub.send_multipart([u'client{}'.format(self.name).encode(
    #         #     'ascii'), u'comes from client{}'.format(self.name).encode('ascii')])
    #         # print(f'client {self._name} polling')
    #         self.zmq_handle()
    #     except KeyboardInterrupt:
    #         pass

    # @ExceptionHandling
    def zmq_handle(self):
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        if self.comms_tcp in evts:
            try:
                while True:
                    msg = self.comms_tcp.recv(zmq.NOBLOCK)
                    if dec(msg)[0] == "?":
                        # answer = retrieve_answer(dec(msg))
                        answer = enc(dictdump(self.data))
                        self.comms_tcp.send(answer)

                    elif dec(msg)[0] == "!":
                        command_dict = dictload(dec(msg)[1:])
                        answer = self.query_on_command(command_dict)
                        self.comms_tcp.send(enc(dictdump(answer)))

                    else:
                        self._logger.error(
                            "received unintelligable message: '%s' ", dec(msg)
                        )
                        self.comms_tcp.send(enc(dictdump({"ERROR": True}) + dec(msg)))

            except zmq.Again:
                pass
        if self.comms_downstream in evts:
            try:
                while True:
                    msg = self.comms_downstream.recv_multipart(zmq.NOBLOCK)
                    command_dict = dictload(dec(msg[1]))
                    self._logger.info(
                        "received command from downstream: %s", command_dict
                    )

                    try:
                        if "interval" in command_dict:
                            self._logger.debug(
                                "setting a new interval: %1.3f",
                                command_dict["interval"],
                            )                        
                        if "lock" in command_dict:
                            self._logger.debug("   locked the loop")
                            self.lock.acquire()
                        elif "unlock" in command_dict:
                            self._logger.debug("un-locked the loop")
                            self.lock.release()

                            self.setInterval(command_dict["interval"])
                    except AttributeError as e:
                        self._logger.exception(e)
                    except RuntimeError as e:
                        self._logger.exception(e)
                    self.act_on_command(command_dict)
                    # act on commands!
            except zmq.Again:
                pass

    def act_on_command(self, command: dict) -> None:
        raise NotImplementedError

    def query_on_command(self, command: dict) -> dict:
        raise NotImplementedError

    def send_data_upstream(self):
        self.comms_upstream.send_multipart(
            [self.comms_name.encode("ascii"), enc(dictdump(self.data))]
        )

    def running(self):
        self.data = {}
        super().running()
        self.data["interval_thread"] = self.interval


class zmqMainControl(zmqBare):
    """docstring for zmqDev"""

    def __init__(
        self,
        context=None,
        _ident="mainControl",
        ip_maincontrol="*",
        ip_data="localhost",
        port_reqp=5556,
        port_downstream=5557,
        # port_upstream=5558,
        port_data=5559,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.comms_name = _ident
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.ROUTER)
        self.comms_tcp.identity = b"mainControl"  # id
        self.comms_tcp.bind(f"tcp://{ip_maincontrol}:{port_reqp}")

        self.comms_data = self._zctx.socket(zmq.DEALER)
        self.comms_data.identity = b"mainControl"  # id
        self.comms_data.connect(f"tcp://{ip_data}:{port_data}")

        self.comms_downstream = self._zctx.socket(zmq.PUB)
        self.comms_downstream.bind(f"tcp://{ip_maincontrol}:{port_downstream}")

        self.comms_inproc = self._zctx.socket(zmq.ROUTER)
        self.comms_inproc.identity = b"mainControl"  # id
        self.comms_inproc.bind("inproc://main")
        # self.comms_upstream = self._zctx.socket(zmq.SUB)
        # self.comms_upstream.bind(f'tcp://{ip_maincontrol}:{port_upstream}')
        # self.comms_upstream.setsockopt(zmq.SUBSCRIBE, b'')

        self.poller = zmq.Poller()
        self.poller.register(self.comms_tcp, zmq.POLLIN)
        self.poller.register(self.comms_inproc, zmq.POLLIN)

        time.sleep(4)
        self._logger.info("mainControl zmq initialisation finished!")
        # needed for the PUB/SUB sockets to find each other!

    def zmq_handle(self):
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        if self.comms_tcp in evts:
            try:
                while True:
                    msg = self.comms_tcp.recv_multipart(zmq.NOBLOCK)
                    address, message = msg[0], msg[1]
                    if dec(message)[0] == "?":
                        pass
                    # do something, most likely this will not be used
                    # extensively
            except zmq.Again:
                pass
        if self.comms_inproc in evts:
            try:
                while True:
                    address, message = self.comms_inproc.recv_multipart(zmq.NOBLOCK)
                    if dec(message)[0] == "?":
                        pass
                        # do something - here, most likely a query is passed on to
                        # the dataStore, and the answer is returned in turn
                        # TODO: change that to a tcp connection
                        self.comms_data.send(message)
                        data = self.comms_data.recv()
                        self.comms_inproc.send_multipart([address, data])
            except zmq.Again:
                pass

    def commanding(self, ID, message):
        # self.comms_downstream.send_multipart([ID.encode('asii'), enc(message)])
        self.comms_downstream.send_multipart([enc(ID), enc(message)])

    def _bare_retrieveDataIndividual(self, dataindicator1, dataindicator2, Live=True):
        message = enc(
            "?" + dictdump(dict(instr=dataindicator1, value=dataindicator2, live=Live))
        )
        try:
            self.comms_data.send(message)
            for _ in range(3):
                for _ in range(5):
                    try:
                        message = dictload(self.comms_data.recv(flags=zmq.NOBLOCK))
                        if "ERROR" in message:
                            self._logger.warning(
                                "received error from dataStorage: %s -- %s",
                                message["ERROR_message"],
                                message["info"],
                            )
                            raise problemAbort(
                                "problem with data retrieval, possibly the requested data is missing"
                            )
                        raise successExit
                    except zmq.Again:
                        time.sleep(0.3)
                self._logger.debug("no answer after 5 trials, sleeping for a while")
                time.sleep(1)

            self._logger.warning("got no answer from dataStorage within 6s")
            # TODO: fallback to querying individual application parts for data
            raise problemAbort("dataStorage unresponsive, abort")
        except zmq.ZMQError as e:
            self._logger.exception(e)
            # raise problemAbort("")
            return None, "zmq error, no data available, abort"
        except successExit:
            return message, None
        except problemAbort as e:
            return None, e

    @ExceptionHandling
    def _bare_readDataFromList(
        self, dataindicator1: str, dataindicator2: str, Live: bool = False
    ) -> float:
        """retrieve a datapoint from the central list at dataStorage logging"""
        uptodate = False
        try:
            startdate = dt.now()
            while not uptodate:
                self.check_running()
                dataPackage = self.retrieveDataIndividual(
                    dataindicator1=dataindicator1,
                    dataindicator2=dataindicator2,
                    Live=Live,
                )
                uptodate = dataPackage["uptodate"]

                if (dt.now() - startdate) / dtdelta(minutes=1) > 2:
                    self._logger.error(
                        "retrieved data %s, %s exists, but after trying for 2min, there is none which is up to date, aborting",
                        dataindicator1,
                        dataindicator2,
                    )
                    # we are not patient anymore
                    raise problemAbort(
                        f"no up-to-date data available for {dataindicator1}, {dataindicator2}, abort"
                    )
                elif (dt.now() - startdate) / dtdelta(seconds=1) > 10:
                    timediff = dataPackage["timediff"]
                    self._logger.warning(
                        "retrieved data %s, %s exists, but is not up to date, timediff: %f s, tried for >10s",
                        dataindicator1,
                        dataindicator2,
                        timediff,
                    )
                    # there might be a problem with the respective device, but we will be patient, for now
            data = dataPackage["data"]
            return data, None  # second value is indicating no error was raised

        except KeyError as err:
            # print('KeyErr')
            self.sig_assertion.emit(
                "Sequence: readData: no data: {}".format(err.args[0])
            )
            self._logger.error(
                "no data: {} for request (Live={}) {}: {}".format(
                    err.args[0], Live, dataindicator1, dataindicator2
                )
            )
            self.check_running()
            time.sleep(1)
            return self.readDataFromList(
                dataindicator1=dataindicator1, dataindicator2=dataindicator2, Live=Live
            )
        except problemAbort as e:
            return None, e

    @raiseProblemAbort(raising=False)
    def retrieve_data_individual(self, dataindicator1, dataindicator2, Live=True):
        return self._bare_retrieveDataIndividual(dataindicator1, dataindicator2, Live)

    @raiseProblemAbort(raising=False)
    def readDataFromList(
        self, dataindicator1: str, dataindicator2: str, Live: bool = False
    ) -> float:
        return self._bare_readDataFromList(dataindicator1, dataindicator2, Live)

    def query_device_data(self, device_id, noblock=False):
        """query data from device directly"""
        data = "?"
        return self._query_device(device_id, data, noblock=noblock)

    def query_device_command(self, device_id, command=None, noblock=False):
        """dictate action and return answer"""
        data = "!" + dictdump(command)
        return self._query_device(device_id, data, noblock=noblock)

    def _query_device(self, device_id, msg, noblock):
        address_retour = None
        address = device_id

        while address_retour != address:
            self._logger.debug("querying %s: %s", address, msg[0])
            self.comms_tcp.send_multipart([address, enc(msg)])
            if noblock:
                time.sleep(0.5)
                address_retour, message = self.comms_tcp.recv_multipart(zmq.NOBLOCK)
            else:
                address_retour, message = self.comms_tcp.recv_multipart()
            self._logger.debug("received data from %s", address_retour)
        return dictload(dec(message))


class zmqDataStore(zmqBare):
    """docstring for zmqDev"""

    def __init__(
        self,
        context=None,
        _ident="dataStore",
        ip_maincontrol="localhost",
        ip_data="*",
        port_reqp=5556,
        port_downstream=5557,
        port_upstream=5558,
        port_data=5559,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.comms_name = _ident
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.DEALER)
        self.comms_tcp.identity = b"dataStore"  # id
        self.comms_tcp.connect(f"tcp://{ip_maincontrol}:{port_reqp}")

        self.comms_data = self._zctx.socket(zmq.ROUTER)
        self.comms_data.identity = b"dataStore"  # id
        self.comms_data.bind(f"tcp://{ip_data}:{port_data}")

        self.comms_upstream = self._zctx.socket(zmq.SUB)
        self.comms_upstream.bind(f"tcp://{ip_data}:{port_upstream}")
        self.comms_upstream.setsockopt(zmq.SUBSCRIBE, b"")

        self.comms_downstream = self._zctx.socket(zmq.SUB)
        self.comms_downstream.connect(f"tcp://{ip_maincontrol}:{port_downstream}")
        self.comms_downstream.setsockopt(
            zmq.SUBSCRIBE, "{}".format(self.comms_name).encode("ascii")
        )

        self.poller = zmq.Poller()
        self.poller.register(self.comms_tcp, zmq.POLLIN)
        self.poller.register(self.comms_upstream, zmq.POLLIN)
        self.poller.register(self.comms_downstream, zmq.POLLIN)
        self.poller.register(self.comms_data, zmq.POLLIN)

        time.sleep(4)
        # needed for the PUB/SUB sockets to find each other!

    def zmq_handle(self):
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        if self.comms_tcp in evts:
            try:
                while True:
                    msg = self.comms_tcp.recv(zmq.NOBLOCK)
                    if dec(msg)[0] == "?":
                        answer = self.get_answer(msg)
                        self.comms_tcp.send(enc(answer))
                    # do something - most likely hand out data to an asking
                    # process
            except zmq.Again:
                pass
        if self.comms_data in evts:
            try:
                while True:
                    address, msg = self.comms_data.recv_multipart(zmq.NOBLOCK)
                    if dec(msg)[0] == "?":
                        try:
                            questiondict = dictload(dec(msg)[1:])
                            answer = dictdump(self.get_answer(questiondict))
                        except decoder.JSONDecodeError as e:
                            answer = dictdump(
                                dict(
                                    ERROR="ERROR",
                                    ERROR_message=e.args[0],
                                    info="something went wrong when decoding your json",
                                )
                            )
                        self.comms_data.send_multipart([address, enc(answer)])
                    # do something - most likely hand out data to an asking
                    # process
            except zmq.Again:
                pass
        if self.comms_upstream in evts:
            try:
                while True:
                    msg = self.comms_upstream.recv_multipart(zmq.NOBLOCK)
                    # print(msg)
                    self.store_data(dec(msg[0]), dictload(dec(msg[1])))
                    # store data!
            except zmq.Again:
                pass
        if self.comms_downstream in evts:
            try:
                while True:
                    msg = self.comms_downstream.recv_multipart(zmq.NOBLOCK)
                    command_dict = dictload(dec(msg[1]))
                    try:
                        if "lock" in command_dict:
                            self.lock.acquire()
                        elif "unlock" in command_dict:
                            self.lock.release()
                    except AttributeError as e:
                        self._logger.exception(e)
                    self.act_on_command(command_dict)
                    # act on commands!
            except zmq.Again:
                pass

    def store_data(self, ID, data):
        raise NotImplementedError

    def get_answer(self, qdict):
        raise NotImplementedError

    def send_data_upstream(self):
        """dummy method so this class can easily be exchanginly used with zmqClient"""
        pass

    def act_on_command(self, command: dict) -> None:
        raise NotImplementedError
