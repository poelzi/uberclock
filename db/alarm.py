"""
Alarm clock logic
"""

from uberclock.tools import Enumeration
from django.conf import settings

import datetime


ACTIONS = Enumeration("ACTIONS",
    (("LIGHTS",1), "WAKEUP"))

class Manager(object):
    """Manages Alarm Programs"""

    def __init__(self):
        self.programs = {}

    def register(self, program):
        """
        Register a new alarm clock program
        """
        if not program.key:
            raise ValueError, "program id (key) is not set"
        if program.key in self.programs and self.programs[program.key] != program:
            raise ValueError, "program id (key) already exists"

        self.programs[program.key] = program

    def list_programs(self):
        """
        Return a list of all programs
        """
        return [program for program in self.programs.iteritems()]

    @property
    def choices_programs(self):
        """
        Return a choices list used in django
        """
        rv = []
        for key,program in self.programs.iteritems():
            rv.append((key, program))
        return rv

    def is_valid_program(self, key):
        for program in self.programs.iteritems():
            if program.key == key:
                return True

    def get_program(self, key):
        return self.programs.get(key, self.programs["basic"] )

    def create_session(self, user_name, program):
        pass

manager = Manager()


class AlarmInstance(object):
    """
    Running instance of a alarm clock.
    It is assigned to a user.
    """

    def __init__(self, user, detector, program=None):
        self.user = user
        self.detector = detector
        self.program = program


class BaseAction(object):
    """
    Action to take
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.background = kwargs.get("background", False)

    def execute(self):
        raise NotImplemented


class ExecuteAction(BaseAction):
    """
    Executes external program
    """
    def execute(self):
        import subprocess
        if self.background:
            self.popen = subprocess.Popen(self.args)
        else:
            self.popen = subprocess.Popen(self.args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return self.popen.communicate()

class BaseAlarm(object):
    """
    Base Class for all alarm logics
    """
    # numeric id. must be unique and change never
    key = None
    name = None
    short_name = None

    def __init__(self, manager, session, **kwargs):
        self.manager = manager
        self.session = session
        self.next_alarm = None
        self.snooze_time = kwargs.get('snooze_time', settings.DEFAULT_SNOOZE_TIME)

    def check(self):
        """
        Returns a alarm action to execute
        """
        return False

    def snooze(self, snooze_time=None):
        """
        User pressed snooze
        """
        if snooze_time is None:
            snooze_time = self.snooze_time

        self.next_alarm = datetime.datetime.now() + \
                              datetime.timedelta(seconds=snooze_time)

    def stop(self):
        self.next_alarm = None

    def feed(self, entry):
        """
        Feed one new Entry into the Alarm program.
        """
        pass

class BasicAlarm(BaseAlarm):
    key = "basic"
    name = "Basic Alarm"
    short_name = "basic"

    def check(self, dt=None):
        """
        Returns a alarm action to execute
        """
        if not dt:
            dt = datetime.datetime.now()
        if not self.next_alarm:
            return False
        if self.next_alarm < dt:
            return ACTIONS.WAKEUP
        return False

manager.register(BasicAlarm)

class MovementAlarm(BasicAlarm):
    key = "simple_movement"
    name = "Simple Movement"
    short_name = "smplmv"
    
    DEFAULT_THRESHHOLDS = {
        0: 20000, # OpenChronos
        None: 1000, # Unknown, default
    }

    def __init__(self, *args, **kwargs):
        super(MovementAlarm, self).__init__(*args, **kwargs)

        th = self.DEFAULT_THRESHHOLDS[None]
        if self.session:
            if self.session.detector:
                th = self.DEFAULT_THRESHHOLDS.get(session.detector.typ, None)
            if self.session.program:
                th = self.session.program.get_var("movement_threshhold", th)
        if "threshhold" in kwargs:
            th = kwargs["threshhold"]
        self.threshold = th

    def check(self, dt=None):
        """
        Returns a alarm action to execute
        """
        if not dt:
            dt = datetime.datetime.now()
        # if the default action is already fireing 
        rv = super(MovementAlarm, self).check(dt)
        if rv:
            return rv
        if not self.session.window:
            return
        fwin = dt - datetime.timedelta(minutes=self.session.window)
        for entry in self.session.entry_set.order_by('-date')[:3]:
            # stop when the entry is befor the considered window
            if entry.date < fwin:
                break
            if entry.value > self.threshold:
                if self.session.action_in_window(ACTIONS.WAKEUP, dt):
                    return ACTIONS.WAKEUP


manager.register(MovementAlarm)

