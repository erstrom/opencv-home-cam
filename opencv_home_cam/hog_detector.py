import cv2
import logging
from collections import namedtuple
from .detector import Detector, DetectorException

HogPeopleDetectorConfig = namedtuple('HogPeopleDetectorConfig',
                                     ['scale_factor',
                                      'padding',
                                      'win_stride'],
                                     verbose=False)


class HogPeopleDetector(Detector):

    def __init__(self, name, config):

        Detector.__init__(self,
                          name=name)

        self._hog = cv2.HOGDescriptor()
        if self._hog is None:
            raise DetectorException("Unable to create HOG descriptor")

        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        self._scale_factor = config.scale_factor
        self._padding = config.padding
        self._win_stride = config.win_stride

    def detect(self, frame):

        # detect people in the image
        (rects, weights) = self._hog.detectMultiScale(frame,
                                                      winStride=self._win_stride,
                                                      padding=self._padding,
                                                      scale=self._scale_factor)
        return rects
