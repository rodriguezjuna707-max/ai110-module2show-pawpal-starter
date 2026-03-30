# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

* **Priority**

  * Reprsents task urgency: LOW → MEDIUM → HIGH → CRITICAL
* **PetTask**

  * A single care task as entered by the user
    * stores what needs doing, how long, and how important it is
* **Pet**

  * Represents the pet
  * Owns its task list and can sort tasks by **priority(Class)**
  * Designed to support multiple pets per owner in the future
* **Owner**

  * Represents the human user
    * Holds the key scheduling constraint:
      * available_minutes_per_day
      * preferred_schedule_start
* **ScheduledTask**

  * Wraps a **PetTask(Class)**
  * concrete start_time, end_time, and a human-readable reason
    * this is what makes the plan explainable
* **DailySchedule**

  * The output of the scheduler.
  * Holds both scheduled and skipped tasks (with skip reasons)
* **Scheduler**

  * Core engine
  * Reads constraints from Owner, reads tasks from Pet, and produces a DailySchedule.
  * Key methods
    * prioritize() (sort by priority + required flag)
    * fits_in_day() (check remaining budget)
    * schedule()

**b. Design changes**

1. Scheduler bypasses Pet.get_tasks_by_priority()
2. PawPalApp holds both owner and pet separately
3. DailySchedule has no link back to Owner or Pet
   * The schedule doesn't know whose schedule it was
   * A owner_name/pet_name field (or a reference) was missing
4. Scheduler.available_minutes is snapshotted at  __init_

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

What constraints does your scheduler consider (for example: time, priority, preferences)?

* Time Avalability - owner available_minutes_per_day
* Priority - CRITICAL , HIGH , MEDIUM , LOW
* Preferred time of day

1. Time and required tasks are a must because
   * if there is no time or the task is critical  It has to happen
2. Priority breaks ties
3. Time-of-day preference is last because not needed to make our app work
   * The scheduler honors it when possible but won't skip a task just because the window passed

**b. Tradeoffs**

- **Tradeoff: The scheduler is greedy — it fills the day in priority order and skips anything that doesn't fit, rather than finding the optimal combination of tasks that maximizes value within the time budget.**
- **Why it's reasonable: A pet owner doesn't need a perfect schedule — they need a fast, predictable one. If medication and a walk are highest priority, those should always show up first without complex calculation. The greedy approach is also easier to explain to the user ("we ran out of time for grooming") which matters more than squeezing in one extra low-priority task.**

---

## 3. AI Collaboration

**a. How you used AI**

- Used AI for initial UML brainstorming, class skeleton generation, and docstring drafting
- Most helpful prompts were specific and structural: "given these attributes and methods, generate a Mermaid class diagram" and "write a `next_occurrence` method that returns a fresh copy with `next_due_date` set using `timedelta`"
- Debugging prompts that included the actual error message and the relevant function got faster, more accurate fixes

**b. Judgment and verification**

- AI initially suggested `Scheduler` snapshot `available_minutes` at `__init__` — rejected this because it would silently use a stale budget if the owner's availability changed mid-session; kept it as a live read from `self.owner.available_minutes_per_day`
- Verified suggestions by running the test suite and tracing through edge cases manually (e.g., adjacent tasks, weekly recurrence boundary at exactly 7 days)

---

## 4. Testing and Verification

**a. What you tested**

- Task completion / reset, recurrence (daily/weekly/as_needed), `is_due_today` boundary conditions
- Priority and time-of-day sort order, required-task-first scheduling, budget enforcement, skip tracking
- Single-pet and cross-pet conflict detection (overlapping, adjacent, non-overlapping cases)
- These covered the three most likely failure modes: wrong priority order, silent budget overflow, and missed conflict warnings

**b. Confidence**

- High confidence in the core happy paths — 38 tests pass covering all seven feature areas
- Would add next: tasks that span midnight, owners with 0-minute budgets, and filter_tasks with combined criteria across many pets

---

## 5. Reflection

**a. What went well**

- The `ScheduledTask` + `DailySchedule` output design — wrapping tasks with concrete times and a `reason` string made both the UI and test assertions straightforward

**b. What you would improve**

- Add `owner_name` / `pet_name` back-references to `ScheduledTask` so conflict warnings don't have to carry that context as strings
- Make the greedy scheduler aware of total cross-pet minutes, not just per-pet budget

**c. Key takeaway**

- AI speeds up boilerplate and structure, but the decisions that matter — what to snapshot vs. read live, when adjacent tasks should or shouldn't conflict — still require a human to catch and push back on
