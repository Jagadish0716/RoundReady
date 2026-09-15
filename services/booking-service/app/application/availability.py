"""Materialize the rolling availability horizon using service-owned HTTP contracts."""

from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from app.application.booking_service import BookingService
from app.domain.models import InterviewerEligibility, Slot, SlotStatus
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert


class Rule(BaseModel):
    weekday: int
    start_time: time
    end_time: time
    timezone: str


class Blockout(BaseModel):
    starts_at: datetime
    ends_at: datetime


class Skill(BaseModel):
    domain: str
    topic: str
    skill_name: str


class Snapshot(BaseModel):
    interviewer_id: UUID
    verified: bool
    deleted: bool
    observed_at: datetime
    rules: list[Rule]
    blockouts: list[Blockout]
    skills: list[Skill]


def windows(
    snapshot: Snapshot, now: datetime, duration_minutes: int
) -> set[tuple[datetime, datetime]]:
    result: set[tuple[datetime, datetime]] = set()
    duration = timedelta(minutes=duration_minutes)
    for rule in snapshot.rules:
        zone = ZoneInfo(rule.timezone)
        today = now.astimezone(zone).date()
        for offset in range(31):
            day = today + timedelta(days=offset)
            if day.weekday() != rule.weekday:
                continue
            start = datetime.combine(day, rule.start_time, zone)
            end = datetime.combine(day, rule.end_time, zone)
            while start + duration <= end:
                finish = start + duration
                first, last = start.astimezone(UTC), finish.astimezone(UTC)
                # Skip nonexistent DST times and windows that change real duration.
                valid = first.astimezone(zone).replace(tzinfo=None) == start.replace(tzinfo=None)
                if (
                    valid
                    and last - first == duration
                    and first > now
                    and first < now + timedelta(days=30)
                    and not any(
                        b.starts_at < last and b.ends_at > first for b in snapshot.blockouts
                    )
                ):
                    result.add((first, last))
                start = finish
    return result


async def synchronize(service: BookingService) -> int:
    settings = service.settings
    headers = {
        "X-User-ID": "00000000-0000-0000-0000-000000000001",
        "X-User-Role": "admin",
        "X-Internal-Identity-Secret": settings.internal_identity_secret.get_secret_value(),
    }
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        response = await client.get(f"{settings.interviewer_service_url}/v1/internal/availability")
        response.raise_for_status()
        snapshots = [Snapshot.model_validate(x) for x in response.json()]
        rubric_response = await client.post(
            f"{settings.interview_service_url}/v1/internal/rubrics/default"
        )
        rubric_response.raise_for_status()
        rubric_id = UUID(rubric_response.json()["id"])
    count = 0
    for snapshot in snapshots:
        await service.set_interviewer_eligibility(
            uuid4(),
            snapshot.interviewer_id,
            snapshot.verified,
            "interviewer.deleted.v1" if snapshot.deleted else "interviewer.snapshot.v1",
            snapshot.observed_at,
        )
        # Serialize against eligibility events; a stale snapshot cannot republish slots.
        eligibility = await service.session.scalar(
            select(InterviewerEligibility)
            .where(InterviewerEligibility.interviewer_id == snapshot.interviewer_id)
            .with_for_update()
        )
        if eligibility is None or eligibility.updated_at > snapshot.observed_at:
            await service.session.commit()
            continue
        now = datetime.now(UTC)
        desired = (
            windows(snapshot, now, settings.session_duration_minutes)
            if (eligibility.verified and snapshot.skills)
            else set()
        )
        existing = list(
            (
                await service.session.scalars(
                    select(Slot)
                    .where(
                        Slot.interviewer_id == snapshot.interviewer_id,
                        Slot.starts_at > now,
                    )
                    .with_for_update()
                )
            ).all()
        )
        occupied = [
            s
            for s in existing
            if s.status == SlotStatus.BOOKED
            or (s.status == SlotStatus.HELD and s.hold_expires_at and s.hold_expires_at > now)
        ]
        desired = {
            (a, b)
            for a, b in desired
            if not any(s.starts_at < b and s.ends_at > a for s in occupied)
        }
        for slot in existing:
            key = (slot.starts_at, slot.ends_at)
            if slot.status == SlotStatus.BOOKED or (
                slot.status == SlotStatus.HELD
                and slot.hold_expires_at
                and slot.hold_expires_at > now
            ):
                continue
            if key not in desired:
                slot.status = SlotStatus.BLOCKED
                slot.hold_expires_at = None
                slot.hold_token_hash = None
                slot.held_by_candidate_id = None
            elif slot.status == SlotStatus.BLOCKED:
                slot.status = SlotStatus.AVAILABLE
        known = {(s.starts_at, s.ends_at) for s in existing}
        if snapshot.skills:
            skill = snapshot.skills[0]
            for first, last in desired - known:
                await service.session.execute(
                    insert(Slot)
                    .values(
                        id=uuid4(),
                        interviewer_id=snapshot.interviewer_id,
                        rubric_id=rubric_id,
                        domain=skill.domain,
                        topic="professional_skills",
                        experience_level="all",
                        starts_at=first,
                        ends_at=last,
                        status=SlotStatus.AVAILABLE,
                    )
                    .on_conflict_do_nothing(constraint="uq_interviewer_slot")
                )
                count += 1
        await service.session.commit()
    return count
