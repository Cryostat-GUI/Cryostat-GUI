import zmq
import logging
from time import sleep as timesleep
from json import loads as dictload
from json import dumps
# from threading import Thread

logger = logging.getLogger('CryostatGUI.zmqComm')


def enc(msg):
    return u'{}'.format(msg).encode('utf-8')


def dec(msg):
    return msg.decode('utf-8')


def dictdump(d):
    return dumps(d, indent=4, sort_keys=True, default=str)


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
            logger.debug(f'received message: {message}')
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
        socket.send_string(f'{query}')
        while True:
            try:
                message = socket.recv(flags=zmq.NOBLOCK)
                raise customEx
            except zmq.Again:
                time.sleep(0.2)
                logger.debug('no answer')

    except zmq.ZMQError as e:
        logger.exception('There was an error in the zmq communication!', e)
        return -1
    except customEx:
        return message


def zmqquery_dict(socket, query):
    # signal.signal(signal.SIGINT, signal.SIG_DFL);
    # context = zmq.Context()
    # socket = context.socket(zmq.REQ)
    # socket.connect("tcp://localhost:5556")
    try:
        socket.send_string(f'{query}')
        while True:
            try:
                message = socket.recv_json(flags=zmq.NOBLOCK)
                raise customEx
            except zmq.Again:
                time.sleep(0.2)
                logger.debug('no answer')

    except zmq.ZMQError as e:
        logger.exception('There was an error in the zmq communication!', e)
        return -1
    except customEx:
        return message


class zmqBare(object):
    """docstring for zmqBare"""
    pass


class zmqClient(zmqBare):
    """docstring for zmqDev"""

    def __init__(self, context=None, identity=None, ip_maincontrol='localhost', ip_storage='localhost', port_reqp=5556, port_downstream=5557, port_upstream=5558, *args, **kwargs):
        # print('zmqClient')
        super().__init__(*args, **kwargs)
        self.comms_name = identity
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.DEALER)
        self.comms_tcp.identity = u'{}'.format(
            identity).encode('ascii')  # id
        self.comms_tcp.connect(f'tcp://{ip_maincontrol}:{port_reqp}')

        self.comms_downstream = self._zctx.socket(zmq.SUB)
        self.comms_downstream.connect(f'tcp://{ip_maincontrol}:{port_downstream}')
        self.comms_downstream.setsockopt(
            zmq.SUBSCRIBE, u'{}'.format(self.comms_name).encode('ascii'))
        # zmq.SUBSCRIBE, b'')

        self.comms_upstream = self._zctx.socket(zmq.PUB)
        self.comms_upstream.connect(f'tcp://{ip_storage}:{port_upstream}')

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

    def zmq_handle(self):
        # print('zmq handling')
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        if self.comms_tcp in evts:
            try:
                while True:
                    msg = self.comms_tcp.recv(zmq.NOBLOCK)
                    if msg.decode('utf-8')[-1] == '?':
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
                    try:
                        if 'lock' in command_dict:
                            self.lock.acquire()
                        elif 'unlock' in command_dict:
                            self.lock.release()
                    except AttributeError as e:
                        logger.exception(e)
                    self.act_on_command(command_dict)
                    # act on commands!
            except zmq.Again:
                pass

    def act_on_command(self, command: dict) -> None:
        raise NotImplementedError

    def send_data_upstream(self):
        self.comms_upstream.send_multipart(
            [self.comms_name, enc(dictdump(self.data))])


class zmqMainControl(zmqBare):
    """docstring for zmqDev"""

    def __init__(self, context=None, _ident='mainControl', ip_maincontrol='*', port_reqp=5556, port_downstream=5557, port_upstream=5558, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.comms_name = _ident
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.ROUTER)
        self.comms_tcp.identity = b'mainControl'  # id
        self.comms_tcp.bind(f'tcp://{ip_maincontrol}:{port_reqp}')

        self.comms_downstream = self._zctx.socket(zmq.PUB)
        self.comms_downstream.bind(f'tcp://{ip_maincontrol}:{port_downstream}')

        self.comms_inproc = self._zctx.socket(zmq.ROUTER)
        self.comms_inproc.identity = b'mainControl'  # id
        self.comms_inproc.bind(f'inproc://main')
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
                    msg = self.comms_tcp.recv_multipart(
                        zmq.NOBLOCK)
                    address, message = msg[0], msg[1]
                    if message.decode('utf-8')[-1] == '?':
                        pass
                    # do something, most likely this will not be used
                    # extensively
            except zmq.Again:
                pass
        if self.comms_inproc in evts:
            try:
                while True:
                    msg = self.comms_inproc.recv_multipart(
                        zmq.NOBLOCK)
                    address, message = msg[0], msg[1]
                    if message.decode('utf-8')[-1] == '?':
                        pass
                        # do something - here, most likely a query is passed on to
                        # the dataStore, and the answer is returned in turn
                        self.comms_inproc.send_multipart(
                            [b'dataStore', message])
                        _, data = self.comms_inproc.recv_multipart()
                        self.comms_tcp.send_multipart([address, data])
            except zmq.Again:
                pass


class zmqDataStore(zmqBare):
    """docstring for zmqDev"""

    def __init__(self, context=None, _ident='dataStore', ip_maincontrol='localhost', ip_storage='*', port_reqp=5556, port_downstream=5557, port_upstream=5558, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.comms_name = _ident
        self._zctx = context or zmq.Context()
        self.comms_tcp = self._zctx.socket(zmq.DEALER)
        self.comms_tcp.identity = b'dataStore'  # id
        self.comms_tcp.connect(f'tcp://{ip_maincontrol}:{port_reqp}')

        self.comms_upstream = self._zctx.socket(zmq.SUB)
        self.comms_upstream.bind(f'tcp://{ip_storage}:{port_upstream}')
        self.comms_upstream.setsockopt(zmq.SUBSCRIBE, b'')

        self.poller = zmq.Poller()
        self.poller.register(self.comms_tcp, zmq.POLLIN)
        self.poller.register(self.comms_upstream, zmq.POLLIN)

    def zmq_handle(self):
        evts = dict(self.poller.poll(zmq.DONTWAIT))
        if self.comms_tcp in evts:
            try:
                while True:
                    msg = self.comms_tcp.recv(zmq.NOBLOCK)
                    if msg.decode('utf-8')[-1] == '?':
                        answer = self.get_answer(msg)
                        self.comms_tcp.send(enc(answer))
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

    def store_data(self, id, data):
        raise NotImplementedError

    def get_answer(self, msg):
        raise NotImplementedError

    def send_data_upstream(self, data):
        """dummy method so this class can easily be exchanginly used with zmqClient"""
        pass
