from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import uuid


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class PetTask:
    """A single pet care activity."""
    title: str
    category: str
    duration_minutes: int
    priority: Priority
    frequency: str = "daily"          # "daily", "weekly", "as_needed"
    preferred_time_of_day: Optional[str] = None  # "morning", "afternoon", "evening"
    is_required: bool = False
    notes: str = ""
    completed: bool = False
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Reset this task to not-done."""
        self.completed = False

    def to_dict(self) -> dict:
        """Serialize the task to a plain dictionary."""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority.name,
            "frequency": self.frequency,
            "preferred_time_of_day": self.preferred_time_of_day,
            "is_required": self.is_required,
            "notes": self.notes,
            "completed": self.completed,
        }

    def __str__(self) -> str:
        """Return a short human-readable summary of the task."""
        status = "X" if self.completed else "o"
        return f"[{status}] {self.title} ({self.duration_minutes}min, {self.priority.name})"


# ---------------------------------------------------------------------------
# ScheduledTask + DailySchedule (output types used by Scheduler)
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A PetTask placed at a concrete time slot with a scheduling reason."""
    task: PetTask
    start_time: str   # "HH:MM"
    end_time: str     # "HH:MM"
    reason: str

    def to_display(self) -> str:
        """Format the scheduled task as a single display line."""
        status = "X" if self.task.completed else "o"
        return (
            f"[{status}] {self.start_time}-{self.end_time}  "
            f"{self.task.title} ({self.task.duration_minutes}min) "
            f"[{self.task.priority.name}] | {self.reason}"
        )


@dataclass
class DailySchedule:
    """The full output of a scheduling run for one pet on one day."""
    date: str
    owner_name: str
    pet_name: str
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[tuple[PetTask, str]] = field(default_factory=list)
    total_minutes_used: int = 0
    reasoning_summary: str = ""

    def add_task(self, scheduled: ScheduledTask) -> None:
        """Append a scheduled task and update the running time total."""
        self.scheduled_tasks.append(scheduled)
        self.total_minutes_used += scheduled.task.duration_minutes

    def skip_task(self, task: PetTask, reason: str) -> None:
        """Record a task that could not be fit into the schedule."""
        self.skipped_tasks.append((task, reason))

    def display(self) -> str:
        """Render the full daily plan as a printable string."""
        lines = [
            f"Daily Plan for {self.pet_name} ({self.date})",
            f"Owner: {self.owner_name}",
            f"Total time: {self.total_minutes_used} min",
            "-" * 48,
        ]
        if self.scheduled_tasks:
            lines.append("Scheduled:")
            for st in self.scheduled_tasks:
                lines.append(f"  {st.to_display()}")
        if self.skipped_tasks:
            lines.append("\nSkipped:")
            for task, reason in self.skipped_tasks:
                lines.append(f"  - {task.title}: {reason}")
        if self.reasoning_summary:
            lines.append(f"\nReasoning: {self.reasoning_summary}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize the full schedule to a plain dictionary."""
        return {
            "date": self.date,
            "owner_name": self.owner_name,
            "pet_name": self.pet_name,
            "scheduled": [st.task.to_dict() | {"start": st.start_time, "end": st.end_time, "reason": st.reason}
                          for st in self.scheduled_tasks],
            "skipped": [{"task": t.to_dict(), "reason": r} for t, r in self.skipped_tasks],
            "total_minutes_used": self.total_minutes_used,
            "reasoning_summary": self.reasoning_summary,
        }


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """Stores pet details and owns a list of care tasks."""
    name: str
    species: str
    breed: str = ""
    age_years: int = 0
    medical_notes: list[str] = field(default_factory=list)
    tasks: list[PetTask] = field(default_factory=list)

    def add_task(self, task: PetTask) -> None:
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID; returns True if found and removed."""
        original_len = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        return len(self.tasks) < original_len

    def get_task_by_id(self, task_id: str) -> Optional[PetTask]:
        """Return the task with the given ID, or None if not found."""
        return next((t for t in self.tasks if t.task_id == task_id), None)

    def get_tasks_by_priority(self) -> list[PetTask]:
        """Return tasks sorted descending by priority, required tasks first."""
        return sorted(
            self.tasks,
            key=lambda t: (t.is_required, t.priority.value),
            reverse=True,
        )

    def get_pending_tasks(self) -> list[PetTask]:
        """Return only tasks not yet marked complete."""
        return [t for t in self.tasks if not t.completed]

    def reset_completion(self) -> None:
        """Reset all tasks to incomplete (start of a new day)."""
        for task in self.tasks:
            task.mark_incomplete()

    def __str__(self) -> str:
        """Return a short summary of the pet and their task count."""
        return f"{self.name} ({self.species}, {self.age_years}yr) — {len(self.tasks)} task(s)"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """Manages multiple pets and provides access to all their tasks."""
    name: str
    email: str = ""
    available_minutes_per_day: int = 120
    preferred_schedule_start: str = "08:00"   # "HH:MM"
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> bool:
        """Remove a pet by name; returns True if found and removed."""
        original_len = len(self.pets)
        self.pets = [p for p in self.pets if p.name != pet_name]
        return len(self.pets) < original_len

    def get_pet(self, pet_name: str) -> Optional[Pet]:
        """Return the pet with the given name, or None if not found."""
        return next((p for p in self.pets if p.name == pet_name), None)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return self.pets

    def set_availability(self, minutes: int) -> None:
        """Update the owner's daily time budget in minutes."""
        if minutes < 0:
            raise ValueError("Available minutes cannot be negative.")
        self.available_minutes_per_day = minutes

    def get_all_tasks(self) -> list[tuple[Pet, PetTask]]:
        """Return every task across all pets as (pet, task) pairs."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def get_all_pending_tasks(self) -> list[tuple[Pet, PetTask]]:
        """Return incomplete tasks across all pets."""
        return [(pet, task) for pet in self.pets for task in pet.get_pending_tasks()]

    def __str__(self) -> str:
        """Return a short summary of the owner and their availability."""
        return f"{self.name} — {len(self.pets)} pet(s), {self.available_minutes_per_day} min/day available"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    The scheduling brain.
    Retrieves tasks from an Owner's pets, prioritizes them, and produces
    a DailySchedule that fits within the owner's available time budget.
    """

    TIME_SLOTS = {
        "morning":   ("06:00", "12:00"),
        "afternoon": ("12:00", "17:00"),
        "evening":   ("17:00", "21:00"),
    }

    def __init__(self, owner: Owner):
        self.owner = owner

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule(self, pet: Pet, date: Optional[str] = None) -> DailySchedule:
        """Build a DailySchedule for one pet using the owner's time budget."""
        date = date or datetime.today().strftime("%Y-%m-%d")
        plan = DailySchedule(
            date=date,
            owner_name=self.owner.name,
            pet_name=pet.name,
        )

        prioritized = self.prioritize(pet.get_pending_tasks())
        current_time = self.owner.preferred_schedule_start
        minutes_used = 0
        budget = self.owner.available_minutes_per_day

        for task in prioritized:
            if not self.fits_in_day(task, minutes_used, budget):
                plan.skip_task(task, f"Not enough time remaining ({budget - minutes_used} min left, needs {task.duration_minutes} min)")
                continue

            start = self._respect_preferred_slot(task, current_time)
            end = self._add_minutes(start, task.duration_minutes)
            reason = self._build_task_reason(task)

            plan.add_task(ScheduledTask(task=task, start_time=start, end_time=end, reason=reason))
            current_time = end
            minutes_used += task.duration_minutes

        plan.reasoning_summary = self.build_reasoning(plan)
        return plan

    def schedule_all_pets(self, date: Optional[str] = None) -> list[DailySchedule]:
        """Produce a DailySchedule for every pet the owner has."""
        return [self.schedule(pet, date) for pet in self.owner.get_pets()]

    def prioritize(self, tasks: list[PetTask]) -> list[PetTask]:
        """
        Sort tasks by:
          1. is_required (required first)
          2. priority value (CRITICAL → LOW)
          3. duration (shorter tasks first as a tiebreaker — easier wins)
        """
        return sorted(
            tasks,
            key=lambda t: (not t.is_required, -t.priority.value, t.duration_minutes),
        )

    def fits_in_day(self, task: PetTask, used_minutes: int, budget: int) -> bool:
        """Return True if the task fits within the remaining daily budget."""
        return (used_minutes + task.duration_minutes) <= budget

    def get_tasks_by_category(self, pet: Pet, category: str) -> list[PetTask]:
        """Filter a pet's tasks by category (e.g. 'walk', 'feeding')."""
        return [t for t in pet.tasks if t.category.lower() == category.lower()]

    def get_high_priority_tasks(self, pet: Pet) -> list[PetTask]:
        """Return all HIGH and CRITICAL tasks for a given pet."""
        return [t for t in pet.tasks if t.priority in (Priority.HIGH, Priority.CRITICAL)]

    def build_reasoning(self, schedule: DailySchedule) -> str:
        """Generate a plain-English summary of scheduling decisions."""
        total = len(schedule.scheduled_tasks) + len(schedule.skipped_tasks)
        scheduled_count = len(schedule.scheduled_tasks)
        skipped_count = len(schedule.skipped_tasks)

        lines = [
            f"Scheduled {scheduled_count} of {total} task(s) within "
            f"{self.owner.available_minutes_per_day} min budget.",
        ]
        if skipped_count:
            skipped_titles = ", ".join(t.title for t, _ in schedule.skipped_tasks)
            lines.append(f"Skipped {skipped_count} task(s) due to time constraints: {skipped_titles}.")
        required = [st for st in schedule.scheduled_tasks if st.task.is_required]
        if required:
            lines.append(f"Required tasks always scheduled first: {', '.join(st.task.title for st in required)}.")
        return " ".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_minutes(self, time_str: str, minutes: int) -> str:
        """Add minutes to a 'HH:MM' string and return a new 'HH:MM' string."""
        t = datetime.strptime(time_str, "%H:%M") + timedelta(minutes=minutes)
        return t.strftime("%H:%M")

    def _respect_preferred_slot(self, task: PetTask, current_time: str) -> str:
        """
        If the task has a preferred time of day and we haven't passed that
        window yet, jump the cursor to the start of that window.
        Otherwise stay at current_time so we don't create gaps.
        """
        if task.preferred_time_of_day and task.preferred_time_of_day in self.TIME_SLOTS:
            slot_start, _ = self.TIME_SLOTS[task.preferred_time_of_day]
            if current_time < slot_start:
                return slot_start          # fast-forward to preferred window
        return current_time                # preferred window passed or no preference

    def _build_task_reason(self, task: PetTask) -> str:
        """Compose a short reason string explaining why this task was scheduled."""
        parts = []
        if task.is_required:
            parts.append("required")
        parts.append(f"priority={task.priority.name}")
        if task.preferred_time_of_day:
            parts.append(f"preferred={task.preferred_time_of_day}")
        return ", ".join(parts)
