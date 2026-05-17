"""
Roast — witty Vietnamese messages for the team bot.
Keeps tone professional but human. No excessive emoji.
"""

import random


def get_morning_roast(overdue_count: int) -> str:
    if overdue_count == 0:
        msgs = [
            "Sạch bảng, ngon. Giữ được không?",
            "Queue trống — hay đang thiếu task?",
            "Không có gì overdue. Tốt.",
        ]
    elif overdue_count <= 2:
        msgs = [
            f"{overdue_count} task đang chờ từ hôm qua.",
            f"Còn {overdue_count} task chưa xong từ hôm qua — đầu ngày giải quyết đi.",
            f"{overdue_count} task overdue. Ưu tiên số 1 sáng nay.",
        ]
    else:
        msgs = [
            f"{overdue_count} task trễ hạn. Cần triage lại.",
            f"Đang có {overdue_count} task overdue — xem lại priority ngay.",
            f"{overdue_count} task tồn đọng. Cái nào drop được thì drop.",
        ]
    return random.choice(msgs)


def get_manager_morning_roast(total_overdue: int, total_active: int) -> str:
    if total_overdue == 0:
        return f"Team đang clean — {total_active} task đang chạy."
    elif total_overdue <= 3:
        return f"{total_overdue} task overdue trong team. Theo dõi chặt hôm nay."
    else:
        return f"{total_overdue} task overdue — cần review priority với team."


def get_done_roast() -> str:
    msgs = [
        "Done. Ghi nhận.",
        "Xong việc. Next.",
        "Task cleared.",
        "Đánh dấu hoàn thành.",
        "Done — chuyển sang cái tiếp theo.",
    ]
    return random.choice(msgs)


def get_snooze_roast() -> str:
    msgs = [
        "Oke, hoãn lại.",
        "Tạm gác. Bot sẽ nhắc lại.",
        "Snooze. Nhớ quay lại.",
        "Đã hoãn. Đừng quên.",
    ]
    return random.choice(msgs)


def get_overdue_roast(hours: float) -> str:
    if hours < 4:
        return "Quá hạn vài tiếng rồi — xử lý hoặc báo block ngay."
    elif hours < 24:
        return "Hơn nửa ngày trôi qua — task này cần quyết định."
    else:
        return f"Trễ {hours:.0f} tiếng — escalate hoặc cancel nếu không còn relevant."


def get_eod_roast(done: int, pending: int, overdue: int) -> str:
    if overdue == 0 and done >= 5:
        msgs = [
            f"Ngày tốt — {done} done, 0 overdue. Đúng hướng.",
            f"{done} task cleared hôm nay. Solid.",
        ]
    elif overdue > 3:
        msgs = [
            f"{overdue} task trễ — cần review lại capacity của team.",
            f"Overdue cao ({overdue}) — ngày mai prioritize lại.",
        ]
    else:
        msgs = [
            f"{done} done, {pending} pending. Ổn.",
            f"Wrap up: {done} xong, {pending} còn lại.",
        ]
    return random.choice(msgs)


def get_assign_confirmation(assignee_name: str, task_summary: str) -> str:
    msgs = [
        f"Đã giao cho {assignee_name}.",
        f"Task gửi {assignee_name} rồi.",
        f"{assignee_name} nhận được task.",
    ]
    return random.choice(msgs)


def get_workload_warning(name: str, count: int) -> str:
    return f"{name} đang có {count} task — workload khá cao."
