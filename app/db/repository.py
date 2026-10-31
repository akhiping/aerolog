from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Aircraft, MaintenanceRecordDB, ManualDocument, Supervisor, Notification


class MaintenanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_record(self, data: dict) -> MaintenanceRecordDB:
        record = MaintenanceRecordDB(
            id=str(uuid4()),
            **data,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_record(self, record_id: str, data: dict) -> MaintenanceRecordDB | None:
        result = await self.db.execute(
            select(MaintenanceRecordDB).where(MaintenanceRecordDB.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None
        for key, value in data.items():
            setattr(record, key, value)
        record.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_record(self, record_id: str) -> MaintenanceRecordDB | None:
        result = await self.db.execute(
            select(MaintenanceRecordDB).where(MaintenanceRecordDB.id == record_id)
        )
        return result.scalar_one_or_none()

    async def list_records(
        self, limit: int = 50, offset: int = 0,
        aircraft_reg: str | None = None,
        severity: str | None = None,
        escalated: bool | None = None,
    ) -> list[MaintenanceRecordDB]:
        query = select(MaintenanceRecordDB)
        if aircraft_reg:
            query = query.where(MaintenanceRecordDB.aircraft_registration == aircraft_reg)
        if severity:
            query = query.where(MaintenanceRecordDB.severity == severity)
        if escalated is not None:
            query = query.where(MaintenanceRecordDB.escalated == escalated)
        query = query.order_by(desc(MaintenanceRecordDB.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_history(
        self, aircraft_reg: str,
        ata_chapter: str | None = None,
        component: str | None = None,
        limit: int = 10,
    ) -> list[MaintenanceRecordDB]:
        query = select(MaintenanceRecordDB).where(
            MaintenanceRecordDB.aircraft_registration == aircraft_reg
        )
        if ata_chapter:
            query = query.where(MaintenanceRecordDB.ata_chapter_code == ata_chapter)
        if component:
            query = query.where(
                MaintenanceRecordDB.component.ilike(f"%{component}%")
            )
        query = query.order_by(desc(MaintenanceRecordDB.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_repeat_defects(
        self, aircraft_reg: str, ata_chapter: str, component: str, days: int = 90
    ) -> list[MaintenanceRecordDB]:
        cutoff = datetime.now(timezone.utc).replace(
            day=max(1, datetime.now(timezone.utc).day),
        )
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = select(MaintenanceRecordDB).where(
            and_(
                MaintenanceRecordDB.aircraft_registration == aircraft_reg,
                MaintenanceRecordDB.ata_chapter_code == ata_chapter,
                MaintenanceRecordDB.component.ilike(f"%{component}%"),
                MaintenanceRecordDB.created_at >= cutoff,
            )
        ).order_by(desc(MaintenanceRecordDB.created_at))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_record_count(self) -> int:
        result = await self.db.execute(select(func.count(MaintenanceRecordDB.id)))
        return result.scalar() or 0

    async def get_escalated_count(self) -> int:
        result = await self.db.execute(
            select(func.count(MaintenanceRecordDB.id)).where(
                MaintenanceRecordDB.escalated == True
            )
        )
        return result.scalar() or 0


class AircraftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, registration: str) -> Aircraft | None:
        result = await self.db.execute(
            select(Aircraft).where(Aircraft.registration == registration)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Aircraft]:
        result = await self.db.execute(select(Aircraft))
        return list(result.scalars().all())

    async def get_overdue(self) -> list[Aircraft]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Aircraft).where(Aircraft.next_inspection_due < now)
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> Aircraft:
        aircraft = Aircraft(**data)
        self.db.add(aircraft)
        await self.db.commit()
        await self.db.refresh(aircraft)
        return aircraft


class ManualRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[ManualDocument]:
        result = await self.db.execute(select(ManualDocument))
        return list(result.scalars().all())

    async def search_by_ata(self, ata_chapter: str) -> list[ManualDocument]:
        result = await self.db.execute(
            select(ManualDocument).where(
                ManualDocument.ata_chapter == ata_chapter
            )
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> ManualDocument:
        doc = ManualDocument(id=str(uuid4()), **data)
        self.db.add(doc)
        await self.db.commit()
        return doc


class SupervisorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> list[Supervisor]:
        result = await self.db.execute(
            select(Supervisor).where(Supervisor.active == True)
        )
        return list(result.scalars().all())

    async def get(self, supervisor_id: str) -> Supervisor | None:
        result = await self.db.execute(
            select(Supervisor).where(Supervisor.id == supervisor_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Supervisor:
        sup = Supervisor(id=str(uuid4()), **data)
        self.db.add(sup)
        await self.db.commit()
        return sup


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> Notification:
        notif = Notification(id=str(uuid4()), **data)
        self.db.add(notif)
        await self.db.commit()
        return notif

    async def list_recent(self, limit: int = 20) -> list[Notification]:
        result = await self.db.execute(
            select(Notification).order_by(desc(Notification.sent_at)).limit(limit)
        )
        return list(result.scalars().all())
