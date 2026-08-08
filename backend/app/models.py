from sqlalchemy import (
    Column, Integer, String, Boolean, Float,
    ForeignKey, DateTime, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ─── Existing tables ──────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    users      = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    full_name     = Column(String(100), nullable=False)
    email         = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id       = Column(Integer, ForeignKey("roles.id"))
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    role            = relationship("Role", back_populates="users")
    learner_profile = relationship("LearnerProfile", back_populates="user")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"))
    learning_level      = Column(String(50))
    preferred_language  = Column(String(50))
    learning_goals      = Column(String)
    assessment_history  = Column(String)
    practice_statistics = Column(String)
    created_at          = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="learner_profile")


# ─── New: Practice Sessions ───────────────────────────────────────────────────

class PracticeSession(Base):
    """
    One session = learner clicks 'Start Practice' until they click 'End' or
    complete all selected alphabets.
    """
    __tablename__ = "practice_sessions"

    id                   = Column(Integer, primary_key=True, index=True)
    session_id           = Column(String(36), unique=True, index=True, nullable=False)
    student_id           = Column(String(100), nullable=False, index=True)

    # Timing
    start_time           = Column(DateTime, default=datetime.utcnow)
    end_time             = Column(DateTime, nullable=True)
    total_duration_secs  = Column(Float, default=0.0)

    # Attempt counters
    total_attempts       = Column(Integer, default=0)
    correct_attempts     = Column(Integer, default=0)
    incorrect_attempts   = Column(Integer, default=0)

    # Aggregates (updated after every attempt)
    session_accuracy     = Column(Float, default=0.0)
    avg_confidence       = Column(Float, default=0.0)
    avg_inference_time   = Column(Float, default=0.0)

    # Which letters were practiced (JSON list stored as Text)
    letters_practiced    = Column(Text, default="[]")

    status               = Column(String(20), default="active")  # active | completed
    created_at           = Column(DateTime, default=datetime.utcnow)

    # Relationships
    attempts = relationship("AssessmentAttempt", back_populates="session")
    summary  = relationship("SessionSummary",    back_populates="session", uselist=False)


# ─── New: Assessment Attempts ─────────────────────────────────────────────────

class AssessmentAttempt(Base):
    """
    Every single prediction+evaluation during a session is one attempt row.
    """
    __tablename__ = "assessment_attempts"

    id                 = Column(Integer, primary_key=True, index=True)
    attempt_id         = Column(String(36), unique=True, index=True, nullable=False)
    session_id         = Column(String(36), ForeignKey("practice_sessions.session_id"), nullable=False)
    student_id         = Column(String(100), nullable=False, index=True)

    target_letter      = Column(String(5),  nullable=False)
    predicted_letter   = Column(String(5),  nullable=False)
    is_correct         = Column(Boolean,    nullable=False)
    confidence         = Column(Float,      nullable=False)
    inference_time_ms  = Column(Float,      nullable=False)
    gesture_accuracy   = Column(Float,      default=0.0)

    # Validation metadata
    hand_detected      = Column(Boolean, default=True)
    frame_valid        = Column(Boolean, default=True)

    attempt_number     = Column(Integer, nullable=False)
    timestamp          = Column(DateTime, default=datetime.utcnow)

    session = relationship("PracticeSession", back_populates="attempts")


# ─── New: Per-Alphabet Learner State ─────────────────────────────────────────

class AlphabetState(Base):
    """
    State machine per (student, letter).

    States:  not_attempted → learning → improving → mastered → needs_revision

    Transition rules (applied after every completed session):
        not_attempted  → learning       : first attempt made
        learning       → improving      : accuracy >= 50% over last 5 attempts
        improving      → mastered       : accuracy >= 80% AND avg_confidence >= 0.75
                                          over last 10 attempts
        mastered       → needs_revision : 3+ consecutive incorrect after mastered
        needs_revision → improving      : accuracy >= 60% over next 5 attempts
    """
    __tablename__ = "alphabet_states"

    id                   = Column(Integer, primary_key=True, index=True)
    student_id           = Column(String(100), nullable=False, index=True)
    letter               = Column(String(5),   nullable=False)

    # Current state
    state                = Column(String(30), default="not_attempted")

    # Running stats
    total_attempts       = Column(Integer, default=0)
    correct_attempts     = Column(Integer, default=0)
    accuracy             = Column(Float,   default=0.0)
    avg_confidence       = Column(Float,   default=0.0)
    consecutive_correct  = Column(Integer, default=0)
    consecutive_incorrect= Column(Integer, default=0)

    # Confusion tracking (JSON: {"B": 3, "D": 1})
    confused_with        = Column(Text, default="{}")

    last_practiced       = Column(DateTime, nullable=True)
    state_changed_at     = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # History of state transitions (JSON list)
    state_history        = Column(Text, default="[]")

    history = relationship("AlphabetStateHistory", back_populates="alphabet_state")


class AlphabetStateHistory(Base):
    """Audit trail — every state transition is logged here."""
    __tablename__ = "alphabet_state_history"

    id             = Column(Integer, primary_key=True, index=True)
    alphabet_state_id = Column(Integer, ForeignKey("alphabet_states.id"))
    student_id     = Column(String(100), nullable=False)
    letter         = Column(String(5),   nullable=False)
    from_state     = Column(String(30),  nullable=False)
    to_state       = Column(String(30),  nullable=False)
    reason         = Column(String(255))
    transitioned_at= Column(DateTime, default=datetime.utcnow)

    alphabet_state = relationship("AlphabetState", back_populates="history")


# ─── New: Session Summary ─────────────────────────────────────────────────────

class SessionSummary(Base):
    """
    Generated once when a session is completed.
    Stores the rolled-up report so dashboards don't need to re-aggregate.
    """
    __tablename__ = "session_summaries"

    id                  = Column(Integer, primary_key=True, index=True)
    session_id          = Column(String(36), ForeignKey("practice_sessions.session_id"),
                                 unique=True, nullable=False)
    student_id          = Column(String(100), nullable=False, index=True)

    overall_accuracy    = Column(Float, default=0.0)
    total_attempts      = Column(Integer, default=0)
    correct             = Column(Integer, default=0)
    incorrect           = Column(Integer, default=0)
    avg_confidence      = Column(Float, default=0.0)
    avg_inference_time  = Column(Float, default=0.0)
    duration_seconds    = Column(Float, default=0.0)

    # JSON fields
    strongest_letters   = Column(Text, default="[]")   # ["A", "B"]
    weakest_letters     = Column(Text, default="[]")   # ["X", "Z"]
    most_improved       = Column(String(5),  nullable=True)
    least_improved      = Column(String(5),  nullable=True)
    recommendations     = Column(Text, default="[]")   # list of strings

    generated_at        = Column(DateTime, default=datetime.utcnow)

    session = relationship("PracticeSession", back_populates="summary")


# ─── New: Cross-Session Progress Metrics ─────────────────────────────────────

class ProgressMetrics(Base):
    """
    One row per completed session per student.
    Enables efficient session-to-session trend queries without re-aggregating attempts.
    """
    __tablename__ = "progress_metrics"

    id                      = Column(Integer, primary_key=True, index=True)
    student_id              = Column(String(100), nullable=False, index=True)
    session_id              = Column(String(36),  nullable=False)
    session_number          = Column(Integer,     nullable=False)  # 1, 2, 3 …

    session_accuracy        = Column(Float, default=0.0)
    prev_session_accuracy   = Column(Float, nullable=True)
    accuracy_delta          = Column(Float, default=0.0)   # positive = improved

    avg_confidence          = Column(Float, default=0.0)
    prev_avg_confidence     = Column(Float, nullable=True)
    confidence_delta        = Column(Float, default=0.0)

    total_learning_progress = Column(Float, default=0.0)   # % of alphabet mastered
    consecutive_days        = Column(Integer, default=0)
    letters_practiced_count = Column(Integer, default=0)
    letters_mastered_count  = Column(Integer, default=0)

    recorded_at             = Column(DateTime, default=datetime.utcnow)