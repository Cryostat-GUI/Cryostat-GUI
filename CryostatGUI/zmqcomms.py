import zmq
import logging
import time
# from threading import Thread

logger = logging.getLogger('CryostatGUI.zmqComm')


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