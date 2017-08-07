import cv2
from collections import namedtuple
import logging
import re
import os


RecorderConfig = namedtuple('RecorderConfig',
                            ['file_limit',
                             'time_limit',
                             'directory',
                             'file_base'],
                            verbose=False)


class Recorder:

    def __init__(self, config, fps, resolution):

        self._logger = logging.getLogger(__name__)

        self._file_limit = config.file_limit
        self._directory = config.directory
        self._file_base = config.file_base
        self._frame_limit = config.time_limit * fps
        self._resolution = resolution
        self._fps = fps
        self._ext = '.avi'
        self._scan_video_files()
        self._open_new_video_file()

    def _scan_video_files(self):

        directory = self._directory
        base = self._file_base
        ext = self._ext
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

        directory = self._directory
        base = self._file_base
        ext = self._ext

        new_file_name = directory + '/' + base + str(self._cur_outfile_index) + ext
        self._logger.info("Opening new output file: %s", new_file_name)
        fourcc = cv2.VideoWriter_fourcc(*'mjpa')
        self._logger.info("recording resoluton: {}".format(self._resolution))
        self._outfile = cv2.VideoWriter(new_file_name, fourcc,
                                        self._fps,
                                        self._resolution)
        self._nbr_of_outfiles += 1
        self._cur_nbr_of_recorded_frames = 0

    def _remove_old_video_file(self):

        directory = self._directory
        base = self._file_base
        ext = self._ext

        oldest_filename = directory + '/' + base + str(self._cur_outfile_lowest_index) + ext
        self._logger.info("Removing old output file: %s", oldest_filename)
        os.remove(oldest_filename)
        # Update oldest and current index by rescanning all outfiles
        self._scan_video_files()

    def record_frame(self, frame):

        if self._cur_nbr_of_recorded_frames > self._frame_limit:
            self._logger.info("Switching output file")
            self._outfile.release()
            self._cur_outfile_index += 1
            self._open_new_video_file()

        self._outfile.write(frame)

        self._cur_nbr_of_recorded_frames += 1
        if self._nbr_of_outfiles > self._file_limit:
            self._remove_old_video_file()

    def close(self):

        if self._outfile is not None:
            self._logger.info("Closing video output file")
            self._outfile.release()
