"""
Roles — permission constants and checks for multi-user team bot.
"""

import os

MANAGER    = "manager"
TEAM_LEAD  = "team_lead"
EMPLOYEE   = "employee"

ROLE_LABELS = {
    MANAGER:   "Manager",
    TEAM_LEAD: "Team Lead",
    EMPLOYEE:  "Nhân viên",
}

ROLE_RANK = {MANAGER: 3, TEAM_LEAD: 2, EMPLOYEE: 1}

MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))


def is_manager(user: dict) -> bool:
    return user and user.get("role") == MANAGER


def is_team_lead(user: dict) -> bool:
    return user and user.get("role") in (MANAGER, TEAM_LEAD)


def can_assign(user: dict) -> bool:
    """Manager and TL can assign tasks."""
    return user and user.get("role") in (MANAGER, TEAM_LEAD)


def can_see_team(user: dict) -> bool:
    """Manager and TL can see team dashboard."""
    return user and user.get("role") in (MANAGER, TEAM_LEAD)


def can_approve_users(user: dict) -> bool:
    return user and user.get("role") == MANAGER


def can_set_roles(user: dict) -> bool:
    return user and user.get("role") == MANAGER


def can_see_task(user: dict, task: dict) -> bool:
    """Check if user has permission to see/act on a task."""
    if not user or not task:
        return False
    if user["role"] == MANAGER:
        return True
    if user["role"] == TEAM_LEAD:
        return (
            task.get("assignee_id") == user["telegram_id"]
            or task.get("team") == user.get("team")
        )
    return task.get("assignee_id") == user["telegram_id"]


def rank(role: str) -> int:
    return ROLE_RANK.get(role, 0)
