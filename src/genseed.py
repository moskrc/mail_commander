#! /usr/bin/env python
#! -*- coding: utf-8 -*-

from random import choice
import hashlib
import os

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
noise = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(2048)])
key = hashlib.md5(noise)
print key.hexdigest()
