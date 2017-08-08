import numpy
import cv2
import imutils
import os
import re
import logging
from collections import namedtuple
from .detector import Detector
from .recorder import Recorder


# frame          - The current frame (image)
# detector_status - A dict of detection status (boolean) for all detectors.
#                  The detector name is the dict key.
#                  True => The detector has detected an object, False => No detection.
# rectangles     - A dict of (x, y, width, height) tuples forming a rectangle
#                  of each match in the current frame. The current detector
#                  name is the dict key.
HomeCamDetectionData = namedtuple('HomeCamDetectionData',
                                  ['frame',
                                   'detector_status',
                                   'rectangles'],
                                  verbose=False)


class HomeCamException(Exception):

    pass


class HomeCam:

    def __init__(self, camera, detectors, recorder):

        self._logger = logging.getLogger(__name__)

        if camera is None:
            raise HomeCamException("Missing camera")

        if recorder is None:
            raise HomeCamException("Missing recorder")

        if detectors is None:
            raise HomeCamException("Missing detector(s)")

        self._camera = camera
        self._recorder = recorder
        self._detectors = detectors
        self._save_frame = False

    # Read one frame from the cam and process it.
    # Returns a HomeCamDetectionData named tuple containing all detection
    # data.
    def read_and_process_frame(self):

        # Initialize the detection data
        detector_status = {}
        rectangles = {}
        for detector in self._detectors:
            detector_status[detector.get_name()] = False
            rectangles[detector.get_name()] = None

        # Capture frame
        frame = self._camera.capture_frame()
        if frame is None:
            return HomeCamDetectionData(frame=None,
                                        detector_status=detector_status,
                                        rectangles=rectangles)

        frame_gs = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Check detections for each detector
        for detector in self._detectors:
            obj = detector.detect(frame_gs)

            if len(obj) == 0:
                continue

            detector_status[detector.get_name()] = True
            rectangles[detector.get_name()] = obj

            for (x, y, w, h) in obj:
                cv2.rectangle(frame, (x, y),
                              (x+w, y+h),
                              detector.get_rgb_tuple(),
                              2)

        if self._save_frame and self._recorder is not None:
            self._recorder.record_frame(frame)

        return HomeCamDetectionData(frame=frame,
                                    detector_status=detector_status,
                                    rectangles=rectangles)

    def enable_frame_saving(self):

        self._save_frame = True

    def disable_frame_saving(self):

        self._save_frame = False

    def close(self):

        self._camera.close()

        if self._recorder is not None:
            self._recorder.close()
