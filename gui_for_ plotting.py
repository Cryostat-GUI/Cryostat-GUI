# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'test.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!



#curently works with database name "test" and tabel name measured data,
#all the variable types to be plotted must have numeric types, otherwise
#it won't plot. This is a pretty beta version, but should work, the data is collected by the database!



from PyQt5 import QtCore, QtGui, QtWidgets
import sqlite3
import numpy as np
import matplotlib.pyplot as plt


def connectdb(dbname):
        try:
            global conn
            conn= sqlite3.connect(dbname)
        except sqlite3.connect.Error as err:
            raise AssertionError("Logger: Couldn't establish connection {}".format(err))
# connectdb("test")
connectdb("Log19102018.db")
mycursor = conn.cursor()

#colnames setup, so that the user can choose from in the GUI, the Comboboxes are filled up witth this array
axis=[]
mycursor.execute("SELECT * FROM LakeShore350")
colnames= mycursor.description
for row in colnames:
    axis.append(row[0])



class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(505, 394)
        self.PlotButton = QtWidgets.QDialogButtonBox(Dialog)
        self.PlotButton.setGeometry(QtCore.QRect(330, 360, 161, 32))
        self.PlotButton.setOrientation(QtCore.Qt.Horizontal)
        self.PlotButton.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.PlotButton.setObjectName("PlotButton")
        self.PlotButton.clicked.connect(self.plotstart) #if ok is clicked let's plot
        self.groupBox = QtWidgets.QGroupBox(Dialog)
        self.groupBox.setGeometry(QtCore.QRect(0, 10, 71, 16))
        self.groupBox.setObjectName("groupBox")
        self.groupBox_2 = QtWidgets.QGroupBox(Dialog)
        self.groupBox_2.setGeometry(QtCore.QRect(0, 50, 61, 16))
        self.groupBox_2.setObjectName("groupBox_2")
        self.comboSetX = QtWidgets.QComboBox(Dialog)

        #setting up the combo box for the selection of x and y axes
        self.comboSetX.setGeometry(QtCore.QRect(90, 10, 300, 22))
        self.comboSetX.setTabletTracking(True)
        self.comboSetX.setObjectName("comboSetX")
        self.comboSetX.addItems(axis)
        self.comboSetX.activated.connect(self.xchanged) #signal when the x axis is selected

        self.comboSetY = QtWidgets.QComboBox(Dialog)
        self.comboSetY.setGeometry(QtCore.QRect(90, 50, 300, 22))
        self.comboSetY.setObjectName("comboSetY")
        self.comboSetY.addItems(axis)
        self.comboSetY.activated.connect(self.ychanged)

        self.retranslateUi(Dialog)
        self.PlotButton.accepted.connect(Dialog.accept)
        self.PlotButton.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.groupBox.setTitle(_translate("Dialog", "X-Axis"))
        self.groupBox_2.setTitle(_translate("Dialog", "Y-Axis"))

    #storing the selected X and Y axes for plotting later on
    def xchanged(self):
        global x
        x=self.comboSetX.currentText()
        print("x was set to: ",x)

    def ychanged(self):
        global y
        y=self.comboSetY.currentText()
        print("y was set to: ",y)

    def plotstart(self):
        exportdatatoarr('LakeShore350',x,y)

def exportdatatoarr (tablename,X,Y):
    #this method gets called as soon as "OK" button is pressed

    array=[]

    sql="SELECT {},{} from {} ".format(X,Y,tablename)
    mycursor.execute(sql)
    data =mycursor.fetchall()

    for row in data:
        array.append(list(row))
        # print(row)

    #■plotting
    nparray = np.asarray(array)
    nparray_x = nparray[:,[0]]
    nparray_y = nparray[:,[1]]
    plt.plot(nparray_x,nparray_y, '*')
    #labels:
    plt.xlabel(X)
    plt.ylabel(Y)

    plt.show()





if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    x=ui.comboSetX.currentText()
    y=ui.comboSetY.currentText()
    sys.exit(app.exec_())
conn.close()
