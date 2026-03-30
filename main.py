from pawpal_system import Priority, PetTask, Pet, Owner, Scheduler

# --- Owner ---
owner = Owner(
    name="Jordan",
    available_minutes_per_day=120,
    preferred_schedule_start="08:00",
)

# --- Pet 1: Mochi the dog ---
mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age_years=3)

mochi.add_task(PetTask(
    title="Morning walk",
    category="exercise",
    duration_minutes=30,
    priority=Priority.HIGH,
    preferred_time_of_day="morning",
    is_required=True,
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
    title="Enrichment puzzle",
    category="enrichment",
    duration_minutes=20,
    priority=Priority.MEDIUM,
    preferred_time_of_day="afternoon",
))
mochi.add_task(PetTask(
    title="Evening grooming",
    category="grooming",
    duration_minutes=15,
    priority=Priority.LOW,
    preferred_time_of_day="evening",
))

# --- Pet 2: Luna the cat ---
luna = Pet(name="Luna", species="cat", breed="Tabby", age_years=5)

luna.add_task(PetTask(
    title="Medication",
    category="health",
    duration_minutes=5,
    priority=Priority.CRITICAL,
    preferred_time_of_day="morning",
    is_required=True,
    notes="Mix into wet food",
))
luna.add_task(PetTask(
    title="Litter box cleaning",
    category="hygiene",
    duration_minutes=10,
    priority=Priority.HIGH,
    is_required=True,
))
luna.add_task(PetTask(
    title="Play session",
    category="enrichment",
    duration_minutes=15,
    priority=Priority.MEDIUM,
    preferred_time_of_day="evening",
))

owner.add_pet(mochi)
owner.add_pet(luna)

# --- Schedule ---
scheduler = Scheduler(owner)
schedules = scheduler.schedule_all_pets()

print("=" * 52)
print("         TODAY'S SCHEDULE - PawPal+")
print("=" * 52)
for schedule in schedules:
    print(schedule.display())
    print()
