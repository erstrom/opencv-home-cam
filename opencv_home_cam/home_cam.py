import numpy
import cv2
import imutils
import os
import re
import logging
from collections import namedtuple
try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str, bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring


HomeCamConfig = namedtuple('HomeCamConfig',
                           ['recording_cam_id',
                            'recording_fps',
                            'recording_file_limit',
                            'recording_time_limit',
                            'recording_enable',
                            'recording_dir',
                            'recording_file_base',
                            'detection_scale_factor',
                            'detection_min_neighbours',
                            'detection_size',
                            'detection_cascade_files'],
                           verbose=False)


# frame          - The current frame (image)
# cascade_status - A dict of detection status (boolean) for all cascades.
#                  The current cascade file is the dict key.
#                  True => The cascade has detected an object, False => No detection.
# rectangles     - A dict of (x, y, width, height) tuples forming a rectangle
#                  of each match in the current frame. The current cascade
#                  file is the dict key.
HomeCamDetectionData = namedtuple('HomeCamDetectionData',
                                  ['frame',
                                   'cascade_status',
                                   'rectangles'],
                                  verbose=False)


# Hard coded BGR tuples for rectangles
BGR_RED = (0, 0, 255)
BGR_GREEN = (0, 255, 0)
BGR_BLUE = (255, 0, 0)
BGR_YELLOW = (0, 255, 255)
BGR_CYAN = (255, 255, 0)
BGR_MAGENTA = (255, 0, 255)
COLORS = [BGR_RED, BGR_GREEN, BGR_BLUE, BGR_YELLOW, BGR_CYAN, BGR_MAGENTA]


class HomeCamException(Exception):

    pass


class HomeCam:

    def __init__(self, config):

        self._logger = logging.getLogger(__name__)

        if config.detection_cascade_files is None:
            raise HomeCamException("Missing cascade file(s)")

        self._min_neighbours = config.detection_min_neighbours
        self._scale_factor = config.detection_scale_factor
        self._size = config.detection_size
        self._cascades = []
        self._save_frame = False
        color_cnt = 0

        for cascade_file in config.detection_cascade_files:
            cur_cascade = cv2.CascadeClassifier(cascade_file)
            if cur_cascade is None:
                raise HomeCamException("Bad cascade file")
            # Associate a color with the cascade.
            # The color will be used when drawing rectangles in the recordings
            # of all detections made with the cascade.
            rgb_tuple = COLORS[color_cnt % len(COLORS)]
            color_cnt += 1
            self._cascades.append((cascade_file, cur_cascade, rgb_tuple))

        self._video_capture = cv2.VideoCapture(int(config.recording_cam_id))
        if self._video_capture is None:
            raise HomeCamException("Unable to open camera")

        # Get the resolution of the capture device and use the same value for
        # recording
        width = self._video_capture.get(3)
        height = self._video_capture.get(4)
        # We are going to resize all captured frames to a width of max 400 pixels,
        # so we must make sure the recording resolution matches the rescaled
        # frames.
        rec_width = min(400, width)
        rec_height = rec_width * height / width
        self._recording_resolution = (int(rec_width), int(rec_height))

        if config.recording_enable:
            self._logger.info("Video recording enabled")
            self._recording_fps = config.recording_fps
            self._recording_file_limit = config.recording_file_limit
            self._recording_frame_limit = config.recording_time_limit * config.recording_fps

            self._recording_dir = config.recording_dir
            self._recording_file_base = config.recording_file_base
            self._recording_ext = '.avi'
            self._scan_video_files()
            self._open_new_video_file()
        else:
            self._outfile = None

    def _scan_video_files(self):

        directory = self._recording_dir
        base = self._recording_file_base
        ext = self._recording_ext
        regex = re.compile(base + '(\d+)')

        self._logger.info("Video files dir: %s. File base: %s",
                          directory, base)

        lowest_idx = 0x7fffffff
        highest_idx = 0
        nbr_of_files = 0
        for anyfile in os.listdir(directory):
            (anyfile_base, anyfile_ext) = os.path.splitext(anyfile)
            if not anyfile_ext == ext:
                continue

            m = regex.match(anyfile_base)
            if m is None:
                continue

            idx = int(m.group(1))
            if idx < lowest_idx:
                lowest_idx = idx
            if idx > highest_idx:
                highest_idx = idx
            nbr_of_files += 1

        self._nbr_of_outfiles = nbr_of_files
        if nbr_of_files == 0:
            # There are no logfiles stored in the log file directory
            self._logger.info("Videofile dir empty.")
            self._cur_outfile_index = 0
            self._cur_outfile_lowest_index = 0
        else:
            self._cur_outfile_index = highest_idx + 1
            self._cur_outfile_lowest_index = lowest_idx

        self._logger.info("Cur indices: highest = %d, lowest = %d",
                          self._cur_outfile_index, self._cur_outfile_lowest_index)

    def _open_new_video_file(self):

        directory = self._recording_dir
        base = self._recording_file_base
        ext = self._recording_ext

        new_file_name = directory + '/' + base + str(self._cur_outfile_index) + ext
        self._logger.info("Opening new output file: %s", new_file_name)
        fourcc = cv2.VideoWriter_fourcc(*'mjpa')
        self._logger.info("recording resoluton: {}".format(self._recording_resolution))
        self._outfile = cv2.VideoWriter(new_file_name, fourcc,
                                        self._recording_fps,
                                        self._recording_resolution)
        self._nbr_of_outfiles += 1
        self._cur_nbr_of_recorded_frames = 0

    def _remove_old_video_file(self):

        directory = self._recording_dir
        base = self._recording_file_base
        ext = self._recording_ext

        oldest_filename = directory + '/' + base + str(self._cur_outfile_lowest_index) + ext
        self._logger.info("Removing old output file: %s", oldest_filename)
        os.remove(oldest_filename)
        # Update oldest and current index by rescanning all outfiles
        self._scan_video_files()

    def _do_save_frame(self, frame):

        if self._cur_nbr_of_recorded_frames > self._recording_frame_limit:
            self._logger.info("Switching output file")
            self._outfile.release()
            self._cur_outfile_index += 1
            self._open_new_video_file()

        self._outfile.write(frame)

        self._cur_nbr_of_recorded_frames += 1
        if self._nbr_of_outfiles > self._recording_file_limit:
            self._remove_old_video_file()

    # Read one frame from the cam and process it.
    # Returns a HomeCamDetectionData named tuple containing all detection
    # data.
    def read_and_process_frame(self):

        # Initialize the detection data
        cascade_status = {}
        rectangles = {}
        for (cascade_file, cascade, rgb_tuple) in self._cascades:
            cascade_status[cascade_file] = False
            rectangles[cascade_file] = None

        # Check error conditions
        if not self._video_capture.isOpened():
            return HomeCamDetectionData(frame=None,
                                        cascade_status=cascade_status,
                                        rectangles=rectangles)

        ret, frame = self._video_capture.read()
        if not ret:
            return HomeCamDetectionData(frame=None,
                                        cascade_status=cascade_status,
                                        rectangles=rectangles)

        # Resize the frame.
        # Below code snippet is taken from:
        # http://www.pyimagesearch.com/2015/11/09/pedestrian-detection-opencv/
        # load the image and resize it to (1) reduce detection time
        # and (2) improve detection accuracy
        frame = imutils.resize(frame, width=min(400, frame.shape[1]))

        frame_gs = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Check detections for each cascade
        for (cascade_file, cascade, rgb_tuple) in self._cascades:
            obj = cascade.detectMultiScale(frame_gs,
                                           scaleFactor=self._scale_factor,
                                           minNeighbors=self._min_neighbours,
                                           minSize=(self._size, self._size))
            if len(obj) == 0:
                continue

            cascade_status[cascade_file] = True
            rectangles[cascade_file] = obj

            for (x, y, w, h) in obj:
                cv2.rectangle(frame, (x, y), (x+w, y+h), rgb_tuple, 2)

        if self._save_frame and self._outfile is not None:
            self._do_save_frame(frame)

        return HomeCamDetectionData(frame=frame_gs,
                                    cascade_status=cascade_status,
                                    rectangles=rectangles)

    def enable_frame_saving(self):

        self._save_frame = True

    def disable_frame_saving(self):

        self._save_frame = False

    def close(self):

        if self._video_capture is not None:
            self._logger.info("Closing video capture device")
            self._video_capture.release()

        if self._outfile is not None:
            self._logger.info("Closing video output file")
            self._outfile.release()
