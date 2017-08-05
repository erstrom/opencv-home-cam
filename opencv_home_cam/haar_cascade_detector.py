import cv2
import logging
from collections import namedtuple
from .detector import Detector, DetectorException

HaarCascadeDetectorConfig = namedtuple('HaarCascadeDetectorConfig',
                                       ['scale_factor',
                                        'min_neighbours',
                                        'min_size',
                                        'cascade_file'],
                                       verbose=False)


class HaarCascadeDetector(Detector):

    def __init__(self, name, config):

        Detector.__init__(self,
                          name=name)

        self._scale_factor = config.scale_factor
        self._min_neighbours = config.min_neighbours
        self._min_size = config.min_size

        self._cascade = cv2.CascadeClassifier(config.cascade_file)
        if self._cascade is None:
            raise DetectorException("Bad cascade file")

    def detect(self, frame):

        rects = self._cascade.detectMultiScale(frame,
                                               scaleFactor=self._scale_factor,
                                               minNeighbors=self._min_neighbours,
                                               minSize=(self._min_size, self._min_size))
        return rects
