from PyQt5 import QtWidgets

from util import Window_plotting


if __name__ == '__main__':
    import numpy as np
    # import random
    import sys

    start_time = 0
    stop_time = 60 * 2

    num = stop_time - start_time + 1

    start_temp = 1
    stop_temp = 3

    time = np.linspace(start_time, stop_time, num)
    temps = np.linspace(start_temp, stop_temp, num)

    data = np.column_stack((time, temps)).transpose()

    app = QtWidgets.QApplication(sys.argv)
    info = dict(data=data,  # [random.random() for i in range(10)],
                title='random data',
                label_x='x-axis',
                label_y='y-axis')

    main = Window_plotting(**info)
    main.show()

    sys.exit(app.exec_())
