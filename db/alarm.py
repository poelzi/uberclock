"""
Alarm clock logic
"""


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

    def execute(self):
        raise NotImplemented


class ExecuteAction(BaseAction):
    """
    Executes external program
    """
    def execute(self):
        import subprocess
        self.popen = subprocess.Popen(self.args)
        self.popen.communicate()

class BaseAlarm(object):
    """
    Base Class for all alarm logics
    """
    # numeric id. must be unique and change never
    key = None
    name = None
    short_name = None

    def __init__(self, manager, session):
        self.manager = manager
        self.session = session
        self.next_alarm = None

    def check(self):
        """
        Returns a alarm action to execute
        """
        return None

    def snooze(self):
        """
        User pressed snooze
        """
        pass

    def feed(self, entry):
        """
        Feed one new Entry into the Alarm program.
        """
        pass

class BasicAlarm(BaseAlarm):
    key = "basic"
    name = "Basic Alarm"
    short_name = "basic"

manager.register(BasicAlarm)