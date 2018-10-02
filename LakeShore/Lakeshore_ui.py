# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Lakeshore_control.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(362, 607)
        self.gridLayout_2 = QtWidgets.QGridLayout(Form)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.textErrors = QtWidgets.QTextBrowser(Form)
        self.textErrors.setObjectName("textErrors")
        self.gridLayout_2.addWidget(self.textErrors, 2, 0, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label_3 = QtWidgets.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.lcdHeaterOutput_mW = QtWidgets.QLCDNumber(Form)
        self.lcdHeaterOutput_mW.setObjectName("lcdHeaterOutput_mW")
        self.gridLayout.addWidget(self.lcdHeaterOutput_mW, 6, 1, 1, 2)
        self.label_6 = QtWidgets.QLabel(Form)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 3, 0, 1, 1)
        self.label_5 = QtWidgets.QLabel(Form)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 6, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(Form)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 5, 0, 1, 1)
        self.lcdSetTemp_K = QtWidgets.QLCDNumber(Form)
        self.lcdSetTemp_K.setObjectName("lcdSetTemp_K")
        self.gridLayout.addWidget(self.lcdSetTemp_K, 0, 2, 1, 1)
        self.spinSetTemp_K = QtWidgets.QDoubleSpinBox(Form)
        self.spinSetTemp_K.setDecimals(4)
        self.spinSetTemp_K.setMaximum(300.0)
        self.spinSetTemp_K.setObjectName("spinSetTemp_K")
        self.gridLayout.addWidget(self.spinSetTemp_K, 0, 1, 1, 1)
        self.lcdSetHeater_mW = QtWidgets.QLCDNumber(Form)
        self.lcdSetHeater_mW.setObjectName("lcdSetHeater_mW")
        self.gridLayout.addWidget(self.lcdSetHeater_mW, 5, 2, 1, 1)
        self.spinSetHeater_mW = QtWidgets.QDoubleSpinBox(Form)
        self.spinSetHeater_mW.setDecimals(1)
        self.spinSetHeater_mW.setMaximum(1000.0)
        self.spinSetHeater_mW.setObjectName("spinSetHeater_mW")
        self.gridLayout.addWidget(self.spinSetHeater_mW, 5, 1, 1, 1)
        self.lcdSensor1_K = QtWidgets.QLCDNumber(Form)
        self.lcdSensor1_K.setObjectName("lcdSensor1_K")
        self.gridLayout.addWidget(self.lcdSensor1_K, 1, 1, 1, 2)
        self.label_2 = QtWidgets.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.lcdSensor2_K = QtWidgets.QLCDNumber(Form)
        self.lcdSensor2_K.setObjectName("lcdSensor2_K")
        self.gridLayout.addWidget(self.lcdSensor2_K, 2, 1, 1, 2)
        self.label_7 = QtWidgets.QLabel(Form)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 4, 0, 1, 1)
        self.lcdSensor3_K = QtWidgets.QLCDNumber(Form)
        self.lcdSensor3_K.setObjectName("lcdSensor3_K")
        self.gridLayout.addWidget(self.lcdSensor3_K, 3, 1, 1, 2)
        self.lcdSensor4_K = QtWidgets.QLCDNumber(Form)
        self.lcdSensor4_K.setObjectName("lcdSensor4_K")
        self.gridLayout.addWidget(self.lcdSensor4_K, 4, 1, 1, 2)
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.label_8 = QtWidgets.QLabel(Form)
        self.label_8.setObjectName("label_8")
        self.gridLayout_2.addWidget(self.label_8, 1, 0, 1, 1)
        self.gridLayout_2.setRowStretch(0, 5)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "LakeShore 350 Control"))
        self.label_3.setText(_translate("Form", "Sens 2"))
        self.label.setText(_translate("Form", "Set Temperature"))
        self.label_6.setText(_translate("Form", "Sens 3"))
        self.label_5.setText(_translate("Form", "Heater Output [mW]"))
        self.label_4.setText(_translate("Form", "Set Heater Ouput [mW]"))
        self.label_2.setText(_translate("Form", "Sens 1"))
        self.label_7.setText(_translate("Form", "Sens 4"))
        self.label_8.setText(_translate("Form", "Error message: "))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

