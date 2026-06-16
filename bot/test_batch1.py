"""
Batch 1 smoke test — runs without Telegram polling.

Tests:
 1. Sheet sync (CSV public mode) — verify mapping + latest-row pick
 2. Auto-decision _is_auto_eligible() — 6 scenarios
 3. route_task() — 4 realistic forwarded messages
 4. recommend_now() — pick best task from mock pending list
 5. DB: list_auto_created_today() + reassign_task() + cancel_task()

Usage:
    cd bot && py test_batch1.py
"""

import asyncio
import os
import sys
import tempfile
import json
from datetime import datetime, timedelta

# Set test DB BEFORE importing store
_test_db = os.path.join(tempfile.gettempdir(), f"test_batch1_{os.getpid()}.db")
os.environ["DB_PATH"] = _test_db

from dotenv import load_dotenv
load_dotenv()


# ─── ANSI colors for readable output ─────────────────────────────────────────
class C:
    OK = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    HEAD = "\033[96m"
    DIM = "\033[90m"
    RST = "\033[0m"


def header(s: str):
    print(f"\n{C.HEAD}{'━' * 60}{C.RST}")
    print(f"{C.HEAD}  {s}{C.RST}")
    print(f"{C.HEAD}{'━' * 60}{C.RST}")


def ok(s: str):
    print(f"  {C.OK}✓{C.RST} {s}")


def fail(s: str):
    print(f"  {C.FAIL}✗ {s}{C.RST}")


def warn(s: str):
    print(f"  {C.WARN}⚠ {s}{C.RST}")


def info(s: str):
    print(f"  {C.DIM}{s}{C.RST}")


PASS_COUNT = 0
FAIL_COUNT = 0


def assert_eq(actual, expected, label):
    global PASS_COUNT, FAIL_COUNT
    if actual == expected:
        PASS_COUNT += 1
        ok(f"{label}  →  {actual}")
    else:
        FAIL_COUNT += 1
        fail(f"{label}  →  got {actual!r}, expected {expected!r}")


def assert_true(cond, label):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        ok(label)
    else:
        FAIL_COUNT += 1
        fail(label)


# ─── TEST 1: Sheet sync ──────────────────────────────────────────────────────

async def test_sheet_sync():
    header("TEST 1 · Google Sheet KPI Sync (CSV public mode)")

    os.environ["GSHEET_ID"] = "1OGLMk0STGWmBJlWzY-l1UtG9YQt4l0Vw9xwtjoLi4Po"
    os.environ["GSHEET_TAB"] = "0"
    os.environ["GSHEET_SERVICE_ACCOUNT_JSON"] = ""

    # Force module reload to pick up env
    import importlib
    import sheet_sync
    importlib.reload(sheet_sync)

    # Test header normalization
    assert_eq(sheet_sync._normalize_header("FR_Core_%"), "fr_core_%", "normalize 'FR_Core_%'")
    assert_eq(sheet_sync._normalize_header("Ngày"), "ngay", "normalize 'Ngày' (diacritic strip)")
    assert_eq(sheet_sync._normalize_header("  Ghi chú  "), "ghi_chu", "normalize 'Ghi chú' (space + diacritic)")

    # Test mapping
    assert_eq(sheet_sync._map_header("FR_Core_%"), "fill_rate_core_pct", "map FR_Core_%")
    assert_eq(sheet_sync._map_header("Ngày"), "_date", "map Ngày → _date")
    assert_eq(sheet_sync._map_header("UnknownColumn"), None, "unknown column returns None")

    # Test cleanup
    assert_eq(sheet_sync._clean_value("1,247"), "1247", "strip thousand separator")
    assert_eq(sheet_sync._clean_value("8.7"), "8.7", "keep decimal")
    assert_eq(sheet_sync._clean_value("Ca thường"), "Ca thường", "keep non-numeric string")

    # Test live fetch
    info("Fetching live sheet via CSV...")
    rows = await sheet_sync._fetch_via_csv_export()
    assert_true(len(rows) >= 1, f"fetched {len(rows)} row(s) from public sheet")

    if rows:
        info(f"Raw row 1 keys: {list(rows[0].keys())}")
        mapped = sheet_sync._rows_to_mapped(rows)
        latest = sheet_sync._pick_latest_row(mapped)
        assert_true(latest is not None, "picked latest row")
        if latest:
            info(f"Latest dated row: {latest.get('_date', '?')}")
            info(f"Mapped metrics: {[(k, v) for k, v in latest.items() if k != '_date']}")
            assert_true("fill_rate_core_pct" in latest, "FR_Core_% → fill_rate_core_pct present")
            assert_true("gsv_today_b" in latest, "GSV → gsv_today_b present")


# ─── TEST 2: Auto-decision logic ─────────────────────────────────────────────

def test_auto_decision():
    header("TEST 2 · Auto-decision threshold logic")

    # Import bot helpers
    import bot as bot_mod

    scenarios = [
        # (label, routed_dict, expected_eligible)
        ("Case 1: P2, conf=0.92, clear assignee", {
            "is_task": True, "priority": "P2", "assignee_confidence": 0.92,
            "assignee_name": "Ngân", "assignee_email": "Nganntk1@ahamove.com",
        }, True),
        ("Case 6: P0, conf=0.95 (high stakes)", {
            "is_task": True, "priority": "P0", "assignee_confidence": 0.95,
            "assignee_name": "Khâm", "assignee_email": "khamnd@ahamove.com",
        }, False),
        ("Case 7: P1, conf=0.88 (high stakes)", {
            "is_task": True, "priority": "P1", "assignee_confidence": 0.88,
            "assignee_name": "Khánh", "assignee_email": "khanhlv@ahamove.com",
        }, False),
        ("Case 9: P2, conf=0.62 (low confidence)", {
            "is_task": True, "priority": "P2", "assignee_confidence": 0.62,
            "assignee_name": None,
        }, False),
        ("Case 13: P3, conf=0.87, routine", {
            "is_task": True, "priority": "P3", "assignee_confidence": 0.87,
            "assignee_name": "Chiến", "assignee_email": "chienpd@ahamove.com",
        }, True),
        ("Case 11: P2, conf=0.81 (borderline)", {
            "is_task": True, "priority": "P2", "assignee_confidence": 0.81,
            "assignee_name": "Thống", "assignee_email": "thonglhn@ahamove.com",
        }, False),
    ]

    for label, routed, expected in scenarios:
        result = bot_mod._is_auto_eligible(routed)
        assert_eq(result, expected, label)


# ─── TEST 3: route_task() with real AI ───────────────────────────────────────

async def test_route_task():
    header("TEST 3 · route_task() — real Gemini calls on 4 messages")

    if not os.getenv("GEMINI_API_KEY"):
        warn("GEMINI_API_KEY not set — skipping AI tests")
        return

    from classifier import route_task

    test_messages = [
        ("Update bảng kê B2B tuần 21 trước thứ 6", "Ngân", "P2"),
        ("Tài xế VSIP đang complain dữ lắm, check ngay đi", "Khâm", "P0"),
        ("Tuyển 30 driver tỉnh Long An tháng này", "Khâm", "P2"),
        ("FR HAN tuần 22 đang tụt, làm insight cho anh xem", "Thương", "P2"),
    ]

    for text, expected_person_hint, expected_priority_hint in test_messages:
        info(f"\nForward: \"{text}\"")
        try:
            result = route_task(text)
        except Exception as e:
            fail(f"route_task threw: {e}")
            continue

        person = result.get("assignee_name", "?")
        priority = result.get("priority", "?")
        conf = result.get("assignee_confidence", 0)
        okr = result.get("okr_ref", "—")
        breakdown = result.get("breakdown", [])
        estimated = result.get("estimated_minutes", "?")

        # Check assignee detected
        person_match = expected_person_hint.lower() in person.lower() if person else False
        prio_match = priority == expected_priority_hint

        print(f"    → assignee: {person} (conf={conf:.2f}) {'✓' if person_match else '⚠'}")
        print(f"    → priority: {priority} {'✓' if prio_match else '⚠ expected ' + expected_priority_hint}")
        print(f"    → OKR ref:  {okr}")
        print(f"    → ETA:      {estimated} phút")
        print(f"    → breakdown: {len(breakdown)} steps")
        for i, step in enumerate(breakdown[:3], 1):
            print(f"         {i}. {step[:80]}")

        # Verdict
        if person_match and prio_match:
            PASS = True
        elif person_match:
            PASS = True  # OK if person right even priority differs
            warn(f"  Priority differs but assignee correct — acceptable")
        else:
            PASS = False

        global PASS_COUNT, FAIL_COUNT
        if PASS:
            PASS_COUNT += 1
            ok(f"Routing acceptable")
        else:
            FAIL_COUNT += 1
            fail(f"Routing wrong (expected {expected_person_hint})")


# ─── TEST 4: recommend_now() with real AI ────────────────────────────────────

async def test_recommend_now():
    header("TEST 4 · /now — recommend_now() with mock pending tasks")

    if not os.getenv("GEMINI_API_KEY"):
        warn("GEMINI_API_KEY not set — skipping")
        return

    from classifier import recommend_now

    now = datetime.now()
    in_2h = (now + timedelta(hours=2)).isoformat()
    in_8h = (now + timedelta(hours=8)).isoformat()
    in_3d = (now + timedelta(days=3)).isoformat()
    overdue = (now - timedelta(hours=5)).isoformat()

    pending = [
        {"id": 101, "summary": "Update bảng kê B2B tuần 21",
         "priority": "P2", "deadline": in_3d, "category": "report",
         "classifier_meta": {"okr_ref": None}},
        {"id": 102, "summary": "FR HAN tuần 22 insight cho anh Huy",
         "priority": "P1", "deadline": in_8h, "category": "data",
         "classifier_meta": {"okr_ref": "O1.1"}},
        {"id": 103, "summary": "Tài xế VSIP đang complain — supply gap",
         "priority": "P0", "deadline": in_2h, "category": "ops",
         "classifier_meta": {"okr_ref": "O1.2"}},
        {"id": 104, "summary": "Decal tài xế HAN batch tháng 5",
         "priority": "P3", "deadline": None, "category": "ops",
         "classifier_meta": {"okr_ref": "O2.5"}},
        {"id": 105, "summary": "Họp retro Q1 với Khánh",
         "priority": "P2", "deadline": overdue, "category": "meeting",
         "classifier_meta": {"okr_ref": None}},
    ]

    info(f"5 pending tasks. Time: {now.strftime('%H:%M %A')}")

    try:
        rec = recommend_now(pending, user_name="Hùng")
    except Exception as e:
        fail(f"recommend_now threw: {e}")
        return

    print(f"\n    Primary pick:     #{rec.get('task_id')}")
    print(f"    Reason:           {rec.get('reason')}")
    print(f"    Alternative:      #{rec.get('alternative_task_id')}")
    print(f"    Alt reason:       {rec.get('alternative_reason')}")

    # AI should pick either #103 (P0 + 2h deadline) or #105 (overdue 5h meeting)
    # Both are defensible — overdue beats not-yet-overdue in some readings.
    picked = rec.get("task_id")
    assert_true(
        picked in (103, 105),
        f"AI picks #103 (P0/2h) or #105 (overdue 5h) — got #{picked}"
    )
    assert_true(rec.get("reason"), "reason is non-empty")
    # And the alternative should be the other urgent one
    alt = rec.get("alternative_task_id")
    if picked == 103:
        assert_true(alt in (102, 105),
                    f"alt should be next-most-urgent (102/105) — got #{alt}")
    elif picked == 105:
        assert_true(alt in (103, 101, 102),
                    f"alt should be urgent or strategic — got #{alt}")


# ─── TEST 5: DB operations ───────────────────────────────────────────────────

def test_db_operations():
    header("TEST 5 · DB: auto-created task lifecycle")

    from store import (
        init_db, register_user, approve_user, add_task,
        list_auto_created_today, reassign_task, cancel_task, get_task,
    )

    init_db()

    # Create 2 test users
    register_user(99001, "test_manager", "Test Manager")
    register_user(99002, "test_employee", "Test Employee")
    approve_user(99001)
    approve_user(99002)
    ok("Created 2 test users")

    # Auto-create a task with source='ai_auto'
    task_id = add_task(
        raw_message="Update bảng kê B2B tuần 21",
        summary="Update bảng kê B2B tuần 21",
        assignee_id=99002,
        assigned_by=99001,
        team="OPS",
        source="ai_auto",
        priority="P2",
        category="report",
        estimated_minutes=60,
        classifier_meta={"okr_ref": "O3.3", "assignee_confidence": 0.92},
    )
    assert_true(task_id > 0, f"add_task returned id={task_id}")

    # Verify list_auto_created_today picks it up
    digest = list_auto_created_today()
    assert_eq(len(digest), 1, "list_auto_created_today returns 1 task")

    if digest:
        t = digest[0]
        assert_eq(t["id"], task_id, f"digest task id matches")
        assert_eq(t["source"], "ai_auto", "source='ai_auto'")
        assert_eq(t.get("assignee_name"), "Test Employee", "joined assignee_name")

    # Add a non-auto task — should NOT appear in digest
    add_task(
        raw_message="Manual task",
        summary="Manual task",
        assignee_id=99002,
        assigned_by=99001,
        team="OPS",
        source="message",  # not ai_auto
        priority="P3",
    )
    digest2 = list_auto_created_today()
    assert_eq(len(digest2), 1, "manual task (source=message) NOT in digest")

    # Test reassign
    register_user(99003, "test_other", "Test Other")
    approve_user(99003)
    ok_reassign = reassign_task(task_id, 99003)
    assert_true(ok_reassign, "reassign_task returns True")

    after = get_task(task_id)
    assert_eq(after["assignee_id"], 99003, "assignee_id updated after reassign")

    # Test cancel (simulating /undo)
    cancel_task(task_id)
    after2 = get_task(task_id)
    assert_eq(after2["status"], "cancelled", "status='cancelled' after undo")

    # After cancel, should still appear in digest? Let's check
    digest3 = list_auto_created_today()
    info(f"After cancel, digest still has {len(digest3)} task — by design (digest shows ALL bot-created today)")


# ─── TEST 6: Auto-digest template ────────────────────────────────────────────

def test_template_rendering():
    header("TEST 6 · Templates render without crashing")

    import templates as tpl

    # msg_auto_assigned
    sample_routed = {
        "summary": "Update bảng kê B2B tuần 21",
        "priority": "P2",
        "deadline_iso": (datetime.now() + timedelta(days=2)).isoformat(),
        "okr_ref": "O3.3",
        "assignee_confidence": 0.92,
    }
    msg1 = tpl.msg_auto_assigned(45, "Ngân", sample_routed, undo_window_min=60)
    assert_true(len(msg1) > 30, "msg_auto_assigned produces output")
    print(f"\n  Sample msg_auto_assigned:\n{C.DIM}{msg1}{C.RST}\n")

    # msg_auto_digest_manager
    sample_tasks = [
        {"id": 101, "summary": "Update bảng kê B2B tuần 21", "priority": "P2",
         "assignee_name": "Ngân", "deadline": (datetime.now() + timedelta(days=2)).isoformat(),
         "classifier_meta": '{"okr_ref": "O3.3"}'},
        {"id": 102, "summary": "FR HAN tuần 22 insight", "priority": "P1",
         "assignee_name": "Thương", "deadline": (datetime.now() + timedelta(hours=8)).isoformat(),
         "classifier_meta": {"okr_ref": "O1.1"}},
        {"id": 103, "summary": "Tuyển 30 driver Long An", "priority": "P2",
         "assignee_name": "Khâm", "deadline": None,
         "classifier_meta": {"okr_ref": "O2.1"}},
    ]
    msg2 = tpl.msg_auto_digest_manager(sample_tasks)
    assert_true(len(msg2) > 50, "msg_auto_digest_manager produces output")
    assert_true("Ngân" in msg2 and "Thương" in msg2 and "Khâm" in msg2,
                "all 3 assignees present in digest")
    print(f"  Sample msg_auto_digest_manager:\n{C.DIM}{msg2}{C.RST}\n")

    # msg_now_recommendation
    sample_primary = {"id": 103, "summary": "Tài xế VSIP supply gap", "priority": "P0",
                      "deadline": (datetime.now() + timedelta(hours=2)).isoformat(),
                      "estimated_minutes": 45,
                      "classifier_meta": {"okr_ref": "O1.2"}}
    sample_alt = {"id": 102, "summary": "FR HAN insight", "priority": "P1",
                  "deadline": (datetime.now() + timedelta(hours=8)).isoformat()}
    msg3 = tpl.msg_now_recommendation(
        primary_task=sample_primary,
        primary_reason="P0 + deadline 2h tới + O1.2 critical",
        alternative_task=sample_alt,
        alternative_reason="Backup nếu chờ supply team trả lời",
    )
    assert_true(len(msg3) > 50, "msg_now_recommendation produces output")
    print(f"  Sample msg_now_recommendation:\n{C.DIM}{msg3}{C.RST}")


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    print(f"{C.HEAD}┏{'━' * 58}┓{C.RST}")
    print(f"{C.HEAD}┃{' Batch 1 Smoke Test — Auto-decision + /now + sync widgets ':^58}┃{C.RST}")
    print(f"{C.HEAD}┗{'━' * 58}┛{C.RST}")
    print(f"{C.DIM}Test DB: {_test_db}{C.RST}")
    print(f"{C.DIM}Env: GEMINI={'set' if os.getenv('GEMINI_API_KEY') else 'MISSING'}  "
          f"TELEGRAM={'set' if os.getenv('TELEGRAM_TOKEN') else 'MISSING'}{C.RST}")

    try:
        await test_sheet_sync()
    except Exception as e:
        fail(f"test_sheet_sync crashed: {e}")
        import traceback; traceback.print_exc()

    try:
        test_auto_decision()
    except Exception as e:
        fail(f"test_auto_decision crashed: {e}")
        import traceback; traceback.print_exc()

    try:
        await test_route_task()
    except Exception as e:
        fail(f"test_route_task crashed: {e}")
        import traceback; traceback.print_exc()

    try:
        await test_recommend_now()
    except Exception as e:
        fail(f"test_recommend_now crashed: {e}")
        import traceback; traceback.print_exc()

    try:
        test_db_operations()
    except Exception as e:
        fail(f"test_db_operations crashed: {e}")
        import traceback; traceback.print_exc()

    try:
        test_template_rendering()
    except Exception as e:
        fail(f"test_template_rendering crashed: {e}")
        import traceback; traceback.print_exc()

    # Cleanup
    try:
        os.remove(_test_db)
    except Exception:
        pass

    # Summary
    print(f"\n{C.HEAD}{'━' * 60}{C.RST}")
    if FAIL_COUNT == 0:
        print(f"{C.OK}  ALL {PASS_COUNT} ASSERTIONS PASSED{C.RST}")
    else:
        print(f"{C.OK}  PASSED: {PASS_COUNT}{C.RST}  {C.FAIL}FAILED: {FAIL_COUNT}{C.RST}")
    print(f"{C.HEAD}{'━' * 60}{C.RST}\n")

    sys.exit(1 if FAIL_COUNT > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
