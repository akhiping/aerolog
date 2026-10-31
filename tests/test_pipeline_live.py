"""Live pipeline tests — runs fresh improvised inputs through the real agent pipeline."""
import json
import httpx
import asyncio

BASE = "http://localhost:8000"

async def start_session(client, tech_id="TECH-099"):
    r = await client.post(f"{BASE}/api/session/start", json={"technician_id": tech_id})
    return r.json()["session_id"]

async def send_input(client, sid, text):
    r = await client.post(f"{BASE}/api/session/{sid}/input", json={"text": text})
    return r.json()["responses"]

def find_record(responses):
    for r in responses:
        if r.get("type") == "record_update" and r.get("record"):
            return r["record"]
    return None

def find_type(responses, msg_type):
    return [r for r in responses if r.get("type") == msg_type]

async def test_all():
    async with httpx.AsyncClient(timeout=30) as client:
        print("=" * 60)
        print("TEST 1: Fresh landing gear brake inspection")
        print("=" * 60)
        sid = await start_session(client)
        responses = await send_input(client, sid,
            "On tail N789GH, ATA 32, main landing gear, found brake pad worn below minimum, "
            "measured 0.08 inches remaining, spec minimum is 0.1 inches. "
            "Replaced brake pads, part number AN6-7A, ops check good, work order WO-2026-1100")
        rec = find_record(responses)
        assert rec, "No record in response"
        print(f"  Aircraft: {rec['aircraft_registration']}")
        print(f"  ATA: {rec['ata_chapter_code']} - {rec['ata_chapter_name']}")
        print(f"  Component: {rec.get('component', '')}")
        print(f"  Severity: {rec['severity']}")
        print(f"  Parts: {rec['parts']}")
        print(f"  Work order: {rec['work_order_id']}")
        print(f"  Ops check: {rec['ops_check_performed']}")
        followups = find_type(responses, "follow_up")
        if followups:
            print(f"  Follow-ups: {[f['content'] for f in followups]}")
        assert rec["aircraft_registration"] == "N789GH", f"Expected N789GH, got {rec['aircraft_registration']}"
        assert rec["ata_chapter_code"] == "32", f"Expected ATA 32, got {rec['ata_chapter_code']}"
        assert rec["ops_check_performed"] == True
        print("  ✓ PASS\n")

        print("=" * 60)
        print("TEST 2: Crack finding — should escalate (CAT-A)")
        print("=" * 60)
        sid = await start_session(client, "TECH-077")
        responses = await send_input(client, sid,
            "On VT-DEF, ATA 53, fuselage frame station 480, found a crack approximately "
            "2 inches long on the lower longeron, appears to be fatigue cracking. "
            "Requires structural repair.")
        rec = find_record(responses)
        assert rec, "No record in response"
        print(f"  Aircraft: {rec['aircraft_registration']}")
        print(f"  Severity: {rec['severity']}")
        print(f"  Escalated: {rec['escalated']}")
        print(f"  Escalation reason: {rec.get('escalation_reason', '')}")
        escalations = find_type(responses, "escalation")
        if escalations:
            print(f"  Escalation msg: {escalations[0]['content'][:100]}")
        assert rec["escalated"] == True, "Should be escalated"
        assert rec["severity"] in ("CAT-A", "CAT_A"), f"Expected CAT-A, got {rec['severity']}"
        print("  ✓ PASS\n")

        print("=" * 60)
        print("TEST 3: Manual Q&A — torque spec lookup")
        print("=" * 60)
        sid = await start_session(client, "TECH-042")
        responses = await send_input(client, sid,
            "What is the torque spec for the number four bearing B-nut?")
        manual = find_type(responses, "manual_answer")
        if manual:
            print(f"  Answer: {manual[0]['content'][:200]}")
            data = manual[0].get("data", {})
            print(f"  Source: {data.get('source', '')} / {data.get('section', '')}")
            assert "bearing" in manual[0]["content"].lower() and "torque" in manual[0]["content"].lower(), "Should mention bearing torque spec"
            print("  ✓ PASS\n")
        else:
            print("  No manual answer found")
            print("  ✗ FAIL\n")

        print("=" * 60)
        print("TEST 4: History read-back on VT-ABC")
        print("=" * 60)
        sid = await start_session(client, "TECH-042")
        responses = await send_input(client, sid,
            "Read me the last service on VT-ABC")
        history = find_type(responses, "history")
        if history:
            print(f"  History: {history[0]['content'][:300]}")
            assert "VT-ABC" in history[0]["content"]
            print("  ✓ PASS\n")
        else:
            print("  No history response found")
            print("  ✗ FAIL\n")

        print("=" * 60)
        print("TEST 5: Hindi code-switched input")
        print("=" * 60)
        sid = await start_session(client, "TECH-055")
        responses = await send_input(client, sid,
            "VT-DEF pe ATA 79, oil filter replace kiya, part number AEL-95237, sab theek hai, ops check good")
        rec = find_record(responses)
        if rec:
            print(f"  Aircraft: {rec['aircraft_registration']}")
            print(f"  ATA: {rec['ata_chapter_code']} - {rec['ata_chapter_name']}")
            print(f"  Corrective: {rec['corrective_action'][:80]}")
            print(f"  Ops check: {rec['ops_check_performed']}")
            assert rec["aircraft_registration"] == "VT-DEF"
            print("  ✓ PASS\n")
        else:
            print("  No record found")
            print("  ✗ FAIL\n")

        print("=" * 60)
        print("TEST 6: Follow-up flow — provide missing field")
        print("=" * 60)
        sid = await start_session(client, "TECH-099")
        responses1 = await send_input(client, sid,
            "Found oil leak on number three engine, ATA 72")
        rec1 = find_record(responses1)
        followups1 = find_type(responses1, "follow_up")
        print(f"  After first input:")
        if rec1:
            print(f"    Aircraft: {rec1['aircraft_registration'] or '(missing)'}")
            print(f"    Discrepancy: {rec1['discrepancy'][:60]}")
        if followups1:
            print(f"    Follow-up: {followups1[0]['content']}")

        # Provide the missing field
        responses2 = await send_input(client, sid,
            "Tail number is N123AB")
        rec2 = find_record(responses2)
        if rec2:
            print(f"  After providing tail number:")
            print(f"    Aircraft: {rec2['aircraft_registration']}")
            assert rec2["aircraft_registration"] == "N123AB", f"Expected N123AB got {rec2['aircraft_registration']}"
            print("  ✓ PASS\n")
        else:
            print("  ✗ FAIL\n")

        print("ALL TESTS COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_all())
