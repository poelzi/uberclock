from django.core.management.base import BaseCommand, CommandError
from uberclock.db.models import DBWriter
from django.conf import settings
import sys, thread

import serial


import wsgiserver
#This can be from cherrypy import wsgiserver if you're not running it standalone.
import os, time
import django.core.handlers.wsgi
import logging

#if __name__ == "__main__":
#    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

class Command(BaseCommand):
    args = ''
    help = 'Runs a background daemon'

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG)
        thread.start_new_thread(self.start_webserver, ())

        if settings.CLOCK_HARDWARE.lower() == "ezchronos":
            self.ez_chronos(*args, **options)
    
    def ez_chronos(self, *args, **options):
        while True:
            try:
                ser = serial.Serial(settings.EZ_SERIAL, 115200,timeout=1)
            except serial.serialutil.SerialException:
                logging.error("Can't open console %s" %settings.EZ_SERIAL)
                time.sleep(5)
                continue

            pv = DBWriter(ser)
            pv.debug = 1
            pv.reset()
            pv.start_ap()
            try:
                logging.info("OpenChronos interface started on %s" %settings.EZ_SERIAL)
                pv.loop_smpl_get()
            except KeyboardInterrupt:
                pv.reset()
                ser.close()
                sys.exit(0)
            except Exception, e:
                logging.exception(e)
                # try to cleanup, which may fail
                try: pv.reset()
                except: pass
                try: pv.close()
                except: pass

    def start_webserver(self):
        server = wsgiserver.CherryPyWSGIServer(
            (settings.SERVER_LISTEN, settings.SERVER_PORT),
            django.core.handlers.wsgi.WSGIHandler(),
            server_name='localhost',
            numthreads = 20,
        )
        logging.info("start webserver. listen at %s:%s" %(settings.SERVER_LISTEN, settings.SERVER_PORT))
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()

