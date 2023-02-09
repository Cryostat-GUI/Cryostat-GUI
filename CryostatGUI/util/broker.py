#!/usr/bin/python
# -*- coding: UTF-8 -*-
# This broker subscribes to all ControlClients (i.e. the "actors" which instantiate a device driver to talk to a hardware device).
# If a ControlClient sends a signal the Broker will publish the signal to all applications subscribed to the broker.
# This is the channel referred to as "upstream"
import zmq


def main():

    context = zmq.Context()

    # Socket facing consumers (i.e MainControls)
    frontend = context.socket(zmq.XPUB)
    frontend.bind("tcp://*:5559")

    # Socket facing producers (i.e. ControlClients)
    backend = context.socket(zmq.XSUB)
    backend.bind("tcp://*:5560")

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
