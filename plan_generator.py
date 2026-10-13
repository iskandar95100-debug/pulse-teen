"""Rule-based 4-week plan generator (PulseTeen protocol)."""
import re

WEEKS = [
    ("Base Building", 30, "Form correction and habit formation. Low intensity, no heavy weights.", (50, 60)),
    ("Progression", 35, "Incremental volume at moderate intensity.", (60, 70)),
    ("The Pulse Challenge", 45, "Pushing new boundaries and heart-rate zones.", (65, 80)),
    ("Peak Performance", 50, "Reaching your target goals and solidifying the habit.", (70, 85)),
]
DAYS = [("Mon", "aer", "Aerobic"), ("Tue", "flx", "Flexibility"), ("Wed", "rest", "Active recovery"),
        ("Thu", "str", "Strength"), ("Fri", "soc", "Team sport or social activity"),
        ("Sat", "out", "Outdoor"), ("Sun", "off", "Full rest")]

# "name|flags": j=impact, k=knee, b=back, s=shoulder, w=wrist, B=bands, G=gym,
# O=needs outdoors, K=kids only, S=seniors only, T=timed (otherwise reps)
POOL = {
    "aer": ["Brisk walk or easy jog intervals|T", "Shuttle runs|jkT", "Marching with high knees|T",
            "Shadow boxing|T", "Dance cardio|T", "Step-ups on a stair|kT", "Jumping jacks|jkT",
            "Skipping rope|jT", "Stationary bike|GT", "Incline fast walk|T", "Bear crawl tag|KT",
            "Seated marching|ST"],
    "flx": ["Cat-cow|wT", "Child's pose|kT", "Hamstring stretch|T", "Hip flexor stretch|kT",
            "Thoracic rotation|T", "Neck and shoulder rolls|T", "Downward dog|wsT", "Butterfly stretch|T",
            "Cobra stretch|bwT", "Seated spinal twist|T", "Gentle yoga flow|T", "Standing quad stretch|kT"],
    "str": ["Bodyweight squats|k", "Wall or incline push-ups|sw", "Glute bridges|", "Plank|wsbT",
            "Reverse lunges|k", "Superman hold|bT", "Dead bug|", "Bird dog|w", "Calf raises|",
            "Chair tricep dips|sw", "Band rows|B", "Band squats|Bk", "Band chest press|Bs",
            "Goblet squat|Gk", "Dumbbell rows|G", "Machine chest press|Gs", "Animal walks|K",
            "Chair squats|S", "Wall push-ups|Sw"],
    "soc": ["Basketball or volleyball with friends|jk", "Badminton or table tennis|",
            "Group walk or dance session|", "Active game with family or friends|j",
            "Community fitness class|", "Partner ball passing|"],
    "out": ["Cycling ride|kO", "Hiking or nature walk|O", "Park walk with a few hills|O",
            "Swimming or water play|", "Stair climbing or indoor brisk walk|", "Home dance session|"],
}
GOAL_NOTES = {
    "fat": "Goal focus: steady aerobic work. From Week 2, try three 1-minute faster bursts in aerobic sessions.",
    "strength": "Goal focus: an extra set in strength circuits.",
    "stamina": "Goal focus: a slightly higher heart-rate ceiling in later weeks.",
    "flex": "Goal focus: extra stretches in flexibility sessions.",
    "focus": "Goal focus: longer breathing practice in every cool-down.",
    "health": "Goal focus: a balanced mix of everything.",
}
LIMIT_WORDS = {"knee": "k", "leg": "k", "hip": "k", "ankle": "k", "back": "b", "spine": "b",
               "shoulder": "s", "arm": "s", "elbow": "s", "wrist": "w", "hand": "w"}


def _name(e): return e.split("|")[0]
def _flags(e): return e.split("|")[1] if "|" in e else ""


def water_for(age):
    """(range text, cups of 250 ml) for the daily water goal."""
    if age is None: return "2.5–3", 12
    for limit, text, litres in ((9, "1.2–1.5", 1.5), (13, "1.5–2", 2), (18, "2–2.5", 2.5),
                                (60, "2.5–3", 3)):
        if age < limit: return text, round(litres * 4)
    return "1.7–2.5", 10


def sleep_for(age):
    if age is None: return "8–10"
    for limit, text in ((6, "10–13"), (13, "9–12"), (18, "8–10"), (65, "7–9")):
        if age < limit: return text
    return "7–8"


def generate_plan(a):
    age, level, goal = a["age"], a["level"], a["goal"]
    eq = a.get("eq") or ["none"]
    lim = {LIMIT_WORDS[w] for w in re.findall("|".join(LIMIT_WORDS), (a.get("lim") or "").lower())}
    bmi = a["weight"] / ((a["height"] / 100) ** 2)          # used quietly, never shown
    low = age >= 60 or a["body"] == "heavier" or bmi >= 30
    slim = a["body"] == "slim"

    def ok(e):
        f = _flags(e)
        return not ((("K" in f) and age >= 13) or (("S" in f) and age < 60)
                    or (("B" in f) and "bands" not in eq) or (("G" in f) and "gym" not in eq)
                    or (("O" in f) and "outdoor" not in eq) or (("j" in f) and low)
                    or any(x in f for x in lim))

    def pick(pool, n, s):
        items = [e for e in pool if ok(e)] or ["Gentle walking|T"]
        return [items[(s + i) % len(items)] for i in range(min(n, len(items)))]

    af = 0.6 if age < 13 else 0.7 if age >= 60 else 1.0
    lf = {"beginner": 0.85, "intermediate": 1.0, "active": 1.1}.get(level, 1.0)
    weeks = []
    for w, (title, base, theme, (lo, hi)) in enumerate(WEEKS):
        total = max(20, min(round(base * af * lf / 5) * 5, a["time"]))
        if a["time"] < 20: total = a["time"]
        wc = 5 if total >= 20 else 3
        pk = total - 2 * wc
        if age >= 60: hi -= 5
        if goal == "stamina": hi += 3
        mx = 220 - age
        zone = ("fun pace: you can still chat" if age < 13
                else f"{round(mx * lo / 100)}–{round(mx * hi / 100)} bpm ({lo}–{hi}% of max)")
        warm = ("Playful moves: arm circles, animal walks, gentle jumps" if age < 13 else
                "Arm circles, leg swings, marching, torso twists, a gradual build-up of pace")
        cool = ("Static stretches, then 4-7-8 breathing for 4 rounds" if goal == "focus" else
                "Static stretches for legs, back and chest, then slow deep breathing")
        days = []
        for i, (d, typ, dtitle) in enumerate(DAYS):
            s, hr, minutes = w * 3 + i, zone, total
            if typ == "aer":
                n = min(3 + (w > 1), max(2, pk // 6)); each = round(pk / n)
                peak = [f"{_name(e)}: {each} min" for e in pick(POOL["aer"], n, s)]
            elif typ == "flx":
                sec = (30, 35, 40, 45)[w]; hr = "Relaxed, breathing easy"
                peak = [f"{_name(e)}: 2 × {sec} s" for e in
                        pick(POOL["flx"], 4 + (w > 1) + (2 if goal == "flex" else 0), s)]
            elif typ == "str":
                sets = max(1, (2, 2, 3, 3)[w] + (goal == "strength") - (age < 13 or age >= 60))
                reps = "8–10" if age >= 60 else "8" if age < 13 else "10–12"
                sec = (20, 30, 40, 45)[w]; hr = "Light to moderate, focus on form"
                peak = [f"{_name(e)}: {sets} × {str(sec) + ' s' if 'T' in _flags(e) else reps}"
                        for e in pick(POOL["str"], 4 + (w > 1) + slim, s)]
                peak.append("Rest 30–45 s between exercises. Keep it light and focus on form"
                            + (". No heavy weights this week." if w == 0 else "."))
            elif typ in ("soc", "out"):
                peak = [f"{_name(e)}: pick one, {pk} min" for e in pick(POOL[typ], 3, s)]
            elif typ == "rest":
                peak = ["Gentle 15–20 min walk", "Light stretching or easy yoga",
                        "Slow 4-7-8 breathing, 4 rounds"]
                minutes, hr = 20, "Easy: you should feel relaxed"
            else:
                peak = ["Full rest. Sleep well, drink water and enjoy time away from training."]
                minutes, hr = 0, "—"
            days.append(dict(d=d, type=typ, title=dtitle, min=minutes, pk=pk,
                             wc=0 if typ in ("rest", "off") else wc, hr=hr,
                             warm=warm, cool=cool, peak=peak))
        weeks.append(dict(title=title, theme=theme, total=total, days=days))

    notes = []
    if age < 13: notes.append("Shorter, play-based sessions suited to children.")
    if age >= 60: notes.append("Gentler, shorter sessions with lower heart-rate targets and low-impact options.")
    if low and age < 60: notes.append("Low-impact options chosen to be kind to your joints.")
    if slim: notes.append("Extra strength work added to help you build steady strength.")
    if "bands" not in eq and "gym" not in eq: notes.append("Bodyweight exercises used because no equipment is available.")
    if "outdoor" not in eq: notes.append("Indoor options chosen for your outdoor day.")
    if lim: notes.append("Exercises that could stress the areas you mentioned were swapped out.")
    notes.append(GOAL_NOTES.get(goal, GOAL_NOTES["health"]))
    return {"weeks": weeks, "notes": notes}
