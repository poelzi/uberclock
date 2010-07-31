"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

from models import *
import alarm
import time, datetime


class NoopAction(alarm.BaseAction):
    name = "noop"
    def execute(self):
        print "noop execute"
        self.done = True

alarm.manager.register_action(NoopAction)

CLOCK_RUN = False

class ClockAction(alarm.BaseAction):
    name = "clock"
    def execute(self):
        global CLOCK_RUN
        if self.is_running:
            return
        self.is_running = True
        assert CLOCK_RUN == False, "Clock already run"
        CLOCK_RUN = True
        self.done = True

alarm.manager.register_action(ClockAction)

settings.COMMANDS["test_clock"] = {"type": "clock"}
settings.COMMANDS["test_noop"] = {"type": "noop"}


class DBTest(TestCase):
    fixtures = ['default_user.json']

    def test_cleanup(self):
        dt = datetime.datetime.now() - datetime.timedelta(days=2)
        # emulate an old session
        session = Session()
        session.save()
        session.stop = dt
        session.save()
        sid = session.id
        Session.objects.cleanup_sessions()
        self.assertEqual(Session.objects.filter(id=sid).count(), 0)

    def test_learndata(self):
        session = Session()
        session.save()
        ld = session.learndata
        ent = Entry(session=session, value=10)
        ent.save()
        self.assertEqual(ld.placed, False)
        for key in ["wake", "start", "stop", "lights"]:
            setattr(ld, key, ent)
            self.assertEqual(ld.placed, True)
            setattr(ld, key, None)
            self.assertEqual(ld.placed, False)

    def test_userprogram(self):
        up = UserProgram(users_id=0)
        up.save()
        uid = up.id
        self.assertEqual(up.get_var("bla"), None)
        self.assertEqual(up.get_var("bla",1), 1)
        up.set_var("bla", 23)
        self.assertEqual(up.get_var("bla",1), 23)
        self.assertEqual(up.get_var("bla"), 23)
        up.set_var("wakeup", datetime.time(7, 30))
        up.save()
        up = UserProgram.objects.get(id=uid)
        # json is not used anymore
        #self.assertEqual(up.settings, '{"bla": 23}')
        self.assertEqual(up.get_var("bla"), 23)
        self.assertEqual(up.get_var("wakeup"), datetime.time(7, 30))
        up.delete()

    def test_session_params(self):
        prog = UserProgram(users_id=123)
        #prog.set_var("wakeup", datetime.time(6,30))
        prog.default_wakeup = datetime.time(3, 45)
        prog.default_window = 29
        #prog.default_sleep_time = None
        
        prog.save()
        session = Session(program=prog)
        self.assertEqual(session.wakeup, time_to_next_datetime(prog.default_wakeup))
        self.assertEqual(session.window, prog.default_window)
        self.assertEqual(session.sleep_time, None)

        prog.default_window = 24
        prog.default_wakeup = datetime.time(3, 23)
        prog.save()
        
        self.assertEqual(session.wakeup, time_to_next_datetime(datetime.time(3, 45)))
        self.assertEqual(session.window, 29)
        self.assertEqual(session.sleep_time, None)

        session.program = prog

        self.assertEqual(session.wakeup, time_to_next_datetime(datetime.time(3, 45)))
        self.assertEqual(session.window, 29)
        self.assertEqual(session.sleep_time, None)

        prog.default_sleep_time = 300
        
        session = Session(program=prog)
        self.assertEqual(session.sleep_time, 300)

        session.save()
        # test log
        session.log("UNKNOWN", "test info")
        session.log("WAKEUP", "test wakeup")
        session.log("LIGHTS", "test lights")
        session.log("INFO", "test info")
        session.log("WARNING", "test warning")
        session.log("ERROR", "test error")
        self.assertEqual(session.logs.count(), 6)
        session.log(123, "last")
        self.assertEqual(session.logs.all()[0].typ, 123)


        prog.delete()
        
    def test_session_functions(self):
        prog = UserProgram(users_id=123)
        #prog.set_var("wakeup", datetime.time(6,30))
        prog.default_wakeup = datetime.time(3, 45)
        prog.default_window = 29
        prog.save()

        session = Session(program=prog)

        now = datetime.datetime.now()
        session.window = 15
        session.wakeup = now + datetime.timedelta(minutes=20)
        self.assertEqual(session.action_in_window(alarm.ACTIONS.WAKEUP), False)
        self.assertEqual(session.action_in_window(alarm.ACTIONS.LIGHTS), True)
        session.window = 21
        self.assertEqual(session.action_in_window(alarm.ACTIONS.WAKEUP), True)
        self.assertEqual(session.action_in_window(alarm.ACTIONS.LIGHTS), True)

    def test_basic_alarm(self):
        prog = UserProgram(users_id=3)
        
        #prog.set_var("wakeup", datetime.time(6,30))
        prog.default_wakeup = datetime.time(3, 45)
        prog.default_window = 29
        prog.wakeup_action = "test_clock"
        prog.save()

        session = Session(program=prog)

        now = datetime.datetime.now()
        session.window = 15
        session.wakeup = now + datetime.timedelta(minutes=20)
        self.assertEqual(session.action_in_window(alarm.ACTIONS.WAKEUP), False)
        self.assertEqual(session.action_in_window(alarm.ACTIONS.LIGHTS), True)
        session.window = 21
        self.assertEqual(session.action_in_window(alarm.ACTIONS.WAKEUP), True)
        self.assertEqual(session.action_in_window(alarm.ACTIONS.LIGHTS), True)



    def test_user(self):
        usr = get_user_or_default(None)
        from django.contrib.auth.models import User
        first = User.objects.all()[0]
        #self.assertEqual(usr.username, settings.DEFAULT_USER)
        # we need to have a user
        self.assertTrue(usr)
        self.assertEqual(get_user_or_default(first), first)
        self.assertEqual(get_user_or_default(first.username), first)
        #usr = get_user_or_default(None)



class ActionTest(TestCase):
    def test_manager(self):
        self.assertEquals(alarm.manager.get_action("execute"),
                          alarm.ExecuteAction)
        self.assertEquals(alarm.manager.get_action("mpd"),
                          alarm.MpdAction)

    def test_action(self):
        ea = alarm.manager.get_action("execute")(commands=("echo", "testrun1"))
        rv = ea.execute()
        self.assertEqual(rv, 0)
        ea = alarm.manager.get_action("execute")(commands=(("echo", "testrun2"),))
        rv = ea.execute()
        self.assertEqual(rv, 0)
        ea = alarm.manager.get_action("execute")(commands=(("true",),("false",),("true")))
        rv = ea.execute()
        self.assertEqual(rv, 1)

    def test_mpd(self):
        ea = alarm.MpdAction()
        import socket
        try:
            rv = ea.execute()
        except socket.error:
            print "skip mpd test"
            return
        self.assertEqual(rv, None)
        self.assertEqual(ea.client.status()['state'], 'play')
        ea.stop()


class AlarmTest(TestCase):
    def test_basic_alarm(self):
        session = Session()
        session.save()
        basic = alarm.BasicAlarm(alarm.manager, session)
        self.assertEqual(basic.check(), False)
        basic.snooze(0.001)
        time.sleep(0.01)
        self.assertEqual(basic.check(), alarm.ACTIONS.WAKEUP)

    def test_manager(self):
        self.assertEqual(alarm.manager.get_program("simple_movement"), 
                         alarm.MovementAlarm)
        self.assertEqual(alarm.manager.get_program("basic"), 
                         alarm.BasicAlarm)
        self.assertEqual(alarm.manager.get_program("bla"), 
                         alarm.BasicAlarm)
        


    def test_movement(self):
        prog = UserProgram(users_id=2)
        #prog.set_var("wakeup", datetime.time(6,30))
        prog.default_wakeup = datetime.time(5, 00)
        prog.default_window = 10
        prog.save()

        session = Session(program=prog)

        now = datetime.datetime.now()
        start = datetime.datetime.now()
        session.window = 15
        session.wakeup = now + datetime.timedelta(minutes=20)
        self.assertEqual(prog.alarm_key, "")
        self.assertEqual(prog.program_class, alarm.BasicAlarm)
        prog.set_program(alarm.manager.get_program("simple_movement"))
        self.assertEqual(prog.alarm_key, "simple_movement")
        self.assertEqual(prog.program_class, alarm.MovementAlarm)
        ai = prog.get_program(session)
        ai.threshold = 3000
        self.assertTrue(isinstance(ai, prog.program_class))
        
        ok =  session.wakeup - datetime.timedelta(minutes=session.window)
        end = now + datetime.timedelta(minutes=15)

        import random
        random.seed(0)
        ctime = now - datetime.timedelta(minutes=15)
        for i in xrange(4000):
            # we should stop here with random tests, they should never have stopped
            # yet
            jit = random.randrange(0, 30)
            ctime += datetime.timedelta(seconds=20+0.3*jit)
            var = random.randrange(0,3242)
            # emulate packet drop
            if jit < 5:
                continue
            if ctime > end:
                var = 3102

            ent = Entry(value=var, date=ctime, session=session)
            ent.save()
            ent.date = ctime
            ent.save()
            ai.feed(ent)
            res = ai.check(ctime)
            if ctime >= ok and var >= 3000 :
                self.assertEquals(res, alarm.ACTIONS.WAKEUP)
                # we can stop now
                break
            else:
                self.assertFalse(res)

            if ctime > end:
                break

        # test default time timeout
        session.wakeup = now - datetime.timedelta(seconds=20)
        ai = prog.get_program(session)
        ai.threshold = 3000
        res = ai.check(ctime)
        self.assertEquals(res, alarm.ACTIONS.WAKEUP)



    def test_test_default_program(self):
        duser = get_user_or_default(None)
        userp = UserProgram.objects.get_program_for_user(duser, 0)
        self.assertEqual(userp.__class__, UserProgram)

        userp2 = UserProgram.objects.get_program_for_user(duser, 1)
        self.assertNotEqual(userp, userp2)
        userp2.default = True
        userp2.save()

        ud = UserProgram.objects.get_users_default(duser)
        self.assertEqual(ud, userp2)


    def test_reload(self):
        wakeup=datetime.datetime.now() + datetime.timedelta(hours=10)
        wakeup2 = datetime.datetime.now() + datetime.timedelta(hours=8)
        duser = get_user_or_default(None)
        session = Session(wakeup=wakeup)
        session.save()
        prog = UserProgram.objects.get_program_for_user(duser, 0)
        aprog = prog.get_program(session)
        self.assertEqual(aprog.session.wakeup, wakeup)
        session.wakeup = wakeup2
        session.save()
        self.assertEqual(aprog.session.wakeup, wakeup2)
        

    def test_clock(self):
        clock = alarm.Clock()

        prog = UserProgram(users_id=2)
        #prog.set_var("wakeup", datetime.time(6,30))
        prog.default_wakeup = datetime.time(5, 00)
        prog.default_window = 10
        prog.wakeup_action = "test_clock"
        prog.set_program(alarm.manager.get_program("basic"))
        prog.save()

        session = Session(program=prog, wakeup=datetime.datetime.now() + datetime.timedelta(seconds=200))
        session.save()

        ai = prog.get_program(session)
        clock.add(ai)


        # update wakeup to working value
        session.wakeup=datetime.datetime.now() + datetime.timedelta(seconds=1)
        session.save()

        run = False
        for i in xrange(100):
            clock.work()
            if CLOCK_RUN:
                clock.stop()
                break
            time.sleep(0.10)
        else:
            self.assertEqual(CLOCK_RUN, True, "Action is not run")
            self.assertEqual(1, 0, "should have stopped. reload broken")
        
        # FIXME
        self.assertEqual(len(clock), 0)
        clock.stop()

    def test_create_action(self):
        tc = alarm.create_action("test_clock")
        self.assertEqual(tc.__class__, ClockAction)
        tc = alarm.create_action("test_noop")
        self.assertEqual(tc.__class__, NoopAction)


    def test_neuro1(self):
        pass



from uberclock.tools.date import time_to_next_datetime
# test some code from tools
class ToolsTest(TestCase):
    def test_time_to_next_datetime(self):
        now = datetime.datetime.now()
        prev = now - datetime.timedelta(minutes=1)
        nd = time_to_next_datetime(prev.time())
        # past test
        self.assertTrue(nd > now)
        self.assertTrue(nd - datetime.timedelta(hours=23, minutes=55) > now)
        
        # futur test
        next = now + datetime.timedelta(minutes=1)
        nd = time_to_next_datetime(next.time())

        self.assertTrue(nd > now)
        self.assertTrue(nd - datetime.timedelta(minutes=2) < now)


