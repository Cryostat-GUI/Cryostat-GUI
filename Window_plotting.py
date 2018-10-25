import sys
from PyQt5 import QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import random

class Window_plotting(QtWidgets.QDialog):
    def __init__(self, data, label_x, label_y, title, parent=None):
        super().__init__()
        self.data = data
        self.label_x = label_x
        self.label_y = label_y
        self.title = title

        # a figure instance to plot on
        self.figure = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Just some button connected to `plot` method
        self.button = QtWidgets.QPushButton('Plot')
        self.button.clicked.connect(self.plot)

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def plot(self):
        ''' plot some random stuff '''
        # random data
        data = self.data # [random.random() for i in range(10)]

        # create an axis
        ax = self.figure.add_subplot(111)

        # discards the old graph
        ax.clear()

        # plot data
        ax.plot(data, '*-')
        ax.set_title(self.title)
        ax.set_xlabel(self.label_x)
        ax.set_ylabel(self.label_y)

        # refresh canvas
        self.canvas.draw()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    info = dict(data = [random.random() for i in range(10)],
                title = 'random data',
                label_x = 'x-axis',
                label_y='y-axis')


    main = Window_plotting(**info)
    main.show()

    sys.exit(app.exec_())