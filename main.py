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
    def __init__(self, **opts):
        opts['type'] = 'bool'
        opts['value'] = True
        pgptype.GroupParameter.__init__(self, **opts)

        self.addChild({'name': '  Connect  ', 
                       'type': 'action'})
        self.addChild({'name': 'Port',
                       'type': 'list', 
                       'values': ['/dev/ttyACM0'], 
                       'value': '/dev/ttyACM0'})
        self.p_btn  = self.param('  Connect  ')
        self.p_port = self.param('Port')
        self.p_btn.sigActivated.connect(self.connect)

    def connect(self):
        global g_serial
        if self.p_btn.name() == '  Connect  ':
            port = self.p_port.value()
            if port in serial.tools.list_ports.comports()[0]:
                g_serial = serial.Serial(port, 115200)
                self.p_btn.setName('  Disconnect  ')
            else:
                g_serial = None
                assert False, "No Device"
        else:
            self.p_btn.setName('  Connect  ')



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
        
        # Create ParamterTree
        params = [
            DeviceParameter(name='DEVICE'),
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

        self.p1 = pgpt.Parameter.create(name='params', type='group', children=params)
        self.p1.sigTreeStateChanged.connect(self.change)
        for ch1 in self.p1.children():
            ch1.sigValueChanging.connect(self.changing)
            for ch2 in ch1.children():
                ch2.sigValueChanging.connect(self.changing)
        
        self.p1.param('SAVE/LOAD', 'Save State').sigActivated.connect(self.save)
        self.p1.param('SAVE/LOAD', 'Load State').sigActivated.connect(self.load)

        self.t1 = pgpt.ParameterTree()
        self.t1.setParameters(self.p1, showTop=False)
        self.t1.setWindowTitle('pyqtgraph example Parameter Tree')
        
        # Create Docks
        d1 = pgda.Dock("PORT", size=(200, 300))
        d2 = pgda.Dock("GRAPH", size=(500, 300))
        d3 = pgda.Dock("SETTING", size=(400, 300))
        
        self.area.addDock(d1, 'left')
        self.area.addDock(d2, 'right')
        self.area.addDock(d3, 'right') 

        d3.addWidget(self.t1)


    def change(self, param, changes):
        print("tree changes:")
        for param, change, data in changes:
            path = self.p1.childPath(param)
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
        g_state = self.p1.saveState()

    def load(self):
        global g_state
        add = self.p1['SAVE/LOAD', 'Load State', 'Add missing items']
        rem = self.p1['SAVE/LOAD', 'Load State', 'Remove extra items']
        self.p1.restoreState(g_state, addChildren=True, removeChildren=True)


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
