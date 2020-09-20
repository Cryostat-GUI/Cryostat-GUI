"""Documentation for usable functions in measuring scripts, to be injected by a user"""

t1 = self.temperature_sample
rho, I, V = AbstractMeasureResistance()
t2 = self.temperature_sample
t_mean = np.mean(t1, t2)
t_std = np.std(t1, t2)
df = pd.DataFrame(dict(temperature=[t_mean],
                       temperature_std=[t_std],
                       rho=[rho['coeff']],
                       rho_residuals=[rho['residuals']],))

with open(self.datafile, 'a', newline='') as f:
    df.tail(1).to_csv(f, header=f.tell() == 0)
