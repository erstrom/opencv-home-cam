import threading
import logging
import configparser
import time
import ast
from collections import namedtuple
import re
from opencv_home_cam import HomeCam, HomeCamException, HomeCamDetectionData
from .camera import Camera, CameraConfig, CameraException
from .recorder import Recorder, RecorderConfig
from .detector import Detector
from .haar_cascade_detector import HaarCascadeDetector, HaarCascadeDetectorConfig
from .action import Action, ActionConfig


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


class HomeCamManagerException(Exception):

    pass


class HomeCamManager:

    def __init__(self, config_file):

        self._logger = logging.getLogger(__name__)

        self._cp = configparser.ConfigParser()
        self._cp.read(config_file)

        self._read_cameras()
        self._read_recorders()
        self._read_detectors()
        self._read_actions()

        if len(self._cameras) == 0:
            # We need at least one camera!
            raise HomeCamManagerException("No cameras specified. Add at least one camera section")

        # Currently, only one camera is supported.
        camera_cfg = self._cameras[0]
        camera = Camera(camera_cfg.cam_id)
        # Get the resolution of the camera. We must use the same resolution
        # for the recorder
        camera_resolution = camera.get_resolution()

        # Find the recorder associated with the camera (if any) and create
        # a recorder object.
        if camera_cfg.recorder in self._recorders:
            recorder_cfg = self._recorders[camera_cfg.recorder]
            recorder = Recorder(config=recorder_cfg,
                                fps=camera_cfg.fps,
                                resolution=camera_resolution)
        else:
            recorder = None

        self._hc = HomeCam(camera=camera,
                           detectors=self._detectors,
                           recorder=recorder)

        self._fps = camera_cfg.fps
        self._running = False
        self._latest_detector_status = None

    def _read_cameras(self):

        camera_nbr = 0
        self._cameras = []

        while True:
            camera_section = 'camera' + str(camera_nbr)
            if camera_section not in self._cp:
                break

            camera_cfg = self._read_camera_config(camera_section)
            if camera_cfg is None:
                break

            self._cameras.append(camera_cfg)

            camera_nbr += 1

    def _read_recorders(self):

        recorder_nbr = 0
        self._recorders = {}

        while True:
            recorder_section = 'recorder' + str(recorder_nbr)
            if recorder_section not in self._cp:
                break

            recorder_cfg = self._read_recorder_config(recorder_section)
            if recorder_cfg is None:
                break

            self._recorders[recorder_section] = recorder_cfg

            recorder_nbr += 1

    def _read_actions(self):

        action_nbr = 0
        self._actions = []

        while True:
            action_section = 'action' + str(action_nbr)
            if action_section not in self._cp:
                break

            action_cfg = self._read_action_config(action_section)
            if action_cfg is None:
                break

            action = Action(config=action_cfg)
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

    def _read_recorder_config(self, recorder_section):

        rec_cfg = self._cp[recorder_section]

        if 'file_limit' in rec_cfg:
            file_limit = cast_string_to_int(rec_cfg['file_limit'])
            if file_limit is None:
                raise HomeCamManagerException("Config: bad file_limit value!")
        else:
            file_limit = 10
            self._logger.info("Config: Missing file_limit value, using default")

        if 'time_limit' in rec_cfg:
            time_limit = cast_string_to_int(rec_cfg['time_limit'])
            if time_limit is None:
                raise HomeCamManagerException("Config: bad time_limit value!")
        else:
            time_limit = 60
            self._logger.info("Config: Missing time_limit value, using default")

        if 'recording_dir' in rec_cfg:
            recording_dir = rec_cfg['recording_dir']
            if recording_dir is None:
                raise HomeCamManagerException("Config: Bad output directory path!")
        else:
            raise HomeCamManagerException("Config: Missing recording_dir value!")

        if 'recording_file_base' in rec_cfg:
            recording_file_base = rec_cfg['recording_file_base']
            if recording_file_base is None:
                raise HomeCamManagerException("Config: Bad output file base!")
        else:
            raise HomeCamManagerException("Config: Missing recording_file_base value!")

        recorder_config = RecorderConfig(file_limit=file_limit,
                                         time_limit=time_limit,
                                         directory=recording_dir,
                                         file_base=recording_file_base)
        return recorder_config

    def _read_camera_config(self, camera_section):

        camera_cfg = self._cp[camera_section]

        if 'id' in camera_cfg:
            cam_id = camera_cfg['id']
            if cam_id is None:
                raise HomeCamManagerException("Config: bad cam_id value!")
        else:
            cam_id = 0
            self._logger.info("Config: Missing cam_id value, using default")

        if 'fps' in camera_cfg:
            fps = cast_string_to_float(camera_cfg['fps'])
            if fps is None:
                raise HomeCamManagerException("Config: bad fps value!")
        else:
            fps = 20.0
            self._logger.info("Config: Missing fps value, using default")

        if 'recorder' in camera_cfg:
            recorder = camera_cfg['recorder']
            if recorder is None:
                raise HomeCamManagerException("Config: bad recorder!")
            if recorder not in self._cp:
                raise HomeCamManagerException("Config: {}: Missing section for {} in config file!".format(camera_section, recorder))
        else:
            recorder = None
            self._logger.info("Config: No recorders for {}".format(camera_section))

        camera_config = CameraConfig(cam_id=cam_id,
                                     fps=fps,
                                     recorder=recorder)
        return camera_config

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

                    for action in self._actions:
                        action.invoke(status, detector_name, detection_data.frame)

            self._latest_detector_status = detection_data.detector_status

            object_detected_new = False
            for status in self._latest_detector_status:
                if status:
                    object_detected_new = True
                    break

            if object_detected_new and not object_detected:
                self._hc.enable_frame_saving()

            object_detected = object_detected_new

            time.sleep(1 / self._fps)

        self._hc.close()
