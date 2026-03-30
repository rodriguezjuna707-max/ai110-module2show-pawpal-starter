import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Priority, PetTask, Pet, Owner, Scheduler, DailySchedule



# ---------------------------------------------------------------------------
# Simple standalone tests
# ---------------------------------------------------------------------------

def test_task_completion_changes_status():
    task = PetTask("Give medication", "health", 5, Priority.CRITICAL)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(PetTask("Evening walk", "exercise", 20, Priority.MEDIUM))
    assert len(pet.tasks) == 1










# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_owner():
    return Owner(
        name="Jordan",
        available_minutes_per_day=60,
        preferred_schedule_start="08:00",
    )


@pytest.fixture
def basic_pet():
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(PetTask(
        title="Morning walk",
        category="exercise",
        duration_minutes=30,
        priority=Priority.HIGH,
        preferred_time_of_day="morning",
        is_required=True,
    ))
    pet.add_task(PetTask(
        title="Breakfast",
        category="feeding",
        duration_minutes=10,
        priority=Priority.CRITICAL,
        preferred_time_of_day="morning",
        is_required=True,
    ))
    pet.add_task(PetTask(
        title="Play session",
        category="enrichment",
        duration_minutes=15,
        priority=Priority.MEDIUM,
    ))
    return pet


# ---------------------------------------------------------------------------
# PetTask tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPet:
    def test_add_task(self, basic_pet):
        assert len(basic_pet.tasks) == 3

    def test_remove_task_returns_true_when_found(self, basic_pet):
        task_id = basic_pet.tasks[0].task_id
        result = basic_pet.remove_task(task_id)
        assert result is True
        assert len(basic_pet.tasks) == 2

    def test_remove_task_returns_false_when_missing(self, basic_pet):
        result = basic_pet.remove_task("nonexistent-id")
        assert result is False

    def test_get_tasks_by_priority_order(self, basic_pet):
        sorted_tasks = basic_pet.get_tasks_by_priority()
        priorities = [t.priority.value for t in sorted_tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_pending_tasks_excludes_completed(self, basic_pet):
        basic_pet.tasks[0].mark_complete()
        pending = basic_pet.get_pending_tasks()
        assert len(pending) == 2

    def test_reset_completion(self, basic_pet):
        for task in basic_pet.tasks:
            task.mark_complete()
        basic_pet.reset_completion()
        assert all(not t.completed for t in basic_pet.tasks)

    def test_get_task_by_id(self, basic_pet):
        task_id = basic_pet.tasks[1].task_id
        found = basic_pet.get_task_by_id(task_id)
        assert found is not None
        assert found.task_id == task_id

    def test_get_task_by_id_missing_returns_none(self, basic_pet):
        assert basic_pet.get_task_by_id("bad-id") is None


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

class TestOwner:
    def test_add_pet(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        assert len(basic_owner.get_pets()) == 1

    def test_remove_pet(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        result = basic_owner.remove_pet("Mochi")
        assert result is True
        assert len(basic_owner.get_pets()) == 0

    def test_remove_pet_missing_returns_false(self, basic_owner):
        assert basic_owner.remove_pet("Ghost") is False

    def test_get_pet_by_name(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        found = basic_owner.get_pet("Mochi")
        assert found is not None
        assert found.name == "Mochi"

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
        pending = basic_owner.get_all_pending_tasks()
        assert len(pending) == 2


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestScheduler:
    def test_schedule_produces_daily_schedule(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(basic_pet)
        assert isinstance(result, DailySchedule)

    def test_schedule_respects_time_budget(self, basic_owner, basic_pet):
        basic_owner.set_availability(30)  # only enough for one 30-min task
        basic_owner.add_pet(basic_pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(basic_pet)
        assert result.total_minutes_used <= 30

    def test_required_tasks_scheduled_before_optional(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(basic_pet)
        scheduled_titles = [st.task.title for st in result.scheduled_tasks]
        required_indices = [i for i, st in enumerate(result.scheduled_tasks) if st.task.is_required]
        optional_indices = [i for i, st in enumerate(result.scheduled_tasks) if not st.task.is_required]
        if required_indices and optional_indices:
            assert max(required_indices) < min(optional_indices)

    def test_skipped_tasks_tracked_when_over_budget(self, basic_owner, basic_pet):
        basic_owner.set_availability(10)  # only 10 min — most tasks skipped
        basic_owner.add_pet(basic_pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(basic_pet)
        assert len(result.skipped_tasks) > 0

    def test_scheduled_task_times_are_sequential(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(basic_pet)
        for i in range(1, len(result.scheduled_tasks)):
            prev_end = result.scheduled_tasks[i - 1].end_time
            curr_start = result.scheduled_tasks[i].start_time
            assert curr_start >= prev_end

    def test_prioritize_puts_critical_first(self, basic_owner):
        tasks = [
            PetTask("Low task", "misc", 5, Priority.LOW),
            PetTask("Critical task", "health", 5, Priority.CRITICAL, is_required=True),
            PetTask("Medium task", "misc", 5, Priority.MEDIUM),
        ]
        scheduler = Scheduler(basic_owner)
        ordered = scheduler.prioritize(tasks)
        assert ordered[0].priority == Priority.CRITICAL

    def test_fits_in_day_true_when_enough_time(self, basic_owner):
        scheduler = Scheduler(basic_owner)
        task = PetTask("Walk", "exercise", 20, Priority.HIGH)
        assert scheduler.fits_in_day(task, used_minutes=30, budget=60) is True

    def test_fits_in_day_false_when_over_budget(self, basic_owner):
        scheduler = Scheduler(basic_owner)
        task = PetTask("Walk", "exercise", 40, Priority.HIGH)
        assert scheduler.fits_in_day(task, used_minutes=30, budget=60) is False

    def test_reasoning_summary_populated(self, basic_owner, basic_pet):
        basic_owner.add_pet(basic_pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(basic_pet)
        assert result.reasoning_summary != ""

    def test_schedule_all_pets_returns_one_per_pet(self, basic_owner, basic_pet):
        luna = Pet(name="Luna", species="cat")
        luna.add_task(PetTask("Feeding", "feeding", 10, Priority.HIGH, is_required=True))
        basic_owner.add_pet(basic_pet)
        basic_owner.add_pet(luna)
        scheduler = Scheduler(basic_owner)
        results = scheduler.schedule_all_pets()
        assert len(results) == 2

    def test_preferred_time_slot_honored(self, basic_owner):
        pet = Pet(name="Rex", species="dog")
        pet.add_task(PetTask(
            title="Afternoon walk",
            category="exercise",
            duration_minutes=20,
            priority=Priority.MEDIUM,
            preferred_time_of_day="afternoon",
        ))
        basic_owner.add_pet(pet)
        scheduler = Scheduler(basic_owner)
        result = scheduler.schedule(pet)
        assert result.scheduled_tasks[0].start_time >= "12:00"

