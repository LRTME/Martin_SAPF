
# Import the PyQt4 module we'll need
from PyQt5 import QtWidgets, QtGui, QtCore
# We need sys so that we can pass argv to QApplication
import sys
# for serial comunication
import com_monitor
# for statistics
import numpy as np
# for ploting
import pyqtgraph as pg
# for data packing and unpacking
import struct
# za stevilke
import math
# za nastavitve komunikacije
import os.path
# za slike
import os

# GUI elementi
import GUI_main_window
import COM_settings_dialog
import COM_statistics_dialog

# za horizontalno skalo grafa
frekvenca = 20000


class ExampleApp(QtWidgets.QMainWindow, GUI_main_window.Ui_MainWindow):

    # instanca com port monitorja
    commonitor = com_monitor.ComMonitor()

    # listi za izris
    ch1_latest = np.zeros(0)
    ch2_latest = np.zeros(0)
    ch3_latest = np.zeros(0)
    ch4_latest = np.zeros(0)
    ch5_latest = np.zeros(0)
    ch6_latest = np.zeros(0)
    ch7_latest = np.zeros(0)
    ch8_latest = np.zeros(0)

    def __init__(self):
        # Explaining super is out of the scope of this article
        # So please google it if you're not familar with it
        # Simple reason why we use it here is that it allows us to
        # access variables, methods etc in the design.py file
        super(self.__class__, self).__init__()

        # konfiguriram PyQtGraph
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # This is defined in GUI_design.py file automatically
        # It sets up layout and widgets that are defined
        self.setupUi(self)

        self.setWindowTitle("SAPF DLOG")
        self.setWindowIcon(QtGui.QIcon(resource_path("Logo_LRTME.png")))

        # crte na grafu
        self.main_plot = self.PlotWidget.plotItem
        self.text = pg.LabelItem()
        self.text.setParentItem(self.main_plot.graphicsItem())
        self.main_plot.scene().sigMouseMoved.connect(self.mouse_moved_over_plot)
        proxy = pg.SignalProxy(self.main_plot.scene().sigMouseMoved, rateLimit=5, slot=self.mouse_moved_over_plot)
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen((255, 0, 0, 128), width=2))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen((255, 0, 0, 128), width=2))
        self.main_plot.addItem(self.vLine, ignoreBounds=True)
        self.main_plot.addItem(self.hLine, ignoreBounds=True)
        # pripravim vse elemente
        self.plot_ch1 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen('r', width=3))
        self.plot_ch2 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen('g', width=3))
        self.plot_ch3 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen('b', width=3))
        self.plot_ch4 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen('c', width=3))
        self.plot_ch5 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen('m', width=3))
        self.plot_ch6 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen('k', width=3))
        self.plot_ch7 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen(0.25, width=3))
        self.plot_ch8 = self.main_plot.plot(np.array([0.0]), np.array([0.0]), pen=pg.mkPen(0.5, width=3))
        # ampak jih vecino odstranim
        self.main_plot.removeItem(self.plot_ch1)
        self.main_plot.removeItem(self.plot_ch2)
        self.main_plot.removeItem(self.plot_ch3)
        self.main_plot.removeItem(self.plot_ch4)
        self.main_plot.removeItem(self.plot_ch5)
        self.main_plot.removeItem(self.plot_ch6)
        self.main_plot.removeItem(self.plot_ch7)
        self.main_plot.removeItem(self.plot_ch8)

        self.main_plot.showGrid(True, True)

        self.vb = self.main_plot.vb
        self.mouse_point = QtCore.QPoint(0.0, 0.0)

        """ connect """
        # registriram rx handlerje
        self.commonitor.connect_rx_handler(0x0901, self.on_received_ch1)
        self.commonitor.connect_rx_handler(0x0902, self.on_received_ch2)
        self.commonitor.connect_rx_handler(0x0903, self.on_received_ch3)
        self.commonitor.connect_rx_handler(0x0904, self.on_received_ch4)
        self.commonitor.connect_rx_handler(0x0905, self.on_received_ch5)
        self.commonitor.connect_rx_handler(0x0906, self.on_received_ch6)
        self.commonitor.connect_rx_handler(0x0907, self.on_received_ch7)
        self.commonitor.connect_rx_handler(0x0908, self.on_received_ch8)

        self.commonitor.connect_rx_handler(0x090A, self.on_dlog_params_received)
        self.commonitor.connect_rx_handler(0x0B0A, self.on_ref_params_received)

        # povezem signal z handlerjem signala
        self.commonitor.connect_crc_handler(self.crc_event_print)

        # se meni-quit
        self.actionQuit.triggered.connect(QtWidgets.qApp.quit)

        # se meni "connect"
        self.actionConnect_Disconnect.triggered.connect(self.com_meni_clicked)

        # se meni "com statistics"
        self.actionCom_statistics.triggered.connect(self.com_statistics_clicked)

        # kontorlni elementi za graf
        self.ch1_chkbox.stateChanged.connect(self.ch1_state_changed)
        self.ch2_chkbox.stateChanged.connect(self.ch2_state_changed)
        self.ch3_chkbox.stateChanged.connect(self.ch3_state_changed)
        self.ch4_chkbox.stateChanged.connect(self.ch4_state_changed)
        self.ch5_chkbox.stateChanged.connect(self.ch5_state_changed)
        self.ch6_chkbox.stateChanged.connect(self.ch6_state_changed)
        self.ch7_chkbox.stateChanged.connect(self.ch7_state_changed)
        self.ch8_chkbox.stateChanged.connect(self.ch8_state_changed)
        # se nr. of. points
        self.points_spin.setOpts(value=200, dec=True, step=1, minStep=1, int=True)
        self.points_spin.setMinimum(10)
        self.points_spin.setMaximum(1000)
        self.points_spin.valueChanged.connect(self.points_changed)
        # za prescalar
        self.prescalar_spin.setOpts(value=1, dec=True, step=1, minStep=1, int=True)
        self.prescalar_spin.setMinimum(1)
        self.prescalar_spin.setMaximum(100)
        self.prescalar_spin.valueChanged.connect(self.prescaler_changed)
        # za trigger
        self.trigger.currentIndexChanged.connect(self.trigger_changed)

        # GUI elementi za generator referencnega signala
        self.naklon_spin.setOpts(value=100, dec=True, step=1, minStep=1, int=True, decimals=4)
        self.naklon_spin.setMinimum(1)
        self.naklon_spin.setMaximum(10000)
        self.naklon_spin.valueChanged.connect(self.naklon_changed)

        self.frekvenca_spin.setOpts(value=1, dec=True, step=1, minStep=0.01, int=False)
        self.frekvenca_spin.setMinimum(0.01)
        self.frekvenca_spin.setMaximum(1000)
        self.frekvenca_spin.valueChanged.connect(self.ref_freq_changed)

        self.sld_amp.valueChanged[int].connect(self.ref_amp_changed)
        self.sld_amp.sliderReleased.connect(self.request_ref_params)

        self.sld_offset.valueChanged[int].connect(self.ref_offset_changed)
        self.sld_offset.sliderReleased.connect(self.request_ref_params)

        self.sld_duty.valueChanged[int].connect(self.ref_duty_changed)
        self.sld_duty.sliderReleased.connect(self.request_ref_params)

        self.oblika_sel.currentIndexChanged.connect(self.type_changed)

    # ko zaprem aplikacijo za ziher zaprem comport
    def closeEvent(self, event):
        # ce je port se odprt, potem sprostim kontrolo
        if self.commonitor.is_port_open() == True:
            # preden ga zaprem, moram samo poskrbeti, da port ni uporabljen v threadih
            self.commonitor.close_port()
        # klicem sistemski handler
        super(ExampleApp, self).closeEvent(event)

    """ rx packets handlesr - in GUI thread"""
    # ko prejmem paket
    def on_received_ch1(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch1_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch1
        if (self.ch1_chkbox.isChecked() and
                not self.ch2_chkbox.isChecked() and
                not self.ch3_chkbox.isChecked() and
                not self.ch4_chkbox.isChecked() and
                not self.ch5_chkbox.isChecked() and
                not self.ch6_chkbox.isChecked() and
                not self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch2(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch2_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch2
        if (self.ch2_chkbox.isChecked() and
                not self.ch3_chkbox.isChecked() and
                not self.ch4_chkbox.isChecked() and
                not self.ch5_chkbox.isChecked() and
                not self.ch6_chkbox.isChecked() and
                not self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch3(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch3_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch3
        if (self.ch3_chkbox.isChecked() and
                not self.ch4_chkbox.isChecked() and
                not self.ch5_chkbox.isChecked() and
                not self.ch6_chkbox.isChecked() and
                not self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch4(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch4_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch4
        if (self.ch4_chkbox.isChecked() and
                not self.ch5_chkbox.isChecked() and
                not self.ch6_chkbox.isChecked() and
                not self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch5(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch5_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch5
        if (self.ch5_chkbox.isChecked() and
                not self.ch6_chkbox.isChecked() and
                not self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch6(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch6_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch6
        if (self.ch6_chkbox.isChecked() and
                not self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch7(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch7_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch7
        if (self.ch7_chkbox.isChecked() and
                not self.ch8_chkbox.isChecked()):
            self.draw_plot()

    def on_received_ch8(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        f_nparray = self.list_to_float(data)

        # spravim zadnje podatke
        self.ch8_latest = f_nparray

        # in klicem izris grafa ce je treba izrisati samo ch1
        if self.ch8_chkbox.isChecked():
            self.draw_plot()

    @staticmethod
    def list_to_float(data):
        # podatke sedaj stevilko za stevilko pretovrim v float
        length_of_data = len(data)
        f_numbers = int(length_of_data/4)
        # sedaj grem pa po vseh elementih in sestavim list iz tega
        i = 0
        f_list = list()
        f_nparray = np.zeros(f_numbers)
        while i < f_numbers:
            value = struct.unpack('<f', data[(i*4):((i+1)*4)])
            f_list.append(value)
            f_nparray[i] = np.array(value)
            i = i + 1
        return f_nparray

    def draw_plot(self):
        # naracunam x os
        dt = self.prescalar_spin.value() / frekvenca
        time = np.arange(0, self.points_spin.value(), 1, dtype=np.float)
        time = time * dt
        # ce gre za milisekunde potem skaliram
        # ampak samo v primeru ko risem casovni plot - ce risem FFT potem morajo biti enote sekunde
        # da dobim pravilne frekvence
        if max(time) < 1.0 and not self.main_plot.ctrl.fftCheck.isChecked():
            time = time * 1000

        # graf narisem samo ce sem v normal ali signle mode nacinu
        if self.trigger_mode.currentText() == "Normal" or self.trigger_mode.currentText() == "Single":
            if self.ch1_chkbox.isChecked() == True:
                if len(self.ch1_latest) == len(time):
                    if self.plot_ch1 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch1)
                    self.plot_ch1.setData(time, self.ch1_latest)

            if self.ch2_chkbox.isChecked() == True:
                if len(self.ch2_latest) == len(time):
                    if self.plot_ch2 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch2)
                    self.plot_ch2.setData(time, self.ch2_latest)

            if self.ch3_chkbox.isChecked() == True:
                if len(self.ch3_latest) == len(time):
                    if self.plot_ch3 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch3)
                    self.plot_ch3.setData(time, self.ch3_latest)

            if self.ch4_chkbox.isChecked() == True:
                if len(self.ch4_latest) == len(time):
                    if self.plot_ch4 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch4)
                    self.plot_ch4.setData(time, self.ch4_latest)

            if self.ch5_chkbox.isChecked() == True:
                if len(self.ch5_latest) == len(time):
                    if self.plot_ch5 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch5)
                    self.plot_ch5.setData(time, self.ch5_latest)

            if self.ch6_chkbox.isChecked() == True:
                if len(self.ch6_latest) == len(time):
                    if self.plot_ch6 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch6)
                    self.plot_ch6.setData(time, self.ch6_latest)

            if self.ch7_chkbox.isChecked() == True:
                if len(self.ch7_latest) == len(time):
                    if self.plot_ch7 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch7)
                    self.plot_ch7.setData(time, self.ch7_latest)

            if self.ch8_chkbox.isChecked() == True:
                if len(self.ch8_latest) == len(time):
                    if self.plot_ch8 not in self.main_plot.listDataItems():
                        self.main_plot.addItem(self.plot_ch8)
                    self.plot_ch8.setData(time, self.ch8_latest)

            # ko narisem podatek, narisem tudi crte. Tako ne upocasnim izrisa
            self.vLine.setPos(self.mouse_point.x())
            self.hLine.setPos(self.mouse_point.y())

            # ce sem v single mode nacinu potem grem v stop mode
            if self.trigger_mode.currentText()=="Single":
                self.trigger_mode.blockSignals(True)
                self.trigger_mode.setCurrentIndex(2)
                self.trigger_mode.blockSignals(False)

    def mouse_moved_over_plot(self, evt):
        pos = evt
        lokacija_miske = self.PlotWidget.lastMousePos
        self.mouse_point = self.vb.mapSceneToView(pos)
        if self.PlotWidget.sceneBoundingRect().contains(pos):
            # ne narisem crte, da ne upocasnim izrisovanja
            # self.vLine.setPos(self.mouse_point.x())
            # self.hLine.setPos(self.mouse_point.y())
            # ob crte napisem tekst
            val_x = eng_string(self.mouse_point.x(), format='%.2f')
            val_y = eng_string(self.mouse_point.y(), format='%.2f')
            self.text.setText("["+val_x+", "+val_y+"]")
            self.text.setPos(lokacija_miske[0], lokacija_miske[1])

    def on_dlog_params_received(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        # sedaj pa odkodiram podatke
        send_ch1 = struct.unpack('<h', data[0:2])[0]
        send_ch2 = struct.unpack('<h', data[2:4])[0]
        send_ch3 = struct.unpack('<h', data[4:6])[0]
        send_ch4 = struct.unpack('<h', data[6:8])[0]
        send_ch5 = struct.unpack('<h', data[8:10])[0]
        send_ch6 = struct.unpack('<h', data[10:12])[0]
        send_ch7 = struct.unpack('<h', data[12:14])[0]
        send_ch8 = struct.unpack('<h', data[14:16])[0]
        points = struct.unpack('<h', data[16:18])[0]
        prescalar = struct.unpack('<h', data[18:20])[0]
        trigger = struct.unpack('<h', data[20:22])[0]

        # ustrezno nastavim GUI elemente
        self.points_spin.blockSignals(True)
        self.points_spin.setValue(points)
        self.points_spin.blockSignals(False)

        self.prescalar_spin.blockSignals(True)
        self.prescalar_spin.setValue(prescalar)
        self.prescalar_spin.blockSignals(False)

        self.ch1_chkbox.blockSignals(True)
        if send_ch1 != 0:
            self.ch1_chkbox.setChecked(True)
        else:
            self.ch1_chkbox.setChecked(False)
            self.plot_ch1.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch1)
        self.ch1_chkbox.blockSignals(False)

        self.ch2_chkbox.blockSignals(True)
        if send_ch2 != 0:
            self.ch2_chkbox.setChecked(True)
        else:
            self.ch2_chkbox.setChecked(False)
            self.plot_ch2.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch2)
        self.ch2_chkbox.blockSignals(False)

        self.ch3_chkbox.blockSignals(True)
        if send_ch3 != 0:
            self.ch3_chkbox.setChecked(True)
        else:
            self.ch3_chkbox.setChecked(False)
            self.plot_ch3.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch3)
        self.ch3_chkbox.blockSignals(False)

        self.ch4_chkbox.blockSignals(True)
        if send_ch4 != 0:
            self.ch4_chkbox.setChecked(True)
        else:
            self.ch4_chkbox.setChecked(False)
            self.plot_ch4.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch4)
        self.ch4_chkbox.blockSignals(False)

        self.ch5_chkbox.blockSignals(True)
        if send_ch5 != 0:
            self.ch5_chkbox.setChecked(True)
        else:
            self.ch5_chkbox.setChecked(False)
            self.plot_ch5.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch5)
        self.ch5_chkbox.blockSignals(False)

        self.ch6_chkbox.blockSignals(True)
        if send_ch6 != 0:
            self.ch6_chkbox.setChecked(True)
        else:
            self.ch6_chkbox.setChecked(False)
            self.plot_ch6.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch6)
        self.ch6_chkbox.blockSignals(False)

        self.ch7_chkbox.blockSignals(True)
        if send_ch7 != 0:
            self.ch7_chkbox.setChecked(True)
        else:
            self.ch7_chkbox.setChecked(False)
            self.plot_ch7.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch7)
        self.ch7_chkbox.blockSignals(False)

        self.ch8_chkbox.blockSignals(True)
        if send_ch8 != 0:
            self.ch8_chkbox.setChecked(True)
        else:
            self.ch8_chkbox.setChecked(False)
            self.plot_ch8.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch8)
        self.ch8_chkbox.blockSignals(False)

        self.trigger.blockSignals(True)
        self.trigger.setCurrentIndex(trigger)
        self.trigger.blockSignals(False)

    def on_ref_params_received(self):
        # potegnem ven podatke
        data = self.commonitor.get_data(self)

        # sedaj pa odkodiram podatke
        amp = struct.unpack('<f', data[0:4])[0]
        offset = struct.unpack('<f', data[4:8])[0]
        freq = struct.unpack('<f', data[8:12])[0]
        duty = struct.unpack('<f', data[12:16])[0]
        slew = struct.unpack('<f', data[16:20])[0]
        type = struct.unpack('<h', data[20:24])[0]

        self.frekvenca_spin.blockSignals(True)
        self.frekvenca_spin.setValue(freq)
        self.frekvenca_spin.blockSignals(False)

        self.sld_amp.blockSignals(True)
        self.sld_amp.setValue(int(amp*100))
        self.sld_amp.blockSignals(False)
        self.lbl_amp.setText(str(self.sld_amp.value() / 100))

        self.sld_offset.blockSignals(True)
        self.sld_offset.setValue(int(offset*100))
        self.sld_offset.blockSignals(False)
        self.lbl_offset.setText(str(self.sld_offset.value() / 100))

        self.sld_duty.blockSignals(True)
        self.sld_duty.setValue(int(duty*100))
        self.sld_duty.blockSignals(False)
        self.lbl_duty.setText(str(self.sld_duty.value() / 100))

        self.naklon_spin.blockSignals(True)
        self.naklon_spin.setValue(slew)
        self.naklon_spin.blockSignals(False)

        self.oblika_sel.blockSignals(True)
        self.oblika_sel.setCurrentIndex(type)
        self.oblika_sel.blockSignals(False)

    def crc_event_print(self):
        crc_num = self.commonitor.get_crc()
        self.statusbar.showMessage("# CRC errors = " + str(crc_num), 2000)

    """ GUI event handlerji """
    # ob pritisku na meni com
    def com_meni_clicked(self):
        com_dialog = COM_settings_dialog.ComDialog(self)
        com_dialog.show()

    def com_statistics_clicked(self):
        com_stat_dialog = COM_statistics_dialog.ComStat(self)
        com_stat_dialog.show()

    def request_ref_params(self):
        self.commonitor.send_packet(0x0B1A, None)

    def ref_amp_changed(self):
        # osvezim napis pod sliderjem
        self.lbl_amp.setText(str(self.sld_amp.value() / 100))
        # posljem paket po portu
        data = pack_Float_As_U_Long(self.sld_amp.value() / 100)
        self.commonitor.send_packet(0x0B10, data)

    def ref_offset_changed(self):
        # osvezim napis pod sliderjem
        self.lbl_offset.setText(str(self.sld_offset.value() / 100))
        # posljem paket po portu
        data = pack_Float_As_U_Long(self.sld_offset.value() / 100)
        self.commonitor.send_packet(0x0B11, data)

    def ref_freq_changed(self):
        # posljem paket po portu
        data = struct.pack('<f', self.frekvenca_spin.value())
        self.commonitor.send_packet(0x0B12, data)

    def ref_duty_changed(self):
        # osvezim napis pod sliderjem
        self.lbl_duty.setText(str(self.sld_duty.value() / 100))
        # posljem paket po portu
        data = pack_Float_As_U_Long(self.sld_duty.value() / 100)
        self.commonitor.send_packet(0x0B13, data)

    # ob spremembi naklona
    def naklon_changed(self):
        # posljem paket po portu
        data = struct.pack('<f', int(self.naklon_spin.value()))
        self.commonitor.send_packet(0x0B14, data)

    # ob spremembi oblike
    def type_changed(self):
        data = struct.pack('<h', int(self.oblika_sel.currentIndex()))
        self.commonitor.send_packet(0x0B15, data)

    # ob spremembi prescalerja
    def prescaler_changed(self):
        # posljem paket po portu
        data = struct.pack('<h', self.prescalar_spin.value())
        self.commonitor.send_packet(0x0920, data)

    # ob spremembi stevila tock
    def points_changed(self):
        # posljem paket po portu
        data = struct.pack('<h', int(self.points_spin.value()))
        self.commonitor.send_packet(0x0921, data)

    # ob spremembi triggerja
    def trigger_changed(self):
        # posljem paket po portu
        self.commonitor.send_packet(0x0922, struct.pack('<h', self.trigger.currentIndex()))

    # ob pritisku na ch 1
    def ch1_state_changed(self):
        if self.ch1_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0911, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch1)
        else:
            self.commonitor.send_packet(0x0911, struct.pack('<h', 0x0000))
            self.plot_ch1.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch1)

    # ob pritisku na ch 2
    def ch2_state_changed(self):
        if self.ch2_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0912, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch2)
        else:
            self.commonitor.send_packet(0x0912, struct.pack('<h', 0x0000))
            self.plot_ch2.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch2)

    # ob pritisku na ch 3
    def ch3_state_changed(self):
        if self.ch3_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0913, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch3)
        else:
            self.commonitor.send_packet(0x0913, struct.pack('<h', 0x0000))
            self.plot_ch3.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch3)

    # ob pritisku na ch 4
    def ch4_state_changed(self):
        if self.ch4_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0914, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch4)
        else:
            self.commonitor.send_packet(0x0914, struct.pack('<h', 0x0000))
            self.plot_ch4.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch4)

    # ob pritisku na ch 5
    def ch5_state_changed(self):
        if self.ch5_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0915, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch5)
        else:
            self.commonitor.send_packet(0x0915, struct.pack('<h', 0x0000))
            self.plot_ch5.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch5)

    # ob pritisku na ch 6
    def ch6_state_changed(self):
        if self.ch6_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0916, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch6)
        else:
            self.commonitor.send_packet(0x0916, struct.pack('<h', 0x0000))
            self.plot_ch6.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch6)

    # ob pritisku na ch 7
    def ch7_state_changed(self):
        if self.ch7_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0917, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch7)
        else:
            self.commonitor.send_packet(0x0917, struct.pack('<h', 0x0000))
            self.plot_ch7.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch7)

    # ob pritisku na ch 8
    def ch8_state_changed(self):
        if self.ch8_chkbox.isChecked() == True:
            self.commonitor.send_packet(0x0918, struct.pack('<h', 0x0001))
            self.main_plot.addItem(self.plot_ch8)
        else:
            self.commonitor.send_packet(0x0918, struct.pack('<h', 0x0000))
            self.plot_ch8.setData(np.array([0.0]), np.array([0.0]))
            self.main_plot.removeItem(self.plot_ch8)


# pomozne funkcije
def pack_Float_As_U_Long(value):
    """ Pack a float as little endian packed data"""
    return struct.pack('<f', value)


def eng_string(x, format='%s', si=False):
    """
    Returns float/int value <x> formatted in a simplified engineering format -
    using an exponent that is a multiple of 3.

    format: printf-style string used to format the value before the exponent.

    si: if true, use SI suffix for exponent, e.g. k instead of e3, n instead of
    e-9 etc.

    E.g. with format='%.2f':
        1.23e-08 => 12.30e-9
             123 => 123.00
          1230.0 => 1.23e3
      -1230000.0 => -1.23e6

    and with si=True:
          1230.0 => 1.23k
      -1230000.0 => -1.23M
    """
    sign = ''
    x = float(x)
    if x < 0:
        x = -x
        sign = '-'
    if x == 0.0:
        exp = 0
    else:
        exp = int(math.floor(math.log10(x)))
    exp3 = exp - (exp % 3)
    x3 = x / (10 ** exp3)

    if si and exp3 >= -24 and exp3 <= 24 and exp3 != 0:
        index_f = ( exp3 - (-24)) / 3
        index = int(index_f)
        exp3_text = 'yzafpnum kMGTPEZY'[index]
    elif exp3 == 0:
        exp3_text = ''
    else:
        exp3_text = 'e%s' % exp3

    return ('%s'+format+'%s') % (sign, x3, exp3_text)


# za uporabo slike v pyinstaller .exe datoteki
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# glavna funkicja
def main():
    # A new instance of QApplication
    app = QtWidgets.QApplication(sys.argv)
    # We set the form to be our ExampleApp (design)
    form = ExampleApp()
    # Show the form
    form.show()
    # and execute the app
    app.exec_()

# start of the program
# if we're running file directly and not importing it
if __name__ == '__main__':
    main()