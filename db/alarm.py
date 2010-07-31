"""
Alarm clock logic
"""

from uberclock.tools import Enumeration
from django.conf import settings
from collections import defaultdict

import datetime
import time
import logging


ACTIONS = Enumeration("ACTIONS",
    (("LIGHTS",1), "WAKEUP"))

class Manager(object):
    """Manages Alarm Programs"""

    def __init__(self):
        self.programs = {}
        self.actions = {}

    def register(self, program):
        """
        Register a new alarm clock program
        """
        if not program.key:
            raise ValueError, "program id (key) is not set"
        if not issubclass(program, BaseAlarm):
            raise ValueError, "program is not a BaseAction"
        if program.key in self.programs and self.programs[program.key] != program:
            raise ValueError, "program id (key) already exists"

        self.programs[program.key] = program

    def register_action(self, action):
        """
        Register a new alarm clock program
        """
        if not issubclass(action, BaseAction):
            raise ValueError, "action is not a subclass of BaseAction"
        if not action.name:
            raise ValueError, "action name is not set"

        self.actions[action.name] = action

    def get_action(self, name):
        """
        Return a action with the name given
        """
        return self.actions[name]

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
            rv.append((key, program.name))
        return rv

    def is_valid_program(self, key):
        for program in self.programs.iteritems():
            if program.key == key:
                return True

    def get_program(self, key):
        return self.programs.get(key, self.programs["basic"] )

manager = Manager()

class Clock(set):
    """
    The actuall clock where alarm programs run in
    """
    def __init__(self):
        self.actions = defaultdict(list)
        return super(Clock, self).__init__()

    def add(self, obj):
        if not isinstance(obj, BaseAlarm):
            raise ValueError
        for x in self:
            # already added
            if x.session == obj.session:
                return
        super(Clock, self).add(obj)

    def has_session(self, session):
        """
        Test if program for a session exist
        """
        for x in self:
            if x.session == session:
                return True
        return False

    def work(self):
        """
        Do one work iteration
        """
        lst = list(self)
        for prog in lst:

            # we only check not stopped programs. they may still be here
            # because a action is still running
            if not prog.stopped:
                # reload the cached
                prog.reload()
                res = prog.check()
                # FIXME finish
                if res:
                    act = prog.execute()
                    if act:
                        self.actions[prog].append(act)
                    if not act.is_running:
                        act.execute()

                self._clean_prog(prog)

    def _clean_prog(self, prog):
        # check the running actions
        for action in self.actions[prog][:]:
            if action.done:
                self.actions[prog].remove(action)
            elif prog.stopped:
                # if the program is stopped, we send a stop signal an the running actions
                action.stop()

        # if no action is running and program is stopped, we can savely remove it
        if prog.stopped and not len(self.actions[prog]):
            self.remove(prog)


    def stop_all(self):
        """
        Stops all programs
        """
        for prog in list(self):
            prog.stop()
            self._clean_prog(prog)


    def run(self):
        """
        Endless working loop
        """
        while True:
            self.work()
            # sleep a tick
            time.sleep(10)

    def running_actions(self):
        res = 0
        for acts in self.actions.itervalues():
            for act in acts:
                if not act.stopped:
                    res += 1
        return res

    def stop(self):
        """
        Stops clock
        """
        self.stop_all()


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
    name = None
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.background = kwargs.get("background", False)
        self.is_running = False
        self.done = False

    def execute(self):
        raise NotImplemented

    def stop(self):
        """stop the action if it is still running"""
        self.is_running = False
        self.done = True

class MpdAction(BaseAction):
    """
    Executes external program
    """
    name = "mpd"

    def __init__(self, *args, **kwargs):
        super(MpdAction, self).__init__(*args, **kwargs)
        from uberclock.tools import mpd
        self.client = mpd.MPDClient()
        self.script_run = False
        self.started = False

    def execute(self):
        self.is_running = True

        from uberclock.tools import mpd
        try:
            self.client.fileno()
        except mpd.ConnectionError:
            host = self.kwargs.get("host", settings.MPD_HOST[0])
            port = self.kwargs.get("port", settings.MPD_HOST[1])
            self.client.connect(host, port)

        status =  self.client.status()

        if not self.script_run:
            for cmds in settings.MPD_COMMANDS:
                try:
                    getattr(self.client, cmds[0])(*cmds[1:])
                except mpd.MPDError:
                    logging.warning("Could not run mpd command: %s" %" ".join(cmds))
            self.script_run = True


        if status["volume"] != settings.MPD_VOLUME:
            try:
                self.client.volume(settings.MPD_VOLUME)
            except mpd.MPDError:
                pass

        if status["state"] != 'play':
            self.started = True
            self.client.play()
        time.sleep(0.5)

    def stop(self):
        super(MpdAction, self).stop()

        if self.started:

            time.sleep(0.5)
            while self.client.status()["state"] == "play":
                self.client.stop()
        self.client.close() # send the close command
        self.client.disconnect()

manager.register_action(MpdAction)

class ExecuteAction(BaseAction):
    """
    Executes external program
    """
    name = "execute"

    def execute(self):
        self.is_running = True
        import subprocess
        name = self.kwargs.get("name", "UNKNOWN")
        cmds = self.kwargs.get('commands', None)

        if not isinstance(cmds, (list, tuple)) or not len(cmds):
            raise ValueError, "configure error: %s 'commands' are wrong. %s" %(name, cmds)

        if isinstance(cmds[0], (list, tuple)):
            for cm in cmds:
                if not isinstance(cm, (list, tuple)):
                    raise ValueError, "configure error: %s commands are wrong" %name
                rv = subprocess.call(cm)
                if rv:
                    return rv
        else:
            return subprocess.call(cmds)
        return rv

manager.register_action(ExecuteAction)

def create_action(action_name):
    if not action_name in settings.COMMANDS:
        logging.error('configuration error: the command "%s" is not configured' %action_name)
        return
    try:
        action_type = settings.COMMANDS[action_name]["type"]
    except KeyError:
        action_type = "execute"
    try:
        exe_class = manager.get_action(action_type)
    except KeyError:
        logging.error('configuration error: type "%s" of action %s is not valid' %(action_type, action_name))
        return
    cmds = settings.COMMANDS[action_name].copy()
    cmds["name"] = action_name
    return exe_class(**cmds)


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
        self.stopped = False
        self.snooze_time = kwargs.get('snooze_time', settings.DEFAULT_SNOOZE_TIME)
        self.wakeup_action = kwargs.get('wakeup_action', None)
        self.lights_action = kwargs.get('lights_action', None)
        self.wakeup_action_inst = None
        self.lights_action_inst = None
        self.done = False


    def reload(self):
        if self.session:
            self.session = self.session.__class__.objects.get(id=self.session.id) 

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
        self.done = False

        self.next_alarm = datetime.datetime.now() + \
                              datetime.timedelta(seconds=snooze_time)

    def stop(self):
        self.next_alarm = None
        self.done = True
        self.stopped = True

    def execute(self):
        """
        Creates a new ActionClass instance and returns it.
        """
        if self.wakeup_action_inst:
            return self.wakeup_action_inst
        action_name = self.wakeup_action or (self.session and self.session.wakeup_action)
        if self.session:
            self.session.log("WAKEUP", "Execute action %s" %action_name)
        self.wakeup_action_inst = create_action(action_name)
        return self.wakeup_action_inst

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
            if self.session and self.session.wakeup:
                if self.session.wakeup < dt:
                    self.next_alarm = dt
                    return ACTIONS.WAKEUP
        if self.next_alarm and self.next_alarm < dt:
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
                th = self.DEFAULT_THRESHHOLDS.get(self.actsession.detector.typ, None)
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

