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

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
