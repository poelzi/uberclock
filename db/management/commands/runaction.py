from django.core.management.base import BaseCommand, CommandError
from uberclock.db import alarm
from django.conf import settings
from optparse import make_option
import logging
import sys

class Command(BaseCommand):
    args = '<name>'
    help = 'Runs a action configured in settings COMMANDS'

    def handle(self, *args, **options):
        if not len(args):
            self.print_help(sys.argv[0], "run_action")
            return
        print args, options
        action_name = args[0]
        print "Execute: %s" %action_name
        inst = alarm.create_action(action_name)
        inst.execute()
        print "Done"
