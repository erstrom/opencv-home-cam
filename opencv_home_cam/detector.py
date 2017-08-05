from abc import ABCMeta, abstractmethod


# Hard coded BGR tuples for rectangles
BGR_RED = (0, 0, 255)
BGR_GREEN = (0, 255, 0)
BGR_BLUE = (255, 0, 0)
BGR_YELLOW = (0, 255, 255)
BGR_CYAN = (255, 255, 0)
BGR_MAGENTA = (255, 0, 255)
COLORS = [BGR_RED, BGR_GREEN, BGR_BLUE, BGR_YELLOW, BGR_CYAN, BGR_MAGENTA]


class DetectorException:
    pass


class Detector:
    __metaclass__ = ABCMeta
    _color_cnt = 0

    def __init__(self, name):
        # Associate a color with the detector.
        # The color will be used when drawing rectangles in the recordings
        # of all detections made with the detector.
        self._rgb_tuple = COLORS[Detector._color_cnt % len(COLORS)]
        Detector._color_cnt += 1
        self._name = name

    @abstractmethod
    def detect(self, frame):
        pass

    def get_rgb_tuple(self):
        return self._rgb_tuple

    def get_name(self):
        return self._name
