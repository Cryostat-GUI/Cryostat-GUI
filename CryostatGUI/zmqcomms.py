import zmq
import logging
from json import loads as dictload
from json import dumps
from json import decoder
import functools

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


class genericAnswer(Exception):
    pass


class customEx(Exception):
    pass


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
                raise customEx
            except zmq.Again:
                time.sleep(0.2)
                logger.debug("no answer")

    except zmq.ZMQError as e:
        logger.exception("There was an error in the zmq communication!", e)
        return -1
    except customEx:
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
                raise customEx
            except zmq.Again:
                time.sleep(0.2)
                logger.debug("no answer")

    except zmq.ZMQError as e:
        logger.exception("There was an error in the zmq communication!", e)
        return -1
    except customEx:
        return message


class zmqBare(object):
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
        *args,
        **kwargs,
    ):
        # print('zmqClient')
        super().__init__(*args, **kwargs)
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
        self.comms_downstream.setsockopt(
            # zmq.SUBSCRIBE, b'')
            zmq.SUBSCRIBE,
            self.comms_name.encode("ascii"),
        )

        self.comms_upstream = self._zctx.socket(zmq.PUB)
        self.comms_upstream.connect(f"tcp://{ip_data}:{port_upstream}")

        self.poller = zmq.Poller()
        self.poller.register(self.comms_tcp, zmq.POLLIN)
        self.poller.register(self.comms_downstream, zmq.POLLIN)

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

    def act_on_command(self, command: dict) -> None:
        raise NotImplementedError

    def send_data_upstream(self):
        self.comms_upstream.send_multipart(
            [self.comms_name.encode("ascii"), enc(dictdump(self.data))]
        )

    def running(self):
        self.data = {}
        super().running()


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
        port_upstream=5558,
        port_data=5559,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
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
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
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
