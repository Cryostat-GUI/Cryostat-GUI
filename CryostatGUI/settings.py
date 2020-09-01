
import os
import json
import logging
import zmq

from PyQt5.QtCore import QSettings
from PyQt5 import QtWidgets, QtGui
from PyQt5.uic import loadUi

from util import Window_ui


logger = logging.getLogger('CryostatGUI.settings')


class windowSettings(Window_ui):
    """docstring for windowSettings"""

    def __init__(self, signals, zmqcontext, data, ui_file='.\\configurations\\settings_global.ui'):
        super(windowSettings, self).__init__(ui_file)
        self._logger = logging.getLogger('CryoGUI.'__name__ + '.' + self.__class__.__name__)
        self.MTsigs = signals
        self.zmq_context = zmqcontext
        self.zmq_sSettings = self.zmq_context.socket(zmq.REQ)
        # self.zmq_sSettings.connect("inproc://main_line")
        self.zmq_sSettings.connect(f"tcp://localhost:{5556}")

        self.MT_data = data['data']
        self.MT_dataLock = data['dataLock']

        self.Sequences_tempcontrol = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout()
        loadUi('.\\configurations\\window_settings_individualwidgets\\Sequence_tempcontrol_compound.ui',
               self.Sequences_tempcontrol)
        grid.addWidget(self.Sequences_tempcontrol)
        self.Sequences_tempcontrol_groupbox.setLayout(grid)

        tempcontrol = self.Sequences_tempcontrol
        self.tempcontrol_conf = dict(control_sensor='',
                                     control_instr='',
                                     measurement_sensor='',
                                     measurement_instr='',
                                     threshold_T_K=5e-1,
                                     threshold_Tmean_K=5e-1,
                                     threshold_stderr_rel=0,
                                     threshold_relslope_Kpmin=0,
                                     threshold_slope_residuals=0)

        # self.groupBox.setEnabled(False)

        self.checkUseAuto.toggled[
            'bool'].connect(self.ITC_useAutoPID)
        self.lineConfFile.textEdited.connect(
            self.ITC_PIDFile_store)
        self.pushConfLoad.clicked.connect(
            self.ITC_PIDFile_send)
        self.lineConfFile.returnPressed.connect(
            self.ITC_PIDFile_send)

        tempcontrol.lineEdit_thresholdsSavingPreset.textEdited.connect(
            self.tempcontrol_preset_storeFilename)
        tempcontrol.lineEdit_thresholdsSavingPreset.returnPressed.connect(
            self.tempcontrol_preset_save)
        tempcontrol.combo_thresholdsLoadingPreset.activated[
            'QString'].connect(self.tempcontrol_preset_restore)

        tempcontrol.command_sendThresholds.clicked.connect(
            self.tempcontrol_sendconf)

        self.tempcontrol_preset_parse()
        tempcontrol.pushRefreshPresets.clicked.connect(
            self.tempcontrol_preset_parse)

        tempcontrol.spin_Sequence_threshold_T_K.valueChanged.connect(
            lambda value: self.tempcontrol_conf_store('threshold_T_K', value))
        tempcontrol.spin_Sequence_threshold_Tmean_K.valueChanged.connect(
            lambda value: self.tempcontrol_conf_store('threshold_Tmean_K', value))
        tempcontrol.spin_Sequence_threshold_stderr.valueChanged.connect(
            lambda value: self.tempcontrol_conf_store('threshold_stderr_rel', value))
        tempcontrol.spin_Sequence_threshold_slope_Kpmin.valueChanged.connect(
            lambda value: self.tempcontrol_conf_store('threshold_relslope_Kpmin', value))
        tempcontrol.spin_Sequence_threshold_slopeResiduals.valueChanged.connect(
            lambda value: self.tempcontrol_conf_store('threshold_slope_residuals', value))

        tempcontrol.combo_SensorControl_Instrument.activated['QString'].connect(
            lambda value: self.tempcontrol_conf_store('control_instr', value))
        tempcontrol.combo_SensorControl_Sensor.activated['QString'].connect(
            lambda value: self.tempcontrol_conf_store('control_sensor', value))
        tempcontrol.combo_SensorMeas_Instrument.activated['QString'].connect(
            lambda value: self.tempcontrol_conf_store('measurement_instr', value))
        tempcontrol.combo_SensorMeas_Sensor.activated['QString'].connect(
            lambda value: self.tempcontrol_conf_store('measurement_sensor', value))

    def refresh_combos(self):
        self.tempcontrol_preset_parse()

    def ITC_useAutoPID(self, boolean):
        """set the variable for the softwareAutoPID
        emit signal to notify Thread
        store it in settings"""
        self.temp_ITC_useAutoPID = boolean
        self.MTsigs['ITC']['useAutocheck'].emit(boolean)
        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue('ITC_useAutoPID', int(boolean))
        del settings

    def ITC_PIDFile_store(self, filename):
        """reaction to signal: ITC PID file: store"""
        self.temp_ITC_PIDFile = filename

    def ITC_PIDFile_send(self):
        """reaction to signal: ITC PID file: send and store permanently"""
        if isinstance(self.temp_ITC_PIDFile, str):
            text = self.temp_ITC_PIDFile
        else:
            text = ''
        self.MTsigs['ITC']['newFilePID'].emit(text)

        settings = QSettings("TUW", "CryostatGUI")
        settings.setValue('ITC_PIDFile', self.temp_ITC_PIDFile)
        del settings

        try:
            with open(self.temp_ITC_PIDFile) as f:
                self.textConfShow.setText(f.read())
        except OSError as e:
            self.show_error_general(f'mainthread: settings PIDFile: OSError {e}')
        except TypeError as e:
            self.show_error_general(f'mainthread: settings PIDFile: missing Filename! (TypeError: {e})')

    def tempcontrol_preset_parse(self) -> None:
        settings = QSettings("TUW", "CryostatGUI")
        self.tempcontrol_presets_path = settings.value(
            'Sequence_PresetsPath', str)
        del settings
        os.makedirs(self.tempcontrol_presets_path, exist_ok=True)
        files = [os.path.splitext(f)[0] for f in os.listdir(
            self.tempcontrol_presets_path) if f.endswith('.json') and
            os.path.isfile(os.path.join(self.tempcontrol_presets_path, f))]
        self.Sequences_tempcontrol.combo_thresholdsLoadingPreset.clear()
        self.Sequences_tempcontrol.combo_thresholdsLoadingPreset.addItem('-')
        self.Sequences_tempcontrol.combo_thresholdsLoadingPreset.addItems(
            files)

    def tempcontrol_preset_restore(self, filename: str) -> None:
        '''restore a preset from a json file'''
        if filename == '-':
            return
        filename = os.path.join(
            self.tempcontrol_presets_path, str(filename) + '.json')
        # print(filename)
        try:
            with open(filename) as f:
                tempcontrol_preset = json.loads(f)
        except FileNotFoundError:
            self.sig_error.emit(f'Settings: The preset file you wanted ({filename}) was not found!')
            self.?logger.warning(f'The preset file you wanted ({filename}) was not found!')
            return

        for key in tempcontrol_preset:
            self.tempcontrol_conf[key] = tempcontrol_preset[key]

        self.Sequences_tempcontrol.spin_Sequence_threshold_T_K.setValue(
            tempcontrol_preset['threshold_T_K'])
        self.Sequences_tempcontrol.spin_Sequence_threshold_Tmean_K.setValue(
            tempcontrol_preset['threshold_Tmean_K'])
        self.Sequences_tempcontrol.spin_Sequence_threshold_stderr.setValue(
            tempcontrol_preset['threshold_stderr_rel'])
        self.Sequences_tempcontrol.spin_Sequence_threshold_slope_Kpmin.setValue(
            tempcontrol_preset['threshold_relslope_Kpmin'])
        self.Sequences_tempcontrol.spin_Sequence_threshold_slopeResiduals.setValue(
            tempcontrol_preset['threshold_slope_residuals'])

    def tempcontrol_preset_save(self):
        '''save the current tempcontrol configuration (self.tempcontrol_conf) as a preset'''
        with open(self.tempcontrol_presets_path + '{}.json'.format(self.tempcontrol_preset_currentFilename), 'w') as output:
            output.write(json.dumps(self.tempcontrol_conf))

    def tempcontrol_conf_store(self, key: str, value: str) -> None:
        '''store key and value in self.tempcontrol_conf'''
        self.tempcontrol_conf[key] = value

    def tempcontrol_preset_storeFilename(self, value):
        self.tempcontrol_preset_currentFilename = value

    def tempcontrol_sendconf(self):
        self.MTsigs['newconf'].emit(self.tempcontrol_conf)
