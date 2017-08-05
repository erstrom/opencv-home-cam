
Overview
--------

opencv-home-cam is a tool used to implement a simple object detection
framework on top of opencv.

The main feature is the possibility to add action hooks (called actions)
that can be invoked if an object is detected. The action hook invocation
and settings for detection is controlled by a configuration file.

Prerequisites
-------------

opencv-home-cam requires the below tools/programs

- Python 3. (Python 2 has some problems with signals and threads)
- OpenCV 3 and its prerequisites

Docker
++++++

An easy and convenient way of running the program is to run it within a
docker container.

The docker container must of course contain all prerequisites (OpenCV and
Python).

An ubuntu based docker setup can be downloaded here:

https://github.com/erstrom/docker-opencv.git

See *README.rst* of *docker-opencv.git* for installation instructions.

If a "native" installation is preferred, the Dockerfile can be used as
documentation of all OpenCV prerequisites. The *build_opencv.sh* script can
of course be used outside of the docker container as well.

Installation
------------

Install opencv-home-cam with the *setup.py* script.

::

	python3 setup.py install

Make sure Python 3 is used, since the program does not work well with
Python 2.

Basic operation
---------------

Launch the program with ``--help`` or ``-h`` to get usage instructions:

::

	opencv_home_cam -h

The program needs a configuration file in order to be operational (see
below).

Configuration
+++++++++++++

The configuration is handled by the Python built-in *configparser* module.
It is capable of parsing config files using the Microsoft INI syntax.

See the official documentation for a detailed description of the config file
syntax:

https://docs.python.org/3/library/configparser.html

An example configuration file can be found in the *example-configs* directory
(*example-configs/config.ini*).

The file is commented with descriptions of each config option.

The configuration is divided into the below three sections:

- recording
- detectors (one section for each detector, see below for more info)
- action (one section for each action, see below for more info)

The recording section has options related to recording of the
captured video stream. Recording is optional and can be enabled/disabled
by setting the ``enable`` option to an appropriate value.

Detectors
+++++++++

The detector sections have options directly related to the OpenCV Haar-detection
algorithm. See the OpenCV documentation for more details:

http://docs.opencv.org/2.4/modules/objdetect/doc/cascade_classification.html
http://docs.opencv.org/trunk/d7/d8b/tutorial_py_face_detection.html

Each detector is associated with one specific cascade file.

The detector sections are defined with the tag ``detector%d`` (*%d* is
a number starting from 0).

Actions
+++++++

Actions are external programs or scripts that will be invoked by
opencv-home-cam when the associated launch criterion is met (usually a
detection or a transition from detection to no detection).

The launch criteria are defined in the config file in a section for each
action. The action sections are defined with the tag ``action%d`` (*%d* is
a number starting from 0).

Each action section will set the below options for the particular action:

- command
- detectors
- triggers
- save_frame

The *command* option is the path to the script that is going to be launched.

The *detectors* option is a comma separated list of detectors for the
action. The action will only be invoked if one of the detectors in the list
was used in the detection.

The *triggers* option is a comma separated list of triggers. Valid values are
``detect`` and ``no-detect``. ``no-detect`` means that the action will be
invoked when there is a transition from detection to no detection for any
of the associated detectors. If the list ``detect,no-detect`` is used, the
action will be invoked for both detections and transitions from detection
to no detection.

If no *triggers* option is present in the config file, a default
value will be used. The default trigger option is ``detect``

If no *detectors* are specified, the action will never be invoked (it must
be associated with a detector).

The *save_frame* option will make opencv-home-cam save the frame that caused
the launch of the action script into a temporary file. The path to the
temporary file will be passed on to the action script with the **IMAGE_PATH**
environment variable. The temporary file will be removed as soon as the
action script terminates.

Actions are optional, and if no action is desired, no ``action%d`` section
needs to be specified.

opencv-home-cam passes data to the action script via a set of environment
variables. They are listed below:

- **TIME_STAMP_RAW**: The "raw" time stamp in second and microseconds since
  the epoch.
- **TIME_STAMP_DATE**: A human readable string of the time stamp in the
  following format: YYYY-MM-DD HH:MM:SS
- **DETECTOR**: The detector that trigged the action invocation.
- **IMAGE_PATH**: The path to a jpg file containing the frame that caused
  the action to be invoked.

If the action is associated with several cascades, the action script might
be launch several time for each detector that has yielded an object detection.
In this case, the **DETECTOR** environment variable will of course be set to
the name of the particular detector that is associated with the action invocation.

Logging
+++++++

opencv-home-cam uses the Python built-in *logging* module for all logging.
The logging is configured using a separate logging configuration file

Below is a link to the specification of the logging configuration file format
used by the Python Logging module:

https://docs.python.org/2/library/logging.config.html#logging-config-fileformat

A ready to use example configuration file can be found in the *example-configs*
directory (example-configs/logging.ini).

Haar cascades
-------------

Depending on what opencv-home-cam is supposed to detect, different Haar
cascades should be used.

The *haar-cascades* subdirectory contains a few cascades for different
purposes.

Each cascade file will detect a specific type object.

As mentioned above, several cascades can be combined if detection of several
different types of objects is desired (resulting in higher CPU load).

OpenCV Haar cascades can be downloaded from various places on the internet.
Below is the location from where I have taken the example files in the
*haar-cascades* directory:

http://alereimondo.no-ip.org/OpenCV/34

