from django.core.management.base import BaseCommand, CommandError
from django.core.management import execute_manager, ManagementUtility
from django.conf import settings

def install_db():
    utility = ManagementUtility(['manage.py', 'syncdb', '--noinput'])
    utility.execute()
    utility = ManagementUtility(['manage.py', 'loaddata', 'db/fixtures/default_user.json'])
    utility.execute()


class Command(BaseCommand):
    args = ''
    help = 'Install uberclock database'

    def handle(self, *args, **options):
        install_db()