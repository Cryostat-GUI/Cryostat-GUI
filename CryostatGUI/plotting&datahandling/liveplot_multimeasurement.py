import sqlite3
import matplotlib.pyplot as plt
import matplotlib.animation as animation
# import time
import pandas as pd
import numpy as np


filebase = './../Logs/'
data_static = [dict(filename=filebase + 'cooldown_20200422_2.db',
                    label='0 deg', df=None), 
              ]
data_dyn = [dict(filename=filebase + 'cooldown_20200422_3.db',
                 label='45 deg', df=None)]

fig = plt.figure()
ax1 = fig.add_subplot(111)
for static in data_static:
    line, = ax1.plot([], [], 'o-',
                     markersize=5, label=static['label'])
    static['lineactor'] = line
for dyn in data_dyn:
    line, = ax1.plot([], [], 'o-', markersize=5, label=dyn['label'])
    dyn['lineactor'] = line

ax1.set_ylabel('SampleResistance_Ohm')
ax1.set_xlabel('Temperature K')  # overwrite the x-label added by `psd`
plt.legend()


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


def conf(datafile):
    conn = create_connection(datafile)

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

    df = pd.DataFrame(dict(times_res=times1, res=res,
                           times_temps=times2, temps=temps))
    return df


def plotting(i, first=False):
    global data_static
    global data_dyn

    for dyn in data_dyn:
        df = dyn['df']

        conn = create_connection(dyn['filename'])

        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT SampleResistance_Ohm from SR830 ORDER BY id DESC LIMIT 1")
            res = np.array(cur.fetchall())[:, 0]
            cur.execute(
                "SELECT timeseconds from SR830 ORDER BY id DESC LIMIT 1")
            times1 = np.array(cur.fetchall())[:, 0]

            cur.execute(
                "SELECT Sensor_1_K from LakeShore350 ORDER BY id DESC LIMIT 1")
            temps = np.array(cur.fetchall())[:, 0]
            cur.execute(
                "SELECT timeseconds from LakeShore350 ORDER BY id DESC LIMIT 1")
            times2 = np.array(cur.fetchall())[:, 0]

        # arr = np.array([times1, times2]).T
        # print(arr)

        # df = pd.DataFrame(dict(times_res=times1, res=res,
        #                        times_temps=times2, temps=temps))
        df = df.append(dict(times_res=times1, res=res,
                            times_temps=times2, temps=temps), ignore_index=True)
        dyn['df'] = df
        plot_res = df.loc[df.times_res - df.times_temps < 1, 'res']
        plot_temp = df.loc[df.times_res - df.times_temps < 1, 'temps']

        dyn['lineactor'].set_xdata(plot_temp)
        dyn['lineactor'].set_ydata(plot_res)

    if first:

        for static in data_static:
            df = static['df']
            plot_res = df.loc[df.times_res - df.times_temps < 1, 'res']
            plot_temp = df.loc[df.times_res - df.times_temps < 1, 'temps']
            static['lineactor'].set_xdata(plot_temp)
            static['lineactor'].set_ydata(plot_res)

    for a in [ax1]:
        a.relim()
        a.autoscale_view()


if __name__ == '__main__':

    for static in data_static:
        static['df'] = conf(static['filename'])
    for dyn in data_dyn:
        dyn['df'] = conf(dyn['filename'])

    plotting(0, first=True)

    ani = animation.FuncAnimation(fig, plotting, interval=10 * 1e3)
    plt.show()
