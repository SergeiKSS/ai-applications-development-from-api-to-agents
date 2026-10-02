---
name: unit-converter
description: >
  Converts values between units of length, weight, temperature, volume, area, speed, time, data,
  pressure, and energy. Use this skill whenever the user asks to convert a value from one unit to
  another (e.g. "convert 100 km to miles", "98.6°F in Celsius", "how many MB is 1.5 TB?").
license: Apache-2.0
metadata:
  author: ai-powered-apps-development-expert
  version: 1.0
allowed-tools: execute_code
---

# Unit Converter

Converts a numeric value between units via the `convert_units(value, from_unit, to_unit)` function
defined in `scripts/convert.py`, executed through the `execute_code` tool. See
`references/how-code-execution-works.md` for how `execute_code` and its `session_id` work, and
`examples.md` for invocation examples and the full list of supported units per category.

## Workflow

### Step 1: Load the script (first call, session_id = "")

Call `execute_code` with `script_path` set to this skill's `scripts/convert.py`, `code` set to the
conversion call from Step 2, and `session_id = ""`. Save the `session_id` returned in
`session_info` for reuse on later calls.

### Step 2: Write the conversion call

Pass as `code`:
```python
result, category = convert_units(<value>, "<from_unit>", "<to_unit>")
print(f"Category: {category}")
print(f"Input:    {<value>} <from_unit>")
print(f"Result:   {fmt(result)} <to_unit>")
```

### Step 3: Return output

Return the printed output as-is to the user (optionally wrapped in one short sentence).

### Step 4: Reuse session

On follow-up conversions in the same conversation, skip Step 1 — pass only the `code` from Step 2
plus the saved `session_id`; the script is already loaded in that session.

### Step 5: Error handling

- **Unknown unit / incompatible categories:** `convert_units` raises a `ValueError` — report the
  error message to the user and list the supported units for the relevant category from
  `examples.md`.
- **Invalid number:** ask the user to clarify the value instead of guessing.
- **Expired session:** if `execute_code` reports the session is missing/expired, silently restart
  from Step 1 with a new session.