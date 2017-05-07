#-*- coding: utf-8 -*-
from base import BasePlugin
from mailer import send_mail 

class Stat(BasePlugin):
    """ 
    Активные пользователи, средняя загрузка, общая информация 
    
    Формат: stat()
    """
    
    def run (self,context, sender):
        import subprocess
        out = ''.join(subprocess.Popen(['w'],stdout=subprocess.PIPE).stdout.readlines())
        send_mail(sender, u'RE: stat', out.decode("utf-8"))        


class Freespace(BasePlugin):
    """ 
    Свободное место на указанном разделе 
    
    Формат: freespace(/dev/sda1)
    """
    
    def run (self,context, sender):
        import subprocess
        out = ''.join(subprocess.Popen(['df','-hlT',context],stdout=subprocess.PIPE).stdout.readlines())
        send_mail(sender, u'RE: Free space on %s' % (context,), out.decode("utf-8"))
