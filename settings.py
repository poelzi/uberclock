# Django settings for uberclock project.

import os, os.path

CONFIG_PATH = os.path.expanduser("~/.config/uberclock")

if not os.path.exists(CONFIG_PATH):
    os.mkdir(CONFIG_PATH)

DEVELOPMENT_MODE = False
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(CONFIG_PATH, "db.sqlite"),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None
if os.path.exists("/etc/timezone"):
    try:
        TIME_ZONE = open("/etc/timezone","r").read().strip()
    except IOError:
        pass

if not TIME_ZONE:
    TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '9y1#-)6*b#my9hr8ktaq^iodt82-1)h_%sj-sgeuc_e6u2y=k)'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'piston.middleware.ConditionalMiddlewareCompatProxy',
    'piston.middleware.CommonMiddlewareCompatProxy',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'uberclock.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.markup',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'uberclock.db',
    'uberclock.webclock',
    'piston',
    'uberclock.api',
)


STATIC_DOC_ROOT = os.path.join(os.path.dirname(__file__), "static")

CLOCK_HARDWARE = "ezchronos"

EZ_SERIAL = "/dev/ttyACM0"

SERVER_LISTEN = '0.0.0.0'
SERVER_PORT = 8000

DEFAULT_USER = 'user'
DEFAULT_ALARM = 'basic'

CLOCK_SESSION_TIMEOUT = 60*30

PISTON_STREAM_OUTPUT = True

# hight in meters above normal hight
CLOCK_ALTITUDE = None

# 5 minutes snooze time
DEFAULT_SNOOZE_TIME = 5 * 60

CHUMBY_URLS = {
  'default' : '<embed width="800" height="480" quality="high" bgcolor="#FFFFFF" wmode="transparent" name="virtualchumby" type="application/x-shockwave-flash" src="http://www.chumby.com/virtualchumby_noskin.swf" FlashVars="_chumby_profile_url=http%3A%2F%2Fwww.chumby.com%2Fxml%2Fvirtualprofiles%2FE8E34C1E-726B-11DF-BA50-001B24F07EF4&amp;baseURL=http%3A%2F%2Fwww.chumby.com" pluginspage="http://www.macromedia.com/go/getflashplayer"></embed>'
}

# execute | mdp

MPD_HOST = ('localhost', 6600)
MPD_VOLUME = 90

MPD_COMMANDS = (
    ('clear',),
    ('add', 'alarm1.mp3'),
)

# mybe put it into a ini file ?
COMMANDS = {
    "wakeup":  {"type": "mpd", 
                "host": "localhost",
                "port": 6600,
                "commands": MPD_COMMANDS
               },
    "lights":  {"type": "execute", 
                 "commands": (("echo", "test"),),
               },
    "test":    {"type": "execute", 
                "commands": (("echo", "test"),),
               },
}

# load user config file
if os.path.exists(os.path.join(CONFIG_PATH, "settings.py")):
    execfile(os.path.join(CONFIG_PATH, "settings.py"), globals())

# load current dir config file
try:
    from settings_local import *
except ImportError:
    import sys
    sys.stderr.write('Unable to read settings_local.py\n')

if DEVELOPMENT_MODE:
    DATABASE_ENGINE = DATABASES['default']['ENGINE'].split('.')[-1]
    INSTALLED_APPS += ('django_evolution',)

try:
    INSTALLED_APPS += ADDITIONAL_APPS
except NameError:
    pass

#PISTON_DISPLAY_ERRORS = DEBUG