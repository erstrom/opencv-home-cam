import numpy
import cv2
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
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring


HomeCamConfig = namedtuple('HomeCamConfig',
                           ['recording_cam_id',
                            'recording_fps',
                            'recording_resolution',
                            'recording_file_limit',
                            'recording_time_limit',
                            'recording_enable',
                            'recording_dir',
                            'recording_file_base',
                            'detection_scale_factor',
                            'detection_min_neighbours',
                            'detection_size'],
                           verbose=False)


class HomeCamException(Exception):

    pass


class HomeCam:

    def __init__(self, cascade_files, config):

        self._logger = logging.getLogger(__name__)
        if cascade_files is None:
            raise HomeCamException("Missing cascade file(s)")

        self._min_neighbours = config.detection_min_neighbours
        self._scale_factor = config.detection_scale_factor
        self._size = config.detection_size
        self._cascades = []
        self._save_frame = False

        if isinstance(cascade_files, basestring):
            cur_cascade = cv2.CascadeClassifier(cascade_files)
            if cur_cascade is None:
                raise HomeCamException("Bad cascade file")
            self._cascades.append(cur_cascade)
        elif isinstance(cascade_files, (list, tuple)):
            for cascade_file in cascade_files:
                cur_cascade = cv2.CascadeClassifier(cascade_file)
                if cur_cascade is None:
                    raise HomeCamException("Bad cascade file")
                self._cascades.append(cur_cascade)

        self._video_capture = cv2.VideoCapture(int(config.recording_cam_id))
        if self._video_capture is None:
            raise HomeCamException("Unable to open camera")

        if not isinstance(config.recording_resolution, tuple):
            raise HomeCamException("Bad resolution")

        if config.recording_enable:
            self._recording_fps = config.recording_fps
            self._recording_resolution = config.recording_resolution
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
    # Return an array of (x, y, w, h) tuples (rectangles) for all matches
    # in the current image.
    # If non of the  cascades detects an object, None will be returned.
    def read_and_process_frame(self):

        if not self._video_capture.isOpened():
            return None

        ret, frame = self._video_capture.read()

        frame_gs = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        objs = []
        for cascade in self._cascades:
            obj = cascade.detectMultiScale(frame_gs,
                                           scaleFactor=self._scale_factor,
                                           minNeighbors=self._min_neighbours,
                                           minSize=(self._size, self._size))
            if len(obj) == 0:
                continue

            objs.append(obj)

        if self._save_frame and self._outfile is not None:
            self._do_save_frame(frame)

        if len(objs) == 0:
            return None
        else:
            return objs

    def enable_frame_saving(self):

        self._logger.info("Frame saving enabled")
        self._save_frame = True

    def disable_frame_saving(self):

        self._logger.info("Frame saving disabled")
        self._save_frame = False

    def close(self):

        if self._video_capture is not None:
            self._logger.info("Closing video capture device")
            self._video_capture.release()

        if self._outfile is not None:
            self._logger.info("Closing video output file")
            self._outfile.release()
