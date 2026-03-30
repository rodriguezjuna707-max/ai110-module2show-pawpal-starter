from pawpal_system import (
    Priority, PetTask, Pet, Owner, Scheduler,
    DailySchedule, ScheduledTask,
)

# --- Owner ---
owner = Owner(
    name="Jordan",
    available_minutes_per_day=120,
    preferred_schedule_start="08:00",
)

# --- Pet 1: Mochi the dog (tasks added out of order) ---
mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)

mochi.add_task(PetTask(
    title="Evening grooming",
    category="grooming",
    duration_minutes=15,
    priority=Priority.LOW,
    preferred_time_of_day="evening",
))
mochi.add_task(PetTask(
    title="Enrichment puzzle",
    category="enrichment",
    duration_minutes=20,
    priority=Priority.MEDIUM,
    preferred_time_of_day="afternoon",
))
mochi.add_task(PetTask(
    title="Breakfast feeding",
    category="feeding",
    duration_minutes=10,
    priority=Priority.CRITICAL,
    preferred_time_of_day="morning",
    is_required=True,
))
mochi.add_task(PetTask(
    title="Morning walk",
    category="exercise",
    duration_minutes=30,
    priority=Priority.HIGH,
    preferred_time_of_day="morning",
    is_required=True,
))

# --- Pet 2: Luna the cat (tasks added out of order) ---
luna = Pet(name="Luna", species="cat", breed="Tabby", age_years=5)

luna.add_task(PetTask(
    title="Play session",
    category="enrichment",
    duration_minutes=15,
    priority=Priority.MEDIUM,
    preferred_time_of_day="evening",
))
luna.add_task(PetTask(
    title="Litter box cleaning",
    category="hygiene",
    duration_minutes=10,
    priority=Priority.HIGH,
    is_required=True,
))
luna.add_task(PetTask(
    title="Medication",
    category="health",
    duration_minutes=5,
    priority=Priority.CRITICAL,
    preferred_time_of_day="morning",
    is_required=True,
    notes="Mix into wet food",
))

owner.add_pet(mochi)
owner.add_pet(luna)

scheduler = Scheduler(owner)

# ------------------------------------------------------------------
# Demo 1 — sort_by_time()
# ------------------------------------------------------------------
print("=" * 52)
print("  DEMO 1: sort_by_time() — Mochi's tasks")
print("  (added evening-first; prints morning-first)")
print("=" * 52)
for t in scheduler.sort_by_time(mochi.tasks):
    slot = t.preferred_time_of_day or "no preference"
    print(f"  [{slot:<12}]  {t.title} ({t.duration_minutes} min, {t.priority.name})")
print()

# ------------------------------------------------------------------
# Demo 2 — filter_tasks() by pet name
# ------------------------------------------------------------------
print("=" * 52)
print("  DEMO 2: filter_tasks(pet_name='Luna')")
print("=" * 52)
for pet, task in owner.filter_tasks(pet_name="Luna"):
    print(f"  {pet.name}: {task.title} — completed={task.completed}")
print()

# ------------------------------------------------------------------
# Demo 3 — SAME-PET conflict detection
# Manually place two tasks at overlapping times (08:00-08:30 and 08:15-08:45)
# to prove detect_conflicts() returns a warning instead of crashing.
# ------------------------------------------------------------------
print("=" * 52)
print("  DEMO 3: same-pet conflict detection")
print("  Two tasks manually placed at overlapping times")
print("=" * 52)

task_a = PetTask(title="Morning walk",     category="exercise", duration_minutes=30, priority=Priority.HIGH)
task_b = PetTask(title="Breakfast feeding", category="feeding",  duration_minutes=10, priority=Priority.CRITICAL)

fake_schedule = DailySchedule(date="2026-03-30", owner_name="Jordan", pet_name="Mochi")
fake_schedule.scheduled_tasks = [
    ScheduledTask(task=task_a, start_time="08:00", end_time="08:30", reason="manual"),
    ScheduledTask(task=task_b, start_time="08:15", end_time="08:25", reason="manual"),  # overlaps task_a
]

same_pet_warnings = scheduler.detect_conflicts(fake_schedule)
if same_pet_warnings:
    for w in same_pet_warnings:
        print(f"  {w}")
else:
    print("  No conflicts detected.")
print()

# ------------------------------------------------------------------
# Demo 4 — CROSS-PET conflict detection
# Both pets start at 08:00 with CRITICAL morning tasks, so their first
# slots overlap naturally — detect_cross_pet_conflicts() should catch it.
# ------------------------------------------------------------------
print("=" * 52)
print("  DEMO 4: cross-pet conflict detection")
print("  Both pets have CRITICAL tasks starting at 08:00")
print("=" * 52)

schedules = scheduler.schedule_all_pets()
cross_warnings = scheduler.detect_cross_pet_conflicts(schedules)
if cross_warnings:
    for w in cross_warnings:
        print(f"  {w}")
else:
    print("  No cross-pet conflicts detected.")
print()

# ------------------------------------------------------------------
# Demo 5 — full schedule (warnings also embedded in reasoning_summary)
# ------------------------------------------------------------------
print("=" * 52)
print("         TODAY'S SCHEDULE — PawPal+")
print("=" * 52)
for schedule in schedules:
    print(schedule.display())
    print()

# ------------------------------------------------------------------
# Demo 6 — find_next_available_slot()
# Ask: "When is the next opening for a 20-min afternoon teeth-cleaning
# task given Mochi's already-generated schedule?"
# ------------------------------------------------------------------
print("=" * 52)
print("  DEMO 6: find_next_available_slot()")
print("  New task: 20-min 'Teeth cleaning' (afternoon)")
print("=" * 52)

mochi_schedule = next(s for s in schedules if s.pet_name == "Mochi")
teeth_cleaning = PetTask(
    title="Teeth cleaning",
    category="grooming",
    duration_minutes=20,
    priority=Priority.MEDIUM,
    preferred_time_of_day="afternoon",
)

slot = scheduler.find_next_available_slot(teeth_cleaning, mochi_schedule)
if slot:
    start, end = slot
    print(f"  Next available slot: {start} – {end}")
else:
    print("  No available slot found in today's schedule.")
print()
