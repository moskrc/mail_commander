Написание плагинов
=============================================================================

Плагин представляет из себя класс наследуемый от BasePlugin с одним 
обязательным методом run (self, context, sender). Переменная context 
будет содержит контекст команды (текст внутри ее скобок), sender - email 
отправителя. Имя класса должно совпадать с именем комманды, но первая буква
должна быть прописаной.

В одном py файле может быть несколько плагинов. См. пример stat_and_freespace.py.
Для структуририрования больших плагинов желательно размещать каждый в отдельном
файле. Имя файла значения не имеет. Важно только название класса. 

Для отправки писем из плагинов предназначен метод send_mail из 
пакета mailer. Аргументы toaddrs, subject, body, fromaddr='noreply@localhost'.  

Также в каждом плагине изначально содержатся два атрибута из основной системы:
self.settings - конфигурационный файл
self.logger - логер

Через них можно прочитать ключи из конф. файла и воспользоваться общим логером. 


Передача на сервер писем с паролем
=============================================================================

1. На стороне сервера выполняем единожды комманду для генерирования зерна 
$ python gen_seed.py > seed

2. В конф. файле указываем авторизацию по паролю и путь к файлу с зерном. В 
секции main присваиваем ключу auth_method значение password. И ключу 
seed_file пусть к зерну.

3. Копируем файл seed в директорию указанную в конфиг файле

4. Раздаем каждому пользователю системы seed файл и программу genkey.py

5. Для получения пароля пользователь должен запустить программу genkey.py в
каталоге где лежит переданное ему зерно seed. Вывод будет примерно таким:
До 15 часа(ов) пароль: a1eaa02542f4e299f24e34e4d7ea7651

6. Пользователь отсылает на сервер письмо с темой mailcom и через решетку 
полученный пароль. Т.е. например: mailcom # a1eaa02542f4e299f24e34e4d7ea7651


Передача на сервер шифрованных и подписанных писем
=============================================================================

1. Создаем сертификат авторити для создания сертификатов:
$ openssl req -newkey rsa:1024 -nodes -x509 -days 365 -out ca_signer.pem -keyout ca_signer.key

2. Создаем запрос на сертификат для отправителя (обязательные поля: CN и email. Делается для каждого клиента системы):
$ openssl req -newkey rsa:1024 -nodes -out signer.csr -keyout signer.key

3. Создаем сертификат отправителя подписанный авторити созданным ранее (Делается для каждого клиента системы):
$ openssl x509 -req -CAkey ca_signer.key -CA ca_signer.pem -in signer.csr -out signer.pem -days 365 -set_serial 1

4. Повторяем пункты 2,3 для получателя, т.е. сервера:
$ openssl req -newkey rsa:1024 -nodes -out recipient.csr -keyout recipient.key
$ openssl x509 -req -CAkey ca_signer.key -CA ca_signer.pem -in recipient.csr -out recipient.pem -days 365 -set_serial 2
Серийный номер нужно постоянно увеличивать, чтобы он всегда был разным.

5. Делаем для каждого клиента системы файл pk12 (для импортирования в почтовые программы).
$ cat signer.pem signer.key > signer_all.pem
$ openssl pkcs12 -export -in signer_all.pem -out signer.p12

Настраиваем Mozilla Thunderbird на отправку шифрованных и подписанных писем
-----------------------------------------------------------------------------

Edit->Preferences->Advanced->Certificates->View Certificates.

Добавляем свой сертификат и сертификат авторити.
Во вкладке Your certificates, Import. Выбираем signer.p12.
Во вкладке Authorities, Import. Выбираем signer_ca.pem

Добавляем сертификат получателя (сервера):
Во вкладке Other People's, Import. Выбираем recipient.pem.

Пишем письмо, вверху жмем на выпадающий список в "желтом замке". 
Выбираем галочки: Encrypt This Message и Sign This Message. 
Теперь если нажать просто на "желтом замке" должен появиться 
диалог в котором будет сообщено что Digitaly signed: Yes, Encrypted: Yes и 
сертификат получателя - Valid. Для выхода из диалога - кнопка ок. Если все так, жмем отправить письмо.

На стороне получателя письма (на сервере) для его прочтения должны быть:
1. Сертификат авторити которым подписан ваш и его сертификат.
2. Ваш сертификат и приватный ключ.
3. Его сертификат.

Эти 4 файла должны лежать в директории certificates_dir.
* ca_signer.pem - certificate authority
* signer.pem - сертификат отправителя (в папке {certificates_dir}/users/), см. конфиг.
* recipient.key - приватный ключ
* recipient.pem - сертификат

А у каждого клиента системы должны быть:
* signer.p12 - сертификат p12
* ca_signer.pem - сертификат авторити 
* recipient.pem - сертификат сервера


Настройка сервера
-----------------------------------------------------------------------------
В конфиг файле, в секции main ставим auth_method
auth_method: smime

В секцию certificates добавляем записи с указанием пути к сертификатам клиентов
вида email:путь к фалу: 
puh@localhost: users/puh_localhost.pem
asu@localhost: users/asu_localhost.pem


Конфигурационный файл
=============================================================================

Представляет из себя INI подобный файл. Структура:

[main] - основные настройки

Куда вести логи
log_file: /home/asu/projects/mailcommander/src/mailcommander.log

Путь к зерну при парольной авторизации
seed_file: /home/asu/projects/mailcommander/src/seed

Директория с плагинами
plugins_dir: /home/asu/projects/mailcommander/src/plugins/

Директория с сертификатами для авторизации по ключам
certificates_dir: /home/asu/projects/mailcommander/src/certificates/

Отладочный вывод
debug: True

Отвечать на письма с темой
response_on_subject: mailcom

Название логера
logger: mailcommander

Тип авторизации
auth_method: smime или password

[pop3_server] - почтовый сервер

Хост
server: localhost

Пользователь
user: asu

Пароль
password: 123

Подключение через SSL
ssl: False

[emails] - электронные адреса

Администратор
admin_email: puh@localhost

Администратор для приема ошибок
admin_email_on_failed: puh@localhost

[certificates] - сертификаты

Сертификаты отправителей - клиентов для авторизации по ключу.
puh@localhost: users/puh_localhost.pem
asu@localhost: users/asu_localhost.pem