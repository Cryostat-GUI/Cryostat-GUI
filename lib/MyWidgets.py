

from inspect import getmembers

from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets, QtCore

import re


dropstring = re.compile(r'([a-zA-Z0-9])')


class sequence_listwidget(QtWidgets.QListWidget):
    """docstring for Sequence_ListWidget"""

    sig_dropped = pyqtSignal(object)

    def __init__(self, cls, **kwargs):
        super(sequence_listwidget, self).__init__(**kwargs)

        self.setAcceptDrops(True)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setTextElideMode(QtCore.Qt.ElideRight)
        self.setMovement(QtWidgets.QListView.Free)
        self.setFlow(QtWidgets.QListView.TopToBottom)
        self.setObjectName("listSequence")


    def dropEvent(self, event):
        # self.sig_dropped.emit(event.mimeData().formats())
        data = self.parse_stringdata(event.mimeData().data('application/x-qabstractitemmodeldatalist'))
        # self.sig_dropped.emit(getmembers(event))
        if not data in ['Wait']:#, 'SetTemperature', 'SetField']: 
            super(sequence_listwidget, self).dropEvent(event)
        else: 
            self.sig_dropped.emit(data)
        event.accept()


    def parse_stringdata(self, data):
        string = str(data.data().decode('utf-8'))
        res = ''
        for x in dropstring.findall(string): 
            res += x
        return res
        