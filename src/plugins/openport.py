#-*- coding: utf-8 -*-
from base import BasePlugin
from mailer import send_mail 

import re
import subprocess

class Openport(BasePlugin):
    """ 
    Открыть порт для хоста на определенное время
     
    Формат: openport(порт,хост,время_в_минутах)
    """
    
    def run (self,context, sender):
        args = context.split(',')
        
        if len(args) != 3:
            raise Exception('Warning: cmd_openport - wrong arguments number (%s)' % (context,))
        
        port, host, time = args

        if not re.match('[\d]+', port):
            raise Exception('Warning: cmd_openport - wrong port value')

        if not re.match('[\d]+', time):
            raise Exception('Warning: cmd_openport - wrong time value')
        
        rule = ['INPUT','-p','tcp','--dport',port,'-s',host,'-j','ACCEPT']
        
        subprocess.call(['iptables','-A',] + rule)
        p1 = subprocess.Popen(['echo','iptables -D '+' '.join(rule)+'; echo "IPTABLES rule *** %s *** was successfully removed" | mail -s "Iptables rule was successfully removed" "%s" -b "%s"' % (' '.join(rule), sender, self.settings['ADMIN_EMAIL'])], stdout = subprocess.PIPE)
        p2 = subprocess.Popen(['at','now','+',time,'min'], stdin = p1.stdout, stdout=subprocess.PIPE).communicate()[0]
        
        send_mail(sender, u'Iptables rule was successfully added', u'IPTABLES rule *** %s *** was successfully added' % (' '.join(rule),))
        send_mail(self.settings['ADMIN_EMAIL'], u'Iptables rule was successfully added', u'IPTABLES rule *** %s *** was successfully added' % (' '.join(rule),))

