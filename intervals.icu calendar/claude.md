# Intervals.icu Scheduler — Claude Reference

## CSV columns
`date` (YYYY-MM-DD), `type`, `name` (suffix), `mins`, `distance_m`, `sport` (override), `reps`, `int_mins`, `notes`, `start_time` (HH:MM)

## Type codes

### Strength
| Code | Session |
|------|---------|
| `sq_rp` | Squat + Rack Pull — Mon/Fri full |
| `sq_rp_taper` | Squat + Rack Pull — 2 sets |
| `sq_rp_light` | Squat + Rack Pull — 80%, return from race |
| `sq_rp_deload` | Squat + Rack Pull — deload |
| `dl_sq` | Deadlift + Light Squat — Wed |
| `dl_sq_taper` | Deadlift + Light Squat — taper |
| `dl_sq_deload` | Deadlift + Light Squat — deload |
| `upper` | Upper body only |
| `full_med` | Full body MED |
| `bw` | Bodyweight full (no gym) |
| `bw_upper` | Bodyweight upper (no gym) |

### Running
| Code | Session |
|------|---------|
| `run_z2` | Easy Z2 — HR ≤145 |
| `run_z2_strides` | Easy Z2 + 4×20s strides |
| `run_long` | Long run — HR ≤150, includes parkrun/club |
| `run_cruise` | Cruise intervals — HR 155–165. Use `reps`+`int_mins` |
| `run_threshold` | Threshold — HR 165–175. Use `reps`+`int_mins` |
| `run_threshold_hard` | Hard threshold — HR 170–178. Use `reps`+`int_mins` |
| `run_easy` | Unstructured easy (MED phase) |

### Cycling
| Code | Session |
|------|---------|
| `ride_easy` | Easy aerobic ride — HR ≤145 |
| `ride_prerace` | Pre-race leg opener — 90 min max |

### Other
| Code | Session |
|------|---------|
| `off` | Rest day |
| `walk` | Easy walk — HR <120 |
| `mobility` | Agile 8 + foam roll + stretch |
| `race` | Race day — use `name` + `notes` |

## Scheduling rules

| Day | Time | Notes |
|-----|------|-------|
| Mon | 07:00 | Strength morning; swim lunchtime (fixed) |
| Tue | 12:00 | |
| Wed | 12:00 | Swim morning (fixed); strength/run at lunch |
| Thu | 12:00 | |
| Fri | 12:00 | |
| Sat | 06:55 | Parkrun 7:00am — always anchor unless race/holiday |
| Sun | 08:00 | Rest/mobility only if needed |

**Saturday long runs:** `mins` = total including parkrun (~26 min). Script calculates start time automatically. Don't set `start_time` manually on Saturdays unless overriding.

**Quality runs:** set `reps` + `int_mins`. Script builds structured steps.

## Context overrides (contexts.csv)
```
start_date,end_date,context,notes
2026-07-04,2026-07-11,holiday,Beach trip
```
`holiday` — no gym, no bike, no run club. Strength → `bw`/`bw_upper`, rides skipped.  
`melbourne` — no gym, no bike, run club available. Strength → `bw`/`bw_upper`, rides skipped.

## Commands
```bash
python schedule.py plan.csv --dry-run             # preview
python schedule.py plan.csv                       # post
python schedule.py plan.csv --clear               # delete range then post
python schedule.py plan.csv --contexts ctx.csv    # with overrides
```

## Weekly structure (fixed anchors — never schedule over these)
- **Mon lunchtime** — swim
- **Wed morning** — swim  
- **Sat 7:00am** — run club

## Post-Beechworth return protocol (Apr 19 onwards)
- 4 days full rest (off)
- 2 days walk (35 min, 25 min)
- 1 day mobility
- 1 day off
- Then: sq_rp_light → run_easy (20 min, stop if anything off) → dl_sq → run_z2 → back to normal