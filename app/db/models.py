from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import JSON


class Base(DeclarativeBase):
    pass


class Aircraft(Base):
    __tablename__ = "aircraft"

    registration: Mapped[str] = mapped_column(String(20), primary_key=True)
    aircraft_type: Mapped[str] = mapped_column(String(100), default="")
    operator: Mapped[str] = mapped_column(String(100), default="")
    next_inspection_due: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    records: Mapped[list["MaintenanceRecordDB"]] = relationship(back_populates="aircraft", lazy="selectin")


class MaintenanceRecordDB(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    aircraft_registration: Mapped[str] = mapped_column(String(20), ForeignKey("aircraft.registration"), index=True)
    ata_chapter_code: Mapped[str] = mapped_column(String(5), default="")
    ata_chapter_name: Mapped[str] = mapped_column(String(200), default="")
    component: Mapped[str] = mapped_column(String(200), default="")
    zone: Mapped[str] = mapped_column(String(100), default="")
    discrepancy: Mapped[str] = mapped_column(Text, default="")
    corrective_action: Mapped[str] = mapped_column(Text, default="")
    parts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    measurements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="ROUTINE")
    ops_check_performed: Mapped[bool] = mapped_column(Boolean, default=False)
    ops_check_result: Mapped[str] = mapped_column(String(200), default="")
    technician_id: Mapped[str] = mapped_column(String(50), default="")
    work_order_id: Mapped[str] = mapped_column(String(50), default="", index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    confidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_transcript: Mapped[str] = mapped_column(Text, default="")
    requires_signoff: Mapped[bool] = mapped_column(Boolean, default=False)
    signoff_status: Mapped[str] = mapped_column(String(20), default="pending")
    signoff_by: Mapped[str] = mapped_column(String(100), default="")
    signoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[str] = mapped_column(Text, default="")
    session_id: Mapped[str] = mapped_column(String(36), default="")
    language_detected: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    aircraft: Mapped[Optional["Aircraft"]] = relationship(back_populates="records", lazy="selectin")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="record", lazy="selectin")


class ManualDocument(Base):
    __tablename__ = "manual_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    ata_chapter: Mapped[str] = mapped_column(String(5), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    notifications: Mapped[list["Notification"]] = relationship(back_populates="supervisor", lazy="selectin")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    record_id: Mapped[str] = mapped_column(String(36), ForeignKey("maintenance_records.id"), index=True)
    supervisor_id: Mapped[str] = mapped_column(String(36), ForeignKey("supervisors.id"))
    channel: Mapped[str] = mapped_column(String(20), default="dashboard")
    message: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    record: Mapped[Optional["MaintenanceRecordDB"]] = relationship(back_populates="notifications", lazy="selectin")
    supervisor: Mapped[Optional["Supervisor"]] = relationship(back_populates="notifications", lazy="selectin")
