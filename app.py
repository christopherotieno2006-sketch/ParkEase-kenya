from datetime import datetime
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='DRIVER', nullable=False)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True)

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    spaces = db.relationship('ParkingSpace', backref='lot', lazy=True, cascade='all, delete-orphan')

class ParkingSpace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    slot_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='AVAILABLE', nullable=False)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_number = db.Column(db.String(30), nullable=False)
    vehicle_type = db.Column(db.String(30), default='CAR', nullable=False)

class ParkingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)
    entry_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    exit_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    amount_due = db.Column(db.Integer)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)
    payment_status = db.Column(db.String(20), default='PENDING', nullable=False)
    vehicle = db.relationship('Vehicle')
    space = db.relationship('ParkingSpace')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('parking_session.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default='PAID', nullable=False)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    session = db.relationship('ParkingSession', backref=db.backref('payment', uselist=False))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != 'ADMIN':
            flash('Administrator access is required.', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped

def calculate_fee(minutes):
    if minutes <= 30:
        return 0
    if minutes <= 120:
        return 50
    if minutes <= 360:
        return 100
    return 300

def seed_data():
    if not User.query.filter_by(email='admin@parkease.co.ke').first():
        db.session.add(User(full_name='System Administrator', email='admin@parkease.co.ke', password_hash=generate_password_hash('Admin123!'), role='ADMIN'))
    if not ParkingLot.query.first():
        lot = ParkingLot(name='ParkEase Main Lot', address='Multimedia University of Kenya')
        db.session.add(lot)
        db.session.flush()
        for i in range(1, 13):
            db.session.add(ParkingSpace(lot_id=lot.id, slot_number=f'A{i:02}', floor=1))
    db.session.commit()

@app.route('/')
def home():
    return redirect(url_for('dashboard')) if current_user.is_authenticated else redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if not name or len(password) < 6:
            flash('Enter a name and a password of at least 6 characters.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
        else:
            user = User(full_name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.commit(); login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user); return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    spaces = ParkingSpace.query.order_by(ParkingSpace.slot_number).all()
    active = ParkingSession.query.filter_by(status='ACTIVE').order_by(ParkingSession.entry_time.desc()).all()
    return render_template('dashboard.html', spaces=spaces, active=active, available=sum(s.status == 'AVAILABLE' for s in spaces), occupied=sum(s.status == 'OCCUPIED' for s in spaces))

@app.route('/vehicles', methods=['GET', 'POST'])
@login_required
def vehicles():
    if request.method == 'POST':
        reg = request.form['registration_number'].strip().upper()
        if not reg:
            flash('Registration number is required.', 'danger')
        else:
            db.session.add(Vehicle(owner_id=current_user.id, registration_number=reg, vehicle_type=request.form.get('vehicle_type', 'CAR')))
            db.session.commit(); flash('Vehicle added.', 'success')
    return render_template('vehicles.html', vehicles=Vehicle.query.filter_by(owner_id=current_user.id).all())

@app.route('/park', methods=['GET', 'POST'])
@login_required
def park():
    if request.method == 'POST':
        vehicle = db.session.get(Vehicle, int(request.form['vehicle_id']))
        space = db.session.get(ParkingSpace, int(request.form['space_id']))
        if not vehicle or vehicle.owner_id != current_user.id:
            flash('Invalid vehicle.', 'danger')
        elif not space or space.status != 'AVAILABLE':
            flash('That slot is no longer available.', 'danger')
        elif ParkingSession.query.join(Vehicle).filter(Vehicle.owner_id == current_user.id, ParkingSession.status == 'ACTIVE').first():
            flash('You already have an active parking session.', 'danger')
        else:
            session = ParkingSession(vehicle_id=vehicle.id, space_id=space.id)
            space.status = 'OCCUPIED'; db.session.add(session); db.session.commit()
            flash('Vehicle parked successfully.', 'success'); return redirect(url_for('dashboard'))
    return render_template('park.html', vehicles=Vehicle.query.filter_by(owner_id=current_user.id).all(), spaces=ParkingSpace.query.filter_by(status='AVAILABLE').all())

@app.route('/checkout/<int:session_id>', methods=['GET', 'POST'])
@login_required
def checkout(session_id):
    session = db.session.get(ParkingSession, session_id)
    if not session or session.status != 'ACTIVE' or session.vehicle.owner_id != current_user.id:
        flash('Parking session not found.', 'danger'); return redirect(url_for('dashboard'))
    now = datetime.utcnow(); minutes = max(0, int((now - session.entry_time).total_seconds() // 60)); fee = calculate_fee(minutes)
    if request.method == 'POST':
        session.exit_time = now; session.duration_minutes = minutes; session.amount_due = fee; session.payment_status = 'PAID'; session.status = 'COMPLETED'; session.space.status = 'AVAILABLE'
        db.session.add(Payment(session_id=session.id, amount=fee, method=request.form.get('method', 'CASH'))); db.session.commit()
        return render_template('receipt.html', session=session, payment=session.payment)
    return render_template('checkout.html', session=session, minutes=minutes, fee=fee)

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html', lots=ParkingLot.query.all(), sessions=ParkingSession.query.order_by(ParkingSession.entry_time.desc()).all())

@app.route('/admin/spaces', methods=['POST'])
@admin_required
def add_space():
    lot = ParkingLot.query.first()
    if lot and request.form['slot_number'].strip():
        db.session.add(ParkingSpace(lot_id=lot.id, slot_number=request.form['slot_number'].strip().upper(), floor=1)); db.session.commit(); flash('Space added.', 'success')
    return redirect(url_for('admin'))

with app.app_context():
    db.create_all(); seed_data()

if __name__ == '__main__':
    app.run(debug=True)
