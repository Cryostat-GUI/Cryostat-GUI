
from data_functions import conf

filebase = './../Logs/'
data = filebase + 'cooldown_20200422_5.db'


if __name__ == '__main__':

    df = conf(data)
    df = df.loc[df.times_res - df.times_temps < 1]
    # print(df.iloc[:, 1:4:2])
    dfexp = df.iloc[:, 1:4:2]
    # print(data[10:-3])
    dfexp.to_csv(data[10:-3] + '.dat', index=False)
