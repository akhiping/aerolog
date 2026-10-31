"""Seed AeroLog database with demo data."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.database import async_session, init_db
from app.db.models import Aircraft, MaintenanceRecordDB, ManualDocument, Supervisor


async def seed():
    await init_db()
    async with async_session() as db:
        result = await db.execute(select(Aircraft))
        if result.scalars().first():
            print("Database already seeded. Delete aerolog.db to re-seed.")
            return

        aircraft = [
            Aircraft(
                registration="N123AB",
                aircraft_type="Boeing 737-800",
                operator="SkyLine Airways",
                next_inspection_due=datetime(2026, 11, 15, tzinfo=timezone.utc),
            ),
            Aircraft(
                registration="VT-ABC",
                aircraft_type="Airbus A320",
                operator="IndiaJet",
                next_inspection_due=datetime(2026, 10, 1, tzinfo=timezone.utc),
            ),
            Aircraft(
                registration="N456CD",
                aircraft_type="Boeing 777-300ER",
                operator="SkyLine Airways",
                next_inspection_due=datetime(2026, 12, 1, tzinfo=timezone.utc),
            ),
            Aircraft(
                registration="VT-DEF",
                aircraft_type="ATR 72-600",
                operator="RegionalAir India",
                next_inspection_due=datetime(2027, 1, 15, tzinfo=timezone.utc),
            ),
            Aircraft(
                registration="N789GH",
                aircraft_type="Cessna 208 Caravan",
                operator="CargoExpress",
                next_inspection_due=datetime(2026, 11, 30, tzinfo=timezone.utc),
            ),
        ]
        db.add_all(aircraft)

        supervisors = [
            Supervisor(
                id=str(uuid4()),
                name="Rajesh Kumar",
                phone="+919876543210",
                email="rajesh.k@mro.example.com",
                active=True,
            ),
            Supervisor(
                id=str(uuid4()),
                name="Sarah Chen",
                phone="+14155551234",
                email="sarah.c@mro.example.com",
                active=True,
            ),
        ]
        db.add_all(supervisors)

        now = datetime.now(timezone.utc)
        records = [
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="VT-ABC",
                ata_chapter_code="72",
                ata_chapter_name="Engine",
                component="#4 bearing",
                discrepancy="Oil residue found around number 4 bearing housing during scheduled inspection",
                corrective_action="Cleaned area, inspected bearing — no damage. Replaced O-ring P/N MS29513-012. Torqued B-nut to 30 in-lbs.",
                parts=[{"part_number": "MS29513-012", "serial_number": "", "qty": 1, "action": "installed"}],
                measurements=[{"name": "torque", "value": 30, "unit": "in-lbs", "spec_min": 27, "spec_max": 33, "in_spec": True}],
                severity="CAT-B",
                ops_check_performed=True,
                ops_check_result="satisfactory",
                technician_id="TECH-042",
                work_order_id="WO-2026-0891",
                raw_transcript="On VT-ABC, number two engine, ATA 72, found oil residue around the number four bearing...",
                requires_signoff=True,
                signoff_status="signed",
                signoff_by="Rajesh Kumar",
                signoff_at=now - timedelta(days=44),
                escalated=False,
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=45),
                updated_at=now - timedelta(days=44),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="VT-ABC",
                ata_chapter_code="72",
                ata_chapter_name="Engine",
                component="#4 bearing",
                discrepancy="Oil weeping again at number 4 bearing, same location as previous finding",
                corrective_action="Replaced bearing assembly and B-nut. New bearing P/N 6205-2RS. Torqued to 30 in-lbs. Ops check good.",
                parts=[
                    {"part_number": "6205-2RS", "serial_number": "SN-88421", "qty": 1, "action": "installed"},
                    {"part_number": "MS29513-012", "serial_number": "", "qty": 1, "action": "installed"},
                ],
                measurements=[{"name": "torque", "value": 30, "unit": "in-lbs", "spec_min": 27, "spec_max": 33, "in_spec": True}],
                severity="CAT-B",
                ops_check_performed=True,
                ops_check_result="satisfactory",
                technician_id="TECH-042",
                work_order_id="WO-2026-0934",
                raw_transcript="VT-ABC again, same bearing, number four, oil is back...",
                requires_signoff=True,
                signoff_status="signed",
                signoff_by="Sarah Chen",
                signoff_at=now - timedelta(days=14),
                escalated=False,
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=15),
                updated_at=now - timedelta(days=14),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="N123AB",
                ata_chapter_code="32",
                ata_chapter_name="Landing Gear",
                component="main landing gear strut",
                discrepancy="Strut extension measured at 5.2 inches, within limits",
                corrective_action="Serviced nitrogen to 1800 PSI. All seals satisfactory. No action required.",
                parts=[],
                measurements=[
                    {"name": "strut extension", "value": 5.2, "unit": "in", "spec_min": 4.5, "spec_max": 6.0, "in_spec": True},
                    {"name": "nitrogen pressure", "value": 1800, "unit": "PSI", "spec_min": 1500, "spec_max": 2000, "in_spec": True},
                ],
                severity="ROUTINE",
                ops_check_performed=False,
                ops_check_result="",
                technician_id="TECH-017",
                work_order_id="WO-2026-0902",
                raw_transcript="N123AB main gear inspection...",
                requires_signoff=False,
                signoff_status="pending",
                escalated=False,
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(days=30),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="N123AB",
                ata_chapter_code="27",
                ata_chapter_name="Flight Controls",
                component="aileron cable",
                discrepancy="Aileron cable tension measured low at 32 lbs, spec is 40 lbs ±5",
                corrective_action="Adjusted cable tension via turnbuckle to 41 lbs. Safety wired per AS567.",
                parts=[],
                measurements=[
                    {"name": "cable tension", "value": 41, "unit": "lbs", "spec_min": 35, "spec_max": 45, "in_spec": True},
                ],
                severity="CAT-C",
                ops_check_performed=True,
                ops_check_result="satisfactory",
                technician_id="TECH-017",
                work_order_id="WO-2026-0903",
                raw_transcript="N123AB flight control rigging check...",
                requires_signoff=True,
                signoff_status="signed",
                signoff_by="Sarah Chen",
                signoff_at=now - timedelta(days=19),
                escalated=False,
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=20),
                updated_at=now - timedelta(days=19),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="N456CD",
                ata_chapter_code="28",
                ata_chapter_name="Fuel",
                component="fuel line fitting",
                discrepancy="Crack found on fuel line B-nut fitting at wing root, approximately 0.5 inch long",
                corrective_action="Aircraft grounded. Fuel line fitting replaced. Pressure test passed at 15 PSI for 30 min.",
                parts=[{"part_number": "AN816-6D", "serial_number": "", "qty": 1, "action": "installed"}],
                measurements=[
                    {"name": "crack length", "value": 0.5, "unit": "in", "spec_min": None, "spec_max": 0.0, "in_spec": False},
                ],
                severity="CAT-A",
                ops_check_performed=True,
                ops_check_result="satisfactory",
                technician_id="TECH-023",
                work_order_id="WO-2026-0910",
                raw_transcript="N456CD fuel system, found a crack on the fuel line fitting...",
                requires_signoff=True,
                signoff_status="signed",
                signoff_by="Rajesh Kumar",
                signoff_at=now - timedelta(days=9),
                escalated=True,
                escalation_reason="Crack on fuel line fitting — airworthiness critical",
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=9),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="VT-DEF",
                ata_chapter_code="79",
                ata_chapter_name="Oil",
                component="oil filter",
                discrepancy="Scheduled oil filter replacement at 500 hour interval",
                corrective_action="Replaced oil filter. No contamination found. Oil analysis sample taken.",
                parts=[{"part_number": "AEL-95237", "serial_number": "", "qty": 1, "action": "installed"}],
                measurements=[],
                severity="ROUTINE",
                ops_check_performed=False,
                ops_check_result="",
                technician_id="TECH-055",
                work_order_id="WO-2026-0925",
                raw_transcript="VT-DEF oil filter replacement...",
                requires_signoff=False,
                signoff_status="pending",
                escalated=False,
                session_id=str(uuid4()),
                language_detected="hi",
                created_at=now - timedelta(days=7),
                updated_at=now - timedelta(days=7),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="N789GH",
                ata_chapter_code="72",
                ata_chapter_name="Engine",
                component="exhaust stack",
                discrepancy="Exhaust stack shows heat discoloration and minor erosion",
                corrective_action="Erosion within limits per CMM. Documented for trend monitoring. Next inspection at 200 hours.",
                parts=[],
                measurements=[],
                severity="CAT-C",
                ops_check_performed=False,
                ops_check_result="",
                technician_id="TECH-017",
                work_order_id="WO-2026-0940",
                raw_transcript="N789GH exhaust inspection...",
                requires_signoff=False,
                signoff_status="pending",
                escalated=False,
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=5),
                updated_at=now - timedelta(days=5),
            ),
            MaintenanceRecordDB(
                id=str(uuid4()),
                aircraft_registration="VT-ABC",
                ata_chapter_code="29",
                ata_chapter_name="Hydraulic Power",
                component="hydraulic pump",
                discrepancy="Hydraulic system pressure fluctuating, pump output low",
                corrective_action="Replaced hydraulic pump. System pressure now stable at 3000 PSI.",
                parts=[{"part_number": "AH-23456", "serial_number": "HP-90122", "qty": 1, "action": "installed"}],
                measurements=[
                    {"name": "system pressure", "value": 3000, "unit": "PSI", "spec_min": 2800, "spec_max": 3200, "in_spec": True},
                ],
                severity="CAT-B",
                ops_check_performed=True,
                ops_check_result="satisfactory",
                technician_id="TECH-042",
                work_order_id="WO-2026-0950",
                raw_transcript="VT-ABC hydraulic system...",
                requires_signoff=True,
                signoff_status="pending",
                escalated=False,
                session_id=str(uuid4()),
                language_detected="en",
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=2),
            ),
        ]
        db.add_all(records)

        manuals = [
            ManualDocument(
                id=str(uuid4()),
                title="Engine Bearing Inspection and Replacement",
                ata_chapter="72",
                content="AMM 72-00-00-200-001 — Torque specs, inspection, replacement procedures for CFM56 bearings",
            ),
            ManualDocument(
                id=str(uuid4()),
                title="Main Landing Gear Inspection",
                ata_chapter="32",
                content="AMM 32-10-00-200-001 — MLG strut, brake, tire inspection procedures",
            ),
            ManualDocument(
                id=str(uuid4()),
                title="Flight Control System Rigging",
                ata_chapter="27",
                content="AMM 27-00-00-200-001 — Control surface travel, cable tension, rigging",
            ),
            ManualDocument(
                id=str(uuid4()),
                title="Fuel System Inspection",
                ata_chapter="28",
                content="AMM 28-20-00-200-001 — Fuel tank, line, filter inspection and leak check",
            ),
        ]
        db.add_all(manuals)

        await db.commit()
        print("✓ Database seeded successfully:")
        print(f"  {len(aircraft)} aircraft")
        print(f"  {len(records)} maintenance records")
        print(f"  {len(supervisors)} supervisors")
        print(f"  {len(manuals)} manual documents")
        print(f"\n  Note: VT-ABC has an OVERDUE inspection (due 2026-10-01)")
        print(f"  Note: VT-ABC has a REPEAT DEFECT on #4 bearing (ATA 72)")


if __name__ == "__main__":
    asyncio.run(seed())
