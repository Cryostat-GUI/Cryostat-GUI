import logging
from prometheus_client import start_http_server
from prometheus_client import Gauge

# from prometheus_client.exposition import REGISTRY
# from prometheus_client.exposition import make_wsgi_app
# from prometheus_client.exposition import make_server
# from prometheus_client.exposition import ThreadingWSGIServer
# from prometheus_client.exposition import _SilentHandler
# import threading


# def start_wsgi_server(port, addr='', registry=REGISTRY):
#     """Starts a WSGI server for prometheus metrics as a daemon thread."""
#     app = make_wsgi_app(registry)
#     httpd = make_server(addr, port, app, ThreadingWSGIServer, handler_class=_SilentHandler)
#     t = threading.Thread(target=httpd.serve_forever)
#     t.daemon = True
#     t.start()
#     return t, httpd


# start_http_server_custom = start_wsgi_server
# start_http_server = start_http_server_custom


class PrometheusGaugeClient:
    """docstring for PrometheusGaugedclient"""

    def __init__(self, *args, prometheus_port=None, prometheus_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._prometheus_port = prometheus_port
        # self._prometheus_initialised = None
        self._prometheus_name = prometheus_name
        self._logger = logging.getLogger(
            "CryoGUI." + __name__ + "." + self.__class__.__name__
        )
        self._gauges = {}

        if None not in (self._prometheus_port, self._prometheus_name):
            self._prometheus_enabled = True
            self._logger.debug("prometheus is enabled here!")
        else:
            self._prometheus_enabled = False

    def start_server(self):
        self._prometheus_thread, self._prometheus_server = start_http_server_custom(
            self._prometheus_port
        )

    def stop_server(self):
        pass

    def run_prometheus(self):
        if self._prometheus_enabled:
            # if self.run_finished:
            try:
                self._prometheus_initialised
            except AttributeError:
                self.initialise_gauges()
                self._prometheus_initialised = True
            self.set_gauges()

    def initialise_gauges(self):
        self._logger.debug(
            "initialising prometheus client service for %s on port %s",
            self._prometheus_name,
            self._prometheus_port,
        )
        for variablekey in self.data:
            self._gauges[variablekey] = Gauge(
                "CryoGUIservice_{}_{}".format(self._prometheus_name, variablekey),
                "no description",
            )
        self.set_gauges()
        start_http_server(self._prometheus_port)

    def set_gauges(self):
        # self._logger.debug("setting prometheus metrics")
        for variablekey in self.data:
            try:
                self._gauges[variablekey].set(self.data[variablekey])
                # self.Gauges[instr][varkey].set(dic[varkey])
            except TypeError as err:
                if not err.args[0].startswith(
                    "float() argument must be a string or a number"
                ):
                    self._logger.exception(err.args[0])
                else:
                    # self._logger.debug(err.args[0] + f'instr:
                    # {instr}, varkey: {varkey}')
                    pass
            except ValueError as err:
                if not err.args[0].startswith("could not convert string to float"):
                    self._logger.exception(err.args[0])
                else:
                    # self._logger.debug(err.args[0] + f'instr:
                    # {instr}, varkey: {varkey}')
                    pass
