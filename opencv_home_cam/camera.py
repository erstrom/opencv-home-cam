import cv2
from collections import namedtuple
import logging
import imutils


CameraConfig = namedtuple('CameraConfig',
                          ['cam_id',
                           'fps',
                           'recorder',
                           'detectors'],
                          verbose=False)


class CameraException(Exception):

    pass


class Camera:

    def __init__(self, cam_id):

        self._logger = logging.getLogger(__name__)

        self._video_capture = cv2.VideoCapture(int(cam_id))
        if not self._video_capture.isOpened():
            raise CameraException("Unable to open camera")

        # Get the resolution of the capture device
        width = self._video_capture.get(3)
        height = self._video_capture.get(4)

        # We are going to resize all captured frames to a width of max 400 pixels,
        # so we must make sure the recording resolution matches the rescaled
        # frames.
        rec_width = min(400, width)
        rec_height = rec_width * height / width
        self._resolution = (int(rec_width), int(rec_height))

    def get_resolution(self):

        return self._resolution

    def capture_frame(self):

        if not self._video_capture.isOpened():
            return None

        ret, frame = self._video_capture.read()
        if not ret:
            return None

        # Resize the frame.
        # Below code snippet is taken from:
        # http://www.pyimagesearch.com/2015/11/09/pedestrian-detection-opencv/
        # load the image and resize it to (1) reduce detection time
        # and (2) improve detection accuracy
        frame = imutils.resize(frame, width=min(400, frame.shape[1]))

        return frame

    def close(self):

        if self._video_capture is not None:
            self._logger.info("Closing video capture device")
            self._video_capture.release()
