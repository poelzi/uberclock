from django.db import models
from uberclock.tools import ez_chronos
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
# Create your models here.

DETECTOR_TYPES = (
 (0, "OpenChronos"),
)

# SESSION_TYPES = (
#  (0, "Normal Sleep"),
#  (1, "Powernap"),
#  (2, "One REM"),
# )

RF_ID_BIT_LENGHT = 3

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

class Session(models.Model):
    """
    One Sleep Session
    """
    start = models.DateTimeField("Start", null=False, auto_now_add=True, editable=False)
    stop = models.DateTimeField("Stop", null=False, auto_now_add=True, editable=False)
    user = models.ForeignKey(User, null=True)
    detector = models.ForeignKey(Detector, null=True)
    program = models.IntegerField("Program", default=0, choices=alarm.manager.choices_programs)
    wakeup = models.DateTimeField("Wakeup", null=True)
    rating = models.IntegerField("Rating", null=True)
    deleted = models.BooleanField("Deleted", default=False)
    rf_id = models.IntegerField("RF Id", null=True)
    closed = models.BooleanField("Session has ended", default=False)
    new = models.BooleanField("Session has not yet run", default=False)

    objects = SessionManager()
    # Do we need this ?
    #alone = models.BooleanField("Alone", null=True, default=True, help_text="Sleeping with someone else in the bed")

    def save(self, *args, **kwargs):
        super(Session, self).save(*args, **kwargs)
        self.learndata

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
        # FIXME: add a zero datapoint maybe if the time 
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
        s = (self.stop - self.start).seconds
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        return (hours, minutes, seconds)


class Entry(models.Model):
    date = models.DateTimeField("Date", null=False, auto_now_add=True)
    value = models.IntegerField(max_length=10, null=False)
    counter = models.IntegerField(max_length=3, null=True)
    session = models.ForeignKey(Session, null=True, db_index=True)

    def __repr__(self):
        return "<Entry %s %d>" %(self.date, self.value)

    def __unicode__(self):
        return u"Entry at %s: %s" %(self.date, time_format(self.date, settings.TIME_FORMAT))


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


SIMPLICITI_PHASE_CLOCK_START_RESPONSE = 0x54

logging.log_level = logging.DEBUG

RF_ID_MASK = 7<<5
COUNTER_MASK = 31

class DBWriter(ez_chronos.CommandDispatcher):

    def __init__(self, *args, **kwargs):
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
        except Session.DoesNotExist:
            logging.warning("Session id sent which is not active. Creating a new Session")
            session = Session(start=now, stop=now, rf_id=rf_id)
            session.save()

        logging.debug("%s S:%2d C:%2d %6d %s" %(session.id, rf_id, counter, var, "#"*max(min((var/500), 80),1)))
        entry = Entry(value=var, counter=counter, session=session)
        session.stop = now
        session.save()
        
        entry.save()

    def smpl_0x04(self, data):
        """
        Start new session
        """
        print "04", repr(data)
        mdata = self.get_smpl_data(data)
        ident = "0x%02x%02x" %(ord(mdata[0]), ord(mdata[1]))
        device, created = Detector.objects.get_or_create(ident=ident, defaults={"name": "eZ430 OpenChronos",
                                                                      "ident": ident,
                                                                      "typ": DETECTOR_TYPES[0][0],
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

        if not active_session:
            rf_id = Session.objects.get_new_rf_id()
            program = ord(mdata[2])
            if not alarm.manager.is_valid_program_id(program):
                program = 0
            active_session = Session(start=now, stop=now, detector=device, user=device.default_user,
                              rf_id=rf_id, program=program)
            active_session.save()

        logging.info("Send Session ID: %s" %(active_session.rf_id))

        data = [SIMPLICITI_PHASE_CLOCK_START_RESPONSE, active_session.rf_id]
        self.send_smpl_data(data)
        # we shall not do anything until the clock reads out the 
        # session data
        time.sleep(0.030)

    def smpl_0x10(self, data):
        """
        Start sync mode
        """
        logging.debug("start sync mode")
        # taken from http://pastebin.com/f62344dbd
        # empty buffer
        self.read_sync_data()
        # read old data
        for x in xrange(1000):
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

        print "send", cdata, self.build_sync_data(cdata)

        for x in xrange(10):
            self.send_smpl_data(self.build_sync_data(cdata))
            time.sleep(0.100)

        self.send_smpl_data([ez_chronos.SYNC_AP_CMD_EXIT])
