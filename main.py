"""
Main Program
"""
import sys
import time
import re

import serial
import serial.tools.list_ports

import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from pyqtgraph import dockarea as pgda
from pyqtgraph import parametertree as pgpt
from pyqtgraph.parametertree import parameterTypes as pgptype

global g_state
global g_samples
global g_period
global g_plot_samples
g_state = None
g_samples = 50
g_period = 1.0
g_plot_samples = 1



class DeviceParameter(pgptype.GroupParameter):
    """
    Device Parameter
    """
    global g_samples
    global g_period
    sigConnectionChanged = QtCore.pyqtSignal(bool)

    def __init__(self, **opts):
        opts['type'] = 'bool'
        opts['value'] = True
        pgptype.GroupParameter.__init__(self, **opts)

        self.addChild({'name': '  Connect  ', 
                       'type': 'action'})
        self.addChild({'name': 'Port',
                       'type': 'list', 
                       'values': ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2'], 
                       'value': '/dev/ttyACM0'})
        self.p_btn  = self.param('  Connect  ')
        self.p_port = self.param('Port')
        self.p_btn.sigActivated.connect(self.connect)
        self.usb_serial = None

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_device)
        self.timer.start(2000)

    def check_device(self):
        ports = serial.tools.list_ports.comports()
        if ports:
            ports = [i[0] for i in ports if i[0].count('/dev/ttyACM')]
        self.p_port.setLimits(ports)

    def has_serial(self):
        return self.usb_serial is not None

    def connect(self):
        if self.p_btn.name() == '  Connect  ':
            port = self.p_port.value()
            ports = serial.tools.list_ports.comports()
            if ports and port in [i[0] for i in ports]:
                try:
                    self.usb_serial = serial.Serial(port, 115200)
                except serial.SerialException as e:
                    print(e)
                    return
                self.p_btn.setName('  Disconnect  ')
                self.sigConnectionChanged.emit(True)
            else:
                self.usb_serial = None
        else:
            self.p_btn.setName('  Connect  ')
            self.usb_serial = None
            self.sigConnectionChanged.emit(False)

    def send_and_recieve(self, commands):
        if self.usb_serial is None:
            return
        for command in commands:
            self.usb_serial.write(command)

        messages = []
        while self.usb_serial.inWaiting():
            s = self.usb_serial.read()
            s = s.decode('utf-8')
            if   s == '<':
                message = ''
                message = s
            elif s == '>':
                message += s
                messages.append(message)
                message = ''
            else:
                message += s
        return messages


class PinTreeWidgetItem(pg.TreeWidgetItem):
    """
    Pin Tree Widget Item
    """
    global g_samples
    global g_period

    def __init__(self, name, analog=True, color='y'):
        super().__init__(name)

        self.name   = name[0]
        self.color  = color
        self.value  = None
        self.values = np.zeros(g_samples)
        self.values_index = 0
        self.plotitem   = None
        self.pin_letter = self.name[0]
        self.pin_number = int(self.name[1])

        self.btn_type   = QtWidgets.QPushButton('Input')
        self.txt_status = QtWidgets.QLineEdit()
        self.cbx_analog = QtWidgets.QCheckBox()
        self.cbx_record = QtWidgets.QCheckBox()
        self.setWidget(1, self.btn_type)
        self.setWidget(2, self.txt_status)
        self.setWidget(3, self.cbx_analog)
        self.setWidget(4, self.cbx_record)

        self.btn_type.setMaximumWidth(50)
        self.btn_type.clicked.connect(self.change_type)
        self.txt_status.setMaximumWidth(50)
        self.txt_status.setReadOnly(True)
        self.plt_status_red = self.txt_status.palette()
        self.plt_status_red.setColor(QtGui.QPalette.Base, QtGui.QColor(255,0,0))
        self.plt_status_grn = self.txt_status.palette()
        self.plt_status_grn.setColor(QtGui.QPalette.Base, QtGui.QColor(57,255,20))
        self.plt_status_wht = self.txt_status.palette()
        self.plt_status_wht.setColor(QtGui.QPalette.Base, QtGui.QColor(255,255,255))
        self.cbx_analog.setEnabled(analog)
        self.cbx_analog.clicked.connect(self.change_analog)

    def change_analog(self):
        if   self.btn_type.text() in 'Input,Output':
            self.btn_type.setText('On')
            self.txt_status.setPalette(self.plt_status_wht)
        elif self.btn_type.text() in 'On,Off':
            self.btn_type.setText('Input')

    def change_type(self):
        if   self.btn_type.text() == 'Input':
            self.btn_type.setText('Output')
        elif self.btn_type.text() == 'Output':
            self.btn_type.setText('Input')
        elif self.btn_type.text() == 'On':
            self.btn_type.setText('Off')
        elif self.btn_type.text() == 'Off':
            self.btn_type.setText('On')
            
    def get_command(self):
        if   self.btn_type.text() in 'On,Off':
            return '(A{0}r)'.format(self.name)
        elif self.btn_type.text() in 'Input,Output':
            return '(DP{0})'.format(self.pin_letter)

    def set_value(self, value):
        if   isinstance(value, int) and self.btn_type.text() in 'Input,Output':
            self.value = value
            self.values[self.values_index] = self.value*5.0
        elif isinstance(value, float) and self.btn_type.text() in 'On,Off':
            self.value = value
            self.values[self.values_index] = self.value
        else:
            return
        self.values_index += 1
        self.values_index = self.values_index % self.values.size
        self.display()

    def get_values(self):
        return np.roll(self.values, -self.values_index)

    def set_plotitem(self, plot_widget):
        if plot_widget is None:
            self.plotitem = None
        else:
            self.plotitem = plot_widget.plot(pen=self.color, name=self.name)

    def get_plotitem(self):
        return self.plotitem

    def plot(self):
        if self.plotitem is not None:
            y = self.get_values()
            x = np.arange(y.size)*g_period
            self.plotitem.setData(x=x, y=y)

    def display(self):
        if   isinstance(self.value, int) and self.value == 1:
            self.txt_status.setText('High')
            self.txt_status.setPalette(self.plt_status_red)
        elif isinstance(self.value, int) and self.value == 0:
            self.txt_status.setText('Low')
            self.txt_status.setPalette(self.plt_status_grn)
        elif isinstance(self.value, float):
            self.txt_status.setText('%.3fV' % self.value)
        else:
            self.txt_status.setText('xxx')
            self.txt_status.setPalette(self.plt_status_wht)


class MainForm(QtWidgets.QMainWindow):
    """
    This is GUI main class.
    """
    global g_samples
    global g_period

    def __init__(self):
        super().__init__()

        self.area = pgda.DockArea()
        self.setCentralWidget(self.area)
        self.resize(1000,500)
        self.setWindowTitle('app-icp12-gui')

        # Create Docks
        dock1 = pgda.Dock("PORT", size=(300, 300))
        dock2 = pgda.Dock("GRAPH", size=(500, 300))
        dock3 = pgda.Dock("SETTING", size=(400, 300))
        
        self.area.addDock(dock1, 'left')
        self.area.addDock(dock2, 'right')
        self.area.addDock(dock3, 'right')

        # Create Tree
        a0 = PinTreeWidgetItem(["A0"], color='b')
        a1 = PinTreeWidgetItem(["A1"], color='g')
        a2 = PinTreeWidgetItem(["A2"], color='r')
        a3 = PinTreeWidgetItem(["A3"], color='c')
        a5 = PinTreeWidgetItem(["A5"], color='y')
        b0 = PinTreeWidgetItem(["B0"], analog=False)
        b1 = PinTreeWidgetItem(["B1"], analog=False)
        b2 = PinTreeWidgetItem(["B2"], color='w')
        c0 = PinTreeWidgetItem(["C0"], analog=False)
        c1 = PinTreeWidgetItem(["C1"], analog=False)
        c2 = PinTreeWidgetItem(["C2"], analog=False)
        c6 = PinTreeWidgetItem(["C6"], analog=False)
        c7 = PinTreeWidgetItem(["C7"], analog=False)

        self.d1tree = pg.TreeWidget()
        self.d1tree.setColumnCount(5)
        self.d1tree.addTopLevelItem(a0)
        self.d1tree.addTopLevelItem(a1)
        self.d1tree.addTopLevelItem(a2)
        self.d1tree.addTopLevelItem(a3)
        self.d1tree.addTopLevelItem(a5)
        self.d1tree.addTopLevelItem(b0)
        self.d1tree.addTopLevelItem(b1)
        self.d1tree.addTopLevelItem(b2)
        self.d1tree.addTopLevelItem(c0)
        self.d1tree.addTopLevelItem(c1)
        self.d1tree.addTopLevelItem(c2)
        self.d1tree.addTopLevelItem(c6)
        self.d1tree.addTopLevelItem(c7)
        [i.cbx_analog.clicked.connect(self.reg_plot) for i in self.d1tree.listAllItems() ]
        self.d1tree.setHeaderLabels(["Name", "Type", "Status", "Analog", "Record"])
        self.d1tree.header().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # self.d1tree.header().setStretchLastSection(False)
        dock1.addWidget(self.d1tree)
        self.d1tree.setEnabled(False)

        # Create Graph
        d2view = pg.GraphicsView()
        d2layout = pg.GraphicsLayout(border=(100,100,100))
        d2view.setCentralItem(d2layout)
        self.d2label = d2layout.addLabel("Plot")
        d2layout.nextRow()
        self.d2plot = d2layout.addPlot()
        self.d2plot.setLabel('left', 'Voltatge', units='V')
        self.d2plot.setLabel('bottom', 'Time', units='s')
        self.d2plot.setXRange(0,g_samples/g_period)
        self.d2plot.setYRange(-1, 6)
        self.d2plot.showGrid(x=True, y=True)
        self.d2plot_leg = self.d2plot.addLegend()
        dock2.addWidget(d2view)

        # Create ParamterTree
        self.device_parameter = DeviceParameter(name='DEVICE')
        self.device_parameter.sigConnectionChanged.connect(self.d1tree.setEnabled)
        params = [
            self.device_parameter,
            {'name': 'LOGGING', 'type': 'group', 'children': [
                {'name': 'Dummy', 'type': 'list', 'values': ['1', '2'], 'value': '2'},
            ]},
            {'name': 'SIGNAL', 'type': 'group', 'children': [
                {'name': 'Dummy', 'type': 'list', 'values': ['1', '2'], 'value': '2'},
            ]},
            {'name': 'SCALE', 'type': 'group', 'children': [
                {'name': 'Dummy', 'type': 'list', 'values': ['1', '2'], 'value': '2'},
            ]},
            {'name': 'TRIGGER', 'type': 'group', 'children': [
                {'name': 'Dummy', 'type': 'list', 'values': ['1', '2'], 'value': '2'},
            ]},
            {'name': 'DISPLAY', 'type': 'group', 'children': [
                {'name': 'Dummy', 'type': 'list', 'values': ['1', '2'], 'value': '2'},
            ]},
            {'name': 'CONTROL', 'type': 'group', 'children': [
                {'name': 'Dummy', 'type': 'list', 'values': ['1', '2'], 'value': '2'},
            ]},    
            {'name': 'SAVE/LOAD', 'type': 'group', 'children': [
                {'name': 'Save State', 'type': 'action'},
                {'name': 'Load State', 'type': 'action', 'children': [
                    {'name': 'Add missing items', 'type': 'bool', 'value': True},
                    {'name': 'Remove extra items', 'type': 'bool', 'value': True},
                ]},
            ]},          
        ]

        self.d3param = pgpt.Parameter.create(name='params', type='group', children=params)
        self.d3param.sigTreeStateChanged.connect(self.change)
        for ch1 in self.d3param.children():
            ch1.sigValueChanging.connect(self.changing)
            for ch2 in ch1.children():
                ch2.sigValueChanging.connect(self.changing)
        
        self.d3param.param('SAVE/LOAD', 'Save State').sigActivated.connect(self.save)
        self.d3param.param('SAVE/LOAD', 'Load State').sigActivated.connect(self.load)

        d3tree = pgpt.ParameterTree()
        d3tree.setParameters(self.d3param, showTop=False)
        d3tree.setWindowTitle('pyqtgraph example Parameter Tree')
        dock3.addWidget(d3tree)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(0)
        self.timer_counter = 0
        self.old_time = time.time()

    def reg_plot(self):
        for pin_item in self.d1tree.listAllItems():
            if   pin_item.cbx_analog.isChecked() and pin_item.get_plotitem() is None:
                pin_item.set_plotitem(self.d2plot)
            elif not pin_item.cbx_analog.isChecked() and pin_item.get_plotitem() is not None:
                self.d2plot.removeItem(pin_item.get_plotitem())
                self.d2plot_leg.removeItem(pin_item.name)
                pin_item.set_plotitem(None)

    def update(self):
        if self.device_parameter.has_serial():
            # send command and recieve message
            commands = [ i.get_command().encode('utf-8') for i in self.d1tree.listAllItems() ]
            commands = sorted(set(commands))
            messages = self.device_parameter.send_and_recieve(commands)
            for message in messages:
                self.parse_message(message)

            # plot graph
            if self.timer_counter % (g_plot_samples):
                pass
            else:
                [i.plot() for i in self.d1tree.listAllItems()]
                new_time = time.time()
                g_period = (new_time-self.old_time)/(g_plot_samples)
                self.old_time = new_time
                self.d2label.setText("Period:{:.4f} [ms]".format(g_period*1.e3))
            self.timer_counter += 1

    def parse_message(self, message):
        if   message[1]=='A' and message[4]=='r':
            pin_name = message[2:4]
            value = float(message[6:12])
            value = 5.*value/1023
            self.set_value(pin_name, value)
        elif message[1:3]=='DP':
            pin_letter = message[3]
            for pin_number in range(8):
                value = message[pin_number+4]
                if value != 'x':
                    pin_name = '{:s}{:d}'.format(pin_letter, pin_number)
                    self.set_value(pin_name, int(value))

    def set_value(self, pin_name, value):
        pin_items = [ i for i in self.d1tree.listAllItems() if i.name == pin_name ]
        for pin_item in pin_items:
            pin_item.set_value(value)

    def change(self, param, changes):
        print("tree changes:")
        for param, change, data in changes:
            path = self.d3param.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            print('  parameter: %s'% childName)
            print('  change:    %s'% change)
            print('  data:      %s'% str(data))
            print('  -----------')

    def changing(self, param, value):
        print("Value changing (not finalized): %s %s" % (param, value))

    def save(self):
        global g_state
        g_state = self.d3param.saveState()

    def load(self):
        global g_state
        add = self.d3param['SAVE/LOAD', 'Load State', 'Add missing items']
        rem = self.d3param['SAVE/LOAD', 'Load State', 'Remove extra items']
        self.d3param.restoreState(g_state, addChildren=True, removeChildren=True)


def main():
    """
    Main Function
    """
    app = QtWidgets.QApplication(sys.argv)
    form = MainForm()
    form.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        main()
