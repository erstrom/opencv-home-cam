import cv2
import threading
import logging
import configparser
import time
import ast
import os
import datetime
import subprocess
from collections import namedtuple
import re
import tempfile
from opencv_home_cam import HomeCam, HomeCamException, HomeCamConfig
from .detector import Detector
from .haar_cascade_detector import HaarCascadeDetector, HaarCascadeDetectorConfig


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
    if (s.lower() == 'true' or
        s.lower() == '1' or
        s.lower() == 'on'):
        return True
    elif (s.lower() == 'false' or
          s.lower() == '0' or
          s.lower() == 'off'):
        return False
    else:
        return None


def cast_string_to_tuple(s):
    try:
        return ast.literal_eval(s)
    except ValueError:
        return None


ActionConfig = namedtuple('ActionConfig',
                          ['command',
                           'detectors',
                           'trigger_detection',
                           'trigger_no_detection',
                           'save_frame',
                           'save_frame_dir'],
                          verbose=False)


class HomeCamManagerException(Exception):

    pass


class HomeCamManager:

    def __init__(self, config_file):

        self._logger = logging.getLogger(__name__)

        self._cp = configparser.ConfigParser()
        self._cp.read(config_file)

        if 'recording' in self._cp:
            self._read_recording_config()

        self._read_detectors()
        self._read_actions()

        self._hc = HomeCam(config=self._hc_config, detectors=self._detectors)

        self._running = False
        self._latest_detector_status = None

    def _create_default_recording_config(self):

        return HomeCamConfig(recording_cam_id=0,
                             recording_fps=20.0,
                             recording_file_limit=10,
                             recording_time_limit=60,
                             recording_enable=False,
                             recording_dir=None,
                             recording_file_base=None)

    def _read_actions(self):

        action_nbr = 0
        self._actions = []

        while True:
            action_section = 'action' + str(action_nbr)
            if action_section not in self._cp:
                break

            action = self._read_action_config(action_section)
            if action is not None:
                self._actions.append(action)

            action_nbr += 1

    def _read_detectors(self):

        detector_nbr = 0
        self._detectors = []

        while True:
            detector_section = 'detector' + str(detector_nbr)
            if detector_section not in self._cp:
                break

            detector_cfg = self._read_detector_config(detector_section)
            if detector_cfg is None:
                break

            detector = HaarCascadeDetector(name=detector_section, config=detector_cfg)
            self._detectors.append(detector)

            detector_nbr += 1

    def _read_recording_config(self):

        rec_cfg = self._cp['recording']

        self._hc_config = self._create_default_recording_config()

        if 'fps' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_fps=cast_string_to_float(rec_cfg['fps']))
            if self._hc_config.recording_fps is None:
                raise HomeCamManagerException("Config: bad fps value!")
        else:
            self._logger.info("Config: Missing fps value, using default")

        if 'file_limit' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_file_limit=cast_string_to_int(rec_cfg['file_limit']))
            if self._hc_config.recording_file_limit is None:
                raise HomeCamManagerException("Config: bad file_limit value!")
        else:
            self._logger.info("Config: Missing file_limit value, using default")

        if 'time_limit' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_time_limit=cast_string_to_int(rec_cfg['time_limit']))
            if self._hc_config.recording_time_limit is None:
                raise HomeCamManagerException("Config: bad time_limit value!")
        else:
            self._logger.info("Config: Missing time_limit value, using default")

        if 'cam_id' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_cam_id=cast_string_to_int(rec_cfg['cam_id']))
            if self._hc_config.recording_cam_id is None:
                raise HomeCamManagerException("Config: bad cam_id value!")
        else:
            self._logger.info("Config: Missing cam_id value, using default")

        if 'enable' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_enable=cast_string_to_bool(rec_cfg['enable']))
            if self._hc_config.recording_enable is None:
                raise HomeCamManagerException("Config: Bad output enable option!")
        else:
            self._logger.info("Config: Missing enable value, using default")

        if 'recording_dir' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_dir=rec_cfg['recording_dir'])
            if self._hc_config.recording_dir is None:
                raise HomeCamManagerException("Config: Bad output directory path!")
        elif self._hc_config.recording_enable is not None:
            raise HomeCamManagerException("Config: Missing recording_dir value!")

        if 'recording_file_base' in rec_cfg:
            self._hc_config = self._hc_config._replace(recording_file_base=rec_cfg['recording_file_base'])
            if self._hc_config.recording_file_base is None:
                raise HomeCamManagerException("Config: Bad output file base!")
        elif self._hc_config.recording_enable is not None:
            raise HomeCamManagerException("Config: Missing recording_file_base value!")

    def _read_detector_config(self, detector_section):

        detection_cfg = self._cp[detector_section]

        if 'cascade' in detection_cfg:
            cascade_str = detection_cfg['cascade']
            if cascade_str is None:
                raise HomeCamManagerException("Config: bad cascade!")
        else:
            raise HomeCamManagerException("Config: Missing cascade file!")

        if 'scale_factor' in detection_cfg:
            scale_factor = cast_string_to_float(detection_cfg['scale_factor'])
            if scale_factor is None:
                raise HomeCamManagerException("Config: bad scale_factor value!")
        else:
            scale_factor = 1.1
            self._logger.info("Config: Missing scale_factor value, using default")

        if 'min_neighbours' in detection_cfg:
            min_neighbours = cast_string_to_int(detection_cfg['min_neighbours'])
            if min_neighbours is None:
                raise HomeCamManagerException("Config: bad min_neighbours value!")
        else:
            min_neighbours = 3
            self._logger.info("Config: Missing min_neighbours value, using default")

        if 'size' in detection_cfg:
            min_size = cast_string_to_int(detection_cfg['size'])
            if min_size is None:
                raise HomeCamManagerException("Config: bad size value!")
        else:
            min_size = 3
            self._logger.info("Config: Missing size value, using default")

        detector_config = HaarCascadeDetectorConfig(scale_factor=scale_factor,
                                                    min_neighbours=min_neighbours,
                                                    min_size=min_size,
                                                    cascade_file=cascade_str)
        return detector_config

    def _read_action_config(self, action_section):

        action_cfg = self._cp[action_section]

        if 'command' in action_cfg:
            command = action_cfg['command']
            if command is None:
                raise HomeCamManagerException("Bad command for section {}!".format(action_section))
        else:
            raise HomeCamManagerException("Missing command for section {}!".format(action_section))

        detectors = []
        if 'detectors' in action_cfg:
            detectors_str = action_cfg['detectors']
            if detectors_str is None:
                raise HomeCamManagerException("Config: bad detectors!")
            detectors_str_a = detectors_str.split(",")
            for detector in detectors_str_a:
                # Make sure the detector exists in the config file
                if detector not in self._cp:
                    raise HomeCamManagerException("Config: {}: Missing section for detector {} in config file!".format(action_section, detector))
                detectors.append(detector)
        else:
            self._logger.info("Missing detectors for {}".format(action_section))
            self._logger.info("Action will be invoked for all detectors.")

        if 'triggers' in action_cfg:
            triggers_str = action_cfg['triggers']
            if triggers_str is None:
                raise HomeCamManagerException("Config: bad trigger!")
            trigger_detection = False
            trigger_no_detection = False
            triggers = triggers_str.split(",")
            for trigger in triggers:
                trigger.strip()
                # We accept a few different string values for triggers.
                # Detection triggers:
                if (trigger.lower() == 'detect' or
                    trigger.lower() == 'detection' or
                    trigger.lower() == 'match'):
                    trigger_detection = True
                # Non-detection triggers:
                elif (trigger.lower() == 'undetect' or
                      trigger.lower() == 'no-detect' or
                      trigger.lower() == 'no-match'):
                    trigger_no_detection = True
        else:
            self._logger.info("Missing triggers for section {}".format(action_section))
            self._logger.info("Using default triggers")
            trigger_detection = True
            trigger_no_detection = False

        if 'save_frame' in action_cfg:
            save_frame = cast_string_to_bool(action_cfg['save_frame'])
            if save_frame is None:
                raise HomeCamManagerException("Config: Bad save_frame option for section {}!".format(action_section))
        else:
            self._logger.info("Missing save_frame option for section {}".format(action_section))
            self._logger.info("Skipping detection frame saving")
            save_frame = False

        if 'save_frame_dir' in action_cfg:
            save_frame_dir = action_cfg['save_frame_dir']
            if save_frame_dir is None:
                raise HomeCamManagerException("Config: Bad save_frame_dir option for section {}!".format(action_section))
        else:
            save_frame_dir = "/tmp"
            self._logger.info("Missing save_frame_dir option for section {}".format(action_section))
            self._logger.info("Using default dir: {}".format(save_frame_dir))

        action_config = ActionConfig(command=command,
                                     detectors=detectors,
                                     trigger_detection=trigger_detection,
                                     trigger_no_detection=trigger_no_detection,
                                     save_frame=save_frame,
                                     save_frame_dir=save_frame_dir)
        return action_config

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

            if self._latest_detector_status is None:
                # Special case: Initially we don't have any saved detector
                # status, so we use the detectors from first processed frames
                # for initialization.
                self._latest_detector_status = {}
                for detector_name in detection_data.detector_status:
                    self._latest_detector_status[detector_name] = False

            for detector_name, status in detection_data.detector_status.items():
                if status != self._latest_detector_status[detector_name]:
                    # The detection status of the current detector has changed
                    if status:
                        self._logger.info("Detector: {} has detected (an) object(s)".format(detector_name))
                        self._logger.info("  Rectangles:")
                        for rectangle in detection_data.rectangles[detector_name]:
                            self._logger.info("    {}".format(rectangle))
                    else:
                        self._logger.info("Detector: {} no longer detects any object(s)".format(detector_name))

                    self._invoke_action(status, detector_name, detection_data.frame)

            self._latest_detector_status = detection_data.detector_status

            object_detected_new = False
            for status in self._latest_detector_status:
                if status:
                    object_detected_new = True
                    break

            if object_detected_new and not object_detected:
                self._hc.enable_frame_saving()

            object_detected = object_detected_new

            time.sleep(1 / self._hc_config.recording_fps)

        self._hc.close()

    def _invoke_action(self, detection, detector_name, frame):

        for action in self._actions:
            if ((action.trigger_detection and detection) or
                (action.trigger_no_detection and not detection)):
                for action_detector in action.detectors:
                    if action_detector == detector_name:
                        if action.save_frame:
                            # Create a temporary file for the current frame
                            image = tempfile.NamedTemporaryFile(suffix='.jpg',
                                                                prefix='opencv-home-cam-',
                                                                dir=action.save_frame_dir)
                            image_path = image.name
                            cv2.imwrite(image_path, frame)
                        else:
                            image_path = "No image"
                        # It is time to invoke the action script
                        self._invoke_action_command(detection,
                                                    detector_name,
                                                    action.command,
                                                    image_path)
                        if action.save_frame:
                            # Remove the temporary file.
                            image.close()
                        break

    def _invoke_action_command(self, detection, detector_name, command, image_path):

        # Setup environment variables that will be passed to the child
        # (action command)
        ts_raw = time.time()
        ts_date = datetime.datetime.fromtimestamp(ts_raw).strftime('%Y-%m-%d %H:%M:%S')

        os.environ["TIME_STAMP_RAW"] = str(ts_raw)
        os.environ["TIME_STAMP_DATE"] = ts_date
        os.environ["DETECTOR"] = detector_name
        if detection:
            os.environ["TRIGGER"] = "detect"
        else:
            os.environ["TRIGGER"] = "no-detect"
        os.environ["IMAGE_PATH"] = image_path

        # Launch command and wait for it to complete.
        res = subprocess.run(command)
        if res.returncode != 0:
            self._logger.warning("Command {} returned non-zero exitcode ({})".format(command, res.returncode))
