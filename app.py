from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__, instance_relative_config=True)

app.config.from_mapping(
    SECRET_KEY='a_new_strong_secret_key_for_sessions',
    SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'events.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER='static/profile_pics' # New upload folder configuration
)

# Ensure required directories exist (instance for SQLite, upload folder for profile pics)
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    profile_pic = db.Column(db.String(120), nullable=True, default='default_profile_pic.png') # New profile picture column

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Event(db.Model):
    event_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='events', lazy=True)
    title = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    allocations = db.relationship('EventResourceAllocation', backref='event', lazy=True)

    def __repr__(self):
        return f"<Event {self.title}>"

class Resource(db.Model):
    resource_id = db.Column(db.Integer, primary_key=True)
    resource_name = db.Column(db.String(100), nullable=False, unique=True)
    resource_type = db.Column(db.String(50), nullable=False) # e.g., 'room', 'instructor', 'equipment'
    allocations = db.relationship('EventResourceAllocation', backref='resource', lazy=True)

    def __repr__(self):
        return f"<Resource {self.resource_name} ({self.resource_type})>"

class EventResourceAllocation(db.Model):
    allocation_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.event_id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.resource_id'), nullable=False)

    def __repr__(self):
        return f"<Allocation {self.allocation_id}: Event {self.event_id} - Resource {self.resource_id}>"

# Context processor to make User model available in all templates
@app.context_processor
def inject_user():
    return dict(User=User)

def check_resource_conflict(resource_id, new_start_time, new_end_time, event_id=None):
    """
    Checks for resource conflicts with existing allocations.
    Returns a list of conflicting events or an empty list if no conflicts.
    """
    conflicting_allocations = EventResourceAllocation.query.filter_by(resource_id=resource_id).join(Event).filter(
        Event.end_time > new_start_time,
        Event.start_time < new_end_time
    )
    if event_id:
        conflicting_allocations = conflicting_allocations.filter(Event.event_id != event_id)
    return conflicting_allocations.all()

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html')

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('logout'))

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        mobile = request.form.get('mobile', '').strip()
        address = request.form.get('address', '').strip()

        if not new_username:
            flash('Username cannot be empty.', 'danger')
            return redirect(url_for('profile'))

        # Update username if changed and still unique
        if new_username != user.username:
            existing = User.query.filter_by(username=new_username).first()
            if existing:
                flash('That username is already taken. Please choose another.', 'danger')
                return redirect(url_for('profile'))
            user.username = new_username
            session['username'] = new_username

        # Store personal details in the session so they show on the profile page
        session['mobile'] = mobile
        session['address'] = address

        db.session.commit()
        flash('Profile details updated successfully.', 'success')
        return redirect(url_for('profile'))

    user_events = Event.query.filter_by(user_id=session['user_id']).all()
    return render_template(
        'profile.html',
        user=user,
        user_events=user_events,
        mobile=session.get('mobile', ''),
        address=session.get('address', '')
    )


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('profile'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('profile'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user = User.query.get(session['user_id'])
        if user.profile_pic and user.profile_pic != 'default_profile_pic.png': # Delete old picture if not default
            try:
                os.remove(os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], user.profile_pic))
            except OSError:
                pass # Ignore if file doesn't exist

        file.save(os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], filename))
        user.profile_pic = filename
        db.session.commit()
        flash('Profile picture updated successfully!', 'success')
    else:
        flash('Allowed image types are png, jpg, jpeg, gif', 'danger')
    return redirect(url_for('profile'))


@app.route('/events')
def list_events():
    events = Event.query.all()
    return render_template('events.html', events=events)


@app.route('/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    if request.method == 'POST':
        title = request.form['title']
        start_time_str = request.form['start_time']
        end_time_str = request.form['end_time']
        description = request.form['description']

        try:
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            flash('Invalid date/time format. Please use YYYY-MM-DDTHH:MM.', 'danger')
            return render_template('event_form.html', event=None)

        if start_time >= end_time:
            flash('Start time must be before end time.', 'danger')
            return render_template('event_form.html', event=None)

        new_event = Event(title=title, start_time=start_time, end_time=end_time, description=description, user_id=session['user_id'])
        db.session.add(new_event)
        db.session.commit()
        flash('Event added successfully!', 'success')
        return redirect(url_for('list_events'))
    return render_template('event_form.html', event=None)


@app.route('/events/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.user_id != session['user_id']:
        flash('You are not authorized to edit this event.', 'danger')
        return redirect(url_for('list_events'))
    if request.method == 'POST':
        original_start_time = event.start_time
        original_end_time = event.end_time

        event.title = request.form['title']
        try:
            event.start_time = datetime.fromisoformat(request.form['start_time'])
            event.end_time = datetime.fromisoformat(request.form['end_time'])
        except ValueError:
            flash('Invalid date/time format. Please use YYYY-MM-DDTHH:MM.', 'danger')
            return render_template('event_form.html', event=event)

        if event.start_time >= event.end_time:
            flash('Start time must be before end time.', 'danger')
            return render_template('event_form.html', event=event)

        # Check for conflicts if event time has changed
        if original_start_time != event.start_time or original_end_time != event.end_time:
            # Get all resources currently allocated to this event
            allocated_resources = [alloc.resource_id for alloc in event.allocations]
            for resource_id in allocated_resources:
                conflicts = check_resource_conflict(resource_id, event.start_time, event.end_time, event.event_id)
                if conflicts:
                    flash(f'Conflict detected for resource ID {resource_id} with updated event times!', 'danger')
                    # Revert changes for now, or implement a more sophisticated conflict resolution
                    db.session.rollback()
                    flash('Event update rolled back due to conflict.', 'danger')
                    return render_template('event_form.html', event=event)

        event.description = request.form['description']
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('list_events'))
    return render_template('event_form.html', event=event)

@app.route('/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.user_id != session['user_id']:
        flash('You are not authorized to delete this event.', 'danger')
        return redirect(url_for('list_events'))
    # Delete all associated allocations first
    EventResourceAllocation.query.filter_by(event_id=event.event_id).delete()
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('list_events'))

# Resources

@app.route('/resources')
def list_resources():
    resources = Resource.query.all()
    return render_template('resources.html', resources=resources)

@app.route('/resources/add', methods=['GET', 'POST'])
def add_resource():
    if request.method == 'POST':
        resource_name = request.form['resource_name']
        resource_type = request.form['resource_type']
        new_resource = Resource(resource_name=resource_name, resource_type=resource_type)
        db.session.add(new_resource)
        db.session.commit()
        flash('Resource added successfully!', 'success')
        return redirect(url_for('list_resources'))
    return render_template('resource_form.html', resource=None)

@app.route('/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    if request.method == 'POST':
        resource.resource_name = request.form['resource_name']
        resource.resource_type = request.form['resource_type']
        db.session.commit()
        flash('Resource updated successfully!', 'success')
        return redirect(url_for('list_resources'))
    return render_template('resource_form.html', resource=resource)


@app.route('/allocate', methods=['GET', 'POST'])
def allocate_resource():
    if request.method == 'POST':
        event_id = request.form['event_id']
        resource_id = request.form['resource_id']

        event = Event.query.get_or_404(event_id)
        resource = Resource.query.get_or_404(resource_id)

        # Check for conflicts
        conflicts = check_resource_conflict(resource.resource_id, event.start_time, event.end_time, event.event_id)
        if conflicts:
            flash(f'Conflict detected for resource {resource.resource_name}! Already booked by:', 'danger')
            for conflict_alloc in conflicts:
                flash(f'- Event: {conflict_alloc.event.title} ({conflict_alloc.event.start_time} to {conflict_alloc.event.end_time})', 'danger')
            return redirect(url_for('allocate_resource'))

        existing_allocation = EventResourceAllocation.query.filter_by(event_id=event_id, resource_id=resource_id).first()
        if existing_allocation:
            flash('Resource already allocated to this event.', 'warning')
        else:
            allocation = EventResourceAllocation(event_id=event_id, resource_id=resource_id)
            db.session.add(allocation)
            db.session.commit()
            flash('Resource allocated successfully!', 'success')
        return redirect(url_for('list_events'))

    events = Event.query.all()
    resources = Resource.query.all()
    allocations = EventResourceAllocation.query.all()
    return render_template('allocate_resource.html', events=events, resources=resources, allocations=allocations)


@app.route('/report/utilization', methods=['GET', 'POST'])
def resource_utilization_report():
    report_data = []
    start_date = None
    end_date = None

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        try:
            if start_date_str: start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            if end_date_str: end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('resource_utilization_report.html', report_data=[], start_date=None, end_date=None)

    resources = Resource.query.all()
    for resource in resources:
        total_hours_utilized = 0
        upcoming_bookings = []

        allocations = EventResourceAllocation.query.filter_by(resource_id=resource.resource_id).join(Event).all()

        for allocation in allocations:
            event = allocation.event
            # Filter by date range if provided
            if start_date and event.end_time < start_date:
                continue
            if end_date and event.start_time > end_date:
                continue

            # Calculate overlap for total hours utilized
            if start_date and end_date:
                overlap_start = max(event.start_time, start_date)
                overlap_end = min(event.end_time, end_date)
            elif start_date:
                overlap_start = max(event.start_time, start_date)
                overlap_end = event.end_time
            elif end_date:
                overlap_start = event.start_time
                overlap_end = min(event.end_time, end_date)
            else:
                overlap_start = event.start_time
                overlap_end = event.end_time

            if overlap_start < overlap_end:
                duration = (overlap_end - overlap_start).total_seconds() / 3600
                total_hours_utilized += duration

            # Upcoming bookings (from now onwards)
            if event.end_time > datetime.now():
                upcoming_bookings.append(event)

        report_data.append({
            'resource_name': resource.resource_name,
            'resource_type': resource.resource_type,
            'total_hours_utilized': round(total_hours_utilized, 2),
            'upcoming_bookings': upcoming_bookings
        })

    return render_template('resource_utilization_report.html', report_data=report_data, start_date=start_date, end_date=end_date)


def create_sample_data():
    from app import db, app, User, Resource, Event, EventResourceAllocation # Import inside function to avoid circular imports
    with app.app_context():
        db.create_all()

        # Create a default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', profile_pic='default_profile_pic.png')
            admin_user.set_password('adminpass') # Change this password in production!
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user 'admin' created with password 'adminpass'")
        else:
            admin_user = User.query.filter_by(username='admin').first()

        # Create resources
        resource1 = Resource(resource_name='Room A', resource_type='room')
        resource2 = Resource(resource_name='Instructor John', resource_type='instructor')
        resource3 = Resource(resource_name='Projector 1', resource_type='equipment')
        resource4 = Resource(resource_name='Room B', resource_type='room')

        db.session.add_all([resource1, resource2, resource3, resource4])
        db.session.commit()

        # Create events with overlapping times, associated with admin_user
        event1 = Event(title='Workshop A', start_time=datetime(2025, 12, 25, 9, 0), end_time=datetime(2025, 12, 25, 11, 0), description='Introductory workshop on Flask.', user=admin_user)
        event2 = Event(title='Seminar B', start_time=datetime(2025, 12, 25, 10, 0), end_time=datetime(2025, 12, 25, 12, 0), description='Advanced topics in SQLAlchemy.', user=admin_user)
        event3 = Event(title='Class C', start_time=datetime(2025, 12, 26, 14, 0), end_time=datetime(2025, 12, 26, 16, 0), description='Python web development basics.', user=admin_user)
        event4 = Event(title='Meeting D', start_time=datetime(2025, 12, 25, 11, 30), end_time=datetime(2025, 12, 25, 13, 0), description='Team sync up.', user=admin_user)
        
        db.session.add_all([event1, event2, event3, event4])
        db.session.commit()

        # Allocate some resources
        allocation1 = EventResourceAllocation(event=event1, resource=resource1) # Event 1 in Room A
        allocation2 = EventResourceAllocation(event=event2, resource=resource1) # Event 2 in Room A (conflict for testing)
        allocation3 = EventResourceAllocation(event=event1, resource=resource2) # Event 1 with Instructor John
        allocation4 = EventResourceAllocation(event=event4, resource=resource4) # Event 4 in Room B

        db.session.add_all([allocation1, allocation2, allocation3, allocation4])
        db.session.commit()

        print("Sample data created!")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Run this once to create sample data. Comment out after first run.
        # create_sample_data()
    app.run(debug=True)
