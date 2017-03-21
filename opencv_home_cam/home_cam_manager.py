import threading
import logging
import configparser
import time
import ast
from collections import namedtuple
from opencv_home_cam import HomeCam, HomeCamException, HomeCamConfig


def cast_string_to_float(s):
    try:
        return float(s)
    except ValueError:
        return None

def cast_string_to_int(s):
    try:
        return int(s)
    except ValueError:
        return None

def cast_string_to_bool(s):
    try:
        return bool(s)
    except ValueError:
        return None

def cast_string_to_tuple(s):
    try:
        return ast.literal_eval(s)
    except ValueError:
        return None


class HomeCamManager:

    def __init__(self, config_file, cascade_files):

        self._set_default_config()

        self._cp = configparser.ConfigParser()
        self._cp.read(config_file)

        if 'recording' in self._cp:
            self._read_recording_config()
        if 'detection' in self._cp:
            self._read_detection_config()

        self._hc = HomeCam(cascade_files=cascade_files,
                           config=self._hc_config)

        self._running = False

    def _set_default_config(self):

        self._hc_config = HomeCamConfig(recording_cam_id=0,
                                        recording_fps=20.0,
                                        recording_resolution=(640,480),
                                        recording_file_limit=10,
                                        recording_time_limit=60,
                                        detection_scale_factor=1.1,
                                        detection_min_neighbours=3,
                                        detection_size=3,
                                        recording_enable=False,
                                        recording_dir=None,
                                        recording_file_base=None)

    def _read_recording_config(self):

        rec_cfg = self._cp['recording']

        if 'fps' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_fps=cast_string_to_float(rec_cfg['fps']))
            if self._hc_config.recording_fps is None:
                logging.error("Config: bad fps value!")

        if 'resolution' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_resolution=cast_string_to_tuple(rec_cfg['resolution']))
            if self._hc_config.recording_resolution is None:
                logging.error("Config: bad resolution value!")

        if 'file_limit' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_file_limit=cast_string_to_int(rec_cfg['file_limit']))
            if self._hc_config.recording_file_limit is None:
                logging.error("Config: bad file_limit value!")

        if 'time_limit' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_time_limit=cast_string_to_int(rec_cfg['time_limit']))
            if self._hc_config.recording_time_limit is None:
                logging.error("Config: bad time_limit value!")

        if 'cam_id' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_cam_id=cast_string_to_int(rec_cfg['cam_id']))
            if self._hc_config.recording_cam_id is None:
                logging.error("Config: bad cam_id value!")

        if 'enable' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_enable=cast_string_to_bool(rec_cfg['enable']))
            if self._hc_config.recording_enable is None:
                logging.error("Config: Bad output enable option!")

        if 'recording_dir' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_dir=rec_cfg['recording_dir'])
            if self._hc_config.recording_dir is None:
                logging.error("Config: Bad output directory path!")

        if 'recording_file_base' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_file_base=rec_cfg['recording_file_base'])
            if self._hc_config.recording_file_base is None:
                logging.error("Config: Bad output file base!")

    def _read_detection_config(self):

        detection_cfg = self._cp['detection']

        if 'scale_factor' in detection_cfg:
            self._hc_config = self._hc_config._replace(detection_scale_factor=cast_string_to_float(detection_cfg['scale_factor']))
            if self._hc_config.detection_scale_factor is None:
                logging.error("Config: bad scale_factor value!")

        if 'min_neighbours' in detection_cfg:
            self._hc_config = self._hc_config._replace(detection_min_neighbours=cast_string_to_int(detection_cfg['min_neighbours']))
            if self._hc_config.detection_min_neighbours is None:
                logging.error("Config: bad min_neighbours value!")

        if 'size' in detection_cfg:
            self._hc_config = self._hc_config._replace(detection_size=cast_string_to_int(detection_cfg['size']))
            if self._hc_config.detection_size is None:
                logging.error("Config: bad size value!")

    def start(self):

        self._running = True
        self._worker_thread = threading.Thread(target=self._process_frames)
        self._worker_thread.start()

    def stop(self):

        self._running = False

    def wait(self):

        self._worker_thread.join()

    def _process_frames(self):

        object_detected = False

        while self._running:

            objects = self._hc.read_and_process_frame()

            if objects is not None:
                if not object_detected:
                    logging.info("Object(s) detected")
                    self._hc.enable_frame_saving()
                object_detected = True
            else:
                if object_detected:
                    logging.info("No object(s) detected")
                    self._hc.disable_frame_saving()
                object_detected = False

            time.sleep(1 / self._hc_config.recording_fps)

        self._hc.close()
