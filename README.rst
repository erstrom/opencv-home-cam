
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

The configuration is divided into subsections with one subsection for each
component. The components are:

- cameras
- recorders
- detectors
- actions

Cameras
_______

Each camera has its own section with the below options:

- id:  The camera ID that will be used by OpenCV to open the camera device.
  On systems with only one camera (built-in camera in laptops etc.) the
  ID is usually 0.
- fps:  The capture rate in frames per second.
  This is how often images will be read from the input device.
  If the value exceeds the maximum fps supported by the recording
  device, the fps will be clamped to the maximum supported value.
- recorder:  An (optional) recorder associated with the camera
- detectors:  A comma separated list of detectors for this camera.

The current version of opencv-home-cam only supports one camera!

The camera sections are defined with the tag ``camera%d`` (*%d* is
a number starting from 0).

Recorders
_________

Recorders are used to record the captured frames from cameras.
A recorder must be connected to a camera (by setting the ``recorders``
option of the camera to an appropriate value) in order to be operational.

The recorder sections have options related to recording of the
captured video stream.

The recorder sections are defined with the tag ``recorder%d`` (*%d* is
a number starting from 0).

Detectors
_________

Detectors are used to detect objects in frames captured by a camera.
Different detectors can be used to detect different types of objects.

Currently, only two types of detectors are supported:

- Haar cascade
- HOG people detector (HOG = Histogram of Oriented Gradients)

The HOG people detector is used to detect pedestrians only, whereas the
Haar cascade detector can be used to detect different types of objects
depending on which cascade file is used.

The detector type is selected with the ``detector_type`` option.

The detection algorithms are parameterized and all parameters (the arguments
to the openCV ``detectMultiscale`` functions) are added in the config file.

The detection parameters are optional, default values will be used if they are
not explicitly added in the config file. The only exception is the
``cascade`` option that is mandatory for Haar cascade detectors (and not used
at all for HOG detectors).

A Haar detector must be associated with one specific cascade file.

For more details about the Haar cascade detection, check out the below links:

http://docs.opencv.org/2.4/modules/objdetect/doc/cascade_classification.html
http://docs.opencv.org/trunk/d7/d8b/tutorial_py_face_detection.html

A detector must be connected to a camera in order to become active. This is
done by adding the detector to the comma-separated ``detectors``-list of
the camera.

The detector sections are defined with the tag ``detector%d`` (*%d* is
a number starting from 0).

Actions
_______

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
- cool_down_time

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

The *cool_down_time* option will cause the action not to be invoked unless
at least cool_down_time seconds have elapsed since the last invocation.
Sometimes when objects are detected, there could be several transitions from
detect to no-detect depending on detector and on how the object moves etc.
It is often not desired to let the action trigger on all those transitions
(there could be a lot of email spamming if the sendemail action is used).

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

If the action is associated with several detectors, the action script might
be launch several times for each detector that has yielded an object detection.
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

