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

    # Show current task list sorted by preferred time of day (morning → afternoon → evening)
    current_tasks = st.session_state.pet.tasks
    if current_tasks:
        st.markdown("**Current tasks (sorted by time of day):**")
        scheduler = Scheduler(st.session_state.owner)
        sorted_tasks = scheduler.sort_by_time(current_tasks)

        PRIORITY_ICON = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        TIME_ICON = {"morning": "🌅 Morning", "afternoon": "☀️ Afternoon", "evening": "🌙 Evening"}

        header = st.columns([2, 1, 1, 1, 1])
        header[0].markdown("**Task**")
        header[1].markdown("**Priority**")
        header[2].markdown("**Duration**")
        header[3].markdown("**Time slot**")
        header[4].markdown("**Required**")
        st.divider()

        for task in sorted_tasks:
            col = st.columns([2, 1, 1, 1, 1])
            col[0].write(task.title)
            col[1].write(f"{PRIORITY_ICON.get(task.priority.name, '')} {task.priority.name}")
            col[2].write(f"{task.duration_minutes} min")
            col[3].write(TIME_ICON.get(task.preferred_time_of_day, "—"))
            col[4].write("Yes" if task.is_required else "—")
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
        budget = st.session_state.owner.available_minutes_per_day
        minutes_left = budget - plan.total_minutes_used

        # Summary metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Time used", f"{plan.total_minutes_used} min", delta=f"-{minutes_left} min remaining")
        m2.metric("Tasks scheduled", len(plan.scheduled_tasks))
        m3.metric("Tasks skipped", len(plan.skipped_tasks))

        # Conflict warnings — rephrased for a pet owner, not a developer
        conflict_scheduler = Scheduler(st.session_state.owner)
        conflicts = conflict_scheduler.detect_conflicts(plan)
        for raw_msg in conflicts:
            # Extract the two task names from the message for a friendlier summary
            # Message format: "WARNING [PetName]: 'TaskA' (HH:MM-HH:MM) overlaps 'TaskB' ..."
            parts = raw_msg.split("'")
            if len(parts) >= 4:
                task_a, task_b = parts[1], parts[3]
                st.warning(
                    f"**Scheduling conflict:** **{task_a}** and **{task_b}** overlap — "
                    f"both are scheduled at the same time. Consider reducing one task's duration, "
                    f"changing its preferred time slot, or lowering its priority so the scheduler "
                    f"can fit them without overlap.",
                    icon="⚠️",
                )
            else:
                st.warning(raw_msg, icon="⚠️")

        # Scheduled tasks
        if plan.scheduled_tasks:
            st.markdown("**Scheduled tasks:**")
            PRIORITY_ICON = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
            for st_task in plan.scheduled_tasks:
                icon = PRIORITY_ICON.get(st_task.task.priority.name, "")
                badge = " ✅ **Required**" if st_task.task.is_required else ""
                st.success(
                    f"`{st_task.start_time} – {st_task.end_time}`  "
                    f"{icon} **{st_task.task.title}** ({st_task.task.duration_minutes} min){badge}"
                )

        # Skipped tasks — severity depends on whether the task was required
        if plan.skipped_tasks:
            st.markdown("**Could not fit into today's schedule:**")
            for task, reason in plan.skipped_tasks:
                msg = f"**{task.title}** — {reason}"
                if task.is_required or task.priority.name == "CRITICAL":
                    st.error(f"⛔ {msg} *(this task is marked required — consider freeing up time)*")
                else:
                    st.warning(f"⏭️ {msg}")

        # Reasoning summary (conflict detail already shown above — strip duplicates)
        summary_clean = plan.reasoning_summary.split("WARNING")[0].strip()
        if summary_clean:
            st.info(f"ℹ️ {summary_clean}")
