from django.db import models

from uberclock.tools import ez_chronos
from uberclock.tools.date import time_to_next_datetime

from django.contrib.auth.models import User
from django.contrib import admin
from django.conf import settings
from django.utils.dateformat import time_format, format
from . import alarm
import struct
import logging
import datetime
import time
import random
import base64
#import simplejson
try:
    import cPickle as pickle
except ImportError:
    import pickle
# Create your models here.

DETECTOR_TYPES = (
 (0, "OpenChronos"),
)

class ChoicesIterator(object):
    def __iter__(self):
        return ((n,n) for n in settings.COMMANDS.iterkeys())

ACTION_CHOICES = ChoicesIterator()


# SESSION_TYPES = (
#  (0, "Normal Sleep"),
#  (1, "Powernap"),
#  (2, "One REM"),
# )

RF_ID_BIT_LENGHT = 3

def get_user_or_default(user=None):
    if user and isinstance(user, User):
        return user
    try:
        return User.objects.get(username=user)
    except User.DoesNotExist:
        try:
            return User.objects.get(username=settings.DEFAULT_USER)
        except User.DoesNotExist:
            try:
                return User.objects.order_by('-id')[0]
            except IndexError:
                return None

class Detector(models.Model):
    """
    Device which messures the sleep state
    """
    name = models.CharField("Name", max_length=100, null=False)
    typ = models.IntegerField("Type", choices=DETECTOR_TYPES)
    ident = models.CharField("Identifier", null=True, max_length=100, unique=True, db_index=True)
    default_user = models.ForeignKey(User, null=True)

    def __repr__(self):
        return '<Detector %s >' %self.ident

class UserProgramManager(models.Manager):
    def get_program_for_user(self, user, id_):
        obj, created = self.get_or_create(user = user, users_id = id_, 
                                          defaults = {
                                            "user":user, "users_id":id_,
                                            "alarm_key":settings.DEFAULT_ALARM
                                          })
        if created:
            obj.save()
        return obj

    def get_users_default(self, user):
        res = self.filter(user=user).order_by("-default", "users_id")
        if not res:
            return None
        return res[0]

class UserProgram(models.Model):
    """
    Maps a alarm program to user and his choosen id

    Object can be used to save settings that are serialsable by simplejson
    """
    user =  models.ForeignKey(User, null=True, db_index=True)
    users_id = models.IntegerField(null=False, db_index=True)
    default = models.BooleanField(default=False)
    alarm_key = models.CharField(null=False, max_length=30, choices=alarm.manager.choices_programs,
                                 help_text="Alarm logic to use")
    rname = models.CharField("name", max_length=30, null=True, blank=True)
    short_name = models.CharField(max_length=5, null=True, blank=True)

    default_wakeup = models.TimeField("Wakeup", null=True, blank=True)
    default_sleep_time = models.IntegerField(null=True, help_text="Minutes of wanted sleep")
    default_window = models.IntegerField(null=True, help_text="Window of Minutes how many minutes before wakeup can be alarmed")

    lights_action = models.CharField("Lights Action", max_length=30, default="lights", choices=ACTION_CHOICES)
    wakeup_action = models.CharField("Wakeup Action", max_length=30, default="wakeup", choices=ACTION_CHOICES)

    settings = models.TextField(default=None, editable=False, null=True)

    objects = UserProgramManager()

    class Meta:
        unique_together = (("user", "users_id"),)

    def _get_name(self):
        if self.rname:
            return self.rname
        return alarm.manager.get_program(self.alarm_key).name

    def _set_name(self, val):
        self.rname = val

    name = property(_get_name, _set_name)

    def get_var(self, name, *args):
        if not hasattr(self, "_settings"):
            if self.settings:
                try:
                    #self._settings = simplejson.loads(self.settings)
                    self._settings = pickle.loads(base64.b64decode(self.settings))
                except Exception, e:
                    logging.warning("could not unpickle settings: %s" %e)
                    print self.settings
                    self._settings = {}
            else:
                self._settings = {}

        if name and len(args):
            return self._settings.get(name, args[0])
        elif name:
            return self._settings.get(name)

        if not self.settings or not isinstance(self.settings, dict):
            self.settings = {}

    def set_var(self, name, value):
        if not hasattr(self, "_settings"):
            self.get_var(None)
        self._settings[name] = value

    def del_var(self, name):
        if not hasattr(self, "_settings"):
            self.get_var(None)
        del self._settings[name]


    def save(self, *args, **kwargs):
        if hasattr(self, "_settings"):
            #self.settings = simplejson.dumps(self._settings, ensure_ascii=False)
            self.settings = base64.b64encode(pickle.dumps(self._settings))
        return super(UserProgram, self).save(*args, **kwargs)

    @property
    def program_class(self):
        return alarm.manager.get_program(self.alarm_key)

    def set_program(self, program):
        if program:
            self.alarm_key = program.key
        else:
            self.alarm_key = None

    def get_program(self, session):
        if hasattr(self, "_program") and self._program.key == self.alarm_key:
            return self._program
        self._program = self.program_class(alarm.manager, session)
        return self._program

    def __unicode__(self):
        return u"%s (%s) of %s" %(self.name, self.users_id, self.user)

class WakeupTime(models.Model):
    """
    User saved wakeup times for shortcuts
    """
    name = models.CharField("Name", max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, null=False)
    # fixme choices etc
    weekday = models.IntegerField("Weekday", null=True) 
    session_typ = models.IntegerField("Type", default=0, choices=alarm.manager.choices_programs)
    wakeup = models.TimeField("Wakeup", null=False)


class SessionManager(models.Manager):
    def get_active_session(self, rf_id):
        now = datetime.datetime.now()
        start = now - datetime.timedelta(seconds=settings.CLOCK_SESSION_TIMEOUT)
        return self.get(stop__gt=start, closed=False, rf_id=rf_id)

    def get_active_sessions(self, **kwargs):
        now = datetime.datetime.now()
        start = now - datetime.timedelta(seconds=settings.CLOCK_SESSION_TIMEOUT)
        return self.filter(stop__gt=start, closed=False, **kwargs)

    def get_new_rf_id(self):
        id_s = range(1, (2**(RF_ID_BIT_LENGHT+1)))
        now = datetime.datetime.now()
        start = now - datetime.timedelta(seconds=settings.CLOCK_SESSION_TIMEOUT)
        actives = self.filter(stop__gt=start).values_list("rf_id", flat=True)
        # return a "random" id
        random.shuffle(id_s)
        for x in id_s:
            if x not in actives:
                return x

    def get_new_session(self, user):
        """
        Return a new Session for the user. If the user created a new session it
        will be returned
        """
        rv = self.filter(user=user, new=True).order_by("id")
        if len(rv):
            rv = rv[0]
            # set the new_ flag to False so it will not be returned again
            rv.new_ = False
            rv.save()
            return rv
        else:
            # create a new session
            pass

    def cleanup_sessions(self):
        """
        Clean up session garbage
        """
        self.delete_empty_sessions()

    def delete_empty_sessions(self):
        # delete empty sessions older then one day
        datelimit = datetime.datetime.now() - datetime.timedelta(days=1)
        for session in Session.objects.annotate(entry_count=models.Count('entry')).filter(entry_count=0, stop__lt=datelimit):
            logging.info("delete %s" %session)
            session.learndata.delete()
            session.delete()


class Session(models.Model):
    """
    One Sleep Session
    """
    start = models.DateTimeField("Start", null=False, auto_now_add=True, editable=False)
    stop = models.DateTimeField("Stop", null=False, auto_now_add=True, editable=False)
    user = models.ForeignKey(User, null=True)
    detector = models.ForeignKey(Detector, null=True, blank=True)
    program = models.ForeignKey(UserProgram, null=True)
    wakeup = models.DateTimeField("Wakeup", null=True, blank=True)
    #FIXME messure real slept length
    sleep_time = models.IntegerField(null=True, help_text="Minutes of wanted sleep", blank=True)
    window = models.IntegerField(null=True, help_text="Window of Minutes how many minutes before wakeup can be alarmed")
    rating = models.IntegerField("Rating", null=True, blank=True)
    deleted = models.BooleanField("Deleted", default=False)
    rf_id = models.IntegerField("RF Id", null=True)
    closed = models.BooleanField("Session has ended", default=False)
    new = models.BooleanField("Session has not yet run", default=False)

    lights_action = models.CharField("Lights Action", max_length=30, default="lights", choices=ACTION_CHOICES)
    wakeup_action = models.CharField("Wakeup Action", max_length=30, default="wakeup", choices=ACTION_CHOICES)

    objects = SessionManager()


    def __init__(self, *args, **kwargs):
        # copy default values from program
        if "program" in kwargs:
            prog = kwargs["program"]
            if not "wakeup" in kwargs and prog.default_wakeup:
                kwargs["wakeup"] = time_to_next_datetime(prog.default_wakeup)
            if not "sleep_time" in kwargs and prog.default_sleep_time:
                kwargs["sleep_time"] = prog.default_sleep_time
            if not "window" in kwargs and prog.default_window:
                kwargs["window"] = prog.default_window
            if not "lights_action" in kwargs and prog.lights_action:
                kwargs["lights_action"] = prog.lights_action
            if not "wakeup_action" in kwargs and prog.wakeup_action:
                kwargs["wakeup_action"] = prog.wakeup_action
        if not "wakeup" in kwargs and "sleep_time" in kwargs:
            kwargs["wakeup"] = datetime.datetime.now() + datetime.timedelta(minutes=kwargs["sleep_time"])
        return super(Session, self).__init__(*args, **kwargs)


    def action_in_window(self, action, dt=None): 
        """
        Checks if a action is allowed to run
        """
        if self.closed:
            return False
        if self.wakeup:
            if not dt:
                dt = datetime.datetime.now()
            if dt > self.wakeup:
                return True
            elif self.window:
                if action == alarm.ACTIONS.LIGHTS:
                    # lights get an aditional larger timedelta
                    if dt >= self.wakeup - datetime.timedelta(minutes=self.window+15):
                        return True
                else:
                    if dt >= self.wakeup - datetime.timedelta(minutes=self.window):
                        return True
                return False


    def get_param(self, name):
        """
        Returns paramenter of the Sessions alarm
        """
        # get the value of the program first
        if name in ["wakeup", "sleep_time", "window"]:
            if getattr(self, name):
                return getattr(self, name)
        # lookup default values of the program
        if self.program:
            return self.program.get_var(name)


    def save(self, *args, **kwargs):
        super(Session, self).save(*args, **kwargs)
        self.learndata

    @property
    def get_user(self):
        if self.user:
            return self.user
        if self.detector and self.detector.default_user:
            # we set self.user here, so changes to a detector will not change 
            # old sessions
            self.user = self.detector.default_user
            return self.user
        # fallback to default user
        self.user = get_user_or_default()
        return self.user

    @property
    def learndata(self):
        if not self.id:
            raise ValueError, "Session Object not saved"
        try:
            return self.learndata_set.all()[0]
        except IndexError, e:
            rv = LearnData(session=self)
            rv.save()
            return rv

    @property
    def week(self):
        return self.start.isocalendar()[1]

    def __repr__(self):
        return "<Session %s %s-%s>" %(self.user, self.start, self.stop)

    def __unicode__(self):
        length = self.length
        entries = self.entry_set.all().count()
        return u"Session from %s %s (%s:%0.2d) (%s Entries)" %(self.user, format(self.start, settings.DATETIME_FORMAT), length[0], length[1], entries)

    def merge(self, source):
        # FIXME: add a zero datapoint if the time between entries is to long
        source.entry_set.all().update(session=self)
        source.learndata_set.all().delete()

        def cifn(key):
            var = getattr(source, key)
            if var and not getattr(self, key):
                setattr(self, key, var)
        # copy usefull variables
        for key in ["user", "wakeup", "rating"]:
            cifn(key)

        if self.entry_set.all().count():
            self.start = self.entry_set.all().order_by('date')[0].date
            self.stop = self.entry_set.all().order_by('-date')[0].date

        self.save()
        source.delete()



    @property
    def length(self):
        if self.start > self.stop:
            return (0, 0, 0)
        s = (self.stop - self.start).seconds
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        return (hours, minutes, seconds)

    def log(self, typ, msg):
        if isinstance(typ, basestring):
            for ti, ta in LOG_TYPES:
                if typ.lower() == ta.lower():
                    typ = ti
                    break
            else:
                typ = LOG_INFO
        entry = LogEntry(session=self, typ=typ, msg=msg)
        entry.save()

LOG_TYPES = (
    ( 0, u"Unknown"),
    ( 1, u"Wakeup"),
    ( 2, u"Lights"),
    ( 3, u"Info"),
    ( 4, u"Warning"),
    ( 5, u"Debug"),
    ( 6, u"Error"),
)

LOG_UNKNOWN = 0
LOG_WAKEUP = 1
LOG_LIGHTS = 2
LOG_INFO = 3
LOG_WARNING = 4
LOG_DEBUG = 5
LOG_ERROR = 6

class LogEntry(models.Model):
    session = models.ForeignKey(Session, db_index=True, related_name="logs")
    date = models.DateTimeField("Date", null=False, auto_now_add=True)
    typ = models.IntegerField("Type", choices=LOG_TYPES)
    msg = models.CharField("msg", max_length=200, blank=True, null=True)

    def __unicode__(self):
        return u"%s %s:%s" %(self.date, self.get_typ_display(), self.msg or "")

    def stdout(self):
        lvl = logging.INFO
        if self.typ == 3:
            lvl = logging.DEBUG
        elif self.typ == 4:
            lvl = logging.ERROR
        logging.log(lvl, u"%s:%s" %(self.get_typ_display(), self.msg))

    class Meta:
        ordering = ("-date",)


class Entry(models.Model):
    date = models.DateTimeField("Date", null=False, auto_now_add=True)
    value = models.IntegerField(max_length=10, null=False)
    counter = models.IntegerField(max_length=3, null=True)
    session = models.ForeignKey(Session, null=True, db_index=True)

    def save(self, *args, **kwargs):
        super(Entry, self).save(*args, **kwargs)
        # update the session new flag to false if any entry is saved to it.
        # it is used then
        if self.session and self.session.new:
            self.session = False
            self.session.save()

    def __repr__(self):
        return "<Entry %s %d>" %(self.date, self.value)

    def __unicode__(self):
        return u"Entry at %s: %s" %(format(self.date, settings.DATETIME_FORMAT), self.value)

    class Meta:
        ordering = ('date',)


class LearnData(models.Model):
    """
    One Sleep Session
    """
    session = models.ForeignKey(Session, null=False)
    lights = models.ForeignKey(Entry, related_name="learn_lights", 
                                help_text="Where the lights should start dimming", null=True)
    wake = models.ForeignKey(Entry, related_name="learn_wake",
                                help_text="Perfect wakeup point", null=True)
    start = models.ForeignKey(Entry, related_name="learn_start",
                                help_text="When sleeping began", null=True)
    stop = models.ForeignKey(Entry, related_name="learn_stop",
                                help_text="When sleep stopped", null=True)
    learned = models.BooleanField(default=False)

    @property
    def placed(self):
        if any([self.lights, self.wake, self.start, self.stop]):
            return True
        return False


def cleanup_db():
    # cleanup sessions
    Session.objects.cleanup_sessions()



SIMPLICITI_PHASE_CLOCK_START_RESPONSE = 0x54

logging.log_level = logging.DEBUG

RF_ID_MASK = 7<<5
COUNTER_MASK = 31

class DBWriter(ez_chronos.CommandDispatcher):

    def __init__(self, *args, **kwargs):
        self.clock = kwargs.pop("clock", None)
        super(DBWriter, self).__init__(*args, **kwargs)
        self.last_msg = {}
        self.session = {}
        self.syncrun = 0

    def smpl_0x01(self, data):
        # acceleration data
        data = self.get_smpl_data(data)
        print "x: %3d y: %3d z: %3d" %(ord(data[0]), ord(data[1]), ord(data[2]))

    # ppt buttons
    #UP
    def smpl_0x32(self, data):
        # a
        print "UP pressed"
    #STAR
    def smpl_0x12(self, data):
        # acceleration data
        print "STAR pressed"
    #SHARP
    def smpl_0x22(self, data):
        # acceleration data
        print "SHARP pressed"

    #phase clock
    def smpl_0x03(self, data):
        """
        Receive sleep data
        """
        # acceleration data
        timeout=datetime.timedelta(seconds=settings.CLOCK_SESSION_TIMEOUT)
        now = datetime.datetime.now()
        #FIXME: detect device
        device = 1
        
        self.last_msg[device] = now
        mdata = self.get_smpl_data(data)
        var = struct.unpack('H', mdata[:2])[0]
        counter = ord(mdata[2])&COUNTER_MASK
        rf_id = (ord(mdata[2])&RF_ID_MASK)>>5

        try:
            session = Session.objects.get_active_session(rf_id)
            if not self.clock.has_session(session):
                self.clock.add(session.program.get_program(session))
        except Session.DoesNotExist:
            logging.warning("Session id %s sent which is not active. Creating a new Session" %rf_id)
            user=get_user_or_default(None)
            program=UserProgram.objects.get_users_default(user)
            session = Session(start=now, stop=now, rf_id=rf_id, 
                              user=user, program=program)
            session.save()
            self.clock.add(program.get_program(session))


        logging.debug("%s S:%2d C:%2d %6d %s" %(session.id, rf_id, counter, var, "#"*max(min((var/500), 80),1)))
        entry = Entry(value=var, counter=counter, session=session)
        session.stop = now
        session.save()
        
        entry.save()

    def smpl_0x04(self, data):
        """
        Start new session
        """
        mdata = self.get_smpl_data(data)
        ident = "0x%02x%02x" %(ord(mdata[0]), ord(mdata[1]))
        device, created = Detector.objects.get_or_create(ident=ident, 
                                                            defaults={"name": "eZ430 OpenChronos",
                                                                      "ident": ident,
                                                                      "typ": DETECTOR_TYPES[0][0],
                                                                      "user": get_user_or_default(None),
                                                                      })
        if created:
            device.save()

        logging.info("New Session Request from: %s" %(device.ident))

        sessions = Session.objects.get_active_sessions(detector=device)

        now = datetime.datetime.now()
        delta = datetime.timedelta(seconds=10)
        active_session = None
        for session in sessions:
            if session.start > now-delta:
                # we have an active session running
                active_session = session

        # find program
        program_id = ord(mdata[2])
        user = get_user_or_default(device.default_user)
        program = UserProgram.objects.get_program_for_user(user, program_id)

        if not active_session:
            rf_id = Session.objects.get_new_rf_id()

            active_session = Session(start=now, stop=now, detector=device,
                                     rf_id=rf_id, 
                                     user=user,
                                     program=program)
            active_session.save()


        logging.info("Send Session ID: %s (user:%s program:%s)" %(active_session.rf_id, active_session.user, active_session.program))

        data = [SIMPLICITI_PHASE_CLOCK_START_RESPONSE, active_session.rf_id]
        self.send_smpl_data(data)
        # we shall not do anything until the clock reads out the 
        # session data
        for x in xrange(10):
            self.send_smpl_data(data, wait=False)
            time.sleep(0.050)

    def smpl_0x05(self, data):
        """
        Receive sleep end packet
        """
        timeout=datetime.timedelta(seconds=settings.CLOCK_SESSION_TIMEOUT)
        #FIXME: detect device
        device = 1

        mdata = self.get_smpl_data(data)
        var = struct.unpack('H', mdata[:2])[0]
        counter = ord(mdata[2])&COUNTER_MASK
        rf_id = (ord(mdata[2])&RF_ID_MASK)>>5

        try:
            session = Session.objects.get_active_session(rf_id)
            session.closed = True
            session.save()
            logging.warning("Session id %s closed" %rf_id)
        except Session.DoesNotExist:
            pass


    def smpl_0x10(self, data):
        """
        Start sync mode
        """
        logging.debug("start sync mode")
        # taken from http://pastebin.com/f62344dbd
        # empty buffer
        self.read_sync_data()
        # read old data
        for x in xrange(100):
            self.send_smpl_data([ez_chronos.SYNC_AP_CMD_GET_STATUS], wait=False)
            time.sleep(0.020)
            if self.get_sync_buffer_status():
                rcv = self.read_sync_data()
                cdata = self.parse_sync_data(rcv)
                if cdata:
                    break
        else:
            print "no data for next step"
            return

        for x in xrange(10):
            # send burst of up to date data
            ctime = datetime.datetime.now()
            #{'alarm_hour': 6, 'hour': 4, 'tempCelcius': 272, 'metric': 1, 'month': 8, 'second': 56, 'year': 2009, 'alarm_minute': 30, 'altMeters': 485, 'day': 1, 'minute': 50}
            if not cdata:
                return
            cdata['hour'] = ctime.hour
            cdata['minute'] = ctime.minute
            cdata['second'] = ctime.second
            cdata['day'] = ctime.day
            cdata['month'] = ctime.month
            cdata['year'] = ctime.year
            if settings.CLOCK_ALTITUDE is not None:
                cdata['alt_meters'] = settings.CLOCK_ALTITUDE

            self.send_smpl_data(self.build_sync_data(cdata))
            time.sleep(0.100)

        self.send_smpl_data([ez_chronos.SYNC_AP_CMD_EXIT])
