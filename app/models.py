from app import db
from datetime import datetime, UTC
import enum
from flask_login import UserMixin
from sqlalchemy import Enum
from werkzeug.security import generate_password_hash, check_password_hash

# Status of task
class TaskStatus(enum.Enum):
    NOT_STARTED = 'Not Started'
    IN_PROGRESS = 'In Progress'
    COMPLETED = 'Completed'

# Friendship request status
class FriendshipStatus(enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

# User model storing account information
class User(UserMixin, db.Model):
    # User email acts as the primary key
    email = db.Column(db.String(120), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    events = db.relationship('Event', backref='user', lazy=True)

    sent_requests = db.relationship(
        'Friendship',
        foreign_keys='Friendship.requester_email',
        backref='requester',
        lazy=True,
        cascade='all, delete-orphan'
    )

    received_requests = db.relationship(
        'Friendship',
        foreign_keys='Friendship.receiver_email',
        backref='receiver',
        lazy=True,
        cascade='all, delete-orphan'
    )

    # Flask-Login method used to uniquely identify users
    def get_id(self):
        return self.email

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Friendship model storing friend requests and relationships
class Friendship(db.Model):

    # Unique friendship/request ID initialised
    id = db.Column(db.Integer, primary_key=True)
    requester_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    receiver_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    status = db.Column(Enum(FriendshipStatus), nullable=False, default=FriendshipStatus.PENDING)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC) )

    def to_dict(self):
        return {
            'id': self.id,
            'requester_email': self.requester_email,
            'receiver_email': self.receiver_email,
            'status': self.status.value,
            'created_at': self.created_at.isoformat()
        }

# Event model storing both events and tasks
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    backgroundColor = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    isTask = db.Column(db.Boolean, default=False)
    taskStatus = db.Column(Enum(TaskStatus), nullable=True)
    owner = db.Column(db.String(120), db.ForeignKey(User.email), nullable=False)

    # Converts event object into dictionary format for FullCalendar/frontend
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'backgroundColor': self.backgroundColor,
            'durationEditable': not self.isTask,
            'extendedProps': {
                'location': self.location,
                'description': self.description,
                'isTask': self.isTask,
                'taskStatus': self.taskStatus.value if self.taskStatus else None,
                'owner': self.owner
            }
        }


def create_test_data():
    testUser = User(email="testuser@example.com", username="testuser")
    testUser.set_password("thisisatestpassword")
    testUser2 = User(email="testuser2@example.com", username="testuser2")
    testUser2.set_password("thisisanotherpassword")
    friendship = Friendship(
        requester_email=testUser.email,
        receiver_email=testUser2.email,
        status=FriendshipStatus.ACCEPTED
    )

    task1 = Event(
        title='Assignment Due',
        start=datetime(2026, 5, 25, 14, 0, 0),
        end=datetime(2026, 5, 25, 14, 0, 0),
        backgroundColor='#6366f1',
        location='UWA Library',
        description='Complete and submit the final assignment.',
        isTask=True,
        taskStatus=TaskStatus.COMPLETED,
        owner=testUser.email
    )

    task2 = Event(
        title='Study for Test',
        start=datetime(2026, 5, 20, 9, 0, 0),
        end=datetime(2026, 5, 20, 9, 0, 0),
        backgroundColor='#6366f1',
        location='Home',
        description='Review lecture notes and practice problems.',
        isTask=True,
        taskStatus=TaskStatus.IN_PROGRESS,
        owner=testUser.email
    )

    event1 = Event(
        title='Gym Session',
        start=datetime(2026, 5, 22, 16, 0, 0),
        end=datetime(2026, 5, 22, 18, 0, 0),
        backgroundColor='#6366f1',
        location='Campus Gym',
        description='Strength workout and cardio session.',
        owner=testUser.email
    )

    event2 = Event(
        title='Group Meeting',
        start=datetime(2026, 5, 23, 10, 0, 0),
        end=datetime(2026, 5, 23, 11, 0, 0),
        backgroundColor='#6366f1',
        location='Engineering Building',
        description='Project discussion with team members.',
        isTask=False,
        owner=testUser.email
    )

    db.session.add_all([testUser, testUser2, friendship])
    db.session.add_all([task1, task2, event1, event2])
    db.session.commit() 