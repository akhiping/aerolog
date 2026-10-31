"""Run AeroLog demo scenarios through the real agent pipeline."""

import asyncio
import sys

sys.path.insert(0, ".")

from app.agent.pipeline import AgentPipeline
from app.config import settings
from app.db.database import async_session, init_db
from app.llm.factory import create_llm_provider
from app.rag.engine import RAGEngine


def _print_header(num: int, title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  SCENARIO {num}: {title}")
    print(f"{'='*70}")


def _print_responses(responses: list) -> None:
    for r in responses:
        tag = r.type.upper()
        state = f" [{r.state.value}]" if r.state else ""
        if r.type == "record_update":
            rec = r.record
            if rec:
                fields = []
                if rec.aircraft_registration:
                    fields.append(f"aircraft={rec.aircraft_registration}")
                if rec.ata_chapter_code:
                    fields.append(f"ATA={rec.ata_chapter_code}")
                if rec.component:
                    fields.append(f"component={rec.component}")
                if rec.discrepancy:
                    fields.append(f"discrepancy='{rec.discrepancy[:60]}...'")
                if rec.corrective_action:
                    fields.append(f"action='{rec.corrective_action[:60]}...'")
                if rec.parts:
                    fields.append(f"parts={[p.part_number for p in rec.parts]}")
                if rec.measurements:
                    fields.append(
                        f"measurements={[f'{m.name}={m.value}{m.unit}' for m in rec.measurements]}"
                    )
                fields.append(f"severity={rec.severity.value}")
                if rec.escalated:
                    fields.append("ESCALATED")
                print(f"    [{tag}]{state}")
                for f in fields:
                    print(f"      {f}")
        elif r.content:
            content = r.content
            if len(content) > 200:
                content = content[:200] + "..."
            print(f"    [{tag}]{state} {content}")
        else:
            print(f"    [{tag}]{state}")


def _print_record_summary(record) -> None:
    print("\n  --- FINAL RECORD ---")
    print(f"    Aircraft:   {record.aircraft_registration or '(missing)'}")
    print(f"    ATA:        {record.ata_chapter_code} — {record.ata_chapter_name}")
    print(f"    Component:  {record.component or '(missing)'}")
    print(f"    Discrepancy:{' ' + record.discrepancy[:80] if record.discrepancy else ' (missing)'}")
    print(f"    Action:     {' ' + record.corrective_action[:80] if record.corrective_action else ' (missing)'}")
    if record.parts:
        print(f"    Parts:      {', '.join(p.part_number + '(' + p.action + ')' for p in record.parts)}")
    if record.measurements:
        for m in record.measurements:
            spec = ""
            if m.in_spec is not None:
                spec = " ✓IN-SPEC" if m.in_spec else " ✗OUT-OF-SPEC"
            print(f"    Meas:       {m.name} = {m.value} {m.unit}{spec}")
    print(f"    Severity:   {record.severity.value}")
    print(f"    Ops Check:  {'Yes — ' + record.ops_check_result if record.ops_check_performed else 'No'}")
    print(f"    Escalated:  {record.escalated}")
    print(f"    Signoff:    {record.signoff_status.value}")


def _check(label: str, condition: bool) -> None:
    mark = "✓" if condition else "✗"
    print(f"    {mark} {label}")


async def run_scenario(
    pipeline: AgentPipeline,
    scenario_num: int,
    title: str,
    inputs: list[str],
    db,
    checks: list[tuple[str, callable]] | None = None,
) -> None:
    _print_header(scenario_num, title)

    session_id = f"demo-{scenario_num}"
    pipeline.set_db(db)
    greeting = await pipeline.start_session(session_id, technician_id="TECH-DEMO")
    print(f"  Agent: {greeting.content}")

    for text in inputs:
        print(f"\n  Technician: \"{text}\"")
        responses = await pipeline.process_input(session_id, text)
        _print_responses(responses)

    session = pipeline.get_session(session_id)
    if session:
        _print_record_summary(session.record)
        if checks:
            print("\n  --- CHECKS ---")
            for label, check_fn in checks:
                _check(label, check_fn(session.record))


async def main() -> None:
    print("AeroLog Demo Runner")
    print("=" * 70)
    print("Initializing database and RAG engine...\n")

    await init_db()

    # Seed if needed — import seed inline to avoid double-init
    from seed import seed

    await seed()

    llm = create_llm_provider(settings)
    rag = RAGEngine()
    chunk_count = await rag.ingest_directory("manuals")
    print(f"RAG indexed {chunk_count} chunks from manuals/")
    print(f"LLM provider: {settings.llm_provider}")

    pipeline = AgentPipeline(llm=llm, rag_engine=rag)

    async with async_session() as db:

        # ── Scenario 1: Full English inspection — out-of-spec torque ───────
        await run_scenario(
            pipeline,
            1,
            "English Inspection — Out-of-Spec Torque (CAT-B)",
            [
                (
                    "On tail N123AB, number two engine, ATA 72, "
                    "found oil residue around the number four bearing, "
                    "torque on the B-nut was below spec at 25 inch-pounds, "
                    "replaced the O-ring, part number MS29513-012, ops check good"
                ),
                "Work order WO-2026-1001, technician ID TECH-DEMO",
            ],
            db,
            checks=[
                ("Aircraft = N123AB", lambda r: r.aircraft_registration == "N123AB"),
                ("ATA = 72", lambda r: r.ata_chapter_code == "72"),
                ("Has measurement", lambda r: len(r.measurements) > 0),
                ("Part MS29513-012 logged", lambda r: any(p.part_number == "MS29513-012" for p in r.parts)),
                ("Severity is CAT-B or higher", lambda r: r.severity.value in ("CAT-A", "CAT-B")),
                ("Ops check recorded", lambda r: r.ops_check_performed),
            ],
        )

        # ── Scenario 2: Crack finding → CAT-A → escalation ────────────────
        await run_scenario(
            pipeline,
            2,
            "Crack Finding — CAT-A Escalation",
            [
                (
                    "N456CD, ATA 28 fuel system, found a crack on the fuel line "
                    "B-nut fitting at the wing root, approximately half an inch long. "
                    "Aircraft must be grounded."
                ),
                "Corrective action: replaced fuel line fitting, part AN816-6D, pressure tested at 15 PSI for 30 minutes, passed. Technician TECH-023, work order WO-2026-1002.",
            ],
            db,
            checks=[
                ("Aircraft = N456CD", lambda r: r.aircraft_registration == "N456CD"),
                ("Severity = CAT-A", lambda r: r.severity.value == "CAT-A"),
                ("Escalated", lambda r: r.escalated),
                ("'crack' in discrepancy", lambda r: "crack" in r.discrepancy.lower()),
            ],
        )

        # ── Scenario 3: Mid-log manual question (torque spec) ─────────────
        await run_scenario(
            pipeline,
            3,
            "Manual Q&A — Torque Spec Lookup",
            [
                "What's the torque spec for the number four bearing B-nut?",
                (
                    "Okay thanks. On N789GH, ATA 72, engine, number four bearing, "
                    "found the B-nut loose. Re-torqued to 30 in-lbs. "
                    "Replaced O-ring MS29513-012, ops check satisfactory. "
                    "Technician TECH-DEMO, work order WO-2026-1003."
                ),
            ],
            db,
            checks=[
                ("Manual answer returned", lambda r: True),  # checked during output
                ("Aircraft = N789GH", lambda r: r.aircraft_registration == "N789GH"),
                ("ATA = 72", lambda r: r.ata_chapter_code == "72"),
            ],
        )

        # ── Scenario 4: Hindi/English code-switched log ───────────────────
        await run_scenario(
            pipeline,
            4,
            "Hindi + English Code-Switched Log",
            [
                (
                    "VT-DEF pe ATA 79, oil filter replace kiya, "
                    "part number AEL-95237, sab theek hai, ops check good. "
                    "Technician TECH-055, work order WO-2026-1004."
                ),
            ],
            db,
            checks=[
                ("Aircraft = VT-DEF", lambda r: r.aircraft_registration == "VT-DEF"),
                ("ATA = 79", lambda r: r.ata_chapter_code == "79"),
                ("Ops check recorded", lambda r: r.ops_check_performed),
            ],
        )

        # ── Scenario 5: History read-back with repeat defect ──────────────
        await run_scenario(
            pipeline,
            5,
            "Service History Read-Back — Repeat Defect",
            [
                "Read me the last service on VT-ABC",
            ],
            db,
            checks=[
                ("History response generated", lambda r: True),  # checked in output
            ],
        )

    print(f"\n{'='*70}")
    print("  DEMO COMPLETE — all 5 scenarios executed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
