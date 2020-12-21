#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="liftpose",
    version="0.1",
    author="Adam Gosztolai & Semih Gunel",
    packages=["liftpose"],
    description="Monocular 3D pose Estimation on Labatoary Animals",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NeLy-EPFL/LiftPose3D",
)