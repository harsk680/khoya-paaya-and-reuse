from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Numeric,
    ForeignKey
)

from sqlalchemy.sql import func

from database import Base


# =========================================================
# USER
# =========================================================

class User(Base):

    __tablename__ = "users"

    user_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        nullable=False
    )

    password = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(30),
        default="student"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# ITEM
# =========================================================

class Item(Base):

    __tablename__ = "items"

    item_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String(150),
        nullable=False
    )

    description = Column(
        Text
    )

    category = Column(
        String(100),
        nullable=False
    )

    location = Column(
        String(150)
    )

    item_date = Column(
        DateTime
    )

    image_path = Column(
        String(255)
    )

    status = Column(
        String(30),
        default="active"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# LOST REPORT
# =========================================================

class LostReport(Base):

    __tablename__ = "lost_reports"

    lost_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    item_id = Column(
        Integer,
        ForeignKey("items.item_id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    lost_date = Column(
        DateTime,
        nullable=False
    )

    lost_location = Column(
        String(150),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# FOUND REPORT
# =========================================================

class FoundReport(Base):

    __tablename__ = "found_reports"

    found_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    item_id = Column(
        Integer,
        ForeignKey("items.item_id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    found_date = Column(
        DateTime,
        nullable=False
    )

    found_location = Column(
        String(150),
        nullable=False
    )
    verification_image_path = Column(
        String(255),
        nullable=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# MATCH
# =========================================================

class Match(Base):

    __tablename__ = "matches"

    match_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    lost_id = Column(
        Integer,
        ForeignKey("lost_reports.lost_id"),
        nullable=False
    )

    found_id = Column(
        Integer,
        ForeignKey("found_reports.found_id"),
        nullable=False
    )

    match_score = Column(
        Numeric(5, 2),
        nullable=False
    )

    status = Column(
        String(30),
        default="possible"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# CLAIM
# =========================================================

class Claim(Base):

    __tablename__ = "claims"

    claim_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    found_id = Column(
        Integer,
        ForeignKey("found_reports.found_id"),
        nullable=False
    )

    claimant_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    claim_date = Column(
        DateTime,
        server_default=func.now()
    )

    status = Column(
        String(30),
        default="pending"
    )


# =========================================================
# COMMITTEE DECISION
# =========================================================

class CommitteeDecision(Base):

    __tablename__ = "committee_decisions"

    decision_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    claim_id = Column(
        Integer,
        ForeignKey("claims.claim_id"),
        nullable=False
    )

    decided_by = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    decision = Column(
        String(30),
        nullable=False
    )

    remarks = Column(
        Text
    )

    decided_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# NOTIFICATION
# =========================================================

class Notification(Base):

    __tablename__ = "notifications"

    notification_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    match_id = Column(
        Integer,
        ForeignKey("matches.match_id")
    )

    message = Column(
        Text,
        nullable=False
    )

    is_read = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# REUSE LISTING
# =========================================================

class ReuseListing(Base):

    __tablename__ = "reuse_listings"

    listing_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    title = Column(
        String(150),
        nullable=False
    )

    description = Column(
        Text
    )

    category = Column(
        String(100)
    )

    price = Column(
        Numeric(10, 2),
        default=0
    )

    condition_status = Column(
        String(50)
    )

    image_path = Column(
        String(255)
    )

    status = Column(
        String(30),
        default="available"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )


# =========================================================
# JOB
# =========================================================

class Job(Base):

    __tablename__ = "jobs"

    job_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    job_type = Column(
        String(50),
        nullable=False
    )

    reference_id = Column(
        Integer
    )
    found_reference_id = Column(
    Integer,
    nullable=True
)

    priority = Column(
        Integer,
        default=3
    )

    status = Column(
        String(30),
        default="waiting"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    started_at = Column(
        DateTime
    )

    completed_at = Column(
        DateTime
    )