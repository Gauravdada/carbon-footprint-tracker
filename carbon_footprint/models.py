from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    full_name     = db.Column(db.String(100), nullable=True)
    city          = db.Column(db.String(50),  nullable=True)
    family_size   = db.Column(db.Integer,     default=1)

    password_hash = db.Column(db.String(256), nullable=True)

    google_id     = db.Column(db.String(100), nullable=True, unique=True)
    profile_pic   = db.Column(db.String(300), nullable=True)

    # ── Email verification ────────────────────────────────────────
    is_verified   = db.Column(db.Boolean, default=False)

    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, nullable=True)
    onboarding_done = db.Column(db.Boolean,  default=False)

    activity_logs = db.relationship("ActivityLog", backref="user", lazy=True,
                                    cascade="all, delete-orphan")
    calculations  = db.relationship("Calculation", backref="user", lazy=True,
                                    cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    log_date        = db.Column(db.Date, default=datetime.utcnow().date)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    car_petrol_km       = db.Column(db.Float, default=0.0)
    car_diesel_km       = db.Column(db.Float, default=0.0)
    two_wheeler_km      = db.Column(db.Float, default=0.0)
    public_transport_km = db.Column(db.Float, default=0.0)
    air_travel_km       = db.Column(db.Float, default=0.0)

    electricity_kwh = db.Column(db.Float, default=0.0)
    lpg_kg          = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<ActivityLog user={self.user_id} date={self.log_date}>"


class Calculation(db.Model):
    __tablename__ = "calculations"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_log_id = db.Column(db.Integer, db.ForeignKey("activity_logs.id"), nullable=True)

    calc_date       = db.Column(db.DateTime, default=datetime.utcnow)

    transport_co2   = db.Column(db.Float, default=0.0)
    home_co2        = db.Column(db.Float, default=0.0)
    total_co2       = db.Column(db.Float, default=0.0)
    family_co2      = db.Column(db.Float, default=0.0)
    city_percentile = db.Column(db.Float, default=50.0)

    def __repr__(self):
        return f"<Calculation user={self.user_id} total={self.total_co2}kg>"