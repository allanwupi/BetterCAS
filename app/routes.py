from flask import flash, jsonify, redirect, render_template, request, url_for, make_response
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from app import db
from app.models import Event, TaskStatus, User
from app.forms import LoginForm, SignupForm
from datetime import datetime, time, timedelta
from icalendar import Calendar, Event as ICalEvent
from app.models import Event, TaskStatus, User, Friendship, FriendshipStatus
from app.blueprints import main


def normalise_email(email):
    return (email or '').strip().lower()


def normalise_username(username):
    return (username or '').strip()


@main.app_template_filter('format_datetime')
def format_datetime(dt):
    # "%-d", "%-I" is not supported on Windows, so we need to remove leading zeros manually
    day = dt.strftime("%d").lstrip("0")
    hour = dt.strftime("%I").lstrip("0")
    return f'{dt.strftime("%b")} {day}, {dt.strftime("%Y")} {hour}:{dt.strftime("%M")} {dt.strftime("%p")}'
    # equivalent to strftime("%b %-d, %Y %-I:%M %p") on Unix-based systems


@main.route('/', methods=['GET'])
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('main.calendar'))
    login_form = LoginForm()
    signup_form = SignupForm()
    return render_template(
        'landing.html',
        login_form=login_form,
        signup_form=signup_form
    )


@main.route('/signup', methods=['POST'])
def signup():

    if current_user.is_authenticated:
        return redirect(url_for('main.calendar'))

    form = SignupForm()

    if not form.validate_on_submit():
        if not form.username.data or not form.email.data or not form.password.data:
            flash('Username, email, and password are required.', 'danger')
        elif '@' not in form.email.data or '.' not in form.email.data:
            flash('Please enter a valid email address.', 'danger')
        elif len(form.password.data) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
        elif form.password.data != form.confirm_password.data:
            flash('Passwords do not match.', 'danger')
        else:
            flash('Please check your sign up details and try again.', 'danger')
        return redirect(url_for('main.landing'))

    username = normalise_username(form.username.data)
    email = normalise_email(form.email.data)
    password = form.password.data

    existing_user = db.session.query(User).filter(
        or_(
            User.email == email,
            User.username == username
        )
    ).first()

    if existing_user:
        if existing_user.email == email:
            flash('An account with that email already exists.', 'danger')
        else:
            flash('That username is already taken.', 'danger')
        return redirect(url_for('main.landing'))

    user = User(
        email=email,
        username=username
    )

    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash('Account created successfully.', 'success')

    return redirect(url_for('main.calendar'))


@main.route('/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.calendar'))

    form = LoginForm()

    if not form.validate_on_submit():
        flash('Invalid form submission. Please try again.','danger')
        return redirect(url_for('main.landing'))

    identifier = form.identifier.data.strip()
    password = form.password.data or ''
    remember = form.remember.data

    user = db.session.query(User).filter(
        or_(
            User.email == identifier.lower(),
            User.username == identifier
        )
    ).first()

    if not user or not user.check_password(password):
        flash('Invalid login details. Please try again.','danger')
        return redirect(url_for('main.landing'))

    login_user(user, remember=remember)

    flash('Logged in successfully.','success')

    return redirect(url_for('main.calendar'))


@main.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.landing'))


@main.route('/calendar', methods=['GET'])
@login_required
def calendar():
    return render_template('calendar-page.html', calendar_active=True)


@main.route('/todo', methods=['GET'])
@login_required
def to_do_list():
    tasks = (
        db.session.query(Event)
        .filter_by(isTask=True, owner=current_user.email)
        .order_by(Event.start.asc())
        .all()
    )
    return render_template('todo-page.html', todo_active=True, tasks=tasks)


@main.route('/friends', methods=['GET'])
@login_required
def friends():
    return render_template('friends-page.html', friends_active=True)


@main.route('/import', methods=['GET'])
@login_required
def imported_calendars():
    return render_template('import-page.html', import_active=True)


@main.route('/upload', methods=['POST'])
@login_required
def upload():

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if not file or file.filename == '':
        return jsonify({"error": "No file provided"}), 400

    if not file.filename.lower().endswith('.ics'):
        return jsonify({"error": "Invalid file type"}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size > 1_000_000:
        return jsonify({"error": "File too large"}), 400
    
    try:
        cal = Calendar.from_ical(file.read())
    except Exception:
        return jsonify({"error": "Invalid ICS format"}), 400

    seen = set()
    events = []
    count = 0
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        try:
            uid = str(component.get('uid', ''))
            if not uid or uid in seen:
                continue
            seen.add(uid)

            dtstart = component.get('dtstart')
            if not dtstart:
                continue

            start = dtstart.dt

            if not hasattr(start, 'isoformat'):
                continue

            dtend = component.get('dtend')
            end = dtend.dt if dtend else None

            if end and end < start:
                end = start

            title = str(component.get('summary', 'Untitled Event'))[:255]
            location = str(component.get('location', ''))[:255]
            description = str(component.get('description', ''))[:1000]

            event = Event(
                title=title,
                start=start,
                end=end,
                backgroundColor=component.get('color', '#6366f1'),
                location=location,
                description=description,
                owner=current_user.email
            )

            db.session.add(event)
            events.append(event)
            count += 1

        except Exception:
            continue

    if count == 0:
        return jsonify({"error": "No valid events found in file"}), 400

    db.session.commit()

    return jsonify({
        "message": "Import successful",
        "count": count,
        "events": [e.to_dict() for e in events]
    }), 200

@main.route('/export/ics', methods=['GET'])
@login_required
def export_ics():
    cal = Calendar()
    cal.add('prodid', '-//My Calendar Export//')
    cal.add('version', '2.0')

    events = Event.query.filter_by(owner=current_user.email).all()

    if not events:
        return jsonify({'error': 'No events to export'}), 400

    for e in events:
        ical_event = ICalEvent()

        ical_event.add('summary', e.title)

        # Ensure datetime objects (adjust if stored differently)
        ical_event.add('dtstart', e.start)
        if e.end:
            ical_event.add('dtend', e.end)

        if e.location:
            ical_event.add('location', e.location)

        if e.description:
            ical_event.add('description', e.description)

        ical_event.add('dtstamp', datetime.utcnow())

        # Unique ID helps calendar apps deduplicate
        ical_event.add('uid', f"{e.id}@myapp")

        cal.add_component(ical_event)

    ics_data = cal.to_ical()

    response = make_response(ics_data)
    response.headers['Content-Type'] = 'text/calendar'
    response.headers['Content-Disposition'] = 'attachment; filename=calendar.ics'

    return response

 
@main.route('/get-events', methods=['GET'])
@login_required
def get_events():
    events = db.session.query(Event).filter_by(owner=current_user.email).all()
    return jsonify([event.to_dict() for event in events]), 200


@main.route('/save/<dtype>', methods=['POST'])
@login_required
def save_event_task(dtype):
    """Save a new event or task to the database with server-side validation.
    Note that the request MUST specify all required parameters for an event/task."""
    try:
        data = request.get_json()
        provided_id = data.get('id')
        # Try to interpret provided ID as an integer (FullCalendar may send strings)
        try:
            provided_id = int(provided_id) if provided_id is not None else None
        except (ValueError, TypeError):
            provided_id = None
        if (dtype == 'task'):
            if not data.get('start'):
                return jsonify({'error': 'Due date is required for tasks'}), 400
            try:
                # FullCalendar will not store the end date for tasks, so we must access the start date
                # This is the same as the end date for tasks which we define as only having a due date
                end = datetime.fromisoformat(data['start'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid date/time format for due date'}), 400
            
            status = data.get('taskStatus', data.get('extendedProps', {}).get('taskStatus'))
            valid_statuses = [status.value for status in TaskStatus]
            if status not in valid_statuses:
                return jsonify({'error': f'Invalid status {status}. Must be one of: {", ".join(valid_statuses)}'}), 400
            
            # If an existing event/task with the provided ID exists, update it
            event = None
            if provided_id is not None:
                event = db.session.query(Event).filter_by(id=provided_id).first()

            if event:
                event.title = data.get('title', event.title).strip()
                event.start = end
                event.end = end
                event.backgroundColor = data.get('backgroundColor', event.backgroundColor)
                event.isTask = True
                event.taskStatus = TaskStatus(status)
            else:
                # Create new task (do NOT set the primary key manually)
                event = Event(
                    title=data['title'].strip(),
                    start=end,
                    end=end,
                    backgroundColor=data.get('backgroundColor', '#6366f1'),
                    isTask=True,
                    taskStatus=TaskStatus(status),
                    owner=current_user.email
                )
        elif (dtype == 'event'): # Create a regular event
            # Server-side validation for events
            if not data.get('title') or not data['title'].strip():
                return jsonify({'error': 'Event title is required'}), 400
            if not data.get('start'):
                return jsonify({'error': 'Start date/time is required'}), 400
            if not data.get('end'):
                return jsonify({'error': 'End date/time is required'}), 400
            
            try:
                start = datetime.fromisoformat(data['start'])
                end = datetime.fromisoformat(data['end'])
                
                if end < start:
                    return jsonify({'error': 'End date/time cannot be before start date/time'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid date/time format'}), 400
            
            # If an existing event with the provided ID exists, update it
            event = None
            if provided_id is not None:
                event = db.session.query(Event).filter_by(id=provided_id).first()

            if event:
                event.title = data['title'].strip()
                event.start = start
                event.end = end
                event.backgroundColor = data.get('backgroundColor', event.backgroundColor)
                event.location = (data.get('location') or data.get('extendedProps', {}).get('location') or '').strip() or None
                event.description = (data.get('description') or data.get('extendedProps', {}).get('description') or '').strip() or None
                event.isTask = False
                event.taskStatus = None
            else:
                event = Event(
                    title=data['title'].strip(),
                    start=start,
                    end=end,
                    backgroundColor=data.get('backgroundColor', '#6366f1'),
                    location=data.get('location', data.get('extendedProps', {}).get('location', '')).strip() or None,
                    description=data.get('description', data.get('extendedProps', {}).get('description', '')).strip() or None,
                    owner=current_user.email
                )
        else:
            return jsonify({'error': f'Invalid data type: {dtype}'}), 400
        # Add new events to the session; existing events are already tracked
        if event.id is None:
            db.session.add(event)
            db.session.commit()
            return jsonify(event.to_dict()), 201
        else:
            db.session.commit()
            return jsonify(event.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({'error': 'Internal Server Error'}), 500


@main.route('/update-task-status', methods=['POST'])
@login_required
def update_task_status():
    """Updates the status of a task (request should only contain the task ID and new status)."""
    try:
        data = request.get_json() or {}
        task_id = data.get('id')
        new_status = data.get('status')

        if not task_id:
            return jsonify({'error': 'Task ID is required'}), 400
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400

        valid_statuses = [status.value for status in TaskStatus]
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400

        task = db.session.query(Event).filter_by(id=task_id, isTask=True, owner=current_user.email).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        task.taskStatus = TaskStatus(new_status)
        db.session.commit()
        return jsonify(task.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({'error': 'Internal Server Error'}), 500


@main.route('/delete-event', methods=['POST'])
@login_required
def delete():
    """Delete an event/task from the database."""
    try:
        data = request.get_json() or {}
        event_id = data.get('id')

        if not event_id:
            return jsonify({'error': 'Event ID is required'}), 400

        event = db.session.query(Event).filter_by(id=event_id, owner=current_user.email).first()
        if not event:
            return jsonify({'error': 'Event not found'}), 404

        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': 'Event deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({'error': 'Internal Server Error'}), 500


@main.route('/api/friends/search', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '').strip()

    if not query:
        return jsonify([])

    users = User.query.filter(
        User.email != current_user.email,
        or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        )
    ).all()

    results = []

    for user in users:
        existing_friendship = Friendship.query.filter(
            or_(
                db.and_(
                    Friendship.requester_email == current_user.email,
                    Friendship.receiver_email == user.email
                ),
                db.and_(
                    Friendship.requester_email == user.email,
                    Friendship.receiver_email == current_user.email
                )
            )
        ).first()

        friendship_status = None

        if existing_friendship:
            friendship_status = existing_friendship.status.value

        results.append({
            'email': user.email,
            'username': user.username,
            'friendship_status': friendship_status
        })

    return jsonify(results)


@main.route('/api/friends/send-request', methods=['POST'])
@login_required
def send_friend_request():
    data = request.get_json()

    receiver_email = data.get('receiver_email')

    if receiver_email == current_user.email:
        return jsonify({'error': 'You cannot add yourself'}), 400

    receiver = User.query.get(receiver_email)

    if not receiver:
        return jsonify({'error': 'User not found'}), 404

    existing_friendship = Friendship.query.filter(
        or_(
            db.and_(
                Friendship.requester_email == current_user.email,
                Friendship.receiver_email == receiver_email
            ),
            db.and_(
                Friendship.requester_email == receiver_email,
                Friendship.receiver_email == current_user.email
            )
        )
    ).first()

    if existing_friendship:
        return jsonify({'error': 'Friend request already exists'}), 400

    friendship = Friendship(
        requester_email=current_user.email,
        receiver_email=receiver_email,
        status=FriendshipStatus.PENDING
    )

    db.session.add(friendship)
    db.session.commit()

    return jsonify({
        'message': 'Friend request sent successfully'
    })


@main.route('/api/friends/accept-request/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend_request(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)

    if friendship.receiver_email != current_user.email:
        return jsonify({'error': 'Unauthorized'}), 403

    friendship.status = FriendshipStatus.ACCEPTED

    db.session.commit()

    return jsonify({
        'message': 'Friend request accepted'
    })


@main.route('/api/friends/reject-request/<int:friendship_id>', methods=['POST'])
@login_required
def reject_friend_request(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)

    if friendship.receiver_email != current_user.email:
        return jsonify({'error': 'Unauthorized'}), 403

    friendship.status = FriendshipStatus.REJECTED

    db.session.commit()

    return jsonify({
        'message': 'Friend request rejected'
    })


@main.route('/api/friends/remove/<int:friendship_id>', methods=['DELETE'])
@login_required
def remove_friend(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)

    if (
        friendship.requester_email != current_user.email and
        friendship.receiver_email != current_user.email
    ):
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(friendship)
    db.session.commit()

    return jsonify({
        'message': 'Friend removed successfully'
    })


@main.route('/api/friends/list', methods=['GET'])
@login_required
def get_friends_list():
    friendships = Friendship.query.filter(
        or_(
            Friendship.requester_email == current_user.email,
            Friendship.receiver_email == current_user.email
        )
    ).all()

    accepted_friends = []
    pending_sent = []
    pending_received = []

    for friendship in friendships:
        if friendship.status == FriendshipStatus.ACCEPTED:
            friend_email = (
                friendship.receiver_email
                if friendship.requester_email == current_user.email
                else friendship.requester_email
            )

            friend = db.session.get(User, friend_email)

            accepted_friends.append({
                'friendship_id': friendship.id,
                'email': friend.email,
                'username': friend.username
            })

        elif friendship.status == FriendshipStatus.PENDING:
            if friendship.requester_email == current_user.email:
                receiver = User.query.get(friendship.receiver_email)

                pending_sent.append({
                    'friendship_id': friendship.id,
                    'email': receiver.email,
                    'username': receiver.username
                })

            elif friendship.receiver_email == current_user.email:
                requester = db.session.get(User, friendship.requester_email)

                pending_received.append({
                    'friendship_id': friendship.id,
                    'email': requester.email,
                    'username': requester.username
                })

    return jsonify({
        'friends': accepted_friends,
        'pending_sent': pending_sent,
        'pending_received': pending_received
    })

def parse_iso_datetime(value):
    """Parse ISO datetime sent from the browser."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        return None


def users_are_accepted_friends(user_email, friend_email):
    """Check that two users are accepted friends."""
    return Friendship.query.filter(
        Friendship.status == FriendshipStatus.ACCEPTED,
        or_(
            db.and_(
                Friendship.requester_email == user_email,
                Friendship.receiver_email == friend_email
            ),
            db.and_(
                Friendship.requester_email == friend_email,
                Friendship.receiver_email == user_email
            )
        )
    ).first() is not None


def merge_busy_intervals(intervals):
    """Merge overlapping busy time intervals."""
    if not intervals:
        return []

    intervals.sort(key=lambda interval: interval[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def generate_common_free_slots(start_range, end_range, busy_events):
    """Generate common free slots between 8am and 8pm."""
    free_slots = []
    current_day = start_range.date()
    final_day = end_range.date()

    while current_day <= final_day:
        day_start = datetime.combine(current_day, time(hour=8))
        day_end = datetime.combine(current_day, time(hour=20))

        clipped_intervals = []

        for event in busy_events:
            event_start = event['start_dt']
            event_end = event['end_dt']

            if event_end <= day_start or event_start >= day_end:
                continue

            clipped_intervals.append((
                max(event_start, day_start),
                min(event_end, day_end)
            ))

        merged_busy = merge_busy_intervals(clipped_intervals)
        cursor = day_start

        for busy_start, busy_end in merged_busy:
            if busy_start > cursor and busy_start - cursor >= timedelta(minutes=30):
                free_slots.append({
                    'title': 'Everyone free',
                    'start': cursor.isoformat(),
                    'end': busy_start.isoformat(),
                    'display': 'background',
                    'backgroundColor': '#bbf7d0'
                })

            cursor = max(cursor, busy_end)

        if day_end > cursor and day_end - cursor >= timedelta(minutes=30):
            free_slots.append({
                'title': 'Everyone free',
                'start': cursor.isoformat(),
                'end': day_end.isoformat(),
                'display': 'background',
                'backgroundColor': '#bbf7d0'
            })

        current_day += timedelta(days=1)

    return free_slots


@main.route('/api/friends/availability', methods=['POST'])
@login_required
def get_friend_availability():
    data = request.get_json() or {}

    selected_friend_emails = data.get('friend_emails', [])
    range_start = parse_iso_datetime(data.get('start'))
    range_end = parse_iso_datetime(data.get('end'))

    if not isinstance(selected_friend_emails, list):
        return jsonify({'error': 'friend_emails must be a list'}), 400

    if not range_start or not range_end:
        return jsonify({'error': 'Start and end date range are required'}), 400

    if range_end <= range_start:
        return jsonify({'error': 'End date range must be after start date range'}), 400

    if len(selected_friend_emails) > 3:
        return jsonify({'error': 'You can compare with a maximum of 3 friends'}), 400

    allowed_friend_emails = []

    for friend_email in selected_friend_emails:
        if not users_are_accepted_friends(current_user.email, friend_email):
            return jsonify({'error': f'{friend_email} is not an accepted friend'}), 403

        allowed_friend_emails.append(friend_email)

    calendar_owners = [current_user.email] + allowed_friend_emails

    events = Event.query.filter(
        Event.owner.in_(calendar_owners),
        Event.end >= range_start,
        Event.start <= range_end
    ).all()

    users_by_email = {
        user.email: user
        for user in User.query.filter(User.email.in_(calendar_owners)).all()
    }

    busy_events = []

    for event in events:
        owner = users_by_email.get(event.owner)
        owner_username = owner.username if owner else event.owner
        is_current_user_event = event.owner == current_user.email

        event_start = event.start
        event_end = event.end

        if event.isTask:
            event_end = event_start + timedelta(hours=1)

        if event_end <= range_start or event_start >= range_end:
            continue

        busy_events.append({
            'title': event.title if is_current_user_event else f'Busy - @{owner_username}',
            'start': event_start.isoformat(),
            'end': event_end.isoformat(),
            'backgroundColor': '#f97316' if is_current_user_event else '#ef4444',
            'borderColor': '#ea580c' if is_current_user_event else '#dc2626',
            'extendedProps': {
                'owner': event.owner,
                'owner_username': owner_username,
                'is_current_user_event': is_current_user_event,
                'location': event.location if is_current_user_event else None,
                'description': event.description if is_current_user_event else None,
                'isTask': event.isTask
            },
            'start_dt': event_start,
            'end_dt': event_end
        })

    free_slots = generate_common_free_slots(range_start, range_end, busy_events)

    public_busy_events = []

    for event in busy_events:
        public_busy_events.append({
            'title': event['title'],
            'start': event['start'],
            'end': event['end'],
            'backgroundColor': event['backgroundColor'],
            'borderColor': event['borderColor'],
            'extendedProps': event['extendedProps']
        })

    return jsonify({
        'busy_events': public_busy_events,
        'free_slots': free_slots
    }), 200