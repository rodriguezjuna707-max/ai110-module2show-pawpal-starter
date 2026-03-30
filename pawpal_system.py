from enum import Enum
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
    last_completed_date: Optional[str] = None   # "YYYY-MM-DD", set by mark_complete
    next_due_date: Optional[str] = None          # "YYYY-MM-DD", set on recurring copies
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def mark_complete(self) -> None:
        """Mark this task as done and record today's date for recurrence tracking."""
        self.completed = True
        self.last_completed_date = datetime.today().strftime("%Y-%m-%d")

    def mark_incomplete(self) -> None:
        """Reset this task to not-done."""
        self.completed = False

    def next_occurrence(self) -> "PetTask":
        """
        Create a fresh copy of this task scheduled for its next due date.

        Uses ``timedelta`` to calculate ``next_due_date`` from today:
          - ``"daily"``  → today + 1 day
          - ``"weekly"`` → today + 7 days

        The copy gets a new ``task_id`` and cleared completion state so it
        appears as a brand-new pending task. ``is_due_today()`` will suppress
        it until ``next_due_date`` arrives.

        Returns:
            A new ``PetTask`` with the same scheduling attributes as this one
            and ``next_due_date`` set to the next occurrence date.
        """
        today = date.today()
        interval = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}
        due = today + interval.get(self.frequency, timedelta(days=1))

        return PetTask(
            title=self.title,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            preferred_time_of_day=self.preferred_time_of_day,
            is_required=self.is_required,
            notes=self.notes,
            next_due_date=due.isoformat(),
        )

    def is_due_today(self, today: Optional[str] = None) -> bool:
        """
        Determine whether this task should appear in today's schedule.

        Frequency rules:
          - "daily":     due unless already completed today.
          - "weekly":    due unless completed within the last 7 days.
          - "as_needed": always due — never auto-suppressed.
        Recurring copies created by next_occurrence() carry a next_due_date
        and are suppressed until that date arrives.

        Args:
            today: ISO date string (``"YYYY-MM-DD"``) to evaluate against.
                   Defaults to the real current date when omitted.

        Returns:
            True if the task should be included in today's pending list,
            False if it is already done or not yet due.
        """
        today_str = today or datetime.today().strftime("%Y-%m-%d")
        today_date = date.fromisoformat(today_str)

        # A recurring copy is not due until its calculated next_due_date.
        if self.next_due_date and today_date < date.fromisoformat(self.next_due_date):
            return False

        if self.frequency == "daily":
            return not self.completed
        if self.frequency == "weekly":
            if not self.last_completed_date:
                return True
            delta = today_date - date.fromisoformat(self.last_completed_date)
            return delta.days >= 7
        # "as_needed" or any unrecognised frequency: always show
        return True

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

    def get_pending_tasks(self, today: Optional[str] = None) -> list[PetTask]:
        """Return tasks that are due today based on their frequency and completion state."""
        return [t for t in self.tasks if t.is_due_today(today)]

    def complete_task(self, task_id: str) -> Optional[PetTask]:
        """
        Mark a task complete and auto-schedule its next occurrence if recurring.

        For ``"daily"`` and ``"weekly"`` tasks, calls ``next_occurrence()`` and
        appends the resulting copy to this pet's task list so the recurrence is
        always present without manual re-entry.

        Args:
            task_id: The 8-character ID of the task to complete.

        Returns:
            The newly created ``PetTask`` for the next occurrence if the task
            is recurring, or ``None`` for ``"as_needed"`` tasks and unknown IDs.
        """
        task = self.get_task_by_id(task_id)
        if task is None:
            return None
        task.mark_complete()
        if task.frequency in ("daily", "weekly"):
            next_task = task.next_occurrence()
            self.tasks.append(next_task)
            return next_task
        return None

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

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
        priority: Optional[Priority] = None,
        category: Optional[str] = None,
    ) -> list[tuple[Pet, PetTask]]:
        """
        Query tasks across all pets with optional filter criteria.

        All parameters are optional and combinable — only the provided filters
        are applied. Omitting all parameters returns every task for every pet.

        Args:
            pet_name:  Case-sensitive pet name to filter by (e.g. ``"Mochi"``).
            completed: ``True`` to return only completed tasks, ``False`` for
                       pending tasks, or ``None`` to return both.
            priority:  A ``Priority`` enum value to match exactly.
            category:  Category string to match (case-insensitive).

        Returns:
            A list of ``(Pet, PetTask)`` tuples satisfying all given filters.
        """
        results = self.get_all_tasks()
        if pet_name is not None:
            results = [(p, t) for p, t in results if p.name == pet_name]
        if completed is not None:
            results = [(p, t) for p, t in results if t.completed == completed]
        if priority is not None:
            results = [(p, t) for p, t in results if t.priority == priority]
        if category is not None:
            results = [(p, t) for p, t in results if t.category.lower() == category.lower()]
        return results

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
        warnings = self.detect_conflicts(plan)
        if warnings:
            plan.reasoning_summary += " " + " ".join(warnings)
        return plan

    def schedule_all_pets(self, date: Optional[str] = None) -> list[DailySchedule]:
        """
        Produce a DailySchedule for every pet the owner has, then check for
        time conflicts across all pets and append any warnings to each schedule's
        reasoning_summary.
        """
        schedules = [self.schedule(pet, date) for pet in self.owner.get_pets()]
        cross_warnings = self.detect_cross_pet_conflicts(schedules)
        if cross_warnings:
            warning_block = " ".join(cross_warnings)
            for s in schedules:
                s.reasoning_summary += f" {warning_block}"
        return schedules

    # Maps preferred_time_of_day to a sort order so tasks flow naturally
    # through the day: morning → afternoon → evening → no preference last.
    _TIME_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}

    def prioritize(self, tasks: list[PetTask]) -> list[PetTask]:
        """
        Sort tasks by:
          1. is_required (required first)
          2. priority value (CRITICAL → LOW)
          3. preferred_time_of_day (morning → afternoon → evening → none)
          4. duration (shorter tasks first as a tiebreaker — easier wins)
        """
        return sorted(
            tasks,
            key=lambda t: (
                not t.is_required,
                -t.priority.value,
                self._TIME_ORDER.get(t.preferred_time_of_day, 3),
                t.duration_minutes,
            ),
        )

    def sort_by_time(self, tasks: list[PetTask]) -> list[PetTask]:
        """
        Sort tasks in chronological time-of-day order.

        Sort key: ``preferred_time_of_day`` (morning → afternoon → evening),
        with tasks that have no time preference placed last. Within the same
        slot, shorter tasks come first as a secondary tiebreaker.

        Unlike ``prioritize()``, this method ignores ``is_required`` and
        ``priority`` — use it when you want a display-order sort, not a
        scheduling-priority sort.

        Args:
            tasks: List of ``PetTask`` objects to sort.

        Returns:
            A new sorted list; the original list is not modified.
        """
        return sorted(
            tasks,
            key=lambda t: (
                self._TIME_ORDER.get(t.preferred_time_of_day, 3),
                t.duration_minutes,
            ),
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

    def detect_conflicts(self, schedule: DailySchedule) -> list[str]:
        """
        Check a single pet's schedule for overlapping time windows.

        Uses the standard interval-overlap test for every task pair:
            ``a.start < b.end  AND  b.start < a.end``
        Returns warning strings instead of raising exceptions so callers can
        display or log the messages without crashing the program.

        Args:
            schedule: The ``DailySchedule`` to inspect.

        Returns:
            A list of human-readable warning strings, one per conflict found.
            Returns an empty list when no overlaps exist.
        """
        warnings = []
        tasks = schedule.scheduled_tasks
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                a, b = tasks[i], tasks[j]
                if self._overlaps(a, b):
                    warnings.append(
                        f"WARNING [{schedule.pet_name}]: '{a.task.title}' "
                        f"({a.start_time}-{a.end_time}) overlaps "
                        f"'{b.task.title}' ({b.start_time}-{b.end_time})."
                    )
        return warnings

    def detect_cross_pet_conflicts(self, schedules: list[DailySchedule]) -> list[str]:
        """
        Check for time overlaps across multiple pets' schedules.

        Flattens all scheduled tasks from every pet into a single tagged list,
        then applies the interval-overlap test to every pair from *different*
        pets. Same-pet overlaps are already covered by ``detect_conflicts()``.

        This is useful when multiple pets share one owner's time budget and
        two care activities are inadvertently booked at the same time.

        Args:
            schedules: List of ``DailySchedule`` objects, typically one per pet,
                       as returned by ``schedule_all_pets()``.

        Returns:
            A list of human-readable warning strings, one per cross-pet
            conflict found. Returns an empty list when no overlaps exist.
        """
        # Build a flat list of (pet_name, ScheduledTask) for easy comparison
        tagged: list[tuple[str, ScheduledTask]] = [
            (s.pet_name, st)
            for s in schedules
            for st in s.scheduled_tasks
        ]
        warnings = []
        for i in range(len(tagged)):
            pet_a, a = tagged[i]
            for j in range(i + 1, len(tagged)):
                pet_b, b = tagged[j]
                if pet_a == pet_b:
                    continue   # same-pet overlaps are caught by detect_conflicts
                if self._overlaps(a, b):
                    warnings.append(
                        f"WARNING [cross-pet]: {pet_a} '{a.task.title}' "
                        f"({a.start_time}-{a.end_time}) overlaps "
                        f"{pet_b} '{b.task.title}' ({b.start_time}-{b.end_time})."
                    )
        return warnings

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _overlaps(a: ScheduledTask, b: ScheduledTask) -> bool:
        """
        Test whether two scheduled tasks have overlapping time windows.

        Uses the standard half-open interval overlap condition:
            ``a.start < b.end  AND  b.start < a.end``
        Tasks that are exactly adjacent (one ends exactly when the next begins)
        are *not* considered overlapping.

        Args:
            a: First scheduled task.
            b: Second scheduled task.

        Returns:
            True if the time windows overlap, False otherwise.
        """
        return a.start_time < b.end_time and b.start_time < a.end_time

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
