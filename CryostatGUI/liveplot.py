import sqlite3
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import pandas as pd
import numpy as np

data = 'Logs/cooldown_20200422.db'

fig = plt.figure()
ax1 = fig.add_subplot(111)


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    # try:
    conn = sqlite3.connect(db_file)
    # except Error as e:
    #     print(e)

    return conn


def plotting(i):
    conn = create_connection(data)

    with conn:
        cur = conn.cursor()
        cur.execute("SELECT SampleResistance_Ohm from SR830")
        res = np.array(cur.fetchall())[:, 0]
        cur.execute("SELECT timeseconds from SR830")
        times1 = np.array(cur.fetchall())[:, 0]

        cur.execute("SELECT Sensor_1_K from LakeShore350")
        temps = np.array(cur.fetchall())[:, 0]
        cur.execute("SELECT timeseconds from LakeShore350")
        times2 = np.array(cur.fetchall())[:, 0]

    # arr = np.array([times1, times2]).T
    # print(arr)

    df = pd.DataFrame(dict(times_res=times1, res=res, times_temps=times2, temps=temps))
    plot_res = df.loc[df.times_res - df.times_temps < 1 , 'res']
    plot_temp = df.loc[df.times_res - df.times_temps < 1 , 'temps']
    # print(df.times_res)

    ax1.clear()
    # ax1.plot(a0ar,a4ar, 'o')
    ax1.plot(plot_temp, plot_res, 'o', color='b')
    # ax1.plot(roll['set_pressure'], roll['resistivity'], '-', color='r')
    # overwrite the x-label added by `psd`
    ax1.set_ylabel('SampleResistance_Ohm')
    ax1.set_xlabel('Temperature K')  # overwrite the x-label added by `psd`


plotting(0)

ani = animation.FuncAnimation(fig, plotting, interval=10 * 1e3)
plt.show()
