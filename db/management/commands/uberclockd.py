from django.core.management.base import BaseCommand, CommandError
from uberclock.db.models import DBWriter
from django.conf import settings
import sys

import serial

class Command(BaseCommand):
    args = ''
    help = 'Runs a background daemon'

    def handle(self, *args, **options):
        if settings.CLOCK_HARDWARE.lower() == "ezchronos":
            self.ez_chronos(*args, **options)
    
    def ez_chronos(self, *args, **options):
        ser = serial.Serial(settings.EZ_SERIAL, 115200,timeout=1)

        pv = DBWriter(ser)
        pv.debug = 1
        pv.reset()
        pv.start_ap()
        try:
            pv.loop_smpl_get()
        except KeyboardInterrupt:
            pv.reset()
            ser.close()
            sys.exit(0)

