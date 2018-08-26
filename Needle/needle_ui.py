# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\klebe\Daten\python gui Qt Design\NeedleControl.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_NeedleControl(object):
    def setupUi(self, NeedleControl):
        NeedleControl.setObjectName("NeedleControl")
        NeedleControl.resize(237, 162)
        self.centralwidget = QtWidgets.QWidget(NeedleControl)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayoutWidget_5 = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget_5.setGeometry(QtCore.QRect(10, 0, 191, 109))
        self.verticalLayoutWidget_5.setObjectName("verticalLayoutWidget_5")
        self.Needle = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_5)
        self.Needle.setContentsMargins(0, 0, 0, 0)
        self.Needle.setObjectName("Needle")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_NeedleValve = QtWidgets.QLabel(self.verticalLayoutWidget_5)
        self.label_NeedleValve.setObjectName("label_NeedleValve")
        self.horizontalLayout.addWidget(self.label_NeedleValve)
        self.Force_Needle_enable = QtWidgets.QCheckBox(self.verticalLayoutWidget_5)
        self.Force_Needle_enable.setEnabled(False)
        self.Force_Needle_enable.setCheckable(True)
        self.Force_Needle_enable.setChecked(True)
        self.Force_Needle_enable.setObjectName("Force_Needle_enable")
        self.horizontalLayout.addWidget(self.Force_Needle_enable)
        self.Needle.addLayout(self.horizontalLayout)
        self.NeedleValve_bar = QtWidgets.QProgressBar(self.verticalLayoutWidget_5)
        self.NeedleValve_bar.setEnabled(True)
        self.NeedleValve_bar.setProperty("value", 0)
        self.NeedleValve_bar.setObjectName("NeedleValve_bar")
        self.Needle.addWidget(self.NeedleValve_bar)
        self.Needle_slider = QtWidgets.QHBoxLayout()
        self.Needle_slider.setObjectName("Needle_slider")
        self.Slider_Needle = QtWidgets.QSlider(self.verticalLayoutWidget_5)
        self.Slider_Needle.setEnabled(True)
        self.Slider_Needle.setMaximum(100)
        self.Slider_Needle.setOrientation(QtCore.Qt.Horizontal)
        self.Slider_Needle.setObjectName("Slider_Needle")
        self.Needle_slider.addWidget(self.Slider_Needle)
        spacerItem = QtWidgets.QSpacerItem(31, 20, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.Needle_slider.addItem(spacerItem)
        self.Needle.addLayout(self.Needle_slider)
        self.Enable_NeedleValve = QtWidgets.QPushButton(self.verticalLayoutWidget_5)
        self.Enable_NeedleValve.setObjectName("Enable_NeedleValve")
        self.Needle.addWidget(self.Enable_NeedleValve)
        NeedleControl.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(NeedleControl)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 237, 21))
        self.menubar.setObjectName("menubar")
        NeedleControl.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(NeedleControl)
        self.statusbar.setObjectName("statusbar")
        NeedleControl.setStatusBar(self.statusbar)

        self.retranslateUi(NeedleControl)
        # self.Enable_NeedleValve.clicked.connect(self.Slider_Needle.deleteLater)
        self.Enable_NeedleValve.clicked.connect(self.toggle_Needle_slider)

        QtCore.QMetaObject.connectSlotsByName(NeedleControl)

    def retranslateUi(self, NeedleControl):
        _translate = QtCore.QCoreApplication.translate
        NeedleControl.setWindowTitle(_translate("NeedleControl", "MainWindow"))
        self.label_NeedleValve.setText(_translate("NeedleControl", "Needle Valve"))
        self.Force_Needle_enable.setText(_translate("NeedleControl", "Needle on manual"))
        self.Enable_NeedleValve.setText(_translate("NeedleControl", "Force Needle Manual"))


    def toggle_Needle_slider(self):
        if self.Slider_Needle.isEnabled(): 
            self.Slider_Needle.setEnabled(False)
            self.Force_Needle_enable.setChecked(False)
            self.Enable_NeedleValve.setText('Force Needle to Manual')
        else: 
            self.Slider_Needle.setEnabled(True)
            self.Force_Needle_enable.setChecked(True)
            self.Enable_NeedleValve.setText('Put Needle back to Auto')


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    NeedleControl = QtWidgets.QMainWindow()
    ui = Ui_NeedleControl()
    ui.setupUi(NeedleControl)
    NeedleControl.show()
    sys.exit(app.exec_())

