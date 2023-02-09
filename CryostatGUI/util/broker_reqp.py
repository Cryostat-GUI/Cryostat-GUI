"""This broker connects controlling nodes with ControlClients which may be controlled

It is different from the two other brokers, in that it does not shuffle
messages from connections it subsribed to, by publishing them forward,
(this would be one way only), but it is a broker for req-rep patterns.
Thus, multiple GUI instances, or Sequence instances can work in parallel
"""
import logging
import zmq
import time

# from zmqcomms import dec, enc, dictdump
from json import loads as dictload
from json import dumps


def enc(msg):
    return "{}".format(msg).encode("utf-8")


def dec(msg):
    return msg.decode("utf-8")


def dictdump(d):
    return dumps(d, indent=4, sort_keys=True, default=str)


port_backend = 5556
port_frontend = 5564

logger = logging.getLogger()


def main():

    context = zmq.Context()

    # establish sockets
    logger.debug("establishing sockets")
    frontend = context.socket(zmq.ROUTER)
    backend = context.socket(zmq.ROUTER)

    # define ports
    logger.debug("defining ports ")
    frontend.bind(f"tcp://192.168.1.101:{port_frontend}")
    backend.bind(f"tcp://192.168.1.101:{port_backend}")

    # register polling events
    logger.debug("register polling events")
    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend, zmq.POLLIN)

    logger.debug("starting loop")
    while True:
        time.sleep(0.01)
        evts = dict(poller.poll(zmq.DONTWAIT))
        # logger.debug("handling evts")

        if frontend in evts:
            logger.debug("frontend received")
            sender, deliverto, message = frontend.recv_multipart()
            logger.debug("frontend received: %s, %s, %s", sender, deliverto, message)

            m = dec(message)
            m_payload = dictload(m[1:])
            m_command = m[0]

            newmessage = m_payload
            newmessage["deliverto"] = dec(sender)
            everything_new = [deliverto, enc(m_command + dictdump(newmessage))]

            logger.debug("sending to backend: %s", everything_new)
            backend.send_multipart(everything_new)

        if backend in evts:
            logger.debug("backend received")
            sender, message = backend.recv_multipart()
            logger.debug("backend received: %s, %s", deliverto, message)

            m = dictload(dec(message))
            deliverto = enc(m["deliverto"])
            sending_now = [deliverto, message]
            logger.debug("sending to frontend: %s", sending_now)
            frontend.send_multipart(sending_now)

    frontend.close()
    backend.close()
    context.term()


if __name__ == "__main__":

    logger.setLevel(logging.DEBUG)

    # from datetime import datetime as dt
    # date = dt.now().strftime("%Y%m%d-%H%M%S")

    # handler_debug = logging.FileHandler(
    #     filename=f"Logs/broker_reqp_{date}.log", mode="a"
    # )
    # handler_debug.setLevel(logging.DEBUG)
    # formatter_debug = logging.Formatter(
    #     "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    # )
    # handler_debug.setFormatter(formatter_debug)

    handler_info = logging.StreamHandler()  # logging.DEBUG, sys.stdout)
    handler_info.setLevel(logging.DEBUG)
    formatter_info = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    )
    handler_info.setFormatter(formatter_info)

    # logger.addHandler(handler_debug)
    logger.addHandler(handler_info)

    main()
