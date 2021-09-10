#!/usr/bin/python
# -*- coding: UTF-8 -*-
#This broker subscribes to all applications. 
#If an application sends a signal, the Broker will publish the signal to all ControlClients subscribed to this broker.
import zmq


def main():

    context = zmq.Context()

    # Socket facing producers
    frontend = context.socket(zmq.XPUB)
    frontend.bind("tcp://127.0.0.1:5561")

    # Socket facing consumers
    backend = context.socket(zmq.XSUB)
    backend.bind("tcp://127.0.0.1:5562")

    zmq.proxy(frontend, backend)

    # We never get here…
    frontend.close()
    backend.close()
    context.term()

if __name__ == "__main__":
    main()
