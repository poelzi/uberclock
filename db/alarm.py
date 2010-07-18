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
        if not program.nid:
            raise ValueError, "program id (nid) is not set"
        if program.nid in self.programs and self.programs[program.nid] != program:
            raise ValueError, "program id (nid) already exists"

        self.programs[program.nid] = program

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
        for program in self.programs.iteritems():
            rv.append((program.nid, program))
        return rv

    def is_valid_program_id(self, nid):
        for program in self.programs.iteritems():
            if program.nid == nid:
                return True

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
    nid = None
    title = None

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
