#! /usr/bin/env python
#! -*- coding: utf-8 -*-

from __future__ import with_statement
import os
import sys
import datetime
import hashlib
    
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))

def gen_key(date = datetime.datetime.today(), seed_file = os.path.join(PROJECT_DIR,"seed")):
    
    if not os.path.exists(seed_file):
        print 'Seed file not found'
        sys.exit(1)
    
    if isinstance(date,str):
        from dateutil import parser
        date = parser.parse(date)
        
    hour = date.timetuple()[3]
    yday = date.timetuple()[-2]
    repeats = yday + hour
    
    with open(seed_file,'r') as file:
        key = file.read() 
    
    for x in range(repeats):
        key = hashlib.md5(key).hexdigest()
    
    return date, key

if __name__ == "__main__":
    date, password = gen_key()
    print u"До %s часа(ов) пароль: %s" % ((date + datetime.timedelta(0,0,0,0,0,1)).strftime("%H"),password) 
