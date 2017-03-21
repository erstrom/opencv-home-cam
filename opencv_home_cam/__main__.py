import argparse
import traceback
import sys
import os
import cv2
import signal
from opencv_home_cam import HomeCamManager, HomeCamException

description = "OpenCV home cam test app"


def signal_handler(signal, frame):

    global hcm

    sys.stderr.write('Signal received!')
    hcm.stop()


def load_options():

    global parsed_args
    parser = argparse.ArgumentParser(prog="home_cam_tester",
                                     description=description)

    parser.add_argument('-a', '--cascade-file', nargs='+', type=str,
                             help="Cascade file(s) for OpenCV.")
    parser.add_argument('-c', '--config-file',
                             help="Configuraton file.")

    parsed_args = parser.parse_args()


def main():
    global parsed_args
    global hcm
    load_options()
    hcm = None

    try:

        if not parsed_args.cascade_file:
            sys.stderr.write('Missing input cascade file(s)\n')
            exit(1)

        if not parsed_args.config_file:
            sys.stderr.write('Missing input config file\n')
            exit(1)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        hcm = HomeCamManager(config_file=parsed_args.config_file,
                             cascade_files=parsed_args.cascade_file)

        hcm.start()
        hcm.wait()

    except IOError as err:
        sys.stderr.write('{}\n'.format(err))
    except HomeCamException as err:
        sys.stderr.write('{}\n'.format(err))
    except:
        traceback.print_exc()

if __name__ == "__main__":
    main()
