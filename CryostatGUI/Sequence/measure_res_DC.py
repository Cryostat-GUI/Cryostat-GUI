"""Documentation for usable functions in measuring scripts, to be injected by a user"""
# import pandas as pd

self._logger.info("MEASURING -- MEASURING -- MEASURING")

t1 = self.getTemperature_force(sensortype="sample")
# rho, I, V = AbstractMeasureResistance()

# res = self.query_device_command(
#     "SR860_1",
#     command={"measure_Resistance": None},
#     retries_n1=10,
#     retries_n2=5,
# )

t2 = self.getTemperature_force(sensortype="sample")

t_mean = np.mean([t1, t2])
t_std = np.std([t1, t2])
# df = pd.DataFrame(
d = dict(
    temperature=[t_mean],
    temperature_std=[t_std],
    rho=[res["SampleResistance_Ohm"]],
    # rho=[rho["coeff"]],
    # rho_residuals=[rho["residuals"]],
)
# )

# self.datafile = "C:/Users/Lab-user/Dropbox/SPLITCOIL_data/tests/second.csv"
self.measuring_store_data(data=d, datafile=self.datafile)


# with open(self.datafile, "a", newline="") as f:
#     df.tail(1).to_csv(f, header=f.tell() == 0, index=False)

# print("Temperature:", self.getTemperature_force(sensortype="sample"))
