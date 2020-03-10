import zmq
import logging
import time
# from threading import Thread

logger = logging.getLogger('CryostatGUI.zmqComm')


class genericAnswer(Exception):
    pass


class customEx(Exception):
    pass


class ZMQdevice(object):
    """docstring for ZMQdevice"""

    def __init__(self, zmqcontext=None, port=5556, *args, **kwargs):
        super(ZMQdevice, self).__init__(*args, **kwargs)
        try:

            self.zmq_tcp = self.zmq_context.socket(zmq.REP)
        except AttributeError:
            self.zmqcontext = zmq.Context()
            self.zmq_tcp = self.zmq_context.socket(zmq.REP)

        self.zmq_tcp.bind(f"tcp://*:{port}")


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
                print('no answer')
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
                print('no answer')
    except zmq.ZMQError as e:
        logger.exception('There was an error in the zmq communication!', e)
        return -1
    except customEx:
        return message
