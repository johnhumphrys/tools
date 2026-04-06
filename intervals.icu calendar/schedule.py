#!/usr/bin/env python3
"""
Intervals.icu Training Scheduler
Reads a minimal CSV plan and posts events to Intervals.icu via API.
All workout descriptions, warmup text, and structure are defined here —
the CSV input is kept as token-friendly/human-friendly as possible.
"""

import csv
import json
import os
import sys
import argparse
import requests
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG — load from env or .env file
# ─────────────────────────────────────────────

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

API_KEY    = os.environ.get("INTERVALS_API_KEY", "")
ATHLETE_ID = os.environ.get("INTERVALS_ATHLETE_ID", "")
BASE_URL   = "https://intervals.icu/api/v1/athlete"

# ─────────────────────────────────────────────
# WARMUP / COOLDOWN LIBRARY
# Stored here so the CSV never needs to include them
# ─────────────────────────────────────────────

WARMUPS = {
    "agile8": (
        "Agile 8 warmup: 8 exercises, ~5 min. "
        "Foam roll IT band / adductors / thoracic. "
        "Glute bridge 10 reps, hip circles 10/side, "
        "leg swings 10/side, lateral band walk 10/side."
    ),
    "hansons": (
        "Hansons DWU1 warmup: ~5 min easy walk + drills. "
        "Leg swings (fore/aft + lateral) 10/side, "
        "ankle circles, high knees 20m, butt kicks 20m, "
        "A-skip 20m. Start the run easy for first 5 min."
    ),
    "none": "",
}

COOLDOWNS = {
    "run": (
        "Post-run 5 min cooldown:\n"
        "- Standing quad stretch 45s/side\n"
        "- Soleus stretch (bent knee against wall) 45s/side\n"
        "- Hip flexor lunge stretch 45s/side"
    ),
    "lift": (
        "Post-lift: foam roll lats + thoracic 2 min. "
        "Shoulder cross-body stretch 30s/side."
    ),
    "none": "",
}

# ─────────────────────────────────────────────
# WORKOUT TYPE LIBRARY
# Maps short codes in the CSV to full descriptions + API fields
# ─────────────────────────────────────────────

WORKOUT_TYPES = {

    # ── STRENGTH ──────────────────────────────
    "sq_rp": {
        "label":        "Strength — Squat + Rack Pull",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2700,
        "description":  (
            "Primary lower day.\n"
            "Squat 3x5 @ working weight (+2.5kg from last session)\n"
            "Rack Pull 3x5 @ working weight\n"
            "Bench Press 3x5 @ working weight\n"
            "Barbell Row 3x8\n\n"
            "Log all weights. Add 2.5kg squat/bench, 5kg rack pull each session."
        ),
    },
    "sq_rp_taper": {
        "label":        "Strength — Squat + Rack Pull (Taper)",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2100,
        "description":  (
            "Taper week — cut to 2 sets, keep working weight.\n"
            "Squat 2x5 @ working weight\n"
            "Rack Pull 2x5 @ working weight\n"
            "Bench Press 2x5 @ working weight\n"
            "Row 2x8\n\n"
            "Do not grind. Legs must be fresh."
        ),
    },
    "sq_rp_light": {
        "label":        "Strength — Squat + Rack Pull (Light)",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2400,
        "description":  (
            "Return/recovery session — 80% of working weight.\n"
            "Squat 3x5 @ 80% working weight\n"
            "Rack Pull 3x5 @ 80% working weight\n"
            "Bench Press 3x5 @ working weight\n"
            "Row 3x8\n\n"
            "Assess how body feels. Stop if anything is off."
        ),
    },
    "sq_rp_deload": {
        "label":        "Strength — Squat + Rack Pull (Deload)",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2100,
        "description":  (
            "Deload week — 2 sets only, no weight added.\n"
            "Squat 2x5 @ working weight\n"
            "Rack Pull 2x5 @ working weight\n"
            "Bench Press 2x5 @ working weight\n"
            "Row 2x8"
        ),
    },
    "dl_sq": {
        "label":        "Strength — Deadlift + Light Squat",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2700,
        "description":  (
            "Secondary lower day.\n"
            "Deadlift 3x5 @ working weight (+5kg from last DL session)\n"
            "Light Squat 3x5 @ 80% of Monday's squat weight\n"
            "OHP 3x5 @ working weight (+2.5kg)\n"
            "Chin-ups 3x max reps"
        ),
    },
    "dl_sq_taper": {
        "label":        "Strength — Deadlift + Light Squat (Taper)",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2100,
        "description":  (
            "Taper week — 2 sets, working weight.\n"
            "Deadlift 2x5 @ working weight\n"
            "Light Squat 2x5 @ 80%\n"
            "OHP 2x5\n"
            "Chin-ups 2x max"
        ),
    },
    "dl_sq_deload": {
        "label":        "Strength — Deadlift + Light Squat (Deload)",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2100,
        "description":  (
            "Deload week — 2 sets only.\n"
            "Deadlift 2x5 @ working weight\n"
            "Light Squat 2x5 @ 80%\n"
            "OHP 2x5\n"
            "Chin-ups 2x max"
        ),
    },
    "upper": {
        "label":        "Strength — Upper Body",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2400,
        "description":  (
            "Upper dominant session (MED / marathon phase).\n"
            "Bench Press 3x5 @ working weight\n"
            "OHP 3x5 @ working weight\n"
            "Barbell Row 3x8\n"
            "Chin-ups 3x max\n"
            "Face pulls 3x15"
        ),
    },
    "full_med": {
        "label":        "Strength — Full Body MED",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2400,
        "description":  (
            "Minimum Effective Dose — full body, keep weights heavy, cut sets.\n"
            "Squat 2x5 @ working weight\n"
            "Deadlift OR Rack Pull 2x5 @ working weight\n"
            "Bench Press 2x5\n"
            "Row 2x8\n\n"
            "Intensity > volume. If short on time, cut sets not weight."
        ),
    },

    # ── RUNNING ───────────────────────────────
    "run_z2": {
        "label":        "Easy Run — Z2",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Easy aerobic run. Strict HR ceiling 145 bpm.\n"
            "Walk immediately if HR exceeds 145 — do not let it creep.\n"
            "Conversational pace throughout — you should be able to hold a full sentence.\n\n"
            "Estimated pace: ~6:00–6:30/km at true Z2 effort.\n"
            "This feels uncomfortably slow. That is correct. Trust the process.\n\n"
            "This is your aerobic base session — the most important run of the week."
        ),
    },
    "run_z2_strides": {
        "label":        "Easy Run — Z2 + Strides",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Easy aerobic run with strides at the end.\n\n"
            "Easy portion: HR cap 145 bpm. Estimated pace ~6:00-6:30/km.\n"
            "Walk immediately if HR exceeds 145.\n\n"
            "Strides (last 5 min of run):\n"
            "4 x 20 sec — smoothly accelerate to ~80% effort, relaxed form, not a sprint.\n"
            "40 sec walk/easy jog recovery between each.\n"
            "HR will spike briefly during strides — that is fine and expected."
        ),
    },
    "run_long": {
        "label":        "Long Run",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Long aerobic run. HR cap 150 bpm.\n\n"
            "Estimated paces:\n"
            "- Easy Z2 portions (pre/post parkrun): ~6:00–6:30/km\n"
            "- Parkrun effort (natural race feel): ~5:00–5:20/km\n\n"
            "Saturday structure:\n"
            "1. Start easy from home/car at the scheduled time\n"
            "2. Run easy Z2 to arrive at parkrun by 6:55am\n"
            "3. Run parkrun at natural effort (HR will exceed 150 — that\'s fine for 5km)\n"
            "4. Any remaining time: easy jog after finish\n\n"
            "⚠️ Known risk: race environment triggers harder effort. Be deliberate on the pre-run.\n"
            "Note your parkrun HR — track it week to week as aerobic fitness improves."
        ),
    },
    "run_cruise": {
        "label":        "Quality Run — Cruise Intervals",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Cruise intervals — comfortably hard but sustainable. Think \'marathon race effort\'.\n\n"
            "Structure:\n"
            "1. Hansons DWU1 + 10 min easy warmup jog (~6:15/km, HR <145)\n"
            "2. Intervals at cruise pace (~5:00–5:15/km, HR 155–165 bpm)\n"
            "3. 90 sec easy jog recovery between each rep\n"
            "4. 10 min easy cooldown jog\n\n"
            "Effort cues: breathing is laboured but you could speak in short phrases.\n"
            "Should feel strong and controlled — not desperate.\n"
            "If HR exceeds 168 or you can\'t complete a rep — slow down, don\'t gut it out."
        ),
    },
    "run_threshold": {
        "label":        "Quality Run — Threshold",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Threshold intervals — hard but controlled. The hardest sustainable pace you could hold for ~1hr.\n\n"
            "Structure:\n"
            "1. Hansons DWU1 + 10 min easy warmup jog (~6:15/km, HR <145)\n"
            "2. Threshold reps at ~4:45–5:00/km, HR 165–175 bpm\n"
            "3. 2 min easy jog recovery between each rep\n"
            "4. 10 min easy cooldown jog\n\n"
            "Effort cues: breathing is hard, can only speak 2–3 words at a time.\n"
            "Should feel hard but not maximal — you have something left.\n"
            "If HR exceeds 178 or form breaks down — cut the rep short, don\'t push through."
        ),
    },
    "run_threshold_hard": {
        "label":        "Quality Run — Threshold Hard",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Short hard threshold reps — high intensity, lower total volume. Think 10km race effort.\n\n"
            "Structure:\n"
            "1. Hansons DWU1 + 10 min easy warmup jog (~6:15/km, HR <145)\n"
            "2. Hard reps at ~4:30–4:45/km, HR 170–178 bpm\n"
            "3. 90 sec easy jog recovery between each rep\n"
            "4. 10 min easy cooldown jog\n\n"
            "Effort cues: can barely speak, breathing very hard.\n"
            "Shorter reps mean you can hit higher quality — don\'t sandbag the first few.\n"
            "Each rep should feel similar effort. If later reps feel much harder, HR is drifting — ease off."
        ),
    },
    "run_easy": {
        "label":        "Easy Run",
        "sport":        "Run",
        "warmup":       "hansons",
        "cooldown":     "run",
        "description":  (
            "Easy unstructured run. No pressure on distance or pace.\n\n"
            "Estimated pace: ~6:00–6:30/km at easy effort.\n"
            "HR cap 145 bpm — walk if it creeps up, especially in the first few minutes.\n\n"
            "MED phase: goal is just to keep the legs moving and maintain aerobic memory.\n"
            "If you feel good, run longer. If you feel tired, cut it short. Both are fine."
        ),
    },

    # ── RIDE ──────────────────────────────────
    "ride_easy": {
        "label":        "Easy Ride — Z2",
        "sport":        "Ride",
        "cooldown":     "none",
        "warmup":       "none",
        "description":  (
            "Easy aerobic ride. HR cap 145 bpm throughout.\n"
            "Conversational pace — if you can't hold a sentence, ease off.\n"
            "This is a base builder / leg flush, not a fitness test."
        ),
    },
    "ride_prerace": {
        "label":        "Pre-Race Ride — Leg Opener",
        "sport":        "Ride",
        "cooldown":     "none",
        "warmup":       "none",
        "description":  (
            "Leg opener only — max 90 min, rolling terrain, no big climbs.\n"
            "HR cap 145 bpm throughout. Conversational pace.\n"
            "Nutrition practice: eat before leaving, 1 gel at 45 min, electrolyte throughout.\n"
            "Goal: feel the legs, not tire them."
        ),
    },

    # ── RECOVERY / OTHER ──────────────────────
    "off": {
        "label":        "Rest Day",
        "sport":        "Workout",
        "warmup":       "none",
        "cooldown":     "none",
        "description":  "Complete rest. Sleep, eat, hydrate.",
    },
    "walk": {
        "label":        "Easy Walk",
        "sport":        "Walk",
        "warmup":       "none",
        "cooldown":     "none",
        "description":  (
            "Easy walk — flat ground, HR under 120 bpm.\n"
            "Active recovery only. Keep it relaxed."
        ),
    },
    "mobility": {
        "label":        "Mobility",
        "sport":        "Workout",
        "warmup":       "none",
        "cooldown":     "none",
        "description":  (
            "Full mobility session. ~25–30 min total. No running, no lifting.\n\n"
            "AGILE 8 (~10 min):\n"
            "1. Foam roll IT band — 60s/side\n"
            "2. Foam roll adductors (inner thigh) — 60s/side\n"
            "3. Foam roll thoracic spine — 60s up and down\n"
            "4. Glute bridge — 2 x 10 reps, squeeze at top\n"
            "5. Hip circles — 10/side, big slow circles\n"
            "6. Leg swings fore/aft — 10/side\n"
            "7. Leg swings lateral — 10/side\n"
            "8. Lateral band walk — 10 steps each direction (or unloaded if no band)\n\n"
            "FOAM ROLL (~8 min):\n"
            "- Quads — 60s/side\n"
            "- ITB — 60s/side\n"
            "- Calves — 60s/side\n"
            "- Glutes — 60s/side\n\n"
            "STRETCHING — post-run system (~7 min):\n"
            "- Standing quad stretch — 45s/side\n"
            "- Soleus stretch (bent knee against wall) — 45s/side\n"
            "  This is the running muscle nobody stretches — prevents Achilles issues\n"
            "- Hip flexor lunge stretch — 45s/side"
        ),
    },
    "race": {
        "label":        "RACE",
        "sport":        "Ride",  # overridden by sport field in CSV if set
        "warmup":       "none",
        "cooldown":     "none",
        "description":  "Race day.",
    },

    # ── BODYWEIGHT (Melbourne / travel — no gym, no bike) ─────────────────
    "bw": {
        "label":        "Strength — Bodyweight",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  2400,
        "description":  (
            "No gym available — full bodyweight session.\n\n"
            "3 rounds of:\n"
            "- Bulgarian split squat 3x10/side (use chair/bed)\n"
            "- Push-ups 3x max (elevate feet for harder)\n"
            "- Single-leg RDL 3x10/side (use any weight available)\n"
            "- Pike push-ups 3x10\n"
            "- Glute bridge 3x15\n"
            "- Chin-ups 3x max (if bar available) or inverted row under table\n\n"
            "Rest 60s between sets. Intensity over volume."
        ),
    },
    "bw_upper": {
        "label":        "Strength — Bodyweight Upper",
        "sport":        "WeightTraining",
        "warmup":       "agile8",
        "cooldown":     "lift",
        "moving_time":  1800,
        "description":  (
            "No gym — upper body focus.\n\n"
            "3 rounds of:\n"
            "- Push-ups 3x max\n"
            "- Pike push-ups 3x10\n"
            "- Chin-ups 3x max (or inverted row under table)\n"
            "- Diamond push-ups 3x10\n"
            "- Plank 3x45s\n\n"
            "Rest 60s between sets."
        ),
    },
}



# ─────────────────────────────────────────────
# WORKOUT CATEGORIES
# Maps type codes to Intervals.icu workout_doc category values.
# Valid values: WORKOUT, RACE, LONG_RUN, LONG_RIDE, RECOVERY, GYM, OTHER
# ─────────────────────────────────────────────

WORKOUT_CATEGORIES = {
    # Valid Intervals.icu event category values: WORKOUT, NOTE, RACE, TARGET
    # Strength
    "sq_rp":              "WORKOUT",
    "sq_rp_taper":        "WORKOUT",
    "sq_rp_light":        "WORKOUT",
    "sq_rp_deload":       "WORKOUT",
    "dl_sq":              "WORKOUT",
    "dl_sq_taper":        "WORKOUT",
    "dl_sq_deload":       "WORKOUT",
    "upper":              "WORKOUT",
    "full_med":           "WORKOUT",
    "bw":                 "WORKOUT",
    "bw_upper":           "WORKOUT",
    # Running
    "run_z2":             "WORKOUT",
    "run_z2_strides":     "WORKOUT",
    "run_long":           "WORKOUT",
    "run_cruise":         "WORKOUT",
    "run_threshold":      "WORKOUT",
    "run_threshold_hard": "WORKOUT",
    "run_easy":           "WORKOUT",
    # Cycling
    "ride_easy":          "WORKOUT",
    "ride_prerace":       "WORKOUT",
    # Other
    "off":                "NOTE",
    "walk":               "WORKOUT",
    "mobility":           "WORKOUT",
    "race":               "RACE",
}

# ─────────────────────────────────────────────
# CONTEXT SYSTEM
# Handles location/holiday overrides that change
# what sessions are available on given dates.
# ─────────────────────────────────────────────

# What each context allows / substitutes
CONTEXT_RULES = {
    "holiday": {
        "description": "On holidays — no gym, no bike, no run club/parkrun",
        "skip":        {"WeightTraining", "Ride"},   # drop these sports entirely
        "substitute":  {                              # swap type codes
            "sq_rp":        "bw",
            "sq_rp_taper":  "bw",
            "sq_rp_light":  "bw",
            "sq_rp_deload": "bw",
            "dl_sq":        "bw_upper",
            "dl_sq_taper":  "bw_upper",
            "dl_sq_deload": "bw_upper",
            "full_med":     "bw",
            "upper":        "bw_upper",
            "ride_easy":    None,                     # None = skip entirely
            "ride_prerace": None,
        },
        "note": "🏖️ HOLIDAY: Gym/bike not available. Session adapted to bodyweight.",
        # parkrun/club also skipped on holidays — handled via Saturday run note
        "skip_parkrun": True,
    },
    "melbourne": {
        "description": "In Melbourne — no home gym, no bike. Run + BW only.",
        "skip":        {"Ride"},
        "substitute":  {
            "sq_rp":        "bw",
            "sq_rp_taper":  "bw",
            "sq_rp_light":  "bw",
            "sq_rp_deload": "bw",
            "dl_sq":        "bw_upper",
            "dl_sq_taper":  "bw_upper",
            "dl_sq_deload": "bw_upper",
            "full_med":     "bw",
            "upper":        "bw_upper",
            "ride_easy":    None,
            "ride_prerace": None,
        },
        "note": "🏙️ MELBOURNE: No gym or bike. Session adapted to bodyweight.",
        "skip_parkrun": False,  # parkrun still available in Melbourne
    },
}


def load_contexts(contexts_file: str) -> list:
    """
    Load a contexts CSV with columns: start_date, end_date, context
    Returns list of (start_date, end_date, context_name) tuples.
    """
    if not contexts_file or not os.path.exists(contexts_file):
        return []
    contexts = []
    with open(contexts_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = datetime.strptime(row["start_date"].strip(), "%Y-%m-%d")
            end   = datetime.strptime(row["end_date"].strip(), "%Y-%m-%d")
            ctx   = row["context"].strip().lower()
            if ctx in CONTEXT_RULES:
                contexts.append((start, end, ctx))
            else:
                print(f"  ⚠️  Unknown context '{ctx}' — skipping")
    return contexts


def get_context_for_date(date_str: str, contexts: list) -> str | None:
    """Return the context name active on a given date, or None."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for start, end, ctx in contexts:
        if start <= dt <= end:
            return ctx
    return None


def apply_context(code: str, payload: dict, context_name: str, date: str) -> dict | None:
    """
    Apply context rules to a payload.
    Returns modified payload, or None if the session should be skipped.
    """
    rules = CONTEXT_RULES[context_name]
    wt    = WORKOUT_TYPES.get(code, {})
    sport = wt.get("sport", "")

    # Check if sport is skipped outright and no substitution exists
    sub_code = rules["substitute"].get(code)
    sport_skipped = sport in rules["skip"]

    if sport_skipped and sub_code is None:
        # No substitute — skip entirely
        print(f"    ⏭️  [{context_name.upper()}] Skipping {code} ({sport} not available)")
        return None

    if code in rules["substitute"]:
        if sub_code is None:
            print(f"    ⏭️  [{context_name.upper()}] Skipping {code} (not available)")
            return None
        # Substitute with new workout type
        new_wt = WORKOUT_TYPES[sub_code]
        warmup_text   = WARMUPS.get(new_wt["warmup"], "")
        cooldown_text = COOLDOWNS.get(new_wt["cooldown"], "")
        body_parts = [rules["note"]]
        if warmup_text:
            body_parts.append(f"WARMUP:\n{warmup_text}")
        body_parts.append(new_wt["description"])
        if cooldown_text:
            body_parts.append(f"COOLDOWN:\n{cooldown_text}")

        payload["name"]         = new_wt["label"]
        payload["type"] = new_wt["sport"]  # raw REST API field name
        payload["workout_doc"]  = {"description": "\n\n".join(body_parts)}
        payload["category"] = WORKOUT_CATEGORIES.get(sub_code, "WORKOUT")
        if new_wt.get("moving_time"):
            payload["moving_time"] = new_wt["moving_time"]
        print(f"    🔄 [{context_name.upper()}] {code} → {sub_code}")
        return payload

    # Session not in substitute map — passes through unchanged,
    # but add context note to description
    if "workout_doc" in payload and "description" in payload["workout_doc"]:
        payload["workout_doc"]["description"] = (
            rules["note"] + "\n\n" + payload["workout_doc"]["description"]
        )

    # Handle Saturday parkrun skip on holidays
    dt = datetime.strptime(date, "%Y-%m-%d")
    if dt.weekday() == 5 and rules.get("skip_parkrun") and code in ("run_long", "run_easy", "run_z2"):
        desc = payload["workout_doc"]["description"]
        payload["workout_doc"]["description"] = (
            desc + "\n\n⚠️ HOLIDAY: Parkrun/club skipped. Run solo at easy effort."
        )

    return payload


# ─────────────────────────────────────────────
# INTERVAL STRUCTURE LIBRARY
# Maps rep/duration shortcodes to workout steps
# ─────────────────────────────────────────────

def build_run_steps(workout_code: str, reps: int, duration_mins: int) -> list:
    """Build structured workout steps for running intervals."""
    warmup_step    = {"duration": 600, "warmup": True,  "text": "Easy warmup",  "hr": {"value": 1, "units": "hr_zone"}}
    cooldown_step  = {"duration": 600, "cooldown": True, "text": "Easy cooldown", "hr": {"value": 1, "units": "hr_zone"}}

    if workout_code in ("run_cruise",):
        interval = {"duration": duration_mins * 60, "text": f"{duration_mins} min cruise", "hr": {"value": 3, "units": "hr_zone"}}
        recovery = {"duration": 90,  "text": "90s recovery jog", "hr": {"value": 1, "units": "hr_zone"}}
    elif workout_code in ("run_threshold",):
        interval = {"duration": duration_mins * 60, "text": f"{duration_mins} min threshold", "hr": {"value": 4, "units": "hr_zone"}}
        recovery = {"duration": 120, "text": "2 min recovery jog", "hr": {"value": 1, "units": "hr_zone"}}
    elif workout_code in ("run_threshold_hard",):
        interval = {"duration": duration_mins * 60, "text": f"{duration_mins} min hard threshold", "hr": {"value": 4, "units": "hr_zone"}}
        recovery = {"duration": 90,  "text": "90s recovery jog", "hr": {"value": 1, "units": "hr_zone"}}
    else:
        return []

    repeat_block = {
        "reps": reps,
        "steps": [interval, recovery]
    }

    return [warmup_step, repeat_block, cooldown_step]


# ─────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────

def api_post_event(payload: dict, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"  [DRY RUN] Would POST: {payload['name']} on {payload.get('start_date_local', payload.get('start_date', ''))}")
        return {}

    url = f"{BASE_URL}/{ATHLETE_ID}/events"
    resp = requests.post(
        url,
        auth=("API_KEY", API_KEY),
        json=payload,
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        print(f"  ❌ Error {resp.status_code}: {resp.text}")
        return {}
    return resp.json()


def api_delete_events_range(start: str, end: str, dry_run: bool = False):
    """Delete all events in a date range before importing."""
    url = f"{BASE_URL}/{ATHLETE_ID}/events"
    resp = requests.get(
        url,
        auth=("API_KEY", API_KEY),
        params={"oldest": start, "newest": end},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"  ❌ Could not fetch events to delete: {resp.status_code}")
        return

    events = resp.json()
    if not events:
        print("  No existing events in range to delete.")
        return

    for ev in events:
        eid = ev.get("id")
        if not eid:
            continue
        if dry_run:
            print(f"  [DRY RUN] Would delete event {eid}: {ev.get('name')}")
        else:
            del_resp = requests.delete(
                f"{BASE_URL}/{ATHLETE_ID}/events/{eid}",
                auth=("API_KEY", API_KEY),
                timeout=15,
            )
            status = "✅" if del_resp.status_code == 200 else "❌"
            print(f"  {status} Deleted {eid}: {ev.get('name')}")


# ─────────────────────────────────────────────
# BUILD EVENT PAYLOAD
# ─────────────────────────────────────────────

def _saturday_run_start(date: str, total_mins: int | None) -> str:
    """
    Calculate Saturday long run start time working backwards from 7:00am parkrun.

    Data basis (from actual activity history):
    - Easy Z2 pace at HR ~155-160 bpm: ~5:40-6:00/km → use 6:00/km for planning
    - Parkrun estimated time: ~26 min (race-ish effort, HR spikes fine)

    Strategy:
    - Arrive parkrun 06:55 (7:00am start)
    - Run easy Z2 from home/car BEFORE arriving if total > ~35 min
    - If total <= 35 min: parkrun alone is enough, arrive 06:55
    - If total > 35 min: start = 07:00 - 5min buffer - (total - 26) min of pre-running

    Example: 60 min total → 34 min before parkrun → start 06:21, arrive ~06:55, run parkrun, done.
    """
    PARKRUN_MINS  = 26   # estimated parkrun time at natural effort
    ARRIVE_BUFFER = 5    # arrive 5 min before 7:00am = 06:55
    PARKRUN_CLOCK = 7 * 60  # 07:00 in minutes from midnight

    if not total_mins or total_mins <= (PARKRUN_MINS + ARRIVE_BUFFER):
        return f"{date}T06:55:00"

    pre_run_mins = total_mins - PARKRUN_MINS
    start_clock  = PARKRUN_CLOCK - ARRIVE_BUFFER - pre_run_mins
    start_clock  = max(start_clock, 5 * 60 + 30)  # sanity floor at 05:30

    h = start_clock // 60
    m = start_clock % 60
    return f"{date}T{h:02d}:{m:02d}:00"


def resolve_start_datetime(date: str, code: str, start_time_override: str, mins: int | None = None) -> str:
    """
    Returns ISO8601 datetime string for the event start time.

    Priority:
    1. start_time column in CSV (HH:MM format) — always wins
    2. Saturday runs → calculated from total duration working back from 7:00am parkrun
    3. Day-of-week defaults:
         Monday         → 07:00 (morning — strength before lunchtime swim)
         Tue/Wed/Thu/Fri → 12:00 (lunchtime)
         Saturday       → 06:55 (non-run sessions)
         Sunday         → 08:00 (flexible)
    """
    if start_time_override:
        return f"{date}T{start_time_override}:00"

    dt = datetime.strptime(date, "%Y-%m-%d")
    weekday = dt.weekday()  # 0=Mon … 5=Sat … 6=Sun

    run_codes = ("run_long", "run_easy", "run_z2", "run_z2_strides",
                 "run_cruise", "run_threshold", "run_threshold_hard")

    if weekday == 5 and code in run_codes:
        return _saturday_run_start(date, mins)

    default_times = {
        0: "07:00",  # Monday — morning strength (lunchtime is swim)
        1: "12:00",  # Tuesday — lunchtime
        2: "12:00",  # Wednesday — lunchtime (morning is swim)
        3: "12:00",  # Thursday — lunchtime
        4: "12:00",  # Friday — lunchtime
        5: "06:55",  # Saturday — non-run sessions
        6: "08:00",  # Sunday — flexible
    }
    return f"{date}T{default_times[weekday]}:00"


def build_parkrun_note(code: str, date: str, mins: int) -> str:
    """
    For Saturday long runs: add parkrun context to the description.
    Explains how the total duration relates to parkrun + additional running.
    """
    dt = datetime.strptime(date, "%Y-%m-%d")
    if dt.weekday() != 5:
        return ""
    if code not in ("run_long", "run_easy", "run_z2"):
        return ""

    parkrun_mins = 27  # conservative estimate ~5:24/km pace at current fitness
    extra_mins = max(0, (mins or 0) - parkrun_mins)

    if extra_mins > 0:
        return (
            f"📍 PARKRUN: Arrive 6:55am sharp (7:00am start).\n"
            f"Parkrun 5km (~{parkrun_mins} min). "
            f"Add ~{extra_mins} min easy running before or after to hit total target.\n"
            f"Run the parkrun at controlled effort — it's part of the long run, not a race."
        )
    else:
        return (
            "📍 PARKRUN: Arrive 6:55am sharp (7:00am start).\n"
            "Parkrun 5km is the session today — no additional running needed.\n"
            "Run at controlled effort, HR cap 150 bpm."
        )


def build_payload(row: dict) -> dict:
    date               = row["date"].strip()
    code               = row["type"].strip().lower()
    name_suffix        = row.get("name", "").strip()
    mins               = int(row["mins"]) if row.get("mins", "").strip() else None
    distance_m         = int(float(row["distance_m"])) if row.get("distance_m", "").strip() else None
    sport_override     = row.get("sport", "").strip()
    reps               = int(row["reps"]) if row.get("reps", "").strip() else None
    int_mins           = int(row["int_mins"]) if row.get("int_mins", "").strip() else None
    notes              = row.get("notes", "").strip()
    start_time_override = (row.get("start_time") or "").strip()

    if code not in WORKOUT_TYPES:
        print(f"  ⚠️  Unknown type '{code}' on {date} — skipping")
        return {}

    wt = WORKOUT_TYPES[code]

    # Build name
    base_name = wt["label"]
    if name_suffix:
        base_name = f"{base_name} | {name_suffix}"

    # Build description
    warmup_text    = WARMUPS.get(wt["warmup"], "")
    cooldown_text  = COOLDOWNS.get(wt["cooldown"], "")
    parkrun_note   = build_parkrun_note(code, date, mins)

    body_parts = []
    if parkrun_note:
        body_parts.append(parkrun_note)
    if warmup_text:
        body_parts.append(f"WARMUP:\n{warmup_text}")
    body_parts.append(wt["description"])
    if mins:
        body_parts.append(f"Duration: {mins} min total")
    if notes:
        body_parts.append(f"Notes: {notes}")
    if cooldown_text:
        body_parts.append(f"COOLDOWN:\n{cooldown_text}")

    description = "\n\n".join(body_parts)

    # Build workout doc
    workout_doc = {"description": description}

    # Add structured steps for quality runs
    if code in ("run_cruise", "run_threshold", "run_threshold_hard") and reps and int_mins:
        steps = build_run_steps(code, reps, int_mins)
        if steps:
            workout_doc["steps"] = steps
            workout_doc["target"] = "HR"

    # Resolve start datetime
    start_dt = resolve_start_datetime(date, code, start_time_override, mins)

    # Build payload
    sport = sport_override if sport_override else wt["sport"]
    moving_time = (mins * 60) if mins else wt.get("moving_time")

    # category is a top-level event field (not inside workout_doc)
    # Valid values: WORKOUT, NOTE, RACE, TARGET
    event_category = WORKOUT_CATEGORIES.get(code, "WORKOUT")
    payload = {
        "start_date_local": start_dt,  # Intervals.icu REST API field name
        "name":         base_name,
        "category":     event_category,
        "type":         sport,        # raw REST API uses "type", not "workout_type"
        "workout_doc":  workout_doc,
    }
    if moving_time:
        payload["moving_time"] = moving_time
    if distance_m:
        payload["distance"] = distance_m

    return payload


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Schedule training events to Intervals.icu from a CSV plan."
    )
    parser.add_argument("csv_file", help="Path to the training plan CSV")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be posted without sending to API")
    parser.add_argument("--clear", action="store_true",
                        help="Delete existing events in CSV date range before importing")
    parser.add_argument("--contexts", metavar="CONTEXTS_CSV",
                        help="Optional CSV of date ranges with context overrides (holiday/melbourne)")
    args = parser.parse_args()

    if not API_KEY or not ATHLETE_ID:
        print("❌ Missing INTERVALS_API_KEY or INTERVALS_ATHLETE_ID in environment / .env file")
        sys.exit(1)

    # Load context overrides
    contexts = load_contexts(args.contexts) if args.contexts else []
    if contexts:
        print(f"🗺️  Loaded {len(contexts)} context override(s):")
        for start, end, ctx in contexts:
            rule = CONTEXT_RULES[ctx]
            print(f"   {start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}: {ctx} — {rule['description']}")

    # Read CSV
    with open(args.csv_file, newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]

    if not rows:
        print("❌ CSV is empty")
        sys.exit(1)

    dates = [r["date"].strip() for r in rows if r.get("date")]
    start_date = min(dates)
    end_date   = max(dates)

    print(f"\n📅 Plan: {start_date} → {end_date} ({len(rows)} events)")

    # Optionally clear existing events
    if args.clear and not args.dry_run:
        print(f"\n🗑️  Clearing existing events {start_date} → {end_date}...")
        api_delete_events_range(start_date, end_date, dry_run=args.dry_run)

    # Post events
    print(f"\n📤 Posting events{'(DRY RUN)' if args.dry_run else ''}...\n")
    success = 0
    skipped = 0

    for row in rows:
        date = row.get("date", "").strip()
        code = row.get("type", "").strip().lower()

        # Build base payload
        payload = build_payload(row)
        if not payload:
            skipped += 1
            continue

        # Apply context override if active on this date
        context_name = get_context_for_date(date, contexts)
        if context_name:
            payload = apply_context(code, payload, context_name, date)
            if payload is None:
                skipped += 1
                continue

        result = api_post_event(payload, dry_run=args.dry_run)
        if result or args.dry_run:
            print(f"  ✅ {payload.get('start_date_local', payload.get('start_date', ''))} — {payload['name']}")
            success += 1
        else:
            skipped += 1

    print(f"\n✅ Done — {success} posted, {skipped} skipped")


if __name__ == "__main__":
    main()