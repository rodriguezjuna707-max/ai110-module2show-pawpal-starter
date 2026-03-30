from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PetTask:
    task_id: str
    title: str
    category: str
    duration_minutes: int
    priority: Priority
    preferred_time_of_day: Optional[str] = None  # "morning", "afternoon", "evening"
    is_required: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        pass


@dataclass
class ScheduledTask:
    task: PetTask
    start_time: str
    end_time: str
    reason: str

    def to_display(self) -> str:
        pass


@dataclass
class DailySchedule:
    date: str
    scheduled_tasks: list[ScheduledTask] = field(default_factory=list)
    skipped_tasks: list[tuple[PetTask, str]] = field(default_factory=list)
    total_minutes_used: int = 0
    reasoning_summary: str = ""

    def add_task(self, scheduled: ScheduledTask) -> None:
        pass

    def skip_task(self, task: PetTask, reason: str) -> None:
        pass

    def display(self) -> str:
        pass

    def to_dict(self) -> dict:
        pass


@dataclass
class Pet:
    name: str
    species: str
    breed: str = ""
    age_years: int = 0
    medical_notes: list[str] = field(default_factory=list)
    tasks: list[PetTask] = field(default_factory=list)

    def add_task(self, task: PetTask) -> None:
        pass

    def remove_task(self, task_id: str) -> bool:
        pass

    def get_tasks_by_priority(self) -> list[PetTask]:
        pass


@dataclass
class Owner:
    name: str
    email: str = ""
    available_minutes_per_day: int = 120
    preferred_schedule_start: str = "08:00"
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def get_pets(self) -> list[Pet]:
        pass

    def set_availability(self, minutes: int) -> None:
        pass


class Scheduler:
    def __init__(self, owner: Owner, pet: Pet):
        self.owner = owner
        self.pet = pet
        self.available_minutes = owner.available_minutes_per_day

    def schedule(self, tasks: list[PetTask]) -> DailySchedule:
        pass

    def prioritize(self, tasks: list[PetTask]) -> list[PetTask]:
        pass

    def fits_in_day(self, task: PetTask, used_minutes: int) -> bool:
        pass

    def build_reasoning(self, schedule: DailySchedule) -> str:
        pass


class PawPalApp:
    def __init__(self):
        self.owner: Optional[Owner] = None
        self.pet: Optional[Pet] = None
        self.scheduler: Optional[Scheduler] = None
        self.current_schedule: Optional[DailySchedule] = None

    def load_session(self) -> None:
        pass

    def save_session(self) -> None:
        pass

    def run_ui(self) -> None:
        pass
