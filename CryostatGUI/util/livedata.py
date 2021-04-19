import logging
from prometheus_client import start_http_server
from prometheus_client import Gauge


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
            except TypeError as err:
                if not err.args[0].startswith(
                    "float() argument must be a string or a number"
                ):
                    self._logger.exception(err.args[0])
                else:
                    # self._logger.debug(err.args[0] + f'instr:
                    # {instr}, varkey: {varkey}')
                    pass
                    # raise err
            except ValueError as err:
                if not err.args[0].startswith("could not convert string to float"):
                    self._logger.exception(err.args[0])
                else:
                    # self._logger.debug(err.args[0] + f'instr:
                    # {instr}, varkey: {varkey}')
                    pass
                    # raise err
            except KeyError:
                self._gauges[variablekey] = Gauge(
                    "CryoGUIservice_{}_{}".format(self._prometheus_name, variablekey),
                    "no description",
                )
                self._gauges[variablekey].set(self.data[variablekey])
