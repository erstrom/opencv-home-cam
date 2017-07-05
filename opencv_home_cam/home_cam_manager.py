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

        self._logger = logging.getLogger(__name__)
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
        self._latest_cascade_status = None

    def _set_default_config(self):

        self._hc_config = HomeCamConfig(recording_cam_id=0,
                                        recording_fps=20.0,
                                        recording_resolution=(640, 480),
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
                self._logger.error("Config: bad fps value!")
        else:
            self._logger.info("Config: Missing fps value, using default")

        if 'resolution' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_resolution=cast_string_to_tuple(rec_cfg['resolution']))
            if self._hc_config.recording_resolution is None:
                self._logger.error("Config: bad resolution value!")
        else:
            self._logger.info("Config: Missing resolution value, using default")

        if 'file_limit' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_file_limit=cast_string_to_int(rec_cfg['file_limit']))
            if self._hc_config.recording_file_limit is None:
                self._logger.error("Config: bad file_limit value!")
        else:
            self._logger.info("Config: Missing file_limit value, using default")

        if 'time_limit' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_time_limit=cast_string_to_int(rec_cfg['time_limit']))
            if self._hc_config.recording_time_limit is None:
                self._logger.error("Config: bad time_limit value!")
        else:
            self._logger.info("Config: Missing time_limit value, using default")

        if 'cam_id' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_cam_id=cast_string_to_int(rec_cfg['cam_id']))
            if self._hc_config.recording_cam_id is None:
                self._logger.error("Config: bad cam_id value!")
        else:
            self._logger.info("Config: Missing cam_id value, using default")

        if 'enable' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_enable=cast_string_to_bool(rec_cfg['enable']))
            if self._hc_config.recording_enable is None:
                self._logger.error("Config: Bad output enable option!")
        else:
            self._logger.info("Config: Missing enable value, using default")

        if 'recording_dir' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_dir=rec_cfg['recording_dir'])
            if self._hc_config.recording_dir is None:
                self._logger.error("Config: Bad output directory path!")
        elif self._hc_config.recording_enable is not None:
            self._logger.error("Config: Missing recording_dir value!")

        if 'recording_file_base' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_file_base=rec_cfg['recording_file_base'])
            if self._hc_config.recording_file_base is None:
                self._logger.error("Config: Bad output file base!")
        elif self._hc_config.recording_enable is not None:
            self._logger.error("Config: Missing recording_file_base value!")

    def _read_detection_config(self):

        detection_cfg = self._cp['detection']

        if 'scale_factor' in detection_cfg:
            self._hc_config = self._hc_config._replace(detection_scale_factor=cast_string_to_float(detection_cfg['scale_factor']))
            if self._hc_config.detection_scale_factor is None:
                self._logger.error("Config: bad scale_factor value!")
        else:
            self._logger.info("Config: Missing scale_factor value, using default")

        if 'min_neighbours' in detection_cfg:
            self._hc_config = self._hc_config._replace(detection_min_neighbours=cast_string_to_int(detection_cfg['min_neighbours']))
            if self._hc_config.detection_min_neighbours is None:
                self._logger.error("Config: bad min_neighbours value!")
        else:
            self._logger.info("Config: Missing min_neighbours value, using default")

        if 'size' in detection_cfg:
            self._hc_config = self._hc_config._replace(detection_size=cast_string_to_int(detection_cfg['size']))
            if self._hc_config.detection_size is None:
                self._logger.error("Config: bad size value!")
        else:
            self._logger.info("Config: Missing size value, using default")

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

            detection_data = self._hc.read_and_process_frame()

            if detection_data is None:
                if object_detected:
                    self._logger.info("No object(s) detected")
                    self._hc.disable_frame_saving()
                object_detected = False
                continue

            if self._latest_cascade_status is None:
                # Special case: Initially we don't have any saved cascade
                # status, so we use the cascades from first processed frames
                # for initialization.
                self._latest_cascade_status = {}
                for cascade_file in detection_data.cascade_status:
                    self._latest_cascade_status[cascade_file] = False

            for cascade_file, status in detection_data.cascade_status.items():
                if status != self._latest_cascade_status[cascade_file]:
                    # The detection status of the current cascade has changed
                    if status:
                        self._logger.info("Cascade: {} has detected (an) object(s)".format(cascade_file))
                        self._logger.info("  Rectangles:")
                        for rectangle in detection_data.rectangles[cascade_file]:
                            self._logger.info("    {}".format(rectangle))
                    else:
                        self._logger.info("Cascade: {} no longer detects any object(s)".format(cascade_file))

            self._latest_cascade_status = detection_data.cascade_status

            object_detected_new = False
            for status in self._latest_cascade_status:
                if status:
                    object_detected_new = True
                    break

            if object_detected_new and not object_detected:
                self._hc.enable_frame_saving()

            object_detected = object_detected_new

            time.sleep(1 / self._hc_config.recording_fps)

        self._hc.close()
