import cv2
import logging
from collections import namedtuple
from .detector import Detector, DetectorException

SimpleMotionDetectorConfig = namedtuple('SimpleMotionDetectorConfig',
                                        ['diff_threshold',
                                         'blurring_size',
                                         'object_min_area',
                                         'pixel_intensity_threshold'],
                                        verbose=False)


# The simple motion detector detects objects by just subtracting the
# current frame with the previous and then analyze the diff.
# If the number of diffing pixels exceeds the threshold an object is
# considered detected.
# The code is a somewhat modified version of an example on Adrian
# Rosebrock's blog post:
#
# http://www.pyimagesearch.com/2015/05/25/basic-motion-detection-and-tracking-with-python-and-opencv/
#
# The most notable difference is that the current frame is diffed against
# the previous frame and not the background.
class SimpleMotionDetector(Detector):

    def __init__(self, name, config):

        Detector.__init__(self,
                          name=name)

        self._logger = logging.getLogger(__name__)

        self._prev_frame = None
        self._blurring_size = config.blurring_size
        self._diff_threshold = config.diff_threshold
        self._object_min_area = config.object_min_area
        self._pixel_intensity_threshold = config.pixel_intensity_threshold

    def detect(self, frame):

        if self._prev_frame is None:
            # Special case: First run.
            # We can't make a diff, so just return an empty rectangles list.
            self._prev_frame = frame
            return []

        # Blur the frame in order to reduce noise
        frame = cv2.GaussianBlur(frame, (self._blurring_size, self._blurring_size), 0)

        # Do the actual diffing
        frame_delta = cv2.absdiff(self._prev_frame, frame)
        thresh = cv2.threshold(frame_delta,
                               self._pixel_intensity_threshold,
                               255, cv2.THRESH_BINARY)[1]

        thresh = cv2.dilate(thresh, None, iterations=2)
        (im2, contours, _) = cv2.findContours(thresh.copy(),
                                              cv2.RETR_EXTERNAL,
                                              cv2.CHAIN_APPROX_SIMPLE)

        rects = []
        total_contour_area = 0
        for c in contours:
            cur_area = cv2.contourArea(c)
            if cur_area < self._object_min_area:
                continue

            total_contour_area += cur_area

            # compute the bounding box for the contour, draw it on the frame,
            # and update the text
            rect = cv2.boundingRect(c)
            rects.append(rect)

        (height, width) = frame.shape
        total_frame_area = height * width
        diff_percentage = (total_contour_area * 100) / total_frame_area
        if diff_percentage < self._diff_threshold:
            # No significant difference between this frame and the previous
            rects = []

        self._prev_frame = frame

        return rects
