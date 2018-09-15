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
global g_sample_time
g_state = None
g_sample_time = 0.010


class DeviceParameter(pgptype.GroupParameter):
    """
    Device Parameter
    """
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
            ports = [i for i in ports[0] if i.count('/dev/ttyACM')]
        self.p_port.setLimits(ports)

    def has_serial(self):
        return self.usb_serial is not None

    def connect(self):
        if self.p_btn.name() == '  Connect  ':
            port = self.p_port.value()
            ports = serial.tools.list_ports.comports()
            if ports and port in ports[0]:
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
    def __init__(self, name, analog=True, color='y'):
        super().__init__(name)

        self.name   = name[0]
        self.color  = color
        self.value  = None
        self.values = np.zeros(int(1/g_sample_time))
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
            x = np.arange(y.size)*g_sample_time
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
    global g_sample_time

    def __init__(self):
        super().__init__()

        self.area = pgda.DockArea()
        self.setCentralWidget(self.area)
        self.resize(1000,500)
        self.setWindowTitle('app-icp12-gui')

        # Create Docks
        d1 = pgda.Dock("PORT", size=(300, 300))
        d2 = pgda.Dock("GRAPH", size=(500, 300))
        d3 = pgda.Dock("SETTING", size=(400, 300))
        
        self.area.addDock(d1, 'left')
        self.area.addDock(d2, 'right')
        self.area.addDock(d3, 'right')

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

        self.t1 = pg.TreeWidget()
        self.t1.setColumnCount(5)
        self.t1.addTopLevelItem(a0)
        self.t1.addTopLevelItem(a1)
        self.t1.addTopLevelItem(a2)
        self.t1.addTopLevelItem(a3)
        self.t1.addTopLevelItem(a5)
        self.t1.addTopLevelItem(b0)
        self.t1.addTopLevelItem(b1)
        self.t1.addTopLevelItem(b2)
        self.t1.addTopLevelItem(c0)
        self.t1.addTopLevelItem(c1)
        self.t1.addTopLevelItem(c2)
        self.t1.addTopLevelItem(c6)
        self.t1.addTopLevelItem(c7)
        [i.cbx_analog.clicked.connect(self.reg_plot) for i in self.t1.listAllItems() ]
        self.t1.setHeaderLabels(["Name", "Type", "Status", "Analog", "Record"])
        self.t1.header().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # self.t1.header().setStretchLastSection(False)
        d1.addWidget(self.t1)
        self.t1.setEnabled(False)

        # Create Graph
        self.p2 = pg.PlotWidget(name='plot1')
        self.p2.setLabel('left', 'Voltatge', units='V')
        self.p2.setLabel('bottom', 'Time', units='s')
        self.p2.setXRange(0,0.5)
        self.p2.setYRange(-1, 6)
        self.p2_leg = self.p2.addLegend()
        d2.addWidget(self.p2)

        # Create ParamterTree
        self.device_parameter = DeviceParameter(name='DEVICE')
        self.device_parameter.sigConnectionChanged.connect(self.t1.setEnabled)
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

        self.p3 = pgpt.Parameter.create(name='params', type='group', children=params)
        self.p3.sigTreeStateChanged.connect(self.change)
        for ch1 in self.p3.children():
            ch1.sigValueChanging.connect(self.changing)
            for ch2 in ch1.children():
                ch2.sigValueChanging.connect(self.changing)
        
        self.p3.param('SAVE/LOAD', 'Save State').sigActivated.connect(self.save)
        self.p3.param('SAVE/LOAD', 'Load State').sigActivated.connect(self.load)

        t3 = pgpt.ParameterTree()
        t3.setParameters(self.p3, showTop=False)
        t3.setWindowTitle('pyqtgraph example Parameter Tree')
        d3.addWidget(t3)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(int(g_sample_time*1000))
        self.timer_counter = 0

    def reg_plot(self):
        for pin_item in self.t1.listAllItems():
            if   pin_item.cbx_analog.isChecked() and pin_item.get_plotitem() is None:
                pin_item.set_plotitem(self.p2)
            elif not pin_item.cbx_analog.isChecked() and pin_item.get_plotitem() is not None:
                self.p2.removeItem(pin_item.get_plotitem())
                self.p2_leg.removeItem(pin_item.name)
                pin_item.set_plotitem(None)

    def update(self):
        if self.device_parameter.has_serial():
            # send command and recieve message
            commands = [ i.get_command().encode('utf-8') for i in self.t1.listAllItems() ]
            commands = sorted(set(commands))
            messages = self.device_parameter.send_and_recieve(commands)
            for message in messages:
                self.parse_message(message)

            # plot graph
            if self.timer_counter % int(0.1/g_sample_time):
                pass
            else:
                [i.plot() for i in self.t1.listAllItems() ]
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
        pin_items = [ i for i in self.t1.listAllItems() if i.name == pin_name ]
        for pin_item in pin_items:
            pin_item.set_value(value)

    def change(self, param, changes):
        print("tree changes:")
        for param, change, data in changes:
            path = self.p3.childPath(param)
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
        g_state = self.p3.saveState()

    def load(self):
        global g_state
        add = self.p3['SAVE/LOAD', 'Load State', 'Add missing items']
        rem = self.p3['SAVE/LOAD', 'Load State', 'Remove extra items']
        self.p3.restoreState(g_state, addChildren=True, removeChildren=True)


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
