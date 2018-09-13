"""
Main Program
"""
import sys

import serial
import serial.tools.list_ports

import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from pyqtgraph import dockarea as pgda
from pyqtgraph import parametertree as pgpt
from pyqtgraph.parametertree import parameterTypes as pgptype

global g_serial
global g_state

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

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_device)
        self.timer.start(2000)

    def check_device(self):
        ports = serial.tools.list_ports.comports()
        if ports:
            ports = [i for i in ports[0] if i.count('/dev/ttyACM')]
        self.p_port.setLimits(ports)

    def connect(self):
        global g_serial
        if self.p_btn.name() == '  Connect  ':
            port = self.p_port.value()
            ports = serial.tools.list_ports.comports()
            if ports and port in ports[0]:
                g_serial = serial.Serial(port, 115200)
                self.p_btn.setName('  Disconnect  ')
                self.sigConnectionChanged.emit(True)
            else:
                g_serial = None
        else:
            self.p_btn.setName('  Connect  ')
            self.sigConnectionChanged.emit(False)


class PinTreeWidgetItem(pg.TreeWidgetItem):
    """
    pin widget class
    """
    def __init__(self, name, analog=True):
        super().__init__(name)

        self.name = name[0]
        self.btn_type   = QtWidgets.QPushButton('Input')
        self.txt_status = QtWidgets.QLineEdit()
        self.cbx_analog = QtWidgets.QCheckBox()
        self.cbx_record = QtWidgets.QCheckBox()
        self.setWidget(1, self.btn_type)
        self.setWidget(2, self.txt_status)
        self.setWidget(3, self.cbx_analog)
        self.setWidget(4, self.cbx_record)

        self.btn_type.setMaximumWidth(50)
        self.txt_status.setMaximumWidth(50)
        self.txt_status.setReadOnly(True)
        self.cbx_analog.setEnabled(analog)



class MainForm(QtWidgets.QMainWindow):
    """
    This is GUI main class.
    """

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
        a0 = PinTreeWidgetItem(["A0"])
        a1 = PinTreeWidgetItem(["A1"])
        a2 = PinTreeWidgetItem(["A2"])
        a3 = PinTreeWidgetItem(["A3"])
        a5 = PinTreeWidgetItem(["A5"])
        b0 = PinTreeWidgetItem(["B0"], analog=False)
        b1 = PinTreeWidgetItem(["B1"], analog=False)
        b2 = PinTreeWidgetItem(["B2"])
        c0 = PinTreeWidgetItem(["C0"], analog=False)
        c1 = PinTreeWidgetItem(["C1"], analog=False)
        c2 = PinTreeWidgetItem(["C2"], analog=False)
        c6 = PinTreeWidgetItem(["C6"], analog=False)
        c7 = PinTreeWidgetItem(["C7"], analog=False)

        t1 = pg.TreeWidget()
        t1.setColumnCount(5)
        t1.addTopLevelItem(a0)
        t1.addTopLevelItem(a1)
        t1.addTopLevelItem(a2)
        t1.addTopLevelItem(a3)
        t1.addTopLevelItem(a5)
        t1.addTopLevelItem(b0)
        t1.addTopLevelItem(b1)
        t1.addTopLevelItem(b2)
        t1.addTopLevelItem(c0)
        t1.addTopLevelItem(c1)
        t1.addTopLevelItem(c2)
        t1.addTopLevelItem(c6)
        t1.addTopLevelItem(c7)
        t1.setHeaderLabels(["Name", "Type", "Status", "Analog", "Record"])
        t1.header().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # t1.header().setStretchLastSection(False)
        d1.addWidget(t1)
        t1.setEnabled(False)

        # Create ParamterTree
        device_paramter = DeviceParameter(name='DEVICE')
        device_paramter.sigConnectionChanged.connect(t1.setEnabled)
        params = [
            device_paramter,
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
