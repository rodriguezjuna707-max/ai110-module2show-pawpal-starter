"""
Pytest test suite for PawPal+ pet scheduler (pawpal_system.py).

Covers six areas:
  1. PetTask — completion, serialization, unique IDs
  2. Pet     — task management, priority ordering, pending queries
  3. Owner   — pet roster, availability, filter_tasks
  4. Sorting correctness (Scheduler.sort_by_time)
  5. Recurrence logic   (Pet.complete_task / PetTask.is_due_today)
  6. Conflict detection (Scheduler.detect_conflicts / detect_cross_pet_conflicts)
  7. Scheduling happy paths (Scheduler.schedule / schedule_all_pets)
"""

import sys
import os
import pytest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import (
    DailySchedule,
    Owner,
    Pet,
    PetTask,
    Priority,
    ScheduledTask,
    Scheduler,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task(title="Task", category="care", duration=30, priority=Priority.MEDIUM,
          frequency="daily", preferred_time=None, is_required=False, **kwargs):
    """Shorthand factory for PetTask with sensible defaults."""
    return PetTask(
        title=title,
        category=category,
        duration_minutes=duration,
        priority=priority,
        frequency=frequency,
        preferred_time_of_day=preferred_time,
        is_required=is_required,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner():
    """Owner with a 120-minute daily budget — used by sorting/recurrence/conflict tests."""
    return Owner(name="Alice", available_minutes_per_day=120, preferred_schedule_start="08:00")


@pytest.fixture
def basic_owner():
    """Owner with a 60-minute daily budget — used by Pet/Owner/Scheduler unit tests."""
    return Owner(name="Jordan", available_minutes_per_day=60, preferred_schedule_start="08:00")


@pytest.fixture
def pet():
    """A pet with no tasks."""
    return Pet(name="Mochi", species="dog")


@pytest.fixture
def basic_pet():
    """A pet pre-loaded with three tasks of varying priority."""
    p = Pet(name="Mochi", species="dog")
    p.add_task(PetTask("Morning walk", "exercise", 30, Priority.HIGH,
                       preferred_time_of_day="morning", is_required=True))
    p.add_task(PetTask("Breakfast", "feeding", 10, Priority.CRITICAL,
                       preferred_time_of_day="morning", is_required=True))
    p.add_task(PetTask("Play session", "enrichment", 15, Priority.MEDIUM))
    return p


@pytest.fixture
def scheduler(owner):
    """Scheduler bound to the 120-minute owner."""
    return Scheduler(owner)


# ===================================================================
# 1. PetTask
# ===================================================================

class TestPetTask:
    def test_mark_complete(self):
        task = PetTask("Walk", "exercise", 20, Priority.HIGH)
        task.mark_complete()
        assert task.completed is True

    def test_mark_incomplete(self):
        task = PetTask("Walk", "exercise", 20, Priority.HIGH)
        task.mark_complete()
        task.mark_incomplete()
        assert task.completed is False

    def test_to_dict_contains_required_keys(self):
        task = PetTask("Walk", "exercise", 20, Priority.HIGH)
        d = task.to_dict()
        for key in ("task_id", "title", "category", "duration_minutes", "priority", "completed"):
            assert key in d

    def test_to_dict_priority_is_string(self):
        task = PetTask("Walk", "exercise", 20, Priority.HIGH)
        assert task.to_dict()["priority"] == "HIGH"

    def test_unique_task_ids(self):
        t1 = PetTask("Walk", "exercise", 20, Priority.HIGH)
        t2 = PetTask("Walk", "exercise", 20, Priority.HIGH)
        assert t1.task_id != t2.task_id


# ===================================================================
# 2. Pet
# ===================================================================

class TestPet:
    def test_add_task_increases_count(self):
        p = Pet(name="Buddy", species="dog")
        p.add_task(PetTask("Evening walk", "exercise", 20, Priority.MEDIUM))
        assert len(p.tasks) == 1

    def test_remove_task_returns_true_when_found(self, basic_pet):
        task_id = basic_pet.tasks[0].task_id
        assert basic_pet.remove_task(task_id) is True
        assert len(basic_pet.tasks) == 2

    def test_remove_task_returns_false_when_missing(self, basic_pet):
        assert basic_pet.remove_task("nonexistent-id") is False

    def test_get_tasks_by_priority_order(self, basic_pet):
        sorted_tasks = basic_pet.get_tasks_by_priority()
        priorities = [t.priority.value for t in sorted_tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_pending_tasks_excludes_completed(self, basic_pet):
        basic_pet.tasks[0].mark_complete()
        assert len(basic_pet.get_pending_tasks()) == 2

    def test_reset_completion(self, basic_pet):
        for task in basic_pet.tasks:
            task.mark_complete()
        basic_pet.reset_completion()
        assert all(not t.completed for t in basic_pet.tasks)

    def test_get_task_by_id(self, basic_pet):
        task_id = basic_pet.tasks[1].task_id
        found = basic_pet.get_task_by_id(task_id)
        assert found is not None and found.task_id == task_id

    def test_get_task_by_id_missing_returns_none(self, basic_pet):
        assert basic_pet.get_task_by_id("bad-id") is None


# ===================================================================
# 3. Owner
# ===================================================================

class TestOwner:
    def test_add_pet(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        assert len(basic_owner.get_pets()) == 1

    def test_remove_pet(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        assert basic_owner.remove_pet("Mochi") is True
        assert len(basic_owner.get_pets()) == 0

    def test_remove_pet_missing_returns_false(self, basic_owner):
        assert basic_owner.remove_pet("Ghost") is False

    def test_get_pet_by_name(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        found = basic_owner.get_pet("Mochi")
        assert found is not None and found.name == "Mochi"

    def test_set_availability(self, basic_owner):
        basic_owner.set_availability(90)
        assert basic_owner.available_minutes_per_day == 90

    def test_set_availability_negative_raises(self, basic_owner):
        with pytest.raises(ValueError):
            basic_owner.set_availability(-10)

    def test_get_all_tasks(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        all_tasks = basic_owner.get_all_tasks()
        assert len(all_tasks) == 3
        assert all(isinstance(pair, tuple) for pair in all_tasks)

    def test_get_all_pending_tasks_excludes_completed(self, basic_owner, basic_pet):
        basic_pet.tasks[0].mark_complete()
        basic_owner.add_pet(basic_pet)
        assert len(basic_owner.get_all_pending_tasks()) == 2


# ===================================================================
# 4. Sorting Correctness  (Scheduler.sort_by_time)
# ===================================================================

class TestSortByTime:
    def test_chronological_order(self, scheduler):
        tasks = [
            _task("Evening Walk",   preferred_time="evening"),
            _task("Morning Feed",   preferred_time="morning"),
            _task("Afternoon Play", preferred_time="afternoon"),
            _task("No Pref Groom",  preferred_time=None),
        ]
        result = scheduler.sort_by_time(tasks)
        assert [t.title for t in result] == [
            "Morning Feed", "Afternoon Play", "Evening Walk", "No Pref Groom"
        ]

    def test_shorter_duration_first_within_same_slot(self, scheduler):
        tasks = [
            _task("Long Morning",  duration=60, preferred_time="morning"),
            _task("Short Morning", duration=15, preferred_time="morning"),
        ]
        result = scheduler.sort_by_time(tasks)
        assert result[0].title == "Short Morning"
        assert result[1].title == "Long Morning"

    def test_single_task(self, scheduler):
        result = scheduler.sort_by_time([_task("Solo", preferred_time="afternoon")])
        assert len(result) == 1 and result[0].title == "Solo"

    def test_all_no_preference_sorted_by_duration(self, scheduler):
        tasks = [
            _task("C", duration=20, preferred_time=None),
            _task("A", duration=10, preferred_time=None),
            _task("B", duration=10, preferred_time=None),
        ]
        result = scheduler.sort_by_time(tasks)
        assert result[0].duration_minutes == 10
        assert result[2].duration_minutes == 20

    def test_original_list_not_mutated(self, scheduler):
        tasks = [
            _task("Evening", preferred_time="evening"),
            _task("Morning", preferred_time="morning"),
        ]
        original = [t.title for t in tasks]
        scheduler.sort_by_time(tasks)
        assert [t.title for t in tasks] == original


# ===================================================================
# 5. Recurrence Logic
# ===================================================================

class TestRecurrence:
    def test_complete_daily_task_appends_new_task(self, pet):
        task = _task("Walk", frequency="daily")
        pet.add_task(task)
        next_task = pet.complete_task(task.task_id)

        assert next_task is not None
        assert next_task.next_due_date == (date.today() + timedelta(days=1)).isoformat()

    def test_new_daily_occurrence_is_incomplete_with_different_id(self, pet):
        task = _task("Walk", frequency="daily")
        pet.add_task(task)
        next_task = pet.complete_task(task.task_id)

        assert next_task.completed is False
        assert next_task.task_id != task.task_id

    def test_original_task_marked_complete(self, pet):
        task = _task("Walk", frequency="daily")
        pet.add_task(task)
        pet.complete_task(task.task_id)
        assert task.completed is True

    def test_new_daily_occurrence_not_due_today(self, pet):
        task = _task("Walk", frequency="daily")
        pet.add_task(task)
        next_task = pet.complete_task(task.task_id)
        assert next_task.is_due_today(date.today().isoformat()) is False

    def test_complete_weekly_task_creates_next_in_7_days(self, pet):
        task = _task("Bath", frequency="weekly")
        pet.add_task(task)
        next_task = pet.complete_task(task.task_id)

        assert next_task is not None
        assert next_task.next_due_date == (date.today() + timedelta(days=7)).isoformat()

    def test_complete_as_needed_returns_none(self, pet):
        task = _task("Vet Visit", frequency="as_needed")
        pet.add_task(task)
        assert pet.complete_task(task.task_id) is None

    def test_complete_as_needed_does_not_add_task(self, pet):
        task = _task("Vet Visit", frequency="as_needed")
        pet.add_task(task)
        pet.complete_task(task.task_id)
        assert len(pet.tasks) == 1

    def test_weekly_due_after_7_days(self):
        task = _task("Bath", frequency="weekly")
        task.last_completed_date = (date.today() - timedelta(days=7)).isoformat()
        assert task.is_due_today(date.today().isoformat()) is True

    def test_weekly_not_due_after_6_days(self):
        task = _task("Bath", frequency="weekly")
        task.last_completed_date = (date.today() - timedelta(days=6)).isoformat()
        assert task.is_due_today(date.today().isoformat()) is False

    def test_weekly_due_when_never_completed(self):
        task = _task("Bath", frequency="weekly")
        assert task.is_due_today(date.today().isoformat()) is True

    def test_complete_unknown_task_returns_none(self, pet):
        assert pet.complete_task("nonexistent") is None


# ===================================================================
# 6. Conflict Detection
# ===================================================================

class TestConflictDetection:
    def _make_scheduled(self, title, start, end):
        return ScheduledTask(task=_task(title), start_time=start, end_time=end, reason="test")

    def _make_schedule(self, pet_name, scheduled_tasks):
        s = DailySchedule(date="2026-03-30", owner_name="Alice", pet_name=pet_name)
        s.scheduled_tasks.extend(scheduled_tasks)
        return s

    def test_identical_times_produce_warning(self, scheduler):
        schedule = self._make_schedule("Mochi", [
            self._make_scheduled("Feed", "08:00", "08:30"),
            self._make_scheduled("Walk", "08:00", "08:30"),
        ])
        warnings = scheduler.detect_conflicts(schedule)
        assert len(warnings) == 1 and "overlaps" in warnings[0]

    def test_partially_overlapping_tasks_produce_warning(self, scheduler):
        schedule = self._make_schedule("Mochi", [
            self._make_scheduled("Feed", "08:00", "08:45"),
            self._make_scheduled("Walk", "08:30", "09:15"),
        ])
        warnings = scheduler.detect_conflicts(schedule)
        assert len(warnings) == 1 and "overlaps" in warnings[0]

    def test_adjacent_tasks_no_warning(self, scheduler):
        """A ends at 08:30, B starts at 08:30 — strict < means no overlap."""
        schedule = self._make_schedule("Mochi", [
            self._make_scheduled("Feed", "08:00", "08:30"),
            self._make_scheduled("Walk", "08:30", "09:00"),
        ])
        assert scheduler.detect_conflicts(schedule) == []

    def test_non_overlapping_tasks_no_warning(self, scheduler):
        schedule = self._make_schedule("Mochi", [
            self._make_scheduled("Feed", "08:00", "08:30"),
            self._make_scheduled("Walk", "09:00", "09:30"),
        ])
        assert scheduler.detect_conflicts(schedule) == []

    def test_cross_pet_overlap_produces_warning(self, scheduler):
        sched_mochi = self._make_schedule("Mochi", [self._make_scheduled("Feed Mochi", "08:00", "08:30")])
        sched_bella = self._make_schedule("Bella", [self._make_scheduled("Feed Bella", "08:15", "08:45")])
        warnings = scheduler.detect_cross_pet_conflicts([sched_mochi, sched_bella])
        assert len(warnings) == 1 and "cross-pet" in warnings[0]

    def test_same_pet_not_double_reported_in_cross_pet(self, scheduler):
        """Same-pet overlaps are not reported by detect_cross_pet_conflicts."""
        schedule = self._make_schedule("Mochi", [
            self._make_scheduled("Feed", "08:00", "08:30"),
            self._make_scheduled("Walk", "08:00", "08:30"),
        ])
        assert scheduler.detect_cross_pet_conflicts([schedule]) == []

    def test_cross_pet_no_overlap(self, scheduler):
        sched_mochi = self._make_schedule("Mochi", [self._make_scheduled("Feed Mochi", "08:00", "08:30")])
        sched_bella = self._make_schedule("Bella", [self._make_scheduled("Feed Bella", "09:00", "09:30")])
        assert scheduler.detect_cross_pet_conflicts([sched_mochi, sched_bella]) == []


# ===================================================================
# 7. Scheduling Happy Paths  (Scheduler.schedule / schedule_all_pets)
# ===================================================================

class TestScheduleHappyPath:
    def test_schedule_produces_daily_schedule(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        result = Scheduler(basic_owner).schedule(basic_pet)
        assert isinstance(result, DailySchedule)

    def test_all_tasks_fit_in_budget(self, owner, pet, scheduler):
        owner.add_pet(pet)
        pet.add_task(_task("Feed", duration=30))
        pet.add_task(_task("Walk", duration=30))
        plan = scheduler.schedule(pet, date="2026-03-30")
        assert len(plan.scheduled_tasks) == 2 and len(plan.skipped_tasks) == 0

    def test_task_over_budget_is_skipped(self, owner, pet, scheduler):
        owner.set_availability(40)
        owner.add_pet(pet)
        pet.add_task(_task("Short Walk", duration=30))
        pet.add_task(_task("Long Hike",  duration=60))
        plan = scheduler.schedule(pet, date="2026-03-30")
        assert "Short Walk" in [st.task.title for st in plan.scheduled_tasks]
        assert "Long Hike"  in [t.title for t, _ in plan.skipped_tasks]

    def test_schedule_respects_time_budget(self, basic_owner, basic_pet):
        basic_owner.set_availability(30)
        basic_owner.add_pet(basic_pet)
        result = Scheduler(basic_owner).schedule(basic_pet)
        assert result.total_minutes_used <= 30

    def test_pet_with_no_tasks_gives_empty_schedule(self, owner, pet, scheduler):
        owner.add_pet(pet)
        plan = scheduler.schedule(pet, date="2026-03-30")
        assert plan.scheduled_tasks == [] and plan.skipped_tasks == []

    def test_required_task_scheduled_before_optional(self, owner, pet, scheduler):
        owner.add_pet(pet)
        pet.add_task(_task("Optional Critical", duration=30, priority=Priority.CRITICAL, is_required=False))
        pet.add_task(_task("Required Low",      duration=30, priority=Priority.LOW,      is_required=True))
        plan = scheduler.schedule(pet, date="2026-03-30")
        titles = [st.task.title for st in plan.scheduled_tasks]
        assert titles.index("Required Low") < titles.index("Optional Critical")

    def test_skipped_tasks_tracked_when_over_budget(self, basic_owner, basic_pet):
        basic_owner.set_availability(10)
        basic_owner.add_pet(basic_pet)
        result = Scheduler(basic_owner).schedule(basic_pet)
        assert len(result.skipped_tasks) > 0

    def test_total_minutes_used_is_correct(self, owner, pet, scheduler):
        owner.add_pet(pet)
        pet.add_task(_task("Feed", duration=20))
        pet.add_task(_task("Walk", duration=40))
        plan = scheduler.schedule(pet, date="2026-03-30")
        assert plan.total_minutes_used == 60

    def test_schedule_reasoning_mentions_skipped(self, owner, pet, scheduler):
        owner.set_availability(20)
        owner.add_pet(pet)
        pet.add_task(_task("Quick Feed", duration=15))
        pet.add_task(_task("Long Bath",  duration=60))
        plan = scheduler.schedule(pet, date="2026-03-30")
        assert "Skipped" in plan.reasoning_summary and "Long Bath" in plan.reasoning_summary

    def test_reasoning_summary_populated(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        result = Scheduler(basic_owner).schedule(basic_pet)
        assert result.reasoning_summary != ""

    def test_scheduled_task_times_are_sequential(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        result = Scheduler(basic_owner).schedule(basic_pet)
        for i in range(1, len(result.scheduled_tasks)):
            assert result.scheduled_tasks[i].start_time >= result.scheduled_tasks[i - 1].end_time

    def test_preferred_time_slot_honored(self, basic_owner):
        p = Pet(name="Rex", species="dog")
        p.add_task(PetTask("Afternoon walk", "exercise", 20, Priority.MEDIUM,
                           preferred_time_of_day="afternoon"))
        basic_owner.add_pet(p)
        result = Scheduler(basic_owner).schedule(p)
        assert result.scheduled_tasks[0].start_time >= "12:00"

    def test_prioritize_puts_critical_first(self, basic_owner):
        tasks = [
            PetTask("Low task",      "misc",   5, Priority.LOW),
            PetTask("Critical task", "health", 5, Priority.CRITICAL, is_required=True),
            PetTask("Medium task",   "misc",   5, Priority.MEDIUM),
        ]
        ordered = Scheduler(basic_owner).prioritize(tasks)
        assert ordered[0].priority == Priority.CRITICAL

    def test_fits_in_day_true(self, basic_owner):
        task = PetTask("Walk", "exercise", 20, Priority.HIGH)
        assert Scheduler(basic_owner).fits_in_day(task, used_minutes=30, budget=60) is True

    def test_fits_in_day_false(self, basic_owner):
        task = PetTask("Walk", "exercise", 40, Priority.HIGH)
        assert Scheduler(basic_owner).fits_in_day(task, used_minutes=30, budget=60) is False

    def test_schedule_all_pets_returns_one_per_pet(self, basic_owner, basic_pet):
        luna = Pet(name="Luna", species="cat")
        luna.add_task(PetTask("Feeding", "feeding", 10, Priority.HIGH, is_required=True))
        basic_owner.add_pet(basic_pet)
        basic_owner.add_pet(luna)
        results = Scheduler(basic_owner).schedule_all_pets()
        assert len(results) == 2
