# from PyQt5 import QtWidgets, QtCore, uic
import sys
from copy import deepcopy
from pickle import dumps, load, loads
from PyQt5.QtCore import QTimer
# import math

class PyMimeData(QtCore.QMimeData):
    """ The PyMimeData wraps a Python instance as MIME data.
    """
    # The MIME type for instances.
    MIME_TYPE = 'application/x-ets-qt4-instance'

    def __init__(self, data=None, **kwargs):
        """ Initialise the instance.
        """
        super(PyMimeData, self).__init__(**kwargs)

        # Keep a local reference to be returned if possible.
        self._local_instance = data

        if data is not None:
            # We may not be able to pickle the data.
            try:
                pdata = dumps(data)
            except:
                return

            # This format (as opposed to using a single sequence) allows the
            # type to be extracted without unpickling the data itself.
            self.setData(self.MIME_TYPE, dumps(data.__class__) + pdata)

    @classmethod
    def coerce(cls, md):
        """ Coerce a QMimeData instance to a PyMimeData instance if possible.
        """
        # See if the data is already of the right type. If it is then we know
        # we are in the same process.
        if isinstance(md, cls):
            return md

        # See if the data type is supported.
        if not md.hasFormat(cls.MIME_TYPE):
            return None

        nmd = cls()
        nmd.setData(cls.MIME_TYPE, md.data())

        return nmd

    def instance(self):
        """ Return the instance.
        """
        if self._local_instance is not None:
            return self._local_instance

        io = StringIO(str(self.data(self.MIME_TYPE)))

        try:
            # Skip the type.
            load(io)

            # Recreate the instance.
            return load(io)
        except:
           pass

        return None

    def instanceType(self):
        """ Return the type of the instance.
        """
        if self._local_instance is not None:
            return self._local_instance.__class__

        try:
            return loads(str(self.data(self.MIME_TYPE)))
        except:
            pass

        return None



# class Node(object):
#     """docstring for Node"""
#     def __init__(self, data):
#         super(Node, self).__init__()
#         self.data = data





class SequenceListModel(QtCore.QAbstractListModel):

    sig_send = QtCore.pyqtSignal(list)

    def __init__(self, sequence = [], parent = None):
        QtCore.QAbstractListModel.__init__(self, parent)
        self.__sequence = sequence
        # self.countinserted = 0
        # self.root = Node(dict(DisplayText='specialnode', arbdata='weha'))
        # self.debug_running()

    def debug_running(self):
        try:
            print(self.__sequence)
        finally:
            QTimer.singleShot(2*1e3,self.debug_running)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return "Sequence"
            else:
                return '{}'.format(section+1)


    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__sequence)

    # def columnCount(self, parent):
    #     return 1

    def data(self, index, role):
        row = index.row()
        if role == QtCore.Qt.EditRole:
            return self.__sequence[row]['DisplayText']
        # if role == QtCore.Qt.ToolTipRole:
        #     return "Hex code: " + self.__sequence[index.row()].name()
        if role == QtCore.Qt.DisplayRole:
            value = self.__sequence[row]['DisplayText']
            return value

    # def setData(self, index, value, role = QtCore.Qt.EditRole):
    #     if role == QtCore.Qt.EditRole:
    #         row = index.row()
    #         self.__sequence[row]['DisplayText'] = value
    #         self.dataChanged.emit(index, index)
    #         return True
    #     return False


    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable#| \
               # QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled


    #=====================================================#
    #INSERTING & REMOVING
    #=====================================================#

    def addItem(self, item):
        parent=QtCore.QModelIndex()
        # print(item, self.rowCount(), self.__sequence)
        self.beginInsertRows(parent, self.rowCount(), self.rowCount())
        self.__sequence.append(item)
        self.endInsertRows()
        # print(item, self.rowCount(), self.__sequence)
        self.dataChanged.emit(parent, parent)

    def clear_all(self):
        parent=QtCore.QModelIndex()
        self.beginRemoveRows(parent, self.rowCount(), self.rowCount())
        self.__sequence = []
        self.endRemoveRows()
        self.dataChanged.emit(parent, parent)


    # -------------------  passing to Gui and writing to file --------------

    def pass_data(self):
        # print(self.__sequence)
        self.sig_send.emit(deepcopy(self.__sequence)) # important for sequence!
        return deepcopy(self.__sequence)



    # ------------------------    drag'n'drop


    # def insertRows(self, position, rows, parent = QtCore.QModelIndex()):
    #     self.beginInsertRows(parent, position, position + rows - 1)
    #     for i in range(rows):
    #         self.__sequence.insert(position, dict(DisplayText='inserted {}'.format(self.countinserted)))
    #         self.countinserted += 1
    #     self.endInsertRows()
    #     self.dataChanged.emit(parent, parent)
    #     return True

    # def removeRows(self, position, rows, parent = QtCore.QModelIndex()):
    #     self.beginRemoveRows(parent, position, position + rows - 1)
    #     for i in range(rows):
    #         value = self.__sequence[position]
    #         self.__sequence.remove(value)
    #     self.endRemoveRows()
    #     return True

    # def insertRow(self, row, parent):
    #     return self.insertRows(row, 1, parent)

    # def removeRow(self, row, parentIndex):
    #     return self.removeRows(row, 1, parentIndex)

    # def mimeTypes(self):
    #     return ['text/xml']

    # def mimeData(self, indexes):
    #     mimedata = QtCore.QMimeData()
    #     mimedata.setData('text/xml', 'mimeData')
    #     return mimedata

    # def dropMimeData(self, data, action, row, column, parent):
    #     print ('dropMimeData {} {} {} {}'.format(data.data('text/xml'), action, row, parent) )
    #     return True


    # def mimeTypes(self):
    #     types = []
    #     types.append('application/x-ets-qt4-instance')
    #     return types

    # def mimeData(self, index):
    #     node = self.__sequence[index[0].row()]
    #     mimeData = PyMimeData(node)
    #     return mimeData


    # def dropMimeData(self, mimedata, action, row, column, parentIndex):
    #     if action == QtCore.Qt.IgnoreAction:
    #         return True

    #     dragNode = mimedata.instance()
    #     # parentNode = self.nodeFromIndex(parentIndex)

    #     # make an copy of the node being moved
    #     newNode = deepcopy(dragNode)
    #     # newNode.setParent(parentNode)
    #     self.insertRow(row, parentIndex)
    #     self.dataChanged.emit(parentIndex, parentIndex)
    #     return True


    # def index(self, row, column, parent):
    #     node = self.nodeFromIndex(parent)
    #     return self.createIndex(row, column)

    # def nodeFromIndex(self, index):
    #     return index.internalPointer() if index.isValid() else self.root




class ScanListModel(QtCore.QAbstractListModel):

    sig_send = QtCore.pyqtSignal(list)
    sig_stepsize = QtCore.pyqtSignal(float)
    sig_Nsteps = QtCore.pyqtSignal(int)

    def __init__(self, signalreceiver, start=None, end=None, Nsteps=None, SizeSteps=None, **kwargs):
        super(ScanListModel, self).__init__(**kwargs)

        self.signalreceiver = signalreceiver
        self.__sequence = []
        self.dic = dict(start=start, end=end, Nsteps=Nsteps, SizeSteps=SizeSteps)
        self.updateData(self.dic)
        self.signalreceiver.sig_updateScanListModel.connect(self.updateData)

        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        # self.countinserted = 0
        # self.root = Node(dict(DisplayText='specialnode', arbdata='weha'))
        # self.debug_running()

    def updateData(self, dic):
        if dic['SizeSteps']:
            self.__sequence = self.Build_Scan_Size(dic['start'], dic['end'], dic['SizeSteps'])
        elif dic['Nsteps']:
            self.__sequence = self.Build_Scan_N(dic['start'], dic['end'], dic['Nsteps'])
        self.debug_running()


    def Build_Scan_N(self, start, end, N):
        N += 1
        stepsize = abs(end-start)/(N-1)
        stepsize = abs(stepsize) if start < end else -abs(stepsize)
        seq = []
        for __ in range(int(N)):
            seq.append(start)
            start += stepsize
        # self.sig_Nsteps.emit(N-1)
        self.sig_stepsize.emit(deepcopy(stepsize))
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        return seq

    def Build_Scan_Size(self, start, end, parameter):
        stepsize = abs(parameter) if start < end else -abs(parameter)
        seq = []
        if start < end:
            while start < end:
                seq.append(start)
                start += stepsize
        else:
           while start > end:
                seq.append(start)
                start += stepsize
        N = len(seq)
        self.sig_Nsteps.emit(deepcopy(N))
        # self.sig_stepsize.emit(stepsize)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        return seq

    def pass_data(self):
        # print(self.__sequence)
        self.sig_send.emit(deepcopy(self.__sequence)) # important for sequence!
        return deepcopy(self.__sequence)



    def debug_running(self):
        try:
            print(self.__sequence)
        finally:
            pass
        #     QTimer.singleShot(2*1e3,self.debug_running)

    def data(self, index, role):
        row = index.row()
        if role == QtCore.Qt.EditRole:
            return self.__sequence[row]
        if role == QtCore.Qt.ToolTipRole:
            return row
        if role == QtCore.Qt.DisplayRole:
            value = self.__sequence[row]
            return value

    def setData(self, index, value, role = QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            row = index.row()
            self.__sequence[row] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.__sequence)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable#  | \
                # QtCore.Qt.ItemIsEditable
               # QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled




if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("plastique")


    #ALL OF OUR VIEWS
    listView = QtWidgets.QListView()
    listView.show()
    # listView.setAcceptDrops(True)
    listView.setFrameShape(QtWidgets.QFrame.StyledPanel)
    listView.setFrameShadow(QtWidgets.QFrame.Sunken)
    # listView.setDragEnabled(True)
    # listView.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
    # listView.setDefaultDropAction(QtCore.Qt.MoveAction)
    listView.setAlternatingRowColors(True)
    # listView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    # listView.setTextElideMode(QtCore.Qt.ElideRight)
    # listView.setMovement(QtWidgets.QListView.Free)
    # listView.setFlow(QtWidgets.QListView.TopToBottom)
    # listView.showDropIndicator()


    first = dict(DisplayText='first', arbdata = 'arvb')
    second = dict(DisplayText='second', arbdata = 'arvb')
    third = dict(DisplayText='third', arbdata = 'arvb')
    fourth = dict(DisplayText='fourth', arbdata = 'arvb')
    five = dict(DisplayText='five', arbdata = 'arvb')







    model = SequenceListModel([first, second, third])
    model.addItem(fourth)

    # model.addItem(dict(DisplayText='wuha', arbdata='noha'))

    listView.setModel(model)

    model.pass_data()

    sys.exit(app.exec_())