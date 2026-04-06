# Intervals.icu Training Scheduler

A Python script that posts training events to Intervals.icu from a minimal CSV plan.
All workout descriptions, warmups, cooldowns, and structure live in the script —
the CSV is kept as small and human-readable as possible.

---

## Setup

### 1. Install dependencies

```bash
pip install requests
```

### 2. Create a `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```
INTERVALS_API_KEY=your_api_key_here
INTERVALS_ATHLETE_ID=your_athlete_id_here
```

Find these in Intervals.icu → Settings → API.

---

## Usage

### Dry run (preview without posting)
```bash
python schedule.py plan.csv --dry-run
```

### Post events to Intervals.icu
```bash
python schedule.py plan.csv
```

### Clear existing events in the date range first, then post
```bash
python schedule.py plan.csv --clear
```

---

## CSV Format

The CSV uses short codes to keep input minimal. Claude generates these CSVs — you don't need to write them by hand.

### Columns

| Column | Required | Description |
|--------|----------|-------------|
| `date` | ✅ | Date in `YYYY-MM-DD` format |
| `type` | ✅ | Workout type code (see table below) |
| `name` | ❌ | Optional suffix added to the event name |
| `mins` | ❌ | Duration in minutes |
| `distance_m` | ❌ | Distance in metres |
| `sport` | ❌ | Override the sport (e.g. `Ride`, `Run`) |
| `reps` | ❌ | Number of interval reps (quality runs only) |
| `int_mins` | ❌ | Duration of each interval in minutes (quality runs only) |
| `notes` | ❌ | Free text added to the event description |

### Example

```csv
date,type,name,mins,distance_m,sport,reps,int_mins,notes
2026-05-04,run_cruise,,,,, 4,8,
2026-05-05,dl_sq,,,,,,,
2026-05-06,run_z2,,35,,,,,
2026-05-08,run_long,,50,,,,,Parkrun — run first half conservatively
```

---

## Workout Type Codes

### Strength

| Code | Session |
|------|---------|
| `sq_rp` | Squat + Rack Pull (full — Mon/Fri) |
| `sq_rp_taper` | Squat + Rack Pull — 2 sets, taper week |
| `sq_rp_light` | Squat + Rack Pull — 80%, return from race |
| `sq_rp_deload` | Squat + Rack Pull — deload week |
| `dl_sq` | Deadlift + Light Squat (Wed) |
| `dl_sq_taper` | Deadlift + Light Squat — taper week |
| `dl_sq_deload` | Deadlift + Light Squat — deload week |
| `upper` | Upper body only (marathon phase) |
| `full_med` | Full body MED — newborn/maintenance phase |

### Running

| Code | Session |
|------|---------|
| `run_z2` | Easy Z2 — HR cap 145 bpm |
| `run_z2_strides` | Easy Z2 + 4x20sec strides at end |
| `run_long` | Long run — HR cap 150 bpm, includes club |
| `run_cruise` | Cruise intervals — HR 155-165 bpm. Use `reps` + `int_mins` |
| `run_threshold` | Threshold — HR 165-175 bpm. Use `reps` + `int_mins` |
| `run_threshold_hard` | Hard threshold — HR 170-178 bpm. Use `reps` + `int_mins` |
| `run_easy` | Unstructured easy run (MED phase) |

### Cycling

| Code | Session |
|------|---------|
| `ride_easy` | Easy aerobic ride — HR cap 145 bpm |
| `ride_prerace` | Pre-race leg opener — 90 min max |

### Recovery / Other

| Code | Session |
|------|---------|
| `off` | Rest day |
| `walk` | Easy walk — HR under 120 bpm |
| `mobility` | Agile 8 + foam roll + stretch |
| `race` | Race day — use `name` and `notes` for details |

---

## Quality Run Interval Format

For `run_cruise`, `run_threshold`, `run_threshold_hard`:
- Set `reps` = number of intervals
- Set `int_mins` = duration of each interval in minutes
- The script builds structured workout steps automatically

```csv
# 4 x 8 min cruise intervals
2026-05-04,run_cruise,,,,,4,8,

# 3 x 10 min threshold
2026-06-08,run_threshold,,,,,3,10,

# 5 x 5 min hard threshold
2026-05-25,run_threshold_hard,,,,,5,5,
```

---

## Context Overrides (Holiday / Melbourne)

Use a `contexts.csv` file to automatically adapt sessions when you don't have access to your gym or bike.

### Contexts CSV format

```csv
start_date,end_date,context,notes
2026-07-04,2026-07-11,holiday,Summer beach trip
2026-08-15,2026-08-17,melbourne,Work trip
```

### Run with contexts

```bash
python schedule.py plan.csv --contexts contexts.csv --dry-run
python schedule.py plan.csv --contexts contexts.csv
```

### What each context does

**`holiday`** — No gym, no bike, no parkrun/club
| Original | Becomes |
|----------|---------|
| `sq_rp` / `sq_rp_*` | `bw` — Bodyweight full session |
| `dl_sq` / `dl_sq_*` | `bw_upper` — Bodyweight upper |
| `upper` / `full_med` | `bw` or `bw_upper` |
| `ride_easy` / `ride_prerace` | ⏭️ Skipped entirely |
| All runs | ✅ Pass through (no parkrun note on Saturday) |
| `mobility` / `off` / `walk` | ✅ Pass through |

**`melbourne`** — No home gym, no bike. Run + bodyweight only.
| Original | Becomes |
|----------|---------|
| `sq_rp` / `sq_rp_*` | `bw` — Bodyweight full session |
| `dl_sq` / `dl_sq_*` | `bw_upper` — Bodyweight upper |
| `ride_easy` / `ride_prerace` | ⏭️ Skipped entirely |
| All runs | ✅ Pass through (parkrun still available) |
| `mobility` / `off` / `walk` | ✅ Pass through |

### Bodyweight workout types

| Code | Session |
|------|---------|
| `bw` | Full bodyweight — split squat, push-up, SL-RDL, pike push-up, glute bridge, chin-up |
| `bw_upper` | Upper bodyweight — push-up, pike push-up, chin-up, diamond push-up, plank |

These can also be used directly in the CSV if needed.



Edit `schedule.py` and add a new entry to the `WORKOUT_TYPES` dictionary:

```python
"my_new_type": {
    "label":       "Descriptive Name",
    "sport":       "Run",          # Run, Ride, Swim, WeightTraining, Walk, Workout
    "warmup":      "hansons",      # agile8 | hansons | none
    "cooldown":    "run",          # run | lift | none
    "moving_time": 3600,           # seconds (optional default)
    "description": "What to do.",
},
```

Then use the new code in any CSV.

---

## Files

```
intervals_scheduler/
├── schedule.py          # Main script — all smarts live here
├── plan_apr7_jun15.csv  # Full plan Apr 7 → Jun 15 2026
├── example_plan.csv     # Minimal example for reference
├── .env                 # Your credentials (never commit this)
├── .env.example         # Template
└── README.md            # This file
```

---

## Generating New Plans with Claude

Ask Claude to generate a CSV in this format. Because all descriptions are stored in the script, Claude only needs to output:

```
date, type, name (optional), mins (optional), reps (optional), int_mins (optional), notes (optional)
```

This keeps token usage minimal — a 10-week plan is ~70 rows of short codes.

---

## Personal Scheduling Rules

These rules are baked into the script's time logic and must be respected when generating any CSV plan.

### Fixed Weekly Anchor Sessions

| Day | Session | Time | Notes |
|-----|---------|------|-------|
| Saturday | parkrun (Tyntynder / Tingling) | **Arrive 6:55am, run starts 7:00am** | Always included unless on holidays or at an event |
| Saturday | Run Club | After parkrun | Always included unless on holidays or at an event |
| Wednesday | Swim | Morning | Fixed — plan around it, not over it |
| Monday | Swim | Lunchtime | Fixed — plan around it, not over it |

### Session Timing by Day

| Day | Preferred Time | Notes |
|-----|---------------|-------|
| Monday | **Morning** | Strength goes in the morning (swim is lunchtime) |
| Tuesday | **Lunchtime** | |
| Wednesday | **Lunchtime** | Swim is in the morning — strength/run at lunch |
| Thursday | **Lunchtime** | |
| Friday | **Lunchtime** | |
| Saturday | **6:55am arrive** | parkrun 7:00am start — long run total time must account for parkrun pace + any additional running before/after |
| Sunday | **Flexible** | Schedule only if required by goals — otherwise rest/mobility |

### Parkrun / Long Run Timing Rule

When a long run falls on Saturday:
- Parkrun is **always** the quality/pace component (5km @ 7:00am)
- Arrive **6:55am** to allow for delays or if the run is taking longer than expected
- Total long run duration in the CSV (`mins`) should **include** parkrun time
- If the long run target is 60 min and parkrun takes ~25–28 min, plan ~32–35 min of easy running before or after
- Start time for the event should be set to **06:55** on Saturdays

### Swimming

- Wednesday morning and Monday lunchtime swims are **fixed commitments** — they are not replaced by other sessions
- Swim sessions are logged separately via Garmin and do not need to appear in the training plan CSV unless a specific swim workout is being prescribed

### Holidays / Events

- If on holidays or at a race event, parkrun and run club are skipped automatically
- Note exceptions in the CSV `notes` field: `notes=on holidays` or `notes=race weekend`

---

## Tips

- Always do `--dry-run` first to verify the plan looks right
- Use `--clear` when re-importing to avoid duplicate events
- The `.env` file is gitignored by default — never commit credentials
- Add new workout types to the script as your training evolves
- When generating Saturday long runs, always set `start_time=06:55` and account for parkrun 5km in total duration
