from unittest import TestCase
from datetime import datetime

from app import create_app, db
from app.config import TestConfig
from app.models import User, Friendship, Event, TaskStatus, create_test_data
import app.routes as routes
from app.routes import (
    format_datetime,
    generate_common_free_slots,
    merge_busy_intervals,
    normalise_email,
    normalise_username,
    parse_iso_datetime,
    users_are_accepted_friends,
)


class TestModels(TestCase):
    def setUp(self):
        testApp = create_app(TestConfig)
        self.testApp = testApp
        self.app_context = testApp.app_context()
        self.app_context.push()
        db.create_all()
        create_test_data()
        return super().setUp()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        return super().tearDown()

    def call_view(self, view_func, *args, path='/', method='GET', json=None, query_string=None):
        view = getattr(view_func, '__wrapped__', view_func)
        with self.testApp.test_request_context(path, method=method, json=json, query_string=query_string):
            return view(*args)
    
    def test_password_hashing(self):
        user = db.session.get(User, "testuser@example.com")
        user.set_password("you-will-never-guess")
        self.assertTrue(user.check_password("you-will-never-guess"), "Password check returned False for correct password, expected True")
        self.assertFalse(user.check_password("this-is-wrong"), "Password check returned True for incorrect password, expected False")
    
    def test_friendship_to_dict(self):
        friendship = db.session.query(Friendship).first()
        friendship_dict = friendship.to_dict()
        self.assertEqual(friendship_dict.get('id'), friendship.id, "Friendship ID in dict does not match Friendship ID")
        self.assertEqual(friendship_dict.get('requester_email'), friendship.requester_email, "Friendship requester_email in dict does not match Friendship requester_email")
        self.assertEqual(friendship_dict.get('receiver_email'), friendship.receiver_email, "Friendship receiver_email in dict does not match Friendship receiver_email")
        self.assertEqual(friendship_dict.get('status'), friendship.status.value, "Friendship status in dict does not match Friendship status value")
        self.assertEqual(friendship_dict.get('created_at'), friendship.created_at.isoformat(), "Friendship created_at in dict does not match Friendship created_at")
    
    def test_event_to_dict(self):
        event = db.session.query(Event).first()
        event_dict = event.to_dict()
        self.assertEqual(event_dict.get('id'), event.id, "Event ID in dict does not match Event ID")
        self.assertEqual(event_dict.get('title'), event.title, "Event title in dict does not match Event title")
        self.assertEqual(event_dict.get('start'), event.start.isoformat(), "Event start time in dict does not match Event start time")
        self.assertEqual(event_dict.get('end'), event.end.isoformat(), "Event end time in dict does not match Event end time")
        self.assertEqual(event_dict.get('backgroundColor'), event.backgroundColor, "Event background color in dict does not match Event background color")
        self.assertEqual(event_dict.get('durationEditable'), not event.isTask, "Event durationEditable in dict does not match expected value based on isTask")
        self.assertEqual(event_dict.get('extendedProps', {}).get('location'), event.location, "Event location in extendedProps does not match Event location")
        self.assertEqual(event_dict.get('extendedProps', {}).get('description'), event.description, "Event description in extendedProps does not match Event description")
        self.assertEqual(event_dict.get('extendedProps', {}).get('isTask'), event.isTask, "Event isTask in extendedProps does not match Event isTask")
        self.assertEqual(event_dict.get('extendedProps', {}).get('taskStatus'), event.taskStatus.value if event.taskStatus else None, "Event taskStatus in extendedProps does not match Event taskStatus value")
        self.assertEqual(event_dict.get('extendedProps', {}).get('owner'), event.owner, "Event owner in extendedProps does not match Event owner")

    def test_users_are_accepted_friends(self):
        self.assertTrue(
            users_are_accepted_friends("friendA@example.com", "friendB@example.com")
        )
        self.assertFalse(
            users_are_accepted_friends("testuser@example.com", "testuser2@example.com")
        )


class TestHelperFunctions(TestCase):
    def test_normalise_email(self):
        email = "  TEST@EXAMPLE.COM  "
        result = normalise_email(email)
        self.assertEqual(
            result,
            "test@example.com"
        )

    def test_normalise_username(self):
        username = "   Hongshen   "
        result = normalise_username(username)
        self.assertEqual(
            result,
            "Hongshen"
        )

    def test_parse_iso_datetime(self):
        value = "2026-05-14T10:30:00"
        result = parse_iso_datetime(value)
        self.assertEqual(
            result,
            datetime(2026, 5, 14, 10, 30)
        )
    
    def test_format_datetime(self):
        dt = datetime(2026, 5, 14, 9, 5)
        self.assertEqual(format_datetime(dt), "May 14, 2026 9:05 AM")

    def test_parse_iso_datetime_handles_z_suffix_and_invalid_values(self):
        self.assertEqual(
            parse_iso_datetime("2026-05-14T10:30:00Z"),
            datetime(2026, 5, 14, 10, 30)
        )
        self.assertIsNone(parse_iso_datetime("not-a-datetime"))

    def test_merge_busy_intervals(self):
        intervals = [
            (
                datetime(2026, 5, 14, 10, 0),
                datetime(2026, 5, 14, 11, 0)
            ),
            (
                datetime(2026, 5, 14, 10, 30),
                datetime(2026, 5, 14, 12, 0)
            )
        ]
        result = merge_busy_intervals(intervals)
        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0][0],
            datetime(2026, 5, 14, 10, 0)
        )
        self.assertEqual(
            result[0][1],
            datetime(2026, 5, 14, 12, 0)
        )
    
    def test_generate_common_free_slots(self):
        # Test data: 8-9 am, 10-12 pm, 3-4 pm on single day
        start_range = datetime(2026, 5, 14, 0, 0)
        end_range = datetime(2026, 5, 14, 23, 59)
        busy_events = [
            {
                'start_dt': datetime(2026, 5, 14, 8, 0),
                'end_dt': datetime(2026, 5, 14, 9, 0)
            },
            {
                'start_dt': datetime(2026, 5, 14, 10, 0),
                'end_dt': datetime(2026, 5, 14, 12, 0)
            },
            {
                'start_dt': datetime(2026, 5, 14, 15, 0),
                'end_dt': datetime(2026, 5, 14, 16, 0)
            }
        ]
        free_slots = generate_common_free_slots(start_range, end_range, busy_events)
        # Expected free slots are 9-10 am, 12 pm-3 pm, 5-8 pm
        self.assertEqual(len(free_slots), 3)
        self.assertEqual(free_slots[0]['start'], datetime(2026, 5, 14, 9, 0).isoformat())
        self.assertEqual(free_slots[0]['end'], datetime(2026, 5, 14, 10, 0).isoformat())
        self.assertEqual(free_slots[1]['start'], datetime(2026, 5, 14, 12, 0).isoformat())
        self.assertEqual(free_slots[1]['end'], datetime(2026, 5, 14, 15, 0).isoformat())
        self.assertEqual(free_slots[2]['start'], datetime(2026, 5, 14, 16, 0).isoformat())
        self.assertEqual(free_slots[2]['end'], datetime(2026, 5, 14, 20, 0).isoformat())
