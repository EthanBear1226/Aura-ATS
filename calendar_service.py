"""Calendar boundary. Production deliberately has no Feishu transport yet."""

import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol

from fastapi import HTTPException

import models


SHANGHAI = timezone(timedelta(hours=8))
WORKING_HOURS = (9, 10, 11, 13, 14, 15, 16, 17)


@dataclass(frozen=True)
class BusyInterval:
    start: datetime
    end: datetime


class CalendarUnavailable(Exception):
    pass


class CalendarProvider(Protocol):
    def busy_intervals(self, identity: models.CalendarIdentity,
                       start: datetime, end: datetime) -> list[BusyInterval]:
        """Return a complete authorized window; partial results must raise."""
        ...


class PendingFeishuProvider:
    def busy_intervals(self, identity, start, end):
        raise CalendarUnavailable("Feishu transport is not implemented")


def build_provider() -> CalendarProvider:
    # Replace this factory after OAuth, permissions and token storage are ready.
    return PendingFeishuProvider()


def external_enabled():
    return os.getenv("FEISHU_CALENDAR_ENABLED", "false").lower() in ("true", "1")


def local_time(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(SHANGHAI).replace(tzinfo=None)
    return value


def resolve_interviewer(db, interviewer_id=None, name=None):
    query = db.query(models.Interviewer)
    if interviewer_id is not None:
        person = query.filter(models.Interviewer.id == interviewer_id).first()
        if not person:
            raise HTTPException(404, "面试官不存在")
    else:
        matches = query.filter(models.Interviewer.name == name).all()
        if len(matches) != 1:
            raise HTTPException(422, "请选择已配置且姓名唯一的面试官")
        person = matches[0]
    # Legacy interview records are assigned by name; reject ambiguous mappings.
    if db.query(models.Interviewer).filter(models.Interviewer.name == person.name).count() != 1:
        if db.query(models.Interview.id).filter(
            models.Interview.interviewer_id.is_(None), models.Interview.interviewer_name == person.name
        ).first():
            raise HTTPException(409, "存在无法区分归属的同名历史排期，请先由管理员处理")
    return person


def local_busy(db, person, start, end):
    from sqlalchemy import or_, and_
    rows = db.query(models.Interview).filter(
        or_(models.Interview.interviewer_id == person.id,
            and_(models.Interview.interviewer_id.is_(None), models.Interview.interviewer_name == person.name)),
        models.Interview.status.notin_(["已取消", "已中止"]),
        models.Interview.start_time < end,
        models.Interview.end_time > start,
    ).all()
    return [BusyInterval(row.start_time, row.end_time) for row in rows]


def overlaps(start, end, intervals):
    return any(start < local_time(item.end) and end > local_time(item.start)
               for item in intervals)


def external_busy(db, person, start, end):
    if not external_enabled():
        return "not_connected", [], "飞书日历未接入；仅检查 Aura 内部排期，安排前请另行确认飞书日程。"
    identity = db.query(models.CalendarIdentity).filter_by(interviewer_id=person.id).first()
    if not identity:
        return "unbound", [], "面试官尚未绑定飞书身份，暂不能确认档期。"
    try:
        intervals = build_provider().busy_intervals(
            identity, start.replace(tzinfo=SHANGHAI), end.replace(tzinfo=SHANGHAI))
        # Malformed or partial provider results must never become 'free'.
        for interval in intervals:
            if interval.start.tzinfo is None or interval.end.tzinfo is None or interval.end <= interval.start:
                raise CalendarUnavailable("Invalid busy interval")
        return "connected", intervals, "已检查 Aura 与飞书日历。"
    except Exception:
        return "unavailable", [], "飞书日历暂不可用，未确认档期，请稍后重试。"


def get_availability(db, person, date_str):
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(422, "日期格式应为 YYYY-MM-DD")
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    internal = local_busy(db, person, start, end)
    status, external, message = external_busy(db, person, start, end)
    slots = []
    for hour in WORKING_HOURS:
        slot_start = start + timedelta(hours=hour)
        slot_end = slot_start + timedelta(hours=1)
        local_conflict = overlaps(slot_start, slot_end, internal)
        external_conflict = overlaps(slot_start, slot_end, external) if status == "connected" else None
        selectable = not local_conflict and (status == "not_connected" or
                                            (status == "connected" and not external_conflict))
        label = "Aura 已占用" if local_conflict else (
            "飞书已占用" if external_conflict else (
                "空闲" if status == "connected" else (
                    "Aura 无冲突 · 飞书未检查" if status == "not_connected" else "档期待确认")))
        slots.append({"time": slot_start.strftime("%H:%M"), "isFree": selectable,
                      "local_busy": local_conflict, "external_busy": external_conflict, "label": label})
    return {"interviewer_id": person.id, "timezone": "Asia/Shanghai", "date": day.isoformat(),
            "external_status": status, "scope": "combined" if status == "connected" else "local_only",
            "message": message, "checked_at": datetime.now(timezone.utc).isoformat(), "slots": slots}


def validate_booking(db, person, start, end):
    start, end = local_time(start), local_time(end)
    if end <= start or end - start > timedelta(hours=8):
        raise HTTPException(422, "面试结束时间应晚于开始时间，且时长不超过 8 小时")
    if overlaps(start, end, local_busy(db, person, start, end)):
        raise HTTPException(409, "该面试官在 Aura 中已有重叠排期，请重新选择时间")
    status, intervals, message = external_busy(db, person, start, end)
    if status in ("unbound", "unavailable"):
        raise HTTPException(503, message)
    if overlaps(start, end, intervals):
        raise HTTPException(409, "该面试官的飞书日程存在冲突，请重新选择时间")
    return start, end
