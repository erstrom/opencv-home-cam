import cv2
import subprocess
from collections import namedtuple
import tempfile
import os
import datetime
import time


ActionConfig = namedtuple('ActionConfig',
                          ['command',
                           'detectors',
                           'trigger_detection',
                           'trigger_no_detection',
                           'save_frame',
                           'save_frame_dir'],
                          verbose=False)


class Action:

    def __init__(self, config):

        self._command = config.command
        self._detectors = config.detectors
        self._trigger_detection = config.trigger_detection
        self._trigger_no_detection = config.trigger_no_detection
        self._save_frame = config.save_frame
        self._save_frame_dir = config.save_frame_dir

    def invoke(self, detection, detector_name, frame):

        if ((self._trigger_detection and detection) or
            (self._trigger_no_detection and not detection)):
            for action_detector in self._detectors:
                if action_detector == detector_name:
                    if self._save_frame:
                        # Create a temporary file for the current frame
                        image = tempfile.NamedTemporaryFile(suffix='.jpg',
                                                            prefix='opencv-home-cam-',
                                                            dir=self._save_frame_dir)
                        image_path = image.name
                        cv2.imwrite(image_path, frame)
                    else:
                        image_path = "No image"
                    # It is time to invoke the action script
                    self._invoke_command(detection,
                                         detector_name,
                                         self._command,
                                         image_path)
                    if self._save_frame:
                        # Remove the temporary file.
                        image.close()
                    break

    def _invoke_command(self, detection, detector_name, command, image_path):

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
