import zmq
import logging
from json import loads as dictload
from json import dumps
from json import decoder
import functools
import time
from datetime import datetime as dt
from datetime import timedelta as dtdelta
from copy import deepcopy

import uuid

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


# def raiseProblemAbort(_f=None, raising=False):
#     # adapted from https://stackoverflow.com/questions/5929107/decorators-with-parameters#answer-60832711
#     assert callable(_f) or _f is None

#     def _decorator(func):
#         """decorating functions which may raise an error internally,
#         re-raising that error if necessary
#         returns a single value if raising=True
#         else it always returns message and error, either of which is None
#         """

#         @functools.wraps(func)
#         def wrapper_raiseProblemAbort(*args, **kwargs):
#             # if inspect.isclass(type(args[0])):
#             message, error = func(*args, **kwargs)
#             if raising:
#                 if error:
#                     if isinstance(error, Exception):
#                         raise error
#                     else:
#                         logger.warning(
#                             "somehow a not-exception object ended up where it should not."
#                         )
#                 return message
#             else:
#                 return message, error

#         return wrapper_raiseProblemAbort

#     return _decorator(_f) if callable(_f) else _decorator


class loops_off_zmq:
    """Context manager for disabling all AbstractLoopThread loops through zmq comms"""

    def __init__(self, control, devices):
        self.devices = devices
        self.control = control

    def __enter__(self, *args, **kwargs):
        for dev in self.devices:
            # self.control.commanding(
            #     dev, dictdump({"lock": None}),
            # )
            self.control._logger.debug("locking device %s", dev)
            self.control.query_device_command(
                dev,
                command={"lock": None},
            )

    def __exit__(self, *args, **kwargs):
        for dev in self.devices:
            # self.control.commanding(
            #     dev, dictdump({"lock": None}),
            # )
            self.control._logger.debug("unlocking device %s", dev)
            self.control.query_device_command(
                dev,
                command={"unlock": None},
            )


class zmqBare:
    """docstring for zmqBare"""

    pass


class zmqClient(zmqBare):
    """docstring for zmqDev"""

    def __init__(
        self,
        context=None,
        identity=None,
        ip_maincontrol="127.0.0.1",
        ip_data="127.0.0.1",
        port_reqp=5556,
        port_downstream=5561,
        port_upstream=5560,
        **kwargs,
    ):
        # print('zmqClient')
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.comms_name = identity
        self._zctx = context or zmq.Context()

        # setting up dealer-router-dealer through broker comms
        self.comms_tcp = self._zctx.socket(zmq.DEALER)
        self.comms_tcp.identity = "{}".format(identity).encode("ascii")  # id
        self.comms_tcp.connect(f"tcp://{ip_maincontrol}:{port_reqp}")

        # setting up downstream: commands from mainControl units
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

        # setting up upstream, sending data back to whoever is interested
        self.comms_upstream = self._zctx.socket(zmq.PUB)
        self.comms_upstream.connect(f"tcp://{ip_data}:{port_upstream}")

        self.poller = zmq.Poller()
        self.poller.register(self.comms_tcp, zmq.POLLIN)
        self.poller.register(self.comms_downstream, zmq.POLLIN)

        time.sleep(4)
        # sleep needed for the PUB/SUB sockets to find each other!

        self.data = {}

    def act_on_general(self, command_dict):
        try:
            if "interval" in command_dict:
                self._logger.debug(
                    "setting a new interval: %3.3fs",
                    command_dict["interval"],
                )
                self.setInterval(command_dict["interval"])
            if "lock" in command_dict:
                self._logger.debug("   locking the loop now")
                if not self.lock.acquire(blocking=False):
                    self._logger.warning(
                        "tried to lock this loop, but it is locked already! "
                    )
            elif "unlock" in command_dict:
                self._logger.debug("un-locking the loop now")
                try:
                    self.lock.release()
                except RuntimeError:
                    self._logger.warning(
                        "tried to unlock this loop, but it is not locked!"
                    )

        except AttributeError as e:
            self._logger.exception(e)
        except RuntimeError as e:
            self._logger.exception(e)

    # @ExceptionHandling
    def zmq_handle(self):
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        self._logger.debug("zmq: handling events")
        if self.comms_tcp in evts:
            try:
                while True:
                    # self._logger.debug("zmq: handling tcp")
                    msg = self.comms_tcp.recv(zmq.NOBLOCK)
                    if dec(msg)[0] == "?":
                        # answer = retrieve_answer(dec(msg))
                        try:
                            command_dict = dictload(dec(msg)[1:])
                            answer = deepcopy(self.data)
                            for keycopy in ("uuid", "deliverto"):
                                try:
                                    answer[keycopy] = command_dict[keycopy]
                                except KeyError:
                                    pass
                        except IndexError:
                            answer = self.data
                        answer = enc(dictdump(answer))
                        self.comms_tcp.send(answer)
                        # self._logger.debug("zmq: answered tcp")

                    elif dec(msg)[0] == "!":
                        command_dict = dictload(dec(msg)[1:])
                        self.act_on_general(command_dict)
                        answer = self.query_on_command(command_dict)
                        try:
                            for keycopy in ("uuid", "deliverto"):
                                try:
                                    answer[keycopy] = command_dict[keycopy]
                                except KeyError:
                                    pass
                        except TypeError:
                            answer = dict(
                                ERROR=True,
                                Errors="internal error, check device driver logs",
                                uuid=command_dict["uuid"],
                                deliverto=command_dict["deliverto"],
                            )
                        self.comms_tcp.send(enc(dictdump(answer)))
                        # self._logger.debug("zmq: answered tcp")

                    else:
                        self._logger.error(
                            "received unintelligable message: '%s' ", dec(msg)
                        )
                        self.comms_tcp.send(enc(dictdump({"ERROR": True}) + dec(msg)))
                        # self._logger.debug("zmq: answered tcp: ERROR")

            except zmq.Again:
                pass
        if self.comms_downstream in evts:
            try:
                while True:
                    # self._logger.debug("zmq: handling downstream")
                    msg = self.comms_downstream.recv_multipart(zmq.NOBLOCK)
                    command_dict = dictload(dec(msg[1]))
                    self._logger.info(
                        "received command from downstream: %s", command_dict
                    )
                    self.act_on_general(command_dict)
                    self.act_on_command(command_dict)
                    self._logger.debug("zmq: acted on commands")
                    # act on commands!
            except zmq.Again:
                pass

    def act_on_command(self, command: dict) -> None:
        raise NotImplementedError

    def query_on_command(self, command: dict) -> dict:
        raise NotImplementedError

    def send_data_upstream(self):
        self.data["noblock"] = False
        self.data["realtime"] = dt.now()
        self.comms_upstream.send_multipart(
            [self.comms_name.encode("ascii"), enc(dictdump(self.data))]
        )

    def send_noblock_upstream(self):
        self.data["noblock"] = True
        self.data["realtime"] = dt.now()
        self.comms_upstream.send_multipart(
            [self.comms_name.encode("ascii"), enc(dictdump(self.data))]
        )


class zmqMainControl(zmqBare):
    """docstring for zmqDev"""

    def __init__(
        self,
        context=None,
        _ident="mainControl",
        ip_maincontrol="127.0.0.1",
        ip_data="localhost",
        port_reqp_c=5564,
        port_downstream=5562,
        # port_upstream=5558,
        port_data=5563,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self.comms_name = _ident
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.DEALER)
        self.comms_tcp.identity = enc(_ident)  # id
        self.comms_tcp.connect(f"tcp://{ip_maincontrol}:{port_reqp_c}")

        self.comms_data = self._zctx.socket(zmq.DEALER)
        self.comms_data.identity = enc(_ident)  # id
        self.comms_data.connect(f"tcp://{ip_data}:{port_data}")

        self.comms_downstream = self._zctx.socket(zmq.PUB)
        self.comms_downstream.connect(f"tcp://{ip_maincontrol}:{port_downstream}")

        self.comms_inproc = self._zctx.socket(zmq.ROUTER)
        self.comms_inproc.identity = enc(_ident)  # id
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
                    # if dec(message)[0] == "?":
                    #     pass
                    self._logger.warning(
                        "received unexpected message from %s: %s", address, message
                    )
                    # self.comms_tcp.
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
        self._logger.debug(
            "sending command to %s: %s",
            ID,
            message.replace("\n", " ").replace("\r", ""),
        )
        self.comms_downstream.send_multipart([enc(ID), enc(message)])

    def _bare_retrieveDataIndividual(self, dataindicator1, dataindicator2, Live=True):
        uuid_now = uuid.uuid4().hex
        message = enc(
            "?"
            + dictdump(
                dict(
                    instr=dataindicator1, value=dataindicator2, live=Live, uuid=uuid_now
                )
            )
        )
        try:
            message = self._bare_requestData_retries(
                message,
                fun_send=self.comms_data.send,
                fun_recv=self.comms_data.recv,
                id_send=None,
                uuid=uuid_now,
            )
            return message
        except zmq.ZMQError as e:
            self._logger.exception(e)
            # raise problemAbort("")
            return None  # , "zmq error, no data available, abort"

    def retrieveDataMultiple(self, dataindicators: dict, Live=True):
        """dataindicators:
        dict of dicts:
            {
                val1: {"instr": instr1, "value": value1},
                val2: {"instr": instr2, "value": value2},
            }
        """
        uuid_now = uuid.uuid4().hex
        message = enc(
            "?"
            + dictdump(
                dict(
                    multiple=dataindicators,
                    live=Live,
                    uuid=uuid_now,
                )
            )
        )
        try:
            message = self._bare_requestData_retries(
                message,
                fun_send=self.comms_data.send,
                fun_recv=self.comms_data.recv,
                id_send=None,
                uuid=uuid_now,
            )
            return message
        except zmq.ZMQError as e:
            self._logger.exception(e)
            # raise problemAbort("")
            return None  # , "zmq error, no data available, abort"

    def _bare_requestData_retries(
        self,
        message,
        fun_send,
        fun_recv,
        id_send=None,
        retries_n1=10,
        retries_n2=5,
        uuid=None,
    ):
        if id_send:
            fun_send([enc(id_send), enc(message)])
        else:
            fun_send(message)

        time_start = dt.now()
        uuid_back = ""

        while uuid != uuid_back:
            try:
                for _ in range(retries_n2):
                    for _ in range(retries_n1):
                        try:
                            # if id_send:
                            msg = fun_recv(flags=zmq.NOBLOCK)
                            self._logger.debug("received message: %s", msg)
                            answer = dictload(dec(msg))
                            uuid_back = answer["uuid"]
                            self._logger.debug(
                                "received answer, comparing uuids: forward: %s, back: %s",
                                uuid,
                                uuid_back,
                            )
                            if "ERROR" in answer:
                                self._logger.warning(
                                    "received error from data source: %s -- %s",
                                    answer["ERROR_message"],
                                    answer["info"],
                                )
                                try:
                                    if answer["retry"] is True:
                                        self._logger.debug(
                                            "retry in error is True, requesting again"
                                        )
                                        answer = self._bare_requestData_retries(
                                            message,
                                            fun_send,
                                            fun_recv,
                                            id_send,
                                            retries_n1,
                                            retries_n2,
                                            uuid,
                                        )
                                    else:
                                        self._logger.debug(
                                            "retry in error is False, aborting"
                                        )
                                        raise KeyError  # not really the KeyError, but less copying of vode
                                except KeyError:
                                    raise problemAbort(
                                        "problem with data retrieval, possibly the requested data is missing"
                                    )
                            raise successExit
                        except zmq.Again:
                            time.sleep(0.1)
                    self._logger.debug("no answer after 5 trials, sleeping for a while")
                    time.sleep(0.5)
                time_delta = (dt.now() - time_start).seconds
                self._logger.warning(
                    "got no answer from dataStorage within %.0fs", time_delta
                )
                raise problemAbort("data source unresponsive, abort")
            # except zmq.ZMQError as e:
            #     self._logger.exception(e)
            #     # raise problemAbort("")
            #     return None, None
            except successExit:
                # self._logger.debug("received answer, comparing uuids: forward: %s, back: %s", uuid, uuid_back)
                pass
        return answer

    @ExceptionHandling
    def _bare_readDataFromList(
        self, dataindicator1: str, dataindicator2: str, Live: bool = False
    ) -> float:
        """retrieve a datapoint from the central list at dataStorage logging

        check whether the data is up to date (according to dataStorage)
        if it is not uptodate, check how long we were already checking
        data which is present but not up to date indicates the following:
            the device-driver (ControlClient) was running at some point,
            but stopped sending data. This could be because it crashed, or
            because its thread-loop was paused, e.g. for a measurement.

            TODO: send unlock statement to the device we need data from"""
        self._logger.debug(
            "reading data from dataStorage: %s -- %s", dataindicator1, dataindicator2
        )
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
                if not uptodate:
                    time.sleep(0.2)
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
            self._logger.debug("received data from dataStorage: %s", str(data))
            return data  # , None  # second value is indicating no error was raised

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
        # except problemAbort as e:
        #     return None, e

    # @raiseProblemAbort(raising=False)
    def retrieveDataIndividual(self, dataindicator1, dataindicator2, Live=True):
        return self._bare_retrieveDataIndividual(dataindicator1, dataindicator2, Live)

    # @raiseProblemAbort(raising=False)
    def readDataFromList(
        self, dataindicator1: str, dataindicator2: str, Live: bool = False
    ) -> float:
        return self._bare_readDataFromList(dataindicator1, dataindicator2, Live)

    def query_device_data(self, device_id, noblock=False):
        """query data from device directly"""
        uuid_now = uuid.uuid4().hex
        data = "?" + dictdump({"uuid": uuid_now})
        return self._query_device_ensureResult(device_id, data, uuid_now)

    def query_device_command(self, device_id, command=None, **kwargs):
        """dictate action and return answer"""
        uuid_now = uuid.uuid4().hex
        command.update({"uuid": uuid_now})
        data = "!" + dictdump(command)
        # return self._query_device(device_id, data, noblock=noblock)
        return self._query_device_ensureResult(device_id, data, uuid_now, **kwargs)

    def _query_device_ensureResult(self, device_id, msg, uuid_now, **kwargs):
        address = device_id
        message = {"uuid": ""}
        while uuid_now != message["uuid"]:
            self._logger.debug(
                "querying (ensureResult) %s, uuid: %s: %s",
                address,
                uuid_now,
                msg.replace("\n", " ").replace("\r", ""),
            )
            message = self._bare_requestData_retries(
                message=msg,
                fun_send=self.comms_tcp.send_multipart,
                fun_recv=self.comms_tcp.recv,
                id_send=address,
                uuid=uuid_now,
                **kwargs,
            )
            self._logger.debug("received data uuid: %s", message["uuid"])
        return message  # dictload(dec(msg)) already done


class zmqDataStore(zmqBare):
    """docstring for zmqDev"""

    def __init__(
        self,
        context=None,
        _ident="dataStore",
        ip_maincontrol="localhost",
        ip_data="127.0.0.1",
        port_reqp_c=5556,
        port_downstream=5557,
        port_upstream=5559,
        port_data=5563,
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
        self.comms_tcp.connect(f"tcp://{ip_maincontrol}:{port_reqp_c}")

        self.comms_data = self._zctx.socket(zmq.ROUTER)
        self.comms_data.identity = b"dataStore"  # id
        self.comms_data.bind(f"tcp://{ip_data}:{port_data}")

        self.comms_upstream = self._zctx.socket(zmq.SUB)
        self.comms_upstream.connect(f"tcp://{ip_data}:{port_upstream}")
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

    def question_to_self(self, msg):
        if dec(msg)[0] == "?":
            try:
                questiondict = dictload(dec(msg)[1:])
                self._logger.debug("received questiondict: %s", questiondict)
                answer = self.get_answer(questiondict)
            except decoder.JSONDecodeError as e:
                answer = dict(
                    ERROR="ERROR",
                    ERROR_message=e.args[0],
                    info="something went wrong when decoding your json",
                    retry=False,
                )

        else:
            answer = dict(
                ERROR="ERROR",
                ERROR_message="",
                info="I do not know how to handle this request",
                retry=False,
            )

        answer["uuid"] = questiondict["uuid"]
        self._logger.debug("sending answer: %s", answer)
        return dictdump(answer)

    def zmq_handle(self):
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        if self.comms_tcp in evts:
            try:
                while True:
                    msg = self.comms_tcp.recv(zmq.NOBLOCK)
                    answer = self.question_to_self(msg)
                    self.comms_tcp.send(enc(answer))
                    self._logger.debug("sent answer")
                    # do something - most likely hand out data to an asking
                    # process
            except zmq.Again:
                pass
        if self.comms_data in evts:
            self._logger.debug("handling data evt")
            try:
                while True:
                    address, msg = self.comms_data.recv_multipart(zmq.NOBLOCK)
                    self._logger.debug("message received: %s, %s", address, msg)
                    answer = self.question_to_self(msg)
                    self.comms_data.send_multipart([address, enc(answer)])
                    self._logger.debug("sent answer to %s", address)
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
