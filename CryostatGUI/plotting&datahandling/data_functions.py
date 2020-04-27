import sqlite3
import pandas as pd
import numpy as np


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

    df = pd.DataFrame(dict(times_temps=times2, temps=temps,
                           times_res=times1, res=res,))
    return df
