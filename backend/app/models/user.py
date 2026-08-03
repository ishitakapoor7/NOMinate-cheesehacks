from datetime import datetime

from app.extensions import db


class User(db.Model):
    """An account. Either email/password, Google, or both.

    password_hash is null for Google-only accounts; google_sub is null for
    email/password-only accounts.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True, index=True)
    avatar_url = db.Column(db.String(1024), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    profile = db.relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    ratings = db.relationship(
        "Rating", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations = db.relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email}>"
