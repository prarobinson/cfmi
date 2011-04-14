#!python

from subprocess import call
from multiprocessing import Process, current_process, Pool, Event
from email.mime.text import MIMEText
from tempfile import mkstemp

import daemon
import signal
import pickle
import smtplib
import os
import sys
import time

from jinja2 import Template, FileSystemLoader, Environment
import zmq

from settings import (BASE_PATH, ARCHIVE_PROCESSES, DICOM_ARCHIVE_FOLDER,
                      EMAIL_FROM, EMAIL_REPLY_TO, ARCHIVE_DOWNLOAD_URL,
                      TEMPLATE_PATHS, TMP_PATH)

JINJA_ENV = Environment(loader=FileSystemLoader(TEMPLATE_PATHS))
EMAIL_TEMPLATE = JINJA_ENV.get_template('email.tpl')
SCRIPT_PATH = BASE_PATH+'/scripts/'

def notify(email, subject, exten):
    url = ARCHIVE_DOWNLOAD_URL+".".join([subject, exten])
    msg = MIMEText(EMAIL_TEMPLATE.render(subject=subject,
                                         url=url, exten=exten))
    msg['Subject'] = "{}: Archive Download ready".format(subject)
    msg['From'] = EMAIL_FROM
    msg['Reply-to'] = EMAIL_REPLY_TO
    msg['To'] = email
    s = smtplib.SMTP()
    s.connect('localhost')
    s.sendmail(EMAIL_FROM, [email], msg.as_string())
    s.quit()

def builder(message):
    email, subject, exten = pickle.loads(message)
    call([SCRIPT_PATH+"compress.sh", subject, exten, 
          DICOM_ARCHIVE_FOLDER])
    notify(email, subject, exten)
    return

def mainloop():
    with open(BASE_PATH+'/dataserver.pid', 'w') as pidfile:
        pidfile.write("{0}".format(os.getpid()))

    pool = Pool(processes=ARCHIVE_PROCESSES)
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://127.0.0.1:5555")

    while not quitflag.is_set():
        # Wait for next request from client
        try:
            message = socket.recv(zmq.NOBLOCK)
        except zmq.ZMQError:
            time.sleep(1)
            continue
        email, subject, exten = pickle.loads(message)
        pool.apply_async(builder, args=[message])
        socket.send(pickle.dumps(True))
    pool.terminate()

def cleanup(a, b):
    quitflag.set()
    os.remove('dataserver.pid')

quitflag = Event()

if __name__ == '__main__':
    context = daemon.DaemonContext(
        working_directory=BASE_PATH,
        umask=0o002,
        )
    context.signal_map = {signal.SIGTERM: cleanup}

    with context:
        mainloop()
