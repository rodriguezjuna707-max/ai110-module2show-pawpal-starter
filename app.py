import streamlit as st
from pawpal_system import Priority, PetTask, Pet, Owner, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("PawPal+")

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

if "pet" not in st.session_state:
    st.session_state.pet = None

if "schedule" not in st.session_state:
    st.session_state.schedule = None

# ---------------------------------------------------------------------------
# Section 1 — Owner + Pet setup
# ---------------------------------------------------------------------------
st.subheader("Owner & Pet Info")

owner_name = st.text_input("Owner name", value="Jordan")
available_minutes = st.number_input("Available minutes per day", min_value=10, max_value=480, value=120)
start_time = st.text_input("Schedule start time (HH:MM)", value="08:00")

st.markdown("---")

pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Save owner & pet"):
    # Owner.add_pet() wires the pet into the owner's roster
    owner = Owner(
        name=owner_name,
        available_minutes_per_day=int(available_minutes),
        preferred_schedule_start=start_time,
    )
    pet = Pet(name=pet_name, species=species)
    owner.add_pet(pet)

    st.session_state.owner = owner
    st.session_state.pet = pet
    st.session_state.schedule = None   # reset any old schedule
    st.success(f"Saved! Owner: {owner_name} | Pet: {pet_name} ({species})")

# ---------------------------------------------------------------------------
# Section 2 — Add tasks (only shown once owner+pet are set)
# ---------------------------------------------------------------------------
if st.session_state.pet is not None:
    st.divider()
    st.subheader("Add a Task")

    PRIORITY_MAP = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH, "critical": Priority.CRITICAL}
    TIME_OPTIONS = [None, "morning", "afternoon", "evening"]

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority_str = st.selectbox("Priority", list(PRIORITY_MAP.keys()), index=2)

    col4, col5 = st.columns(2)
    with col4:
        preferred_time = st.selectbox("Preferred time of day", TIME_OPTIONS)
    with col5:
        is_required = st.checkbox("Required (must happen today)")

    if st.button("Add task"):
        # Pet.add_task() stores the PetTask object on the pet
        task = PetTask(
            title=task_title,
            category="general",
            duration_minutes=int(duration),
            priority=PRIORITY_MAP[priority_str],
            preferred_time_of_day=preferred_time,
            is_required=is_required,
        )
        st.session_state.pet.add_task(task)
        st.session_state.schedule = None   # stale schedule — force regeneration
        st.success(f"Added task: {task_title}")

    # Show current task list
    current_tasks = st.session_state.pet.tasks
    if current_tasks:
        st.markdown("**Current tasks:**")
        st.table([t.to_dict() for t in current_tasks])
    else:
        st.info("No tasks yet. Add one above.")

# ---------------------------------------------------------------------------
# Section 3 — Generate schedule
# ---------------------------------------------------------------------------
if st.session_state.pet is not None and st.session_state.pet.tasks:
    st.divider()
    st.subheader("Generate Schedule")

    if st.button("Generate schedule"):
        # Scheduler.schedule() reads owner constraints + pet tasks and produces a DailySchedule
        scheduler = Scheduler(st.session_state.owner)
        st.session_state.schedule = scheduler.schedule(st.session_state.pet)

    if st.session_state.schedule is not None:
        plan = st.session_state.schedule
        st.markdown(f"**{plan.date} — {plan.pet_name}** ({plan.total_minutes_used} min used)")

        if plan.scheduled_tasks:
            st.markdown("**Scheduled:**")
            for st_task in plan.scheduled_tasks:
                st.markdown(
                    f"- `{st_task.start_time}-{st_task.end_time}` &nbsp; "
                    f"**{st_task.task.title}** ({st_task.task.duration_minutes} min) "
                    f"[{st_task.task.priority.name}]"
                )

        if plan.skipped_tasks:
            st.markdown("**Skipped (not enough time):**")
            for task, reason in plan.skipped_tasks:
                st.markdown(f"- ~~{task.title}~~ — {reason}")

        if plan.reasoning_summary:
            st.info(plan.reasoning_summary)
