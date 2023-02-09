#!/usr/bin/python
# -*- coding: UTF-8 -*-
# This broker subscribes to all applications (MainControl instances, i.e. "directors" who send commands through this channel).
# If an application sends a signal, the Broker will publish the signal to all ControlClients subscribed to this broker.
# This is the channel referred to as "downstream"
import zmq


def main():

    context = zmq.Context()

    # Socket facing consumers (i.e. we are publishing what we received on the backend to the frontend, in this case the ControlClients)
    frontend = context.socket(zmq.XPUB)
    frontend.bind("tcp://192.168.1.101:5561")

    # Socket facing producers (i.e. we subscribe to the applications, in this case the MainControls)
    backend = context.socket(zmq.XSUB)
    backend.bind("tcp://192.168.1.101:5562")

    zmq.proxy(frontend, backend)

    # We never get here…
    frontend.close()
    backend.close()
    context.term()


if __name__ == "__main__":
    import logging

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    handler_info = logging.StreamHandler()  # logging.DEBUG, sys.stdout)
    handler_info.setLevel(logging.DEBUG)
    formatter_info = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s"
    )
    handler_info.setFormatter(formatter_info)

    # logger.addHandler(handler_debug)
    logger.addHandler(handler_info)

    main()
