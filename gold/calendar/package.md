---
family: calendar
version: "0.1.0"
kind: library
ladder: oracle_bound
qualification: none
exports:
  - isleap
  - weekday
  - leapdays
  - monthrange
  - month_name
  - MONDAY
  - SUNDAY
public_oracle: zspecs/calendar.zspec.zsdl
docs:
  - "https://docs.python.org/3/library/calendar.html"
rfcs:
  []
---

# calendar

Proleptic Gregorian calendar helpers. isleap follows 4/100/400; weekday is 0=Monday; monthrange returns (weekday-of-first, day-count). This file is the **authority** for the characterization cohort family. It is not an implementation and it is not an executable oracle. The oracle is `zspecs/calendar.zspec.zsdl`.

## Public surface

Exports listed in the frontmatter are the characterization surface. Layer 2 invariants call those names with arguments against the installed library.

## What is in scope

isleap including 1900/2000, weekday of documented dates, leapdays half-open range, month_name[1]==January, MONDAY==0, monthrange(2024, 2)==(3, 29).

## What is not in scope

TextCalendar/HTMLCalendar formatting strings; setfirstweekday process-global mutation; locale month names.

## Characterization loop

Draft from public docs/RFCs. Confirm expected values with `tools/live_probe.py` against the installed library. Do not read implementation source into a generation prompt. Review `uncertainty.yaml` until every item is `resolved`, `deferred`, or `held_out`. Passing the public oracle is **not** qualification (ADR 0001). This family is characterization-only: no held-out oracle and no clean-room attempt.

## Provenance

Derived from the docs and RFCs in the frontmatter. Not derived from implementation source files.
