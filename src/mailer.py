#! -*- coding: utf-8 -*-

import smtplib
import logging
from email.MIMEText import MIMEText

def send_mail(toaddrs, subject, body, fromaddr='noreply@localhost'):
    """ Отправка почты """
    logger = logging.getLogger("mailcommander")
    msg = MIMEText(body.encode("utf-8"), "", "UTF-8")
    msg['Subject'] = subject
    msg['From'] = fromaddr
    msg['To'] = toaddrs
    
    try:
        con = smtplib.SMTP('localhost')
        con.set_debuglevel(0)
        con.sendmail(fromaddr, toaddrs, msg.as_string())
        con.quit()
    except Exception, e:
        logger.info('Message send failed %s' % str(e))
