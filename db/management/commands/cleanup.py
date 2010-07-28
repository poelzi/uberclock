from django.core.management.base import BaseCommand, CommandError
from uberclock.db.models import cleanup_db
from django.conf import settings
from optparse import make_option
import logging

class Command(BaseCommand):
    args = ''
    help = 'Cleanup the database'

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG)
        logging.info("cleanup database")
        cleanup_db()
        logging.info("done")