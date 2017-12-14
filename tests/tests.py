
from datetime import timedelta, datetime
from time import sleep

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.template import Template, Context
from django.http import HttpResponseNotAllowed
from django.contrib.auth.models import User

from django_timer.models import Timer, Segment, TimerResumeException, TimerStartException

class ModelTest(TestCase):

    def test_start_timer_through_manager(self):
        timer = Timer.objects.start()
        self.assertEqual(timer.segment_set.count(), 1)
        self.assertIsInstance(timer.segment_set.first().start_time, datetime)

    def test_start_timer_through_model(self):
        timer = Timer.objects.create()
        self.assertEqual(timer.segment_set.count(), 0)
        timer.start()
        self.assertEqual(timer.segment_set.count(), 1)
        self.assertIsInstance(timer.segment_set.last().start_time, datetime)

        # Starting again raises Error
        with self.assertRaises(TimerStartException):
            timer.start()

    def test_duration_if_timer_still_running(self):
        timer = Timer.objects.start()
        d1 = timer.duration()
        sleep(0.01)
        d2 = timer.duration()
        self.assertTrue(d2>d1)

    def test_stop_timer(self):
        timer = Timer.objects.start()
        timer.stop()
        self.assertIsInstance(timer.segment_set.first().stop_time, datetime)
        self.assertIsInstance(timer.segment_set.last().duration(), timedelta)
        self.assertIsInstance(timer.duration(), timedelta)

    def test_pause_timer(self):
        timer = Timer.objects.start()
        timer.pause()
        self.assertIsInstance(timer.segment_set.first().stop_time, datetime)
        self.assertIsInstance(timer.duration(), timedelta)

    def test_resume_timer(self):
        timer = Timer.objects.start()
        timer.pause()
        timer.resume()
        # Timer cannot be resumed a second time, if it's still running
        with self.assertRaises(TimerResumeException):
            timer.resume()
        self.assertEqual(timer.segment_set.count(), 2)
        self.assertIsNone(timer.segment_set.last().stop_time)
        timer.pause()
        timer.resume()
        self.assertEqual(timer.segment_set.count(), 3)

    def test_timer_stopped(self):
        timer = Timer.objects.start()
        timer.stop()
        with self.assertRaises(TimerResumeException):
            timer.resume()

    def test_with_time(self):
        timer = Timer.objects.start()
        sleep(0.1)
        timer.pause()
        timer.resume()
        sleep(0.1)
        timer.stop()
        self.assertAlmostEqual(timer.duration().total_seconds(), 0.2, delta=0.05)

    def test_with_user(self):
        user = User.objects.create_user(username='foo', password='bar')
        timer = Timer.objects.start(user=user)
        self.assertEqual(timer.user, user)

    def test_get_or_start(self):
        t1 = Timer.objects.get_or_start()
        self.assertEqual(Timer.objects.count(), 1)
        t2 = Timer.objects.get_or_start()
        self.assertEqual(Timer.objects.count(), 1)
        self.assertEqual(t1.pk, t2.pk)
        t2.stop()
        t3 = Timer.objects.get_or_start()
        self.assertEqual(Timer.objects.count(), 2)
        self.assertNotEqual(t2.pk, t3.pk)
        user = User.objects.create_user(username='foo', password='bar')
        t4 = Timer.objects.get_or_start(user=user)
        self.assertEqual(Timer.objects.count(), 3)
        
    def test_get_for_user(self):
        u1 = User.objects.create_user(username='foo', password='bar')
        u2 = User.objects.create_user(username='bar', password='foo')
        t1 = Timer.objects.get_or_start(user=u1)
        t1.stop()
        t1a = Timer.objects.get_or_start(user=u1)
        t2 = Timer.objects.get_or_start(user=u2)
        t0 = Timer.objects.get_or_start(user=None)
        self.assertEqual(Timer.objects.count(), 4)

        self.assertEqual(Timer.objects.get_for_user(), t0)
        self.assertEqual(Timer.objects.get_for_user(user=u1), t1a)
        self.assertEqual(Timer.objects.get_for_user(user=u2), t2)

        t2.stop()
        with self.assertRaises(Timer.DoesNotExist):
            Timer.objects.get_for_user(user=u2)

    def test_status_flags(self):
        t = Timer.objects.start()
        self.assertTrue(t.running)
        self.assertFalse(t.paused)
        self.assertFalse(t.stopped)

        t.pause()
        self.assertFalse(t.running)
        self.assertTrue(t.paused)
        self.assertFalse(t.stopped)

        t.resume()
        self.assertTrue(t.running)
        self.assertFalse(t.paused)
        self.assertFalse(t.stopped)

        t.stop()
        self.assertFalse(t.running)
        self.assertFalse(t.paused)
        self.assertTrue(t.stopped)

class ViewTest(TestCase):

    def test_start_and_stop_timer(self):
        self.client.post(reverse('start_timer'))
        self.assertEqual(Timer.objects.count(), 1)
        self.client.post(reverse('pause_timer'))
        self.assertIsInstance(Timer.objects.first().segment_set.last().stop_time, datetime)
        self.client.post(reverse('resume_timer'))
        self.assertEqual(Timer.objects.first().segment_set.count(), 2)
        self.assertIsNone(Timer.objects.first().segment_set.last().stop_time)
        self.client.post(reverse('stop_timer'))
        self.assertTrue(Timer.objects.first().stopped) 

    def test_start_timer_as_user(self):
        user = User.objects.create_user(username='foo', password='bar')
        self.client.login(username='foo', password='bar')
        self.client.post(reverse('start_timer'))
        timer = Timer.objects.first()
        self.assertEqual(timer.user, user)

    def test_method_not_allowed(self):

        response = self.client.get(reverse('start_timer'))
        self.assertEqual(response.status_code, 405)

        response = self.client.get(reverse('pause_timer'))
        self.assertEqual(response.status_code, 405)

        response = self.client.get(reverse('resume_timer'))
        self.assertEqual(response.status_code, 405)

        response = self.client.get(reverse('stop_timer'))
        self.assertEqual(response.status_code, 405)

    def test_pause_and_resume_race_conditions(self):

        self.client.post(reverse('start_timer'))
        self.client.post(reverse('pause_timer'))

        self.client.post(reverse('resume_timer'))
        # Resuming a second time shouldn't raise
        self.client.post(reverse('resume_timer'))

        self.client.post(reverse('stop_timer'))
        # Resuming or pausing a stopped timer shouldn't raise
        self.client.post(reverse('pause_timer'))
        self.client.post(reverse('resume_timer'))

    def test_start_if_timer_running(self):

        self.client.post(reverse('start_timer'))
        self.client.post(reverse('start_timer'))

        self.assertEqual(Timer.objects.count(), 1) 

    def test_stop_if_no_timer_is_running(self):

        self.client.post(reverse('start_timer'))
        self.client.post(reverse('stop_timer'))
        # Stopping a second time shouldn't raise
        self.client.post(reverse('stop_timer'))

class TemplateTagsTest(TestCase):

    def test_render_timer(self):
        timer = Timer.objects.start()
        template = Template('{% load timer %}{% render_timer timer %}')
        context = Context({'timer': timer})
        html = template.render(context)
        self.assertIn('id="django-timer"', html)
        