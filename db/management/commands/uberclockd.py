from django.core.management.base import BaseCommand, CommandError

from uberclock.db.models import DBWriter
from uberclock.db.alarm import Clock

from django.conf import settings
import sys, thread
from optparse import make_option

import serial


import wsgiserver
#This can be from cherrypy import wsgiserver if you're not running it standalone.
import os, time
import django.core.handlers.wsgi
import logging

class Command(BaseCommand):
    args = ''
    help = 'Runs the UberClock background daemon'
    option_list = BaseCommand.option_list + (
        make_option('--msp-ap',
            dest='msp_ap',
            default=None,
            help='EZ430 Accesspoint Path'),
        )

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG)

        # main clock instance
        self.clock = Clock()

        thread.start_new_thread(self.start_webserver, ())
        thread.start_new_thread(self.start_clock, ())

        if settings.CLOCK_HARDWARE.lower() == "ezchronos":
            self.msp_ap = options['msp_ap'] or settings.EZ_SERIAL
            self.ez_chronos(*args, **options)

    def start_clock(self, *args, **options):
        self.clock.run()

    def ez_chronos(self, *args, **options):
        while True:
            try:
                ser = serial.Serial(self.msp_ap, 115200,timeout=1)
            except serial.serialutil.SerialException:
                logging.error("Can't open console %s" %self.msp_ap)
                time.sleep(5)
                continue

            pv = DBWriter(ser, clock=self.clock)
            pv.debug = 0
            pv.reset()
            pv.start_ap()
            try:
                logging.info("OpenChronos interface started on %s" %self.msp_ap)
                pv.loop_smpl_get()
            except KeyboardInterrupt:
                pv.close()
                ser.close()
                sys.exit(0)
            except Exception, e:
                logging.exception(e)
                # try to cleanup, which may fail
                try: pv.reset()
                except: pass
                try: pv.close()
                except: pass
                try:
                    ser.close()
                    del ser
                except: pass

    def start_webserver(self):
        from django.core.servers.basehttp import AdminMediaHandler
        server = wsgiserver.CherryPyWSGIServer(
            (settings.SERVER_LISTEN, settings.SERVER_PORT),
            AdminMediaHandler(django.core.handlers.wsgi.WSGIHandler(), ""),
            server_name='localhost',
            numthreads = 20,
        )
        logging.info("start webserver. listen at %s:%s" %(settings.SERVER_LISTEN, settings.SERVER_PORT))
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()

