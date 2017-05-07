#! /usr/bin/env python
#! -*- coding: utf-8 -*-

"""
==============================================================================
=== MailCommander - v 1.2.0 26.02.2010 г. для Python 2.5.4
==============================================================================

Просматривает почтовые сообщения с определенной темой и выполняет
содержащиеся в них команды. В одном письме может быть несколько команд,
каждая команда на новой строке. Расширяется путем написания реализации
для новых команд.

Как работает:

Для каждой строки в подходящем для анализа письме производится поиск команды.
Команда - выглядит как вызов функции в любом языке программирования. Т.е. это 
строка заканчивающаяся круглыми скобками в которых могут быть аргументы 
передаваемые этой команде.

Примеры возможных команд: freespace(/dev/sda1), shutdown(), 
openport(888, 192.168.1.1, 5) или synctime(timeserver.ru).

Если команда успешно найдена и соответствует изложенным выше требованиям - 
производится поиск плагина которому она будет передана для обработки.

Имя класса плагина имеет тоже самое имя что и команда но начинаться должна 
с большой буквы. Например, для команды freespace(/dev/sda1) будет вызван 
метод run плагина Freespace и в него будет передана строка '/dev/sda1'. 

Для того чтобы научить систему реагировать на новые команды нужно добавить
плагин с соответствующим именем и написать внутри него метод run с требуемой
логикой.

В качестве примера можно посмотреть реализацию команды которая открывает
для определенного узла порт машины на указанное время.

Формат команды: openport(номер_порта,адрес_удаленной_машины,время_в_минутах)

==============================================================================
"""
import os
import re
import inspect
import logging
import getopt, sys
import logging.handlers
from genkey import gen_key
from mailer import send_mail
import poplib, smtplib, email
from email.MIMEText import MIMEText
from ConfigParser import SafeConfigParser
from email.message import Message
    
PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))

class MailCommander(object):
    """ Базовая функциональность """
    
    def __init__(self, config_file):
        """ Конструктор """

        self.settings = self.load_settings(config_file)
        self.logger = self.load_logger('mailcommander') 
        self.logger.debug("Starting...")
        self.plugins = self.load_plugins()
        
    def load_logger(self,name):
        """ Логер с ротацией логов """

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        rh = logging.handlers.RotatingFileHandler(self.settings['LOG_FILE'], maxBytes=100000, backupCount=5)
        logger.addHandler(rh)

        if self.settings['DEBUG']:
            rh.setLevel(logging.DEBUG)
        else:
            rh.setLevel(logging.INFO)
    
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",datefmt='%d.%m.%y %H:%M:%S')
        rh.setFormatter(formatter)
        return logger

    def load_settings(self,config_file):
        """ Чтение файла конфигурации """
        
        def str2bool(v):
            return v.lower() in ["yes", "true", "t", "1", "y"]
        
        config = SafeConfigParser()

        if not os.path.exists(config_file):
            print 'Config file %s not found' % (config_file,)
            sys.exit(1)
            
        config.read(config_file)

        settings = {}
        
        settings['LOGGER'] = config.get('main', 'logger', 'mailcommander')
        settings['LOG_FILE'] = config.get('main', 'log_file', os.path.join(PROJECT_DIR,'mailcommander.log'))
        settings['SEED_FILE'] = config.get('main', 'seed_file', os.path.join(PROJECT_DIR,'seed'))
        settings['PLUGINS_DIR'] = config.get('main', 'plugins_dir', os.path.join(PROJECT_DIR,'plugins'))
        settings['CERTIFICATES_DIR'] = config.get('main', 'certificates_dir', os.path.join(PROJECT_DIR,'certificates'))
        settings['DEBUG'] = str2bool(config.get('main', 'debug', 'True'))
        settings['RESPONSE_ON_SUBJECT'] = config.get('main', 'response_on_subject', 'mailcom')
        settings['AUTH_METHOD'] = config.get('main', 'auth_method', 'password')
        
        settings['SERVER'] = config.get('pop3_server', 'server', 'localhost')
        settings['USER'] = config.get('pop3_server', 'user', 'root')
        settings['PASSWORD'] = config.get('pop3_server', 'password', '')
        settings['SSL'] = str2bool(config.get('pop3_server', 'ssl', 'False'))
        
        settings['ADMIN_EMAIL'] = config.get('emails', 'ADMIN_EMAIL', 'root@localhost')
        settings['ADMIN_EMAIL_ON_FAILED'] = config.get('emails', 'ADMIN_EMAIL_ON_FAILED', 'root@localhost')
        
        settings['CERTIFICATES'] = {}
        for x in config.items('certificates'):
            settings['CERTIFICATES'][x[0]] = x[1]
        
        return settings
        
    def load_plugins(self):
        """ Загрузка плагинов """
        
        import plugins.base

        _plugins = {}
        
        # Имена загруженных модулей
        modules = []
        
        # Перебирем файлы в папке plugins
        for fname in os.listdir(self.settings['PLUGINS_DIR']):
        
            # Нас интересуют только файлы с расширением .py
            if fname.endswith (".py"):
        
                # Обрежем расширение .py у имени файла
                module_name = fname[: -3]
                
                # Пропустим файлы base.py и __init__.py
                if module_name != "base" and module_name != "__init__":
                    self.logger.info("Loading module %s..." % module_name)
        
                    try:
                        # Загружаем модуль и добавляем его имя в список загруженных модулей
                        package_obj = __import__(self.settings['PLUGINS_DIR'].split('/')[-2] + "." +  module_name)
                        modules.append (module_name)
                    except Exception,e:
                        self.logger.info("Loading module %s failed. Details: %s" % (module_name, repr(e),))

        # Перебираем загруженные модули
        for modulename in modules:
            module_obj = getattr (package_obj, modulename)
    
            # Перебираем все, что есть внутри модуля
            for elem in dir (module_obj):  
                obj = getattr (module_obj, elem)
                # Это класс?
                if inspect.isclass(obj):
                    # Класс производный от BasePlugin?
                    if issubclass(obj, plugins.base.BasePlugin) and obj.__name__ != 'BasePlugin':
                        # Создаем экземпляр и выполняем функцию run
                        _plugins[obj.__name__] = obj(self.settings)
        
        return _plugins

    def check_mail(self):
        """ Поиск почтовых сообщений с нужной темой и запуск их обработки """
        
        self.logger.debug('Connecting to pop3 mail server')

        if self.settings['SSL']:
            con = poplib.POP3_SSL(self.settings['SERVER'])
        else:
            con = poplib.POP3(self.settings['SERVER'])
        
        con.getwelcome()
        con.user(self.settings['USER'])
        con.pass_(self.settings['PASSWORD'])
        
        # Находим сообщения с нужной темой
        our_letters = []
        response, lst, octets = con.list()
        
        for msg_num, msgsize in [i.split() for i in lst]:
            (resp, lines, octets) = con.retr(msg_num)
            message = email.message_from_string("\n".join(lines) + "\n\n")
            msg_subject = "".join([text for text, enc in email.Header.decode_header(message['subject'])])
            if re.search(self.settings['RESPONSE_ON_SUBJECT'], msg_subject.strip()): 
                our_letters.append({'message':message,'message_id':msg_num})

        # Обрабатываем наши сообщения
        self.logger.debug('Check mail, total found %d letters, %d letter(s) with commands' % (len(lst),len(our_letters)))
        for i, m in enumerate(our_letters):
            self.logger.info('Processing message %d of %d...' % (i+1, len(our_letters),))
            try:
                if self.settings['AUTH_METHOD'] == 'smime':
                    data = self.get_data_from_smime_message(m['message'])
                else:
                    data = self.get_data_from_password_message(m['message'])
                    
                self.process_message(data,m['message'])
                
            except Exception, e:
                self.logger.error(e)
                
            con.dele(m['message_id'])
        
        # Отключаемся
        self.logger.debug("Disconnecting...")
        con.quit()
    
    def clean_email(self,email):
        if '<' in email:
            beg = email.find('<')+1
            end = email.find('>')
            return email[beg:end]
        return email        
    
    def get_data_from_smime_message(self,message):
        """ Чтение текста из шифрованного сообщения """
        
        from M2Crypto import BIO, SMIME, X509
        msg_parts = [(part.get_filename(), part.get_payload(decode=True)) for part in message.walk() if part.get_content_type() == 'application/x-pkcs7-mime']
        self.logger.debug('Crypted message from %s' % message['from'])
        
        for name, data in msg_parts:
            if name == 'smime.p7m':
                s = SMIME.SMIME()
                
                # Свои ключ и сертификат
                recipient_key = os.path.join(self.settings['CERTIFICATES_DIR'],'recipient.key')
                recipient_cert = os.path.join(self.settings['CERTIFICATES_DIR'],'recipient.pem',)
                
                if not os.path.exists(recipient_key):
                    raise Exception("Recipient key %s not found" % recipient_key)

                if not os.path.exists(recipient_cert):
                    raise Exception("Recipient certificate %s not found" % recipient_cert)
                
                s.load_key(recipient_key,recipient_cert)
                bio = BIO.MemoryBuffer(str(message))
                p7, data = SMIME.smime_load_pkcs7_bio(bio)
                out = s.decrypt(p7)
                
                # Ищем сертификат отправителя письма
                try:
                    signer_cert_file_name = self.settings['CERTIFICATES'][self.clean_email(message['from'])]
                except KeyError:
                    raise Exception("Certificate record for email %s not found" % self.clean_email(message['from']))
                
                signer_cert_file = os.path.join(self.settings['CERTIFICATES_DIR'],signer_cert_file_name)
                
                if not os.path.exists(signer_cert_file):
                    raise Exception("Sender certificate %s not found" % signer_cert_file)
                
                x509 = X509.load_cert(signer_cert_file)
                sk = X509.X509_Stack()
                sk.push(x509)
                s.set_x509_stack(sk)

                # И авторити которым он был подписан
                signer_ca_file_name = 'ca_signer.pem'
                signer_ca_file = os.path.join(self.settings['CERTIFICATES_DIR'],signer_ca_file_name)

                if not os.path.exists(signer_ca_file):
                    raise Exception("Sender certificate authority %s not found" % signer_ca_file)
                
                st = X509.X509_Store()
                st.load_info(signer_ca_file)
                s.set_x509_store(st)
                
                p7_bio = BIO.MemoryBuffer(out)
                p7, data = SMIME.smime_load_pkcs7_bio(p7_bio)
                return s.verify(p7,data)
    
    def get_data_from_password_message(self,message):
        """ Чтение текста из сообщения с паролем """
        self.logger.debug('Password message from %s' % message['from'])
        
        msg_subject = "".join([text for text, enc in email.Header.decode_header(message['subject'])])
        try:
            subj, password = msg_subject.strip().split('#')
            if password.strip() != gen_key(message['date'], self.settings['SEED_FILE'])[1]:
                raise Exception('Bad password')
        except Exception, e:
            send_mail(self.settings['ADMIN_EMAIL_ON_FAILED'], 'Check password failed', 'Check password failed on message from %s. Message subject: %s' % ( message['from'], msg_subject, ))
            self.logger.info('Check password failed on message from %s.' % ( message['from'],))
            return
        
        msg_parts = [(part.get_filename(), part.get_payload(decode=True)) for part in message.walk() if part.get_content_type() == 'text/plain']

        for name, data in msg_parts:
            if not name:
                    self.logger.debug('Message from %s'%(message['from'],))
                    return str(data)
    
    def process_message(self, body, message):
        """ Отработка комманд внутри сообщения """
        
        for line in str(body).split('\n'):
            if line:
                try:
                    m = re.match('^([\w-]+)\(([\w\/,.-]*)',line.strip())
                    
                    if not m:
                        continue
                    
                    cmd, args = m.groups()
                    cmd_class_name = "%s" % (cmd.capitalize(),)
                    
                    if cmd_class_name in self.plugins:
                        send_mail(self.settings['ADMIN_EMAIL'], 'Received command', 'Execute %s with context %s from %s' % (cmd_class_name, args, message['from']))
                        self.logger.info('Execute %s with context %s from %s' % (cmd_class_name, args, message['from']))
                        self.plugins[cmd_class_name].run(args, message['from'])
                    else:
                        send_mail(self.settings['ADMIN_EMAIL_ON_FAILED'], 'Received bad command', 'Try to execute %s from %s. Method not found.' % (line, message['from']))
                        self.logger.info('Warning: method %s not found' % (cmd_class_name, ))
                        
                except Exception, e:
                    send_mail(self.settings['ADMIN_EMAIL_ON_FAILED'], 'Error on executing command', 'Try to execute %s from %s. Error: %s' % (line, message['from'], str(e)))
                    self.logger.error(e)
                                
# ============================================================================

def main():
    """ Загрузчик """
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
            
    mc = MailCommander(sys.argv[1])
    mc.check_mail()

def usage():
    """ Справка """
    print 'Usage: mailcommander.py config_file'

if __name__ == "__main__":
    main()
