from unittest import TestCase
from datetime import datetime

from app import create_app, db
from app.config import TestConfig
from app.models import User, Friendship, Event, TaskStatus, create_test_data


class UnitTests(TestCase):
    def setUp(self):
        testApp = create_app(TestConfig)
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
