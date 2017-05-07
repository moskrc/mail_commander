#-*- coding: utf-8 -*-

import logging

class BasePlugin (object):
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(settings['LOGGER'])
        
    def run(self, context, sender ):
        pass