from data_functions import conf
import shutil

filebase = "./../Logs/"
data = filebase + "cooldown_20200422_19.db"


if __name__ == "__main__":

    df = conf(data)
    df = df.loc[df.times_res - df.times_temps < 1]
    # print(df.iloc[:, 1:4:2])
    dfexp = df.iloc[:, 1:4:2]
    # print(data[10:-3])
    newfile = data[10:-3] + ".dat"
    dfexp.to_csv(newfile, index=False)
    shutil.copyfile(
        newfile, "C:/Users/Lab-user/Dropbox/SPLITCOIL_data/Eugen_27_M2/" + newfile
    )
