from django.db import models
from uberclock.tools import ez_chronos
from django.contrib.auth.models import User
from django.conf import settings
import struct
import logging
import datetime
# Create your models here.

DETECTOR_TYPES = (
 (0, "OpenChronos"),
)

SESSION_TYPES = (
 (0, "Normal Sleep"),
 (1, "Powernap"),
 (2, "One REM"),
)


class Detector(models.Model):
    """
    Device which messures the sleep state
    """
    name = models.CharField("Name", max_length=100, null=False)
    typ = models.IntegerField("Type", choices=DETECTOR_TYPES)
    default_user = models.ForeignKey(User, null=True)

class WakeupTime(models.Model):
    """
    User saved wakeup times for shortcuts
    """
    name = models.CharField("Name", max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, null=False)
    # fixme choices etc
    weekday = models.IntegerField("Weekday", null=True) 
    session_typ = models.IntegerField("Type", default=0, choices=SESSION_TYPES)
    wakeup = models.TimeField("Wakeup", null=False)

class Session(models.Model):
    """
    One Sleep Session
    """
    start = models.DateTimeField("Start", null=False, auto_now_add=True, editable=False)
    stop = models.DateTimeField("Stop", null=False, auto_now_add=True, editable=False)
    user = models.ForeignKey(User, null=True)
    detector = models.ForeignKey(Detector, null=True)
    typ = models.IntegerField("Type", default=0, choices=SESSION_TYPES)
    wakeup = models.DateTimeField("Wakeup", null=True)
    rating = models.IntegerField("Rating", null=True)
    deleted = models.BooleanField("Deleted", default=False)
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



class DBWriter(ez_chronos.CommandDispatcher):

    def __init__(self, *args, **kwargs):
        super(DBWriter, self).__init__(*args, **kwargs)
        self.last_msg = {}
        self.session = {}

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
        # acceleration data
        timeout=datetime.timedelta(seconds=settings.CLOCK_SESSION_TIMEOUT)
        now = datetime.datetime.now()
        #FIXME: detect device
        device = 1
        
        # autostart a new session if there where no messages in timeout
        if not device in self.last_msg or not device in self.session or\
           now > self.last_msg[device]+timeout:
            #FIXME add device & user
            self.session[device] = session = Session(start=now, stop=now)
            session.save()
            logging.debug("start new session: %s @ %s" %(session.id, session.start))
        else:
            session = self.session[device]
        self.last_msg[device] = now
        mdata = self.get_smpl_data(data)
        var = struct.unpack('H', mdata[:2])[0]
        counter = ord(mdata[2])
        logging.debug("%s %3d %6d %s" %(session.id, counter, var, "#"*max(min((var/500), 80),1)))
        entry = Entry(value=var, counter=counter, session=session)
        session.stop = now
        session.save()
        
        entry.save()
