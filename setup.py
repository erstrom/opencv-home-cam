#!/usr/bin/env python

from setuptools import setup

setup(name="opencv_home_cam",
      version="0.1",
      description="OpenCV object detection wrapper for webcams",
      url="https://github.com/erstrom/opencv_home_cam",
      author="Erik Stromdahl",
      author_email="erik.stromdahl@gmail.com",
      license="MIT",
      long_description="\n",
      entry_points={
        "console_scripts": ["opencv_home_cam=opencv_home_cam.__main__:main"]
      },
      packages=["opencv_home_cam"],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development"
      ]
)
