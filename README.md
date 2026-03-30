# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

Four algorithmic improvements were added to make the scheduler more realistic:

- **Sort by time** — `Scheduler.sort_by_time()` orders tasks morning → afternoon → evening for display, separate from priority-based scheduling order.
- **Filter tasks** — `Owner.filter_tasks()` queries tasks across all pets by pet name, completion status, priority, or category in any combination.
- **Recurring tasks** — `PetTask.is_due_today()` respects the `frequency` field (`"daily"`, `"weekly"`, `"as_needed"`). Completing a recurring task via `Pet.complete_task()` automatically creates the next occurrence with a `next_due_date` calculated using `timedelta`.
- **Conflict detection** — `Scheduler.detect_conflicts()` checks a single pet's schedule for overlapping time windows; `Scheduler.detect_cross_pet_conflicts()` checks across all pets. Both return warning strings rather than raising exceptions.

## Testing PawPal+

All tests live in a single file: `tests/test_pawpal.py`.

### Running the tests

```bash
python -m pytest
```

All 60 tests should pass. For verbose output showing each test name:

```bash
python -m pytest -v
```

### What is tested

The suite is organised into seven test classes (60 tests total):

| Class | Tests | What it covers |
|---|---|---|
| `TestPetTask` | 5 | `mark_complete`, `mark_incomplete`, `to_dict` keys/types, unique IDs |
| `TestPet` | 8 | `add_task`, `remove_task`, priority ordering, pending queries, `reset_completion` |
| `TestOwner` | 8 | Pet roster management, `set_availability` (including negative-value guard), `get_all_tasks` |
| `TestSortByTime` | 5 | Chronological order (morning → afternoon → evening → no preference), tiebreaker by duration, list immutability |
| `TestRecurrence` | 11 | Daily/weekly next-occurrence dates, `completed=False` on new copy, `as_needed` returns `None`, 6-vs-7-day weekly boundary |
| `TestConflictDetection` | 7 | Identical/overlapping times flagged, adjacent tasks not flagged, cross-pet overlap detection, no double-reporting |
| `TestScheduleHappyPath` | 16 | Budget enforcement, skip tracking, required-before-optional ordering, time-slot preference, sequential task times, reasoning summary |

### Confidence Level

**4 / 5 stars**

All 60 tests pass, covering the core scheduling logic end-to-end — sorting, recurrence, conflict detection, and budget-based scheduling — with both happy-path and edge-case scenarios (adjacent task boundaries, 6-vs-7-day weekly cutoffs, `as_needed` tasks, empty rosters, negative availability).

One star is withheld because the Streamlit UI (`app.py`) has no automated test coverage. Session state persistence across re-renders, form validation (blank task title, malformed `HH:MM` input), and visual rendering are untested and could fail silently in the browser.
