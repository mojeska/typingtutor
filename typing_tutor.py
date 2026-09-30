#!/usr/bin/env python3
"""Terminal touch-typing tutor for QWERTY, Dvorak and Colemak keyboards.

Teaching approach (the classic touch-typing method used by most courses):
  * Start from the home-row anchors (F / J) and add two keys at a time,
    working outward: home row, top row, bottom row, then Shift, numbers
    and punctuation.
  * Every exercise uses only keys you have already been taught.
  * Each key belongs to one finger. The on-screen keyboard is coloured by
    finger and highlights the next key, so you never need to look down.
  * Accuracy first: a wrong key must be corrected before you can move on,
    and a lesson unlocks the next one only at >= 95% accuracy plus a
    modest speed goal.
  * Per-key error and speed stats drive a "weak keys" practice mode, and
    the keys you type by mistake drive "confused pairs" contrast drills.
  * Timed tests (1, 2, 5 minutes) and typing your own text files.
  * Lessons are defined by physical key position, so the same course works
    for every layout. Dvorak/Colemak can be learned on a QWERTY system by
    letting the tutor translate keys.

WPM uses the standard definition: (characters typed / 5) per minute.
Each person has a profile; progress is saved to
$XDG_DATA_HOME/typing-tutor/profiles/<name>.json.
"""
import argparse
import curses
import glob
import json
import locale
import os
import random
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "typing-tutor"
PROFILES_DIR = DATA_DIR / "profiles"
LEGACY_FILE = DATA_DIR / "progress.json"  # single-user progress from before profiles
SETTINGS_FILE = DATA_DIR / "settings.json"
DATA_FILE = LEGACY_FILE  # the active profile's file, set by open_profile()
PASS_ACCURACY = 95.0
EXERCISE_TOKENS = 30

# The course, by physical key position (row, column) so it works on any layout.
# Rows: 0 number, 1 top, 2 home, 3 bottom. {0}/{1} in tips are the key names.
LESSON_PLAN = [
    dict(title="Home row", pos=[(2, 3), (2, 6)], wpm=10,
         tip="Rest your index fingers on {0} and {1} - feel the bumps? That's home."),
    dict(title="Home row", pos=[(2, 2), (2, 7)], wpm=10,
         tip="Middle fingers rest on {0} and {1}, right beside your index fingers."),
    dict(title="Home row", pos=[(2, 1), (2, 8)], wpm=12,
         tip="Ring fingers rest on {0} and {1}."),
    dict(title="Home row", pos=[(2, 0), (2, 9)], wpm=12,
         tip="Pinkies rest on {0} and {1}. Thumbs float over the space bar."),
    dict(title="Home row", pos=[(2, 4), (2, 5)], wpm=13,
         tip="Index fingers reach sideways to {0} and {1}, then snap back home."),
    dict(title="Top row", pos=[(1, 2), (1, 7)], wpm=14,
         tip="Middle fingers reach up to {0} and {1}. Keep the other fingers anchored."),
    dict(title="Top row", pos=[(1, 3), (1, 6)], wpm=15,
         tip="Index fingers reach up to {0} and {1}."),
    dict(title="Top row", pos=[(1, 4), (1, 5)], wpm=15,
         tip="Index fingers stretch up and inward to {0} and {1}."),
    dict(title="Top row", pos=[(1, 1), (1, 8)], wpm=16,
         tip="Ring fingers reach up to {0} and {1}."),
    dict(title="Top row", pos=[(1, 0), (1, 9)], wpm=16,
         tip="Pinkies reach up to {0} and {1}."),
    dict(title="Bottom row", pos=[(3, 3), (3, 6)], wpm=17,
         tip="Index fingers curl down to {0} and {1}."),
    dict(title="Bottom row", pos=[(3, 2), (3, 7)], wpm=17,
         tip="Middle fingers curl down to {0} and {1}."),
    dict(title="Bottom row", pos=[(3, 1), (3, 8)], wpm=18,
         tip="Ring fingers curl down to {0} and {1}."),
    dict(title="Bottom row", pos=[(3, 0), (3, 9)], wpm=18,
         tip="Pinkies curl down to {0} and {1}."),
    dict(title="Bottom row", pos=[(3, 4), (3, 5)], wpm=18,
         tip="Index fingers reach down and inward to {0} and {1}."),
    dict(title="Capitals and {0}", pos=[(2, 10)], caps=True, wpm=18,
         tip="Hold Shift with the pinky of the OPPOSITE hand to the letter. "
             "The right pinky types the {0}."),
    dict(title="Number row", keys="1234567890", wpm=15,
         tip="Reach straight up; each number uses the same finger as the letters below it."),
    dict(title="Punctuation: ? ! : -", keys="?!:-", wpm=18,
         tip="? ! and : need Shift. The highlighted keys show where each one lives."),
    dict(title="Real sentences", keys="", sentences=True, wpm=25,
         tip="Everything together. Aim for a steady rhythm rather than bursts of speed."),
]

_WORDS = """
a add adds ads all alas ask asks dad dads fad fads fall falls flask lad lads lass sad salad salsa
as has had half hall halls hash gas glad flag flags flash shall slash lash gash dash hag jag sag
she he see seed seek side sides idea ideas like likes lake jade fed fee feel feels field fields
desk desks kid kids said seal sell self shed his is if did die dies hide hike hill dish fish fig
gift shift held head heal deal ideal age ages aide
her here red read ride rise risk rug sure use used user rush fur fire free fresh hurt hard shirt
sugar area large the that this they their them there then these those than it its at to too tree
street treat true hat heat eat tea yet yes yard year day days try tiny type style trust truth
third three thirty data we was way what who whose wash wide wife will with work word world write
wrote water white while wood would window own two row show slow low how now tower power follow
quit quiet quite quick queen question equal square request quota pie pay page paper peer people
place plus pure post point open top help keep deep upper hope pepper spot sport support
very save give live love move over have even ever every seven voice video valid vast visit movie
him make more most much must my me may man men mind mile time team some same seem small home room
can come call care case city cool cost cover clock check coach cycle back black cake
fox box six next text tax fix mix extra exact exit expert explain
zero size zone lazy amaze prize dozen crazy freeze puzzle quiz jazz
be but by big bag bed bus bit best both book brown blue job jump number ban band bank banana begin
being between nine name new not no night note never know knew kind under nothing known
about above after again against almost along also always among another answer any anyone around
because before below better bring build business busy change child children class clear close
common company complete could country course create current different during early easy either end
enough enter example face fact family far fast father few final find fine first five food for
force form found four friend from front full game general get girl goal good great green ground
group grow guess hand happy heart heavy high hold horse hour house human hundred important inside
interest into itself just land language last late later laugh learn least leave left less letter
level life light line list listen little long look main many matter mean measure might minute money
month morning mother mountain music near need north notice often old once only order other our out
outside paint part party pass past pattern person picture piece plan plant play please poor
possible pound present problem produce public pull put rain reach ready real reason remember rest
right river road rock round rule run school science sea second sentence set several shape short
should simple since sing sister sit sleep smile snow something song soon sound south space speak
special spell spring stand star start state stay step still stop story strong student study such
summer sun system table take talk teach tell thank thing think though thought through today
together told tomorrow took town travel turn until upon usual walk wall want warm watch week weight
well went were west where which why wind winter wish without woman wonder young your
"""
WORDS = sorted({w for w in _WORDS.split() if w.isalpha()})

SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "Pack my box with five dozen liquor jugs.",
    "How vexingly quick daft zebras jump!",
    "Sphinx of black quartz, judge my vow.",
    "Keep your eyes on the screen and your fingers on the home row.",
    "Accuracy comes first; speed will follow with steady practice.",
    "Slow and even typing builds muscle memory that lasts.",
    "Every finger has its own keys, so let each one do its job.",
    "Return to the home row after every reach, even when you are in a hurry.",
    "Short daily sessions beat one long session each week.",
    "Rhythm matters more than raw speed: type each key at the same pace.",
    "If you make a mistake, slow down a little and reset your rhythm.",
    "The five boxing wizards jump quickly.",
    "A good typist can reach 40 to 60 words per minute without looking down.",
    "Don't stare at the keyboard - trust your fingers to find their way.",
    "Sit up straight, relax your shoulders, and keep your wrists level.",
    "Jackdaws love my big sphinx of quartz.",
    "Practice makes progress, and progress makes practice easier.",
    "She sold 12 jars of jam at the market on Saturday.",
    "Is it better to type fast with errors, or slowly and correctly?",
    "The train leaves at 7:45, so we should get to the station by 7:30.",
    "Write clearly, read carefully, and check your work twice.",
    "My new laptop has a quiet keyboard with a light, crisp touch.",
    "Waltz, bad nymph, for quick jigs vex.",
]

# ---------------------------------------------------------------------------
# Keyboard model
# ---------------------------------------------------------------------------

LAYOUTS = {
    "qwerty": dict(name="QWERTY",
                   rows=("`1234567890-=", "qwertyuiop[]", "asdfghjkl;'", "zxcvbnm,./"),
                   shifted=("~!@#$%^&*()_+", "QWERTYUIOP{}", 'ASDFGHJKL:"', "ZXCVBNM<>?")),
    "dvorak": dict(name="Dvorak",
                   rows=("`1234567890[]", "',.pyfgcrl/=", "aoeuidhtns-", ";qjkxbmwvz"),
                   shifted=("~!@#$%^&*(){}", '"<>PYFGCRL?+', "AOEUIDHTNS_", ":QJKXBMWVZ")),
    "colemak": dict(name="Colemak",
                    rows=("`1234567890-=", "qwfpgjluy;[]", "arstdhneio'", "zxcvbkm,./"),
                    shifted=("~!@#$%^&*()_+", "QWFPGJLUY:{}", 'ARSTDHNEIO"', "ZXCVBKM<>?")),
}
ROW_OFFSETS = (0, 6, 7, 9)
KB_WIDTH = 56
# Finger for each column of the letter rows; the number row sits half a key left.
COL_FINGERS = ["left pinky", "left ring", "left middle", "left index", "left index",
               "right index", "right index", "right middle", "right ring"]
KEY_NAMES = {",": "comma", ".": "period", "/": "slash", ";": "semicolon",
             "'": "apostrophe", "-": "hyphen", "[": "left bracket", "=": "equals"}

# Set by set_layout(): the active layout's keyboard, fingers and course.
LAYOUT = "qwerty"
KB_ROWS, FINGERS, SHIFTED, TYPEABLE, REMAP, LESSONS = [], {}, {}, set(), {}, []


def key_name(k):
    return KEY_NAMES.get(k, k.upper())


def build_lessons(rows):
    lessons = []
    for plan in LESSON_PLAN:
        lesson = dict(plan)
        if "pos" in plan:
            keys = "".join(rows[r][c] for r, c in plan["pos"])
            names = [key_name(k) for k in keys]
            lesson["keys"] = keys
            lesson["title"] = (plan["title"].format(*keys) if "{" in plan["title"]
                               else f"{plan['title']}: {' '.join(keys)}")
            lesson["tip"] = plan["tip"].format(*names)
            del lesson["pos"]
        lessons.append(lesson)
    return lessons


def set_layout(key, remap=False):
    """Activate a layout. With remap, keys from a QWERTY system are translated."""
    global LAYOUT, KB_ROWS, FINGERS, SHIFTED, TYPEABLE, REMAP, LESSONS
    lay = LAYOUTS[key]
    rows, shifted = lay["rows"], lay["shifted"]
    LAYOUT = key
    KB_ROWS = list(zip(rows, ROW_OFFSETS))
    FINGERS = {" ": "either thumb"}
    for r, row in enumerate(rows):
        for c, k in enumerate(row):
            col = max(0, c - (r == 0))
            FINGERS[k] = COL_FINGERS[col] if col < len(COL_FINGERS) else "right pinky"
    SHIFTED = {s: u for srow, urow in zip(shifted, rows) for s, u in zip(srow, urow)
               if not s.isalpha()}
    TYPEABLE = set("".join(rows + shifted)) | {" "}
    qw = LAYOUTS["qwerty"]
    REMAP = {q: k for qrow, krow in zip(qw["rows"] + qw["shifted"], rows + shifted)
             for q, k in zip(qrow, krow) if q != k} if remap else {}
    LESSONS = build_lessons(rows)


set_layout("qwerty")

# colour pair numbers
GREEN, RED, PINKY, RING, MIDDLE, INDEX, ERRBG = range(1, 8)
YELLOW = INDEX
FINGER_COLOR = {"pinky": PINKY, "ring": RING, "middle": MIDDLE, "index": INDEX, "thumb": 0}


def base_key(ch):
    """Return (unshifted key, needs_shift) for a character."""
    if ch.isupper():
        return ch.lower(), True
    if ch in SHIFTED:
        return SHIFTED[ch], True
    return ch, False


def shift_side(base):
    """Touch typists press Shift with the hand opposite the key."""
    return "shift_r" if FINGERS.get(base, "").startswith("left") else "shift_l"


# ---------------------------------------------------------------------------
# Exercise generation
# ---------------------------------------------------------------------------

def lesson_chars(upto):
    """Characters taught in lessons 0..upto, and whether capitals are taught."""
    chars, caps = set(), False
    for lesson in LESSONS[:upto + 1]:
        chars |= set(lesson["keys"])
        caps = caps or lesson.get("caps", False)
    return chars, caps


def pseudo_word(letters, focus):
    return "".join(random.choice(focus) if focus and random.random() < 0.4 else random.choice(letters)
                   for _ in range(random.randint(2, 5)))


def key_drill(new, letters, new_caps):
    """Short repetition drills for the keys being introduced."""
    toks = [k * 3 for k in new]
    for _ in range(max(3, 6 - len(new))) if new else ():
        toks.append("".join(random.choice(new) if random.random() < 0.5 or not letters
                            else random.choice(letters) for _ in range(random.randint(3, 4))))
    if new_caps:
        toks += [c.upper() + c for c in random.sample(letters, min(4, len(letters)))]
    return toks[:12]


def attach(word, sym, pool):
    if sym in "/-":
        return word + sym + random.choice(pool)
    if sym == "'":
        return word + "'s"
    return word + sym


def make_exercise(chars, new, caps=False, new_caps=False, n=EXERCISE_TOKENS):
    """Build practice text from `chars`, emphasising the keys in `new`."""
    letters = sorted(c for c in chars if c.isalpha())
    digits = sorted(c for c in chars if c.isdigit())
    symbols = sorted(c for c in chars if not c.isalnum())
    new_letters = [c for c in new if c.isalpha()]
    new_digits = [c for c in new if c.isdigit()]
    new_symbols = [c for c in new if not c.isalnum()]
    pool = [w for w in WORDS if set(w) <= set(letters)]
    focus = [w for w in pool if any(c in w for c in new_letters)]

    tokens = key_drill(list(new), letters, new_caps)
    while len(tokens) < n:
        if focus and random.random() < 0.5:
            word = random.choice(focus)
        elif pool and (len(pool) >= 40 or random.random() < 0.6):
            word = random.choice(pool)
        else:
            word = pseudo_word(letters, new_letters)
        if caps and random.random() < (0.5 if new_caps else 0.2):
            word = word.capitalize()
        if digits and random.random() < (0.4 if new_digits else 0.08):
            word = "".join(random.choice(new_digits or digits) for _ in range(random.randint(1, 4)))
        elif symbols:
            sym = None
            if new_symbols and random.random() < 0.4:
                sym = random.choice(new_symbols)
            elif random.random() < 0.1:
                sym = random.choice(symbols)
            if sym:
                word = attach(word, sym, pool or [word])
        tokens.append(word)
    return " ".join(tokens)


def sentence_text(min_len=280):
    """Random sentences (no repeats until all have been used)."""
    out, picks, total = [], [], 0
    while total < min_len:
        if not picks:
            picks = random.sample(SENTENCES, len(SENTENCES))
        out.append(picks.pop())
        total += len(out[-1]) + 1
    return " ".join(out)


def confusion_exercise(chars, pairs, n=EXERCISE_TOKENS):
    """Contrast drills for key pairs that get mixed up: (intended, typed)."""
    letters = sorted(c for c in chars if c.isalpha())
    pool = [w for w in WORDS if set(w) <= set(letters)]
    both = {p: [w for w in pool if p[0] in w and p[1] in w] for p in pairs}
    either = {p: [w for w in pool if p[0] in w or p[1] in w] for p in pairs}

    def contrast(a, b):
        return "".join(random.choice((a, b)) for _ in range(random.randint(3, 5)))

    tokens = []
    for a, b in pairs:
        tokens += [a + b + a, b + a + b, a * 2 + b * 2]
    while len(tokens) < n:
        p = random.choice(pairs)
        r = random.random()
        if both[p] and r < 0.4:
            tokens.append(random.choice(both[p]))
        elif either[p] and r < 0.85:
            tokens.append(random.choice(either[p]))
        else:
            tokens.append(contrast(*p))
    return " ".join(tokens)


TEXT_FIXES = {"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201c": '"', "\u201d": '"',
              "\u201e": '"', "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2026": "...",
              "\u00a0": " "}


def clean_text(raw):
    """Make arbitrary text typeable: ASCII-fy quotes/dashes/accents, one space between words."""
    raw = unicodedata.normalize("NFKD", "".join(TEXT_FIXES.get(c, c) for c in raw))
    return " ".join("".join(c for c in raw if c in TYPEABLE or c.isspace()).split())


def next_chunk(text, offset, size=300):
    """Next ~size characters from offset, ending at a sentence or word break.
    Returns (chunk, offset of the following chunk)."""
    if len(text) - offset <= size * 1.3:
        return text[offset:], len(text)
    lo, hi = offset + int(size * 0.7), offset + int(size * 1.3)
    stop = max(text.rfind(p, lo, hi) for p in (". ", "! ", "? "))
    space = stop + 1 if stop >= 0 else text.find(" ", offset + size)
    if space < 0:
        return text[offset:offset + size], offset + size
    return text[offset:space], space + 1


def lesson_text(i):
    lesson = LESSONS[i]
    if lesson.get("sentences"):
        return sentence_text()
    chars, caps = lesson_chars(i)
    return make_exercise(chars, lesson["keys"], caps, lesson.get("caps", False))


# ---------------------------------------------------------------------------
# Progress storage
# ---------------------------------------------------------------------------

def load_progress():
    try:
        data = json.loads(DATA_FILE.read_text())
    except FileNotFoundError:
        data = {}
    except json.JSONDecodeError:
        DATA_FILE.replace(DATA_FILE.with_suffix(".corrupt.json"))
        data = {}
    layouts = data.setdefault("layouts", {})
    # Version 1 kept a single (QWERTY) course at the top level.
    old = {k: data.pop(k) for k in ("unlocked", "lessons", "keys") if k in data}
    if old:
        layouts.setdefault("qwerty", old)
    if data.get("layout") not in LAYOUTS:
        data["layout"] = "qwerty"
    data.setdefault("remap", False)
    data.setdefault("sessions", [])
    data.setdefault("custom", {"path": None, "offsets": {}})
    return data


def lay(prog):
    """Progress for the active layout."""
    d = prog["layouts"].setdefault(prog["layout"], {})
    d.setdefault("unlocked", 0)
    d.setdefault("lessons", {})
    d.setdefault("keys", {})
    d.setdefault("confusions", {})
    d.setdefault("game_best", {"score": 0, "level": 0})
    return d


def layout_sessions(prog, games=False):
    """This layout's sessions. Games are left out unless asked for: their WPM includes
    time spent waiting for things to fall, so it would drag the averages down."""
    return [s for s in prog["sessions"] if s.get("layout", "qwerty") == prog["layout"]
            and (games or s["mode"] != "game")]


def save_progress(prog):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(prog, indent=1))
    tmp.replace(DATA_FILE)


def slugify(name):
    """File-name-safe version of a profile name (case-insensitive)."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or name.encode().hex()[:40]


def profile_path(name):
    return PROFILES_DIR / f"{slugify(name)}.json"


def list_profiles():
    """[(path, progress)] for every saved profile, by name."""
    out = []
    for f in PROFILES_DIR.glob("*.json"):
        try:
            out.append((f, json.loads(f.read_text())))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(out, key=lambda p: p[1].get("name", p[0].stem).lower())


def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def open_profile(path, name):
    """Make `path` the active profile (creating it if new) and return its progress."""
    global DATA_FILE
    DATA_FILE = path
    prog = load_progress()
    prog.setdefault("name", name)
    save_progress(prog)
    settings = load_settings()
    settings["last_profile"] = path.stem
    SETTINGS_FILE.write_text(json.dumps(settings))
    return prog


def record(prog, mode, lesson_idx, res, **extra):
    """Save a finished exercise. Returns pass/fail for lessons, else None."""
    lp = lay(prog)
    prog["sessions"].append(dict(
        date=datetime.now().isoformat(timespec="seconds"), mode=mode, lesson=lesson_idx,
        layout=prog["layout"], wpm=round(res["wpm"], 1), accuracy=round(res["accuracy"], 1),
        seconds=round(res["seconds"], 1), chars=res["chars"], errors=res["errors"], **extra))
    for k, (hits, errs, secs, timed) in res["keys"].items():
        s = lp["keys"].setdefault(k, {"hits": 0, "errors": 0, "time": 0.0, "timed": 0})
        s["hits"] += hits
        s["errors"] += errs
        s["time"] = round(s["time"] + secs, 3)
        s["timed"] += timed
    for pair, n in res["confusions"].items():
        lp["confusions"][pair] = lp["confusions"].get(pair, 0) + n
    passed = None
    if mode == "lesson":
        passed = res["accuracy"] >= PASS_ACCURACY and res["wpm"] >= LESSONS[lesson_idx]["wpm"]
        rec = lp["lessons"].setdefault(str(lesson_idx), {
            "attempts": 0, "best_wpm": 0.0, "best_accuracy": 0.0, "passed": False})
        rec["attempts"] += 1
        rec["best_wpm"] = max(rec["best_wpm"], round(res["wpm"], 1))
        rec["best_accuracy"] = max(rec["best_accuracy"], round(res["accuracy"], 1))
        rec["passed"] = rec["passed"] or passed
        if passed:
            lp["unlocked"] = max(lp["unlocked"], min(lesson_idx + 1, len(LESSONS) - 1))
    save_progress(prog)
    return passed


def key_totals(prog):
    """Per-key [hits, errors, seconds, timed] merged by physical key."""
    agg = {}
    for k, s in lay(prog)["keys"].items():
        a = agg.setdefault(base_key(k)[0], [0, 0, 0.0, 0])
        a[0] += s["hits"]
        a[1] += s["errors"]
        a[2] += s["time"]
        a[3] += s["timed"]
    return agg


def weak_keys(prog, allowed, n=3):
    """Keys with the worst mix of error rate and slowness (needs some data)."""
    scored = []
    for k, (hits, errs, secs, timed) in key_totals(prog).items():
        if k in allowed and hits + errs >= 5:
            scored.append((errs / (hits + errs) * 5 + (secs / timed if timed else 0), k))
    return [k for _, k in sorted(scored, reverse=True)[:n]]


def confused_pairs(prog, n=3):
    """Most frequent (intended, typed) mix-ups, ignoring forgotten Shifts and space."""
    pairs = []
    for k, cnt in sorted(lay(prog)["confusions"].items(), key=lambda kv: -kv[1]):
        a, b = k
        if cnt < 2 or " " in k or b not in TYPEABLE or base_key(a)[0] == base_key(b)[0]:
            continue
        if a.isalpha() and b.isalpha():
            a, b = a.lower(), b.lower()
        if (a, b) not in pairs and (b, a) not in pairs:
            pairs.append((a, b))
        if len(pairs) == n:
            break
    return pairs


def practice_streak(sessions):
    days = {s["date"][:10] for s in sessions}
    d = date.today()
    if d.isoformat() not in days:
        d -= timedelta(days=1)
    streak = 0
    while d.isoformat() in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def C(n):
    return curses.color_pair(n) if curses.has_colors() else 0


def init_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    for n, fg in [(GREEN, curses.COLOR_GREEN), (RED, curses.COLOR_RED),
                  (PINKY, curses.COLOR_MAGENTA), (RING, curses.COLOR_BLUE),
                  (MIDDLE, curses.COLOR_CYAN), (INDEX, curses.COLOR_YELLOW)]:
        curses.init_pair(n, fg, bg)
    curses.init_pair(ERRBG, curses.COLOR_WHITE, curses.COLOR_RED)


def put(scr, y, x, s, attr=0):
    """addstr that clips to the window instead of raising."""
    h, w = scr.getmaxyx()
    if not 0 <= y < h or not 0 <= x < w:
        return
    try:
        scr.addstr(y, x, s[:w - x], attr)
    except curses.error:
        pass  # writing the bottom-right cell raises after succeeding


def footer(scr, y, x, text):
    """Key hints like "Enter: start   Esc: back" - key names bold cyan, the rest plain."""
    for part in re.split(r"(\s{2,})", text):
        key, sep, desc = part.partition(": ")
        if sep:
            put(scr, y, x, key, C(MIDDLE) | curses.A_BOLD)
            put(scr, y, x + len(key), sep + desc)
        else:
            put(scr, y, x, part)
        x += len(part)


def text_width(s):
    """Terminal columns taken by s (wide CJK characters count 2, combining marks 0)."""
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


# The mascot's faces, from the reference sheet of fp-bits/mascota-ascii (MIT licence).
# The table flip uses a plain ")" instead of the original full-width one, which
# misaligns in terminals.
FACES = dict(
    normal="(°_°)", blink="(−_−)", happy="(^_^)", sleepy="(˘_˘)", disapproval="(ಠ_ಠ)",
    frustrated="(>_<)", shocked="(⊙_⊙)", crying="(T_T)", shrug="¯\\_(ツ)_/¯",
    surprised="(◉_◉)", unimpressed="(¬_¬)", left="(<_°)", right="(°_>)", up="(↑_↑)",
    down="(↓_↓)", sleeping="(˘_˘)zzZ", dancing="♪(^_^)♪", table_flip="(╯°□°)╯",
    hugging="(づ｡◕‿‿◕｡)づ", celebrating="(ノ^_^)ノ")
SAD_FACES = {"crying", "frustrated", "disapproval", "table_flip", "shocked"}
GLAD_FACES = {"happy", "dancing", "celebrating", "hugging"}


def face_attr(mood):
    color = RED if mood in SAD_FACES else GREEN if mood in GLAD_FACES else MIDDLE
    return C(color) | curses.A_BOLD


def greeting_face():
    """A face for the main menu title: sleepy late at night, otherwise a random friendly one."""
    if datetime.now().hour >= 23 or datetime.now().hour < 5:
        return "sleeping"
    return random.choice(["normal", "happy", "dancing", "celebrating", "hugging", "surprised",
                          "right", "up"])


def put_titled(scr, y, x, title, mood):
    """A screen title followed by the mascot."""
    put(scr, y, x, title, curses.A_BOLD | C(MIDDLE))
    put(scr, y, x + len(title) + 2, FACES[mood], face_attr(mood))


class Mascot:
    """The game's mascot: shows a reaction for a moment, otherwise a face chosen from
    the game state (passed to face()), blinking now and then."""

    def __init__(self):
        self.mood, self.hold = "surprised", 1.5
        self.blink_in = random.uniform(3, 6)

    def react(self, mood, secs=1.0):
        self.mood, self.hold = mood, secs

    def tick(self, dt):
        self.hold -= dt
        self.blink_in -= dt
        if self.blink_in < -0.15:
            self.blink_in = random.uniform(3, 6)

    def face(self, idle_mood):
        if self.hold > 0:
            return self.mood
        if idle_mood == "normal" and self.blink_in < 0:
            return "blink"
        return idle_mood


def center_x(scr, width):
    return max(0, (scr.getmaxyx()[1] - width) // 2)


def fmt_time(secs):
    secs = int(secs)
    return f"{secs // 60}:{secs % 60:02d}"


def finger_attr(chars):
    """Keys coloured by finger; keys not used in this text are dimmed."""
    bases = {base_key(c)[0] for c in chars}
    has_shift = any(base_key(c)[1] for c in chars)

    def attr(k):
        if k in ("shift_l", "shift_r"):
            return C(PINKY) | curses.A_BOLD if has_shift else curses.A_DIM
        if k not in bases:
            return curses.A_DIM
        return C(FINGER_COLOR[FINGERS.get(k, "thumb").split()[-1]]) | curses.A_BOLD
    return attr


def draw_keyboard(scr, y, x, attr_for, highlight=()):
    hl = curses.A_REVERSE | curses.A_BOLD
    for r, (keys, off) in enumerate(KB_ROWS):
        for i, k in enumerate(keys):
            put(scr, y + r, x + off + i * 4, f"[{k}]", attr_for(k) | (hl if k in highlight else 0))
    for name, kx in (("shift_l", 0), ("shift_r", 49)):
        put(scr, y + 3, x + kx, "[shift]", attr_for(name) | (hl if name in highlight else 0))
    put(scr, y + 4, x + 17, "[" + "space".center(26) + "]",
        attr_for(" ") | (hl if " " in highlight else 0))


def draw_finger_legend(scr, y):
    parts = [("Fingers: ", 0), ("pinky ", C(PINKY)), ("ring ", C(RING)),
             ("middle ", C(MIDDLE)), ("index ", C(INDEX)), ("thumb", 0)]
    x = center_x(scr, sum(len(p) for p, _ in parts))
    for text, attr in parts:
        put(scr, y, x, text, attr | curses.A_BOLD)
        x += len(text)


def wait_key(scr):
    scr.timeout(-1)
    while True:
        ch = scr.get_wch()
        if ch != curses.KEY_RESIZE:
            return ch


def message(scr, title, lines):
    scr.erase()
    put(scr, 1, 2, title, curses.A_BOLD | C(MIDDLE))
    for i, line in enumerate(lines):
        put(scr, 3 + i, 4, line)
    footer(scr, scr.getmaxyx()[0] - 1, 2, "Press any key")
    scr.refresh()
    wait_key(scr)


def menu(scr, title, items, header=(), sel=0, mood=None):
    """Vertical menu. items: [(label, enabled)]. Returns index or None."""
    scr.timeout(-1)
    enabled = [i for i, (_, en) in enumerate(items) if en]
    if sel not in enabled:
        sel = enabled[0]
    top = 0
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        if mood:
            put_titled(scr, 1, 2, title, mood)
        else:
            put(scr, 1, 2, title, curses.A_BOLD | C(MIDDLE))
        y = 3
        for line in header:
            put(scr, y, 4, line)
            y += 1
        y += 1 if header else 0
        rows = max(1, h - y - 2)
        top = min(max(top, sel - rows + 1), sel)
        for i in range(top, min(len(items), top + rows)):
            label, en = items[i]
            attr = curses.A_REVERSE if i == sel else (0 if en else curses.A_DIM)
            put(scr, y + i - top, 4, f" {label} ", attr)
        footer(scr, h - 1, 2, "Up/Down or j/k: move   Enter: select   Esc/q: back")
        scr.refresh()
        ch = scr.get_wch()
        if ch in (curses.KEY_UP, "k"):
            sel = max([i for i in enabled if i < sel], default=sel)
        elif ch in (curses.KEY_DOWN, "j"):
            sel = min([i for i in enabled if i > sel], default=sel)
        elif ch in ("\n", "\r", curses.KEY_ENTER):
            return sel
        elif ch in ("\x1b", "q"):
            return None


# ---------------------------------------------------------------------------
# Typing screens
# ---------------------------------------------------------------------------

def wrap(text, width):
    """Split text into (start_index, line) chunks, breaking after spaces."""
    lines, start = [], 0
    while start < len(text):
        if len(text) - start <= width:
            lines.append((start, text[start:]))
            break
        cut = text.rfind(" ", start, start + width)
        if cut <= start:
            cut = start + width - 1
        lines.append((start, text[start:cut + 1]))
        start = cut + 1
    return lines


def intro(scr, heading, lines, text, highlight):
    """Pre-exercise screen. Returns False if the user backs out."""
    scr.timeout(-1)
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        x0 = center_x(scr, 64)
        put(scr, 1, x0, heading, curses.A_BOLD | C(MIDDLE))
        for i, line in enumerate(lines):
            put(scr, 3 + i, x0, line)
        ky = 4 + len(lines)
        draw_keyboard(scr, ky, center_x(scr, KB_WIDTH), finger_attr(text), highlight)
        draw_finger_legend(scr, ky + 6)
        footer(scr, h - 2, x0, "Enter/Space: start    Esc: back")
        scr.refresh()
        ch = scr.get_wch()
        if ch in ("\n", "\r", " ", curses.KEY_ENTER):
            return True
        if ch == "\x1b":
            return False


def draw_exercise(scr, title, text, pos, wrong, missed, elapsed, errors, limit=None):
    scr.erase()
    h, w = scr.getmaxyx()
    if h < 20 or w < 60:
        put(scr, 0, 0, "Please enlarge the terminal to at least 60x20.")
        scr.refresh()
        return
    width = min(64, w - 4)
    x0 = center_x(scr, width)
    wpm = pos / 5 / (elapsed / 60) if elapsed > 1 else 0.0
    acc = 100 * pos / (pos + errors) if pos + errors else 100.0
    put(scr, 0, x0, title, curses.A_BOLD | C(MIDDLE))
    progress = (f"{fmt_time(max(0.0, limit - elapsed))} left" if limit
                else f"{fmt_time(elapsed)}   {100 * pos // len(text)}% done")
    put(scr, 1, x0, f"{wpm:5.1f} WPM   {acc:5.1f}% accuracy   {progress}", curses.A_DIM)

    lines = wrap(text, width)
    cur = next(i for i, (s, line) in enumerate(lines) if s <= pos < s + len(line))
    first = max(0, cur - 1)
    for row, (s, line) in enumerate(lines[first:first + 5]):
        for j, c in enumerate(line):
            i = s + j
            if i < pos:
                attr = C(RED) if i in wrong else C(GREEN)
                if c == " " and i in wrong:
                    c = "·"
            elif i == pos:
                attr = C(ERRBG) if missed else curses.A_REVERSE
            else:
                attr = 0
            put(scr, 3 + row, x0 + j, c, attr)

    want = text[pos]
    base, shifted = base_key(want)
    highlight = {base} | ({shift_side(base)} if shifted else set())
    draw_keyboard(scr, 9, center_x(scr, KB_WIDTH), finger_attr(text), highlight)
    hint = f"Next: {'space' if want == ' ' else want}  -  {FINGERS.get(base, '?')}"
    if shifted:
        hint += f" + {'right' if shift_side(base) == 'shift_r' else 'left'} pinky on Shift"
    put(scr, 15, center_x(scr, len(hint)), hint, curses.A_BOLD)
    if missed:
        put(scr, 16, center_x(scr, 30), "Oops - press the correct key.", C(RED))
    footer(scr, h - 1, 2, "Esc: back to menu (this attempt is not saved)")
    scr.refresh()


def run_exercise(scr, title, text, limit=None):
    """Type `text`. Wrong keys must be corrected. With `limit` (seconds) the round
    ends when time runs out. Returns result dict or None."""
    scr.timeout(200)  # redraw periodically so the clock ticks
    pos = errors = 0
    start = last = None
    missed = False
    wrong = set()
    keys = {}  # char -> [hits, errors, seconds, timed]
    confusions = {}  # intended + typed char -> count
    timed_out = False
    while pos < len(text):
        now = time.monotonic()
        if limit and start and now - start >= limit:
            timed_out = True
            break
        draw_exercise(scr, title, text, pos, wrong, missed,
                      now - start if start else 0.0, errors, limit)
        try:
            ch = scr.get_wch()
        except curses.error:
            continue
        if ch == "\x1b":
            return None
        if not isinstance(ch, str) or not ch.isprintable():
            continue
        ch = REMAP.get(ch, ch)
        now = time.monotonic()
        if start is None:
            start = last = now
        elif limit and now - start >= limit:
            timed_out = True
            break
        want = text[pos]
        stat = keys.setdefault(want, [0, 0, 0.0, 0])
        if ch == want:
            stat[0] += 1
            if pos and now - last < 5:  # ignore long pauses in per-key speed
                stat[2] += now - last
                stat[3] += 1
            last = now
            pos += 1
            missed = False
        else:
            stat[1] += 1
            confusions[want + ch] = confusions.get(want + ch, 0) + 1
            errors += 1
            wrong.add(pos)
            missed = True
    secs = limit if timed_out else max(last - start, 1.0)
    return dict(wpm=pos / 5 / (secs / 60), accuracy=100 * pos / max(1, pos + errors),
                seconds=secs, chars=pos, errors=errors, keys=keys, confusions=confusions)


def results(scr, heading, res, goal_wpm=None, passed=None, best=None, last_lesson=False,
            extra=()):
    """Show results. Returns 'next', 'more', 'retry' or 'menu'."""
    ok, bad = C(GREEN) | curses.A_BOLD, C(RED) | curses.A_BOLD
    lines = []
    if passed is not None:
        if passed and last_lesson:
            lines.append(("You've completed the course! Keep it up with free typing.", ok))
        elif passed:
            lines.append(("Lesson passed - next lesson unlocked!", ok))
        else:
            lines.append(("Not quite yet - have another go.", bad))
        lines.append(("", 0))
    wpm_line = f"Speed:     {res['wpm']:5.1f} WPM"
    acc_line = f"Accuracy:  {res['accuracy']:5.1f}%"
    if goal_wpm is not None:
        wpm_line += f"    goal {goal_wpm} WPM"
        acc_line += f"     goal {PASS_ACCURACY:.0f}%"
    lines.append((wpm_line, ok if goal_wpm is None or res["wpm"] >= goal_wpm else bad))
    lines.append((acc_line, ok if res["accuracy"] >= PASS_ACCURACY else bad))
    lines.append((f"Time:      {fmt_time(res['seconds'])}    errors: {res['errors']}", 0))
    if best is not None:
        lines.append((f"Best on this lesson: {best:.1f} WPM", 0))
    lines += extra
    trouble = sorted(((s[1], k) for k, s in res["keys"].items() if s[1]), reverse=True)[:5]
    if trouble:
        lines.append(("", 0))
        lines.append(("Trouble keys: " + ", ".join(
            f"{'space' if k == ' ' else k} ({n})" for n, k in trouble), 0))
    if res["accuracy"] < PASS_ACCURACY:
        lines.append(("Tip: slow down. Speed comes from accuracy, not the other way round.",
                      curses.A_DIM))
    if passed is not None:
        mood = ("dancing" if last_lesson else "celebrating") if passed else "frustrated"
    else:
        mood = ("happy" if res["accuracy"] >= PASS_ACCURACY else
                "normal" if res["accuracy"] >= 90 else "frustrated")
    can_advance = passed and not last_lesson
    enter = "next lesson" if can_advance else "try again"
    if passed is None:
        enter = "another round"

    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        x0 = center_x(scr, 64)
        put_titled(scr, 1, x0, heading, mood)
        for i, (text, attr) in enumerate(lines):
            put(scr, 3 + i, x0, text, attr)
        footer(scr, h - 2, x0, f"Enter: {enter}    r: retry    Esc: menu")
        scr.refresh()
        ch = wait_key(scr)
        if ch in ("\n", "\r", curses.KEY_ENTER):
            return "next" if can_advance else "more" if passed is None else "retry"
        if ch == "r":
            return "retry"
        if ch in ("\x1b", "q"):
            return "menu"


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def play_lesson(scr, prog, i):
    while True:
        lesson = LESSONS[i]
        text = lesson_text(i)
        heading = f"Lesson {i + 1}/{len(LESSONS)}: {lesson['title']}"
        info = [lesson["tip"], "",
                f"Goal: {PASS_ACCURACY:.0f}% accuracy and {lesson['wpm']} WPM.",
                "Wrong keys must be fixed before you move on. Don't look at your hands!"]
        highlight = {base_key(c)[0] for c in lesson["keys"]}
        if lesson.get("caps"):
            highlight |= {"shift_l", "shift_r"}
        if not intro(scr, heading, info, text, highlight):
            return
        res = run_exercise(scr, heading, text)
        if res is None:
            return
        passed = record(prog, "lesson", i, res)
        action = results(scr, heading, res, lesson["wpm"], passed,
                         lay(prog)["lessons"][str(i)]["best_wpm"], i == len(LESSONS) - 1)
        if action == "menu":
            return
        if action == "next":
            i += 1


def taught(prog):
    """Characters from the lessons passed so far on this layout (at least the first
    lesson's), and whether capitals are among them. "unlocked" is the lesson the
    user is currently on, which hasn't been learned yet."""
    return lesson_chars(max(0, lay(prog)["unlocked"] - 1))


def play_weak(scr, prog):
    chars, caps = taught(prog)
    while True:
        weak = weak_keys(prog, chars)
        if not weak:
            message(scr, "Weak-key practice", [
                "Not enough data yet.", "Finish a lesson or two first and I'll find your weak keys."])
            return
        text = make_exercise(chars, "".join(weak), caps)
        names = ", ".join("space" if k == " " else k for k in weak)
        heading = "Weak-key practice"
        if not intro(scr, heading, [f"Focusing on your slowest / least accurate keys: {names}",
                                    "Uses only keys you've already been taught."],
                     text, set(weak)):
            return
        res = run_exercise(scr, heading, text)
        if res is None:
            return
        record(prog, "weak", None, res)
        if results(scr, heading, res) == "menu":
            return


def play_confusions(scr, prog):
    heading = "Confused-pair drills"
    while True:
        pairs = confused_pairs(prog)
        if not pairs:
            message(scr, heading, [
                "No mix-ups recorded yet.",
                "Every time you press one key instead of another I note the pair.",
                "Once a pair has happened a couple of times it shows up here."])
            return
        chars, _ = taught(prog)
        chars = chars | {c for p in pairs for c in p}
        text = confusion_exercise(chars, pairs)
        info = ["Pairs of keys you tend to mix up (meant -> typed):",
                "   " + "    ".join(f"{a} -> {b}" for a, b in pairs), "",
                "Contrast drills make each finger learn exactly which key is its own.",
                "Go slowly enough to get every one right."]
        if not intro(scr, heading, info, text, {base_key(c)[0] for p in pairs for c in p}):
            return
        res = run_exercise(scr, heading, text)
        if res is None:
            return
        record(prog, "confusion", None, res)
        if results(scr, heading, res) == "menu":
            return


TEST_LENGTHS = (60, 120, 300)


def play_test(scr, prog):
    def best(limit):
        return max((s["wpm"] for s in layout_sessions(prog)
                    if s["mode"] == "test" and s.get("limit") == limit), default=None)

    items = []
    for limit in TEST_LENGTHS:
        b = best(limit)
        label = f"{limit // 60} minute{'s' if limit > 60 else ' '}"
        items.append((label + (f"    best {b:5.1f} WPM" if b is not None else ""), True))
    full = lay(prog)["unlocked"] == len(LESSONS) - 1
    header = ["Type as far as you can before the clock runs out.",
              "Text: real sentences." if full else
              "Text: only the keys you've learned (finish the course for real sentences)."]
    choice = menu(scr, "Timed test", items, header)
    if choice is None:
        return
    limit = TEST_LENGTHS[choice]
    heading = f"Timed test - {limit // 60} minute{'s' if limit > 60 else ''}"
    while True:
        if full:
            text = sentence_text(limit * 15)
        else:
            chars, caps = taught(prog)
            text = make_exercise(chars, "", caps, n=limit * 3)
        if not intro(scr, heading, ["The clock starts with your first key.",
                                    "Wrong keys still have to be fixed, so accuracy pays."],
                     text, set()):
            return
        res = run_exercise(scr, heading, text, limit)
        if res is None:
            return
        prev = best(limit)
        record(prog, "test", None, res, limit=limit)
        extra = [("", 0), ("New personal best!", C(GREEN) | curses.A_BOLD)] \
            if prev is not None and res["wpm"] > prev else []
        time.sleep(0.5)  # don't let a keystroke typed at the buzzer dismiss the results
        curses.flushinp()
        if results(scr, heading, res, extra=extra) == "menu":
            return


GAME_LIVES = 5
CLEARS_PER_LEVEL = 10
GAME_ZONES = 5  # the field is split top to bottom; clearing an item in the top zone scores x5


def game_context(prog):
    """What the falling-words game may drop, from the user's course progress."""
    chars, caps = taught(prog)
    letters = sorted(c for c in chars if c.isalpha())
    return dict(chars=chars, letters=letters, caps=caps,
                digits=sorted(c for c in chars if c.isdigit()),
                symbols=sorted(c for c in chars if not c.isalnum() and c != " "),
                pool=[w for w in WORDS if set(w) <= set(letters)],
                weak=[k for k in weak_keys(prog, chars, n=4) if k != " "])


def game_item(level, ctx):
    """Something to drop. Single keys at first; words, capitals, numbers and
    punctuation join in as the level rises (if the course has taught them)."""
    def key():
        if ctx["weak"] and random.random() < 0.3:
            return random.choice(ctx["weak"])
        return random.choice(ctx["letters"])

    pool = ctx["pool"]
    if len(pool) >= 8 and random.random() < min(0.85, 0.25 * (level - 1)):
        item = random.choice([w for w in pool if len(w) <= 2 + level] or pool)
        if ctx["caps"] and level >= 3 and random.random() < 0.25:
            item = item.capitalize()
        if ctx["symbols"] and level >= 4 and random.random() < 0.3:
            item = attach(item, random.choice(ctx["symbols"]), pool)
        return item
    if level >= 3 and random.random() < 0.25:
        if ctx["digits"] and (not ctx["symbols"] or random.random() < 0.5):
            return "".join(random.choice(ctx["digits"])
                           for _ in range(random.randint(1, min(4, level - 1))))
        if ctx["symbols"]:
            return random.choice(ctx["symbols"])
    n = 1 if level < 2 or random.random() < 0.5 else random.randint(2, min(4, level))
    item = "".join(key() for _ in range(n))
    if ctx["caps"] and level >= 3 and random.random() < 0.2:
        item = item.capitalize()
    return item


def level_news(level, ctx):
    if level == 2 and len(ctx["pool"]) >= 8:
        return "Words incoming!"
    if level == 3:
        extra = [name for name, on in (("capitals", ctx["caps"]), ("numbers", ctx["digits"]),
                                       ("symbols", ctx["symbols"])) if on]
        if extra:
            return f"{', '.join(extra).capitalize()} join in!"
    if level == 4 and ctx["symbols"] and len(ctx["pool"]) >= 8:
        return "Punctuated words!"
    return "Faster!"


def type_secs(n, wpm):
    """Rough time to spot and type an n-character item."""
    return 1.5 + n * 12 / wpm


def run_game(scr, ctx, wpm):
    """Falling-words game loop. Returns a result dict (same shape as run_exercise
    plus score/level/cleared)."""
    scr.timeout(30)
    items, popups = [], []  # items: dict(text, x, y 0..1, speed, typed)
    target = None
    score = combo = cleared = correct = errors = 0
    level, lives = 1, GAME_LIVES
    keys, confusions = {}, {}
    banner, banner_ttl, flash = "Level 1 - go!", 2.0, 0.0
    spawn_in, play_time, last_hit = 0.8, 0.0, None
    ease = 1.0  # < 1 slows new items after a miss; recovers as items are cleared
    paused = quit_game = False
    mascot, recent_errors, last_key = Mascot(), [], time.monotonic()
    last = time.monotonic()
    while lives > 0 and not quit_game:
        h, w = scr.getmaxyx()
        small = h < 20 or w < 60
        fw = min(70, w - 4)
        rows = h - 5
        fx = center_x(scr, fw)
        now = time.monotonic()
        dt, last = min(0.1, now - last), now
        mult = 1 + min(combo // 5, 3)

        if not (paused or small):
            play_time += dt
            mascot.tick(dt)
            spawn_in -= dt
            if not items:
                spawn_in = min(spawn_in, 0.4)  # never leave the player waiting on an empty field
            if spawn_in <= 0 and len(items) < 4 + level:
                text = game_item(level, ctx)
                for _ in range(10):  # avoid overlapping items near the top
                    x = random.randint(1, max(1, fw - len(text) - 2))
                    if not any(it["y"] < 3 / rows and x - 2 < it["x"] + len(it["text"])
                               and it["x"] - 2 < x + len(text) for it in items):
                        break
                slack = max(1.4, 5.0 * 0.88 ** (level - 1))
                items.append(dict(text=text, x=x, y=0.0, typed=0,
                                  speed=ease / (type_secs(len(text), wpm) * slack)))
                spawn_in = type_secs(len(text), wpm) * max(0.7, 1.8 * 0.9 ** (level - 1)) / ease
            for it in items[:]:
                it["y"] += it["speed"] * dt
                if it["y"] >= 1:
                    items.remove(it)
                    lives -= 1
                    combo = 0
                    flash = 0.5
                    ease = max(0.6, ease * 0.85)
                    mascot.react("crying", 1.2)
                    if it is target:
                        target = None
            for p in popups[:]:
                p[3] -= dt
                if p[3] <= 0:
                    popups.remove(p)
            banner_ttl -= dt
            flash -= dt

        # --- draw ---
        scr.erase()
        if small:
            put(scr, 0, 0, "Please enlarge the terminal to at least 60x20.")
        else:
            put(scr, 0, fx, "Falling Words", curses.A_BOLD | C(MIDDLE))
            status = f"Score {score:,}   Level {level}   Combo x{mult}   "
            hearts = "♥" * lives + "♡" * (GAME_LIVES - lives)
            sx = fx + fw - len(status) - len(hearts)
            put(scr, 0, sx, status, curses.A_BOLD)
            put(scr, 0, sx + len(status), hearts, C(RED) | curses.A_BOLD)
            put(scr, 1, fx, "┌" + "─" * (fw - 2) + "┐")
            for r in range(rows):
                put(scr, 2 + r, fx, "│")
                put(scr, 2 + r, fx + fw - 1, "│")
            for z in range(GAME_ZONES):
                r = 2 + z * rows // GAME_ZONES
                if z:
                    put(scr, r, fx, "├")
                    put(scr, r, fx + fw - 1, "┤")
                put(scr, r, fx + fw, f"x{GAME_ZONES - z}", C(INDEX) | curses.A_BOLD)
            ground = C(ERRBG) if flash > 0 else C(RED) | curses.A_BOLD
            put(scr, 2 + rows, fx, "└" + "═" * (fw - 2) + "┘", ground)
            for it in items:
                y = 2 + min(rows - 1, int(it["y"] * rows))
                x = fx + 1 + it["x"]
                t = it["text"]
                if it is target:
                    put(scr, y, x, t[:it["typed"]], C(GREEN) | curses.A_BOLD)
                    put(scr, y, x + it["typed"], t[it["typed"]], curses.A_REVERSE | curses.A_BOLD)
                    put(scr, y, x + it["typed"] + 1, t[it["typed"] + 1:], C(INDEX) | curses.A_BOLD)
                else:
                    put(scr, y, x, t, (C(RED) if it["y"] > 0.75 else 0) | curses.A_BOLD)
            for py, px, ptext, _ in popups:
                put(scr, py, px, ptext, C(GREEN) | curses.A_BOLD)
            if banner_ttl > 0:
                put(scr, 2 + rows // 3, fx + (fw - len(banner)) // 2, banner,
                    C(MIDDLE) | curses.A_BOLD)
            # The mascot stands on the ground in the middle, watching the action.
            mx = fx + fw // 2
            if paused:
                idle = "sleeping"
            elif target:
                dx = fx + 1 + target["x"] + len(target["text"]) // 2 - mx
                idle = ("left" if dx < -6 else "right" if dx > 6 else
                        "down" if target["y"] > 0.6 else "up")
            elif any(it["y"] > 0.75 for it in items):
                idle = "shocked"
            elif items and now - last_key > 8:
                idle = "unimpressed"
            else:
                idle = "normal"
            mood = "sleeping" if paused else mascot.face(idle)
            badge = f" {FACES[mood]} "
            put(scr, 1 + rows, mx - text_width(badge) // 2, badge, face_attr(mood) | curses.A_REVERSE)
            if target:
                want = target["text"][target["typed"]]
                base, shifted = base_key(want)
                hint = f"Next: {want}  -  {FINGERS.get(base, '?')}"
                if shifted:
                    hint += f" + {'right' if shift_side(base) == 'shift_r' else 'left'} pinky on Shift"
            else:
                hint = "Type the first key of any falling item to lock on"
            put(scr, 3 + rows, center_x(scr, len(hint)), hint, curses.A_BOLD)
            if paused:
                msg = "  PAUSED  "
                put(scr, 2 + rows // 2, fx + (fw - len(msg)) // 2, msg,
                    curses.A_REVERSE | curses.A_BOLD)
                footer(scr, h - 1, 2, "Esc/Enter: resume   q: end game")
            else:
                footer(scr, h - 1, 2, "Esc: pause   Backspace: let go of a word")
        scr.refresh()

        # --- input ---
        try:
            ch = scr.get_wch()
        except curses.error:
            continue
        if paused:
            if ch in ("\x1b", "\n", "\r", curses.KEY_ENTER):
                paused = False
            elif ch == "q":
                quit_game = True
            continue
        if ch == "\x1b":
            paused = True
            continue
        if small:
            continue
        if ch in (curses.KEY_BACKSPACE, "\x7f", "\b"):
            if target:
                target["typed"] = 0
                target = None
            continue
        if not isinstance(ch, str) or not ch.isprintable() or ch == " ":
            continue
        ch = REMAP.get(ch, ch)
        now = last_key = time.monotonic()

        def oops():
            recent_errors[:] = [t for t in recent_errors if now - t < 2] + [now]
            mascot.react(*(("disapproval", 1.5) if len(recent_errors) >= 3 else ("frustrated", 0.6)))

        if target is None:
            cands = [it for it in items if it["text"][0] == ch]
            if not cands:
                errors += 1
                combo = 0
                oops()
                continue
            target = max(cands, key=lambda it: it["y"])  # the most urgent one
        want = target["text"][target["typed"]]
        stat = keys.setdefault(want, [0, 0, 0.0, 0])
        if ch != want:
            stat[1] += 1
            confusions[want + ch] = confusions.get(want + ch, 0) + 1
            errors += 1
            combo = 0
            oops()
            continue
        stat[0] += 1
        if target["typed"] and last_hit and now - last_hit < 2:
            stat[2] += now - last_hit
            stat[3] += 1
        last_hit = now
        correct += 1
        target["typed"] += 1
        if target["typed"] == len(target["text"]):
            combo += 1
            mult = 1 + min(combo // 5, 3)
            row = min(rows - 1, int(target["y"] * rows))
            # Score by the zone the item is drawn in, matching the marks on the walls.
            zone = GAME_ZONES - max(z for z in range(GAME_ZONES) if z * rows // GAME_ZONES <= row)
            points = 10 * len(target["text"]) * level * mult * zone
            score += points
            y = 2 + row
            popups.append([y, fx + 1 + target["x"], f"+{points}" + (f" x{zone}" if zone > 1 else ""),
                           0.8])
            items.remove(target)
            target = None
            cleared += 1
            ease = min(1.0, ease + 0.03)
            mascot.react(*(("dancing", 1.5) if combo % 5 == 0 and combo <= 20 else ("happy", 0.8)))
            if cleared >= level * CLEARS_PER_LEVEL:
                level += 1
                mascot.react("celebrating", 2.5)
                banner, banner_ttl = f"Level {level} - {level_news(level, ctx)}", 2.5
                if level % 5 == 0 and lives < GAME_LIVES:
                    lives += 1
                    banner += "  +1 life"
    secs = max(play_time, 1.0)
    return dict(score=score, level=level, cleared=cleared, quit=quit_game,
                wpm=correct / 5 / (secs / 60), accuracy=100 * correct / max(1, correct + errors),
                seconds=secs, chars=correct, errors=errors, keys=keys, confusions=confusions)


def game_over(scr, res, best):
    """Game summary. Returns 'again' or 'menu'."""
    ok = C(GREEN) | curses.A_BOLD
    lines = [("Game over!" if not res["quit"] else "Game ended.", C(MIDDLE) | curses.A_BOLD), ("", 0)]
    mood = ("hugging" if res["score"] > best["score"] else "shrug" if res["quit"]
            else "table_flip")
    if res["score"] > best["score"]:
        lines += [("New high score!", ok), ("", 0)]
    lines += [(f"Score:     {res['score']:,}", curses.A_BOLD),
              (f"Level:     {res['level']}", 0),
              (f"Cleared:   {res['cleared']} items", 0),
              (f"Accuracy:  {res['accuracy']:5.1f}%", 0),
              (f"High score: {max(best['score'], res['score']):,}", 0)]
    trouble = sorted(((s[1], k) for k, s in res["keys"].items() if s[1]), reverse=True)[:5]
    if trouble:
        lines += [("", 0), ("Trouble keys: " + ", ".join(f"{k} ({n})" for n, k in trouble), 0)]
    time.sleep(0.5)  # swallow keys typed as the last item hit the ground
    curses.flushinp()
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        x0 = center_x(scr, 64)
        put_titled(scr, 1, x0, "Falling Words", mood)
        for i, (text, attr) in enumerate(lines):
            put(scr, 3 + i, x0, text, attr)
        footer(scr, h - 2, x0, "Enter: play again    Esc: menu")
        scr.refresh()
        ch = wait_key(scr)
        if ch in ("\n", "\r", curses.KEY_ENTER):
            return "again"
        if ch in ("\x1b", "q"):
            return "menu"


def play_game(scr, prog):
    while True:
        ctx = game_context(prog)
        recent = layout_sessions(prog)[-10:]
        wpm = min(120.0, max(8.0, sum(s["wpm"] for s in recent) / len(recent))) if recent else 12.0
        best = dict(lay(prog)["game_best"])
        joins = [name for name, on in (("words", len(ctx["pool"]) >= 8), ("capitals", ctx["caps"]),
                                       ("numbers", ctx["digits"]), ("punctuation", ctx["symbols"]))
                 if on]
        info = ["Type each item before it hits the ground. Five misses and it's over.",
                "Type an item's first key to lock onto it; Backspace lets go.",
                "The higher up you clear it, the more it's worth: x5 at the top down to x1.",
                f"Tuned to you: only keys you've learned, starting pace from your {wpm:.0f} WPM.",
                ("Levels bring " + ", ".join(joins) + " and more speed." if joins
                 else "Each level falls faster - learn more keys to unlock words."),
                "Your weak keys (highlighted) turn up more often." if ctx["weak"] else "",
                f"High score: {best['score']:,} (level {best['level']})" if best["score"] else ""]
        if not intro(scr, "Falling Words", info, "".join(sorted(ctx["chars"] - {" "})),
                     {base_key(k)[0] for k in ctx["weak"]}):
            return
        res = run_game(scr, ctx, wpm)
        if res["chars"] + res["errors"]:
            if res["score"] > best["score"]:
                lay(prog)["game_best"] = {"score": res["score"], "level": res["level"]}
            record(prog, "game", None, res, score=res["score"], level=res["level"])
        if game_over(scr, res, best) == "menu":
            return


def play_free(scr, prog):
    while True:
        text = sentence_text()
        heading = "Free typing"
        if not intro(scr, heading, ["Real sentences using the full keyboard.",
                                    "Capitals, numbers and punctuation included."],
                     text, set()):
            return
        res = run_exercise(scr, heading, text)
        if res is None:
            return
        record(prog, "free", None, res)
        if results(scr, heading, res) == "menu":
            return


def prompt(scr, title, lines, default="", complete=True):
    """Single-line text input, with Tab filename completion if `complete`.
    Returns str or None."""
    buf, matches = default, []
    scr.timeout(-1)
    try:
        curses.curs_set(1)
    except curses.error:
        pass
    try:
        while True:
            scr.erase()
            h, w = scr.getmaxyx()
            put(scr, 1, 2, title, curses.A_BOLD | C(MIDDLE))
            for i, line in enumerate(lines):
                put(scr, 3 + i, 4, line)
            y = 4 + len(lines)
            for i, m in enumerate(matches[:h - y - 4]):
                put(scr, y + 2 + i, 6, m, curses.A_DIM)
            footer(scr, h - 1, 2, "Enter: OK   Tab: complete   Ctrl-U: clear   Esc: back" if complete
                   else "Enter: OK   Ctrl-U: clear   Esc: back")
            shown = buf[-(w - 8):]
            put(scr, y, 4, "> " + shown)
            scr.move(y, min(w - 1, 6 + len(shown)))
            scr.refresh()
            ch = scr.get_wch()
            matches = []
            if ch in ("\n", "\r", curses.KEY_ENTER):
                return buf.strip()
            if ch == "\x1b":
                return None
            if ch in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                buf = buf[:-1]
            elif ch == "\x15":
                buf = ""
            elif ch == "\t" and complete:
                found = sorted(glob.glob(os.path.expanduser(buf) + "*"))
                if found:
                    common = os.path.commonprefix(found)
                    if len(found) == 1 and os.path.isdir(common):
                        common += "/"
                    if buf.startswith("~"):
                        common = "~" + common[len(os.path.expanduser("~")):]
                    buf = common if len(common) >= len(buf) else buf
                    if len(found) > 1:
                        matches = [os.path.basename(f.rstrip("/")) for f in found]
            elif isinstance(ch, str) and ch.isprintable():
                buf += ch
    finally:
        try:
            curses.curs_set(0)
        except curses.error:
            pass


def play_custom(scr, prog):
    custom = prog["custom"]
    path = custom.get("path")
    if path:
        name = os.path.basename(path)
        choice = menu(scr, "Type your own text", [
            (f"Continue {name}", True), (f"Start {name} from the beginning", True),
            ("Open a different file", True)])
        if choice is None:
            return
        if choice == 1:
            custom["offsets"][path] = 0
        elif choice == 2:
            path = None
    if not path:
        entered = prompt(scr, "Type your own text", [
            "Path to a plain-text file (a book chapter, article, notes, code comments...).",
            "Curly quotes, dashes and accents are simplified; untypeable characters are dropped.",
            "Your place in each file is remembered."], custom.get("path") or "~/")
        if not entered:
            return
        path = str(Path(os.path.expanduser(entered)).resolve())
    try:
        text = clean_text(Path(path).read_text(errors="replace"))
    except OSError as e:
        message(scr, "Type your own text", [f"Couldn't read {path}:", str(e.strerror or e)])
        return
    if not text:
        message(scr, "Type your own text", ["That file has no typeable text in it."])
        return
    custom["path"] = path
    save_progress(prog)
    heading = f"Your text: {os.path.basename(path)}"
    while True:
        offset = custom["offsets"].get(path, 0)
        if offset >= len(text):
            offset = 0
        chunk, nxt = next_chunk(text, offset)
        info = [f"{100 * offset // len(text)}% of the way through "
                f"({len(text):,} characters in all).",
                "Everything on the keyboard is fair game here."]
        if not intro(scr, heading, info, chunk, set()):
            return
        res = run_exercise(scr, heading, chunk)
        if res is None:
            return
        record(prog, "custom", None, res)
        extra = [("", 0), ("You reached the end - next round starts from the top.", 0)] \
            if nxt >= len(text) else []
        action = results(scr, heading, res, extra=extra)
        if action != "retry":
            custom["offsets"][path] = 0 if nxt >= len(text) else nxt
            save_progress(prog)
        if action == "menu":
            return


def choose_layout(scr, prog):
    keys = list(LAYOUTS)
    items = []
    for k in keys:
        passed = sum(1 for r in prog["layouts"].get(k, {}).get("lessons", {}).values()
                     if r.get("passed"))
        mark = "✓" if k == prog["layout"] else " "
        items.append((f"{mark} {LAYOUTS[k]['name']:<8}  {passed:2}/{len(LESSONS)} lessons passed", True))
    i = menu(scr, "Keyboard layout", items,
             ["Lessons, statistics and mix-ups are tracked separately for each layout."],
             keys.index(prog["layout"]))
    if i is None:
        return
    key, remap = keys[i], False
    if key != "qwerty":
        name = LAYOUTS[key]["name"]
        j = menu(scr, f"{name}: how is your computer set up?", [
            (f"My system keyboard layout is already {name}", True),
            (f"My system is QWERTY - translate my keys to {name}", True)],
            [f"Translating lets you learn {name} without changing any system settings:",
             f"press the key where the {name} letter sits and the tutor sees that letter."],
            1 if prog["remap"] else 0)
        if j is None:
            return
        remap = j == 1
    prog["layout"], prog["remap"] = key, remap
    set_layout(key, remap)
    lay(prog)
    save_progress(prog)


def choose_lesson(scr, prog):
    lp = lay(prog)
    items = []
    for i, lesson in enumerate(LESSONS):
        rec = lp["lessons"].get(str(i), {})
        mark = "✓" if rec.get("passed") else ("▸" if i == lp["unlocked"] else " ")
        best = f"best {rec['best_wpm']:4.1f} WPM" if rec.get("attempts") else ""
        items.append((f"{mark} {i + 1:2}. {lesson['title']:<22} goal {lesson['wpm']:2} WPM   {best}",
                      i <= lp["unlocked"]))
    return menu(scr, "Choose a lesson", items, sel=lp["unlocked"])


def pick_lesson(scr, prog):
    i = choose_lesson(scr, prog)
    if i is not None:
        play_lesson(scr, prog, i)


def sparkline(values):
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    return "".join(blocks[int((v - lo) / span * (len(blocks) - 1))] for v in values)


def layout_label(prog):
    name = LAYOUTS[prog["layout"]]["name"]
    return name + (" (translated from QWERTY)" if prog["remap"] else "")


def summary_lines(prog):
    all_sessions = prog["sessions"]
    sessions = layout_sessions(prog)
    passed = sum(1 for r in lay(prog)["lessons"].values() if r.get("passed"))
    lines = [f"{LAYOUTS[prog['layout']]['name']} lessons passed: {passed}/{len(LESSONS)}"]
    if sessions:
        recent = sessions[-10:]
        lines.append(f"Last {len(recent)} sessions: "
                     f"{sum(s['wpm'] for s in recent) / len(recent):.1f} WPM, "
                     f"{sum(s['accuracy'] for s in recent) / len(recent):.1f}% accuracy")
    if all_sessions:
        today = date.today().isoformat()
        mins = sum(s["seconds"] for s in all_sessions if s["date"].startswith(today)) / 60
        lines.append(f"Today: {mins:.0f} min practised    streak: "
                     f"{practice_streak(all_sessions)} day(s)")
    return lines


def stats_screen(scr, prog):
    sessions = layout_sessions(prog)
    if not sessions:
        message(scr, "Statistics", [f"No {LAYOUTS[prog['layout']]['name']} sessions yet - "
                                    "go type something!"])
        return
    totals = key_totals(prog)

    def acc_attr(k):
        if k not in totals or not sum(totals[k][:2]):
            return curses.A_DIM
        hits, errs = totals[k][:2]
        acc = hits / (hits + errs)
        return C(GREEN if acc >= 0.97 else YELLOW if acc >= 0.92 else RED) | curses.A_BOLD

    scr.erase()
    x0 = 4
    put(scr, 1, 2, f"Statistics - {layout_label(prog)}", curses.A_BOLD | C(MIDDLE))
    lines = summary_lines(prog) + [
        f"Sessions: {len(sessions)}    total time: {fmt_time(sum(s['seconds'] for s in sessions))}"
        f"    best: {max(s['wpm'] for s in sessions):.1f} WPM",
    ]
    tests = [f"{m // 60} min {max(s['wpm'] for s in sessions if s.get('limit') == m):.1f}"
             for m in TEST_LENGTHS
             if any(s["mode"] == "test" and s.get("limit") == m for s in sessions)]
    if tests:
        lines.append("Timed-test bests (WPM): " + "   ".join(tests))
    if lay(prog)["game_best"]["score"]:
        gb = lay(prog)["game_best"]
        lines.append(f"Falling-words high score: {gb['score']:,} (level {gb['level']})")
    mixups = sorted(lay(prog)["confusions"].items(), key=lambda kv: -kv[1])[:5]
    if mixups:
        lines.append("Common mix-ups (meant>typed): " + "  ".join(
            f"{'space' if k[0] == ' ' else k[0]}>{'space' if k[1] == ' ' else k[1]} {n}"
            for k, n in mixups))
    for i, line in enumerate(lines):
        put(scr, 3 + i, x0, line)
    y = 4 + len(lines)
    trend = [s["wpm"] for s in sessions[-50:]]
    put(scr, y, x0, f"WPM trend (last {len(trend)}):  {min(trend):.0f} ", 0)
    put(scr, y, x0 + 26 + len(f"{min(trend):.0f}"), sparkline(trend) + f" {max(trend):.0f}",
        C(GREEN))
    y += 2
    put(scr, y, x0, "Per-key accuracy:", 0)
    for text, attr, dx in (("97%+", C(GREEN), 19), ("92-97%", C(YELLOW), 25),
                           ("<92%", C(RED), 33), ("no data", curses.A_DIM, 39)):
        put(scr, y, x0 + dx, text, attr | curses.A_BOLD)
    draw_keyboard(scr, y + 1, x0, acc_attr)
    y += 7
    ranked = sorted(((e / (h + e), (t / n if n else 0), k) for k, (h, e, t, n) in totals.items()
                     if h + e >= 5), reverse=True)[:min(6, scr.getmaxyx()[0] - y - 3)]
    if ranked:
        put(scr, y, x0, "Least accurate keys:", curses.A_BOLD)
        for i, (err, avg, k) in enumerate(ranked):
            put(scr, y + 1 + i, x0 + 2,
                f"{'space' if k == ' ' else k:>5}   {100 - err * 100:5.1f}% accurate   "
                f"{avg * 1000:4.0f} ms avg")
    footer(scr, scr.getmaxyx()[0] - 1, 2, "Press any key")
    scr.refresh()
    wait_key(scr)


def friendly_day(iso):
    days = (date.today() - date.fromisoformat(iso[:10])).days
    return "today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"


def profile_label(prog):
    lk = prog.get("layout") if prog.get("layout") in LAYOUTS else "qwerty"
    passed = sum(1 for r in prog.get("layouts", {}).get(lk, {}).get("lessons", {}).values()
                 if r.get("passed"))
    sessions = prog.get("sessions", [])
    last = f"last practised {friendly_day(sessions[-1]['date'])}" if sessions else "new"
    return f"{prog.get('name', '?'):<18} {LAYOUTS[lk]['name']:<8} {passed:2}/{len(LESSONS)} lessons   {last}"


def ask_name(scr, lines):
    while True:
        name = prompt(scr, "Typing Tutor", lines + ["", "What's your name?"], complete=False)
        if name is None:
            return None
        if name:
            return name[:30]


def choose_profile(scr):
    """'Who's typing?' Returns the chosen profile's progress, or None to quit."""
    while True:
        profiles = list_profiles()
        if not profiles:
            if LEGACY_FILE.exists():
                name = ask_name(scr, [
                    "Typing Tutor now has profiles, so several people can share it: each person",
                    "gets their own lessons, statistics and game scores.",
                    "Your progress so far will be kept under your name."])
                if name is None:
                    return None
                PROFILES_DIR.mkdir(parents=True, exist_ok=True)
                LEGACY_FILE.replace(profile_path(name))
            else:
                name = ask_name(scr, ["Welcome! Everyone who uses this gets their own profile,",
                                      "with their own lessons, statistics and game scores."])
                if name is None:
                    return None
            return open_profile(profile_path(name), name)
        last = load_settings().get("last_profile")
        items = [(profile_label(p), True) for _, p in profiles] + [("+ New profile", True)]
        sel = next((i for i, (f, _) in enumerate(profiles) if f.stem == last), 0)
        i = menu(scr, "Who's typing?", items, ["Pick your name, or add a new profile."], sel,
                 greeting_face())
        if i is None:
            return None
        if i < len(profiles):
            path, p = profiles[i]
            return open_profile(path, p.get("name", path.stem))
        name = ask_name(scr, ["New profile: lessons, statistics and scores start fresh.",
                              "(If the name already exists, you'll just switch to it.)"])
        if name is not None:
            return open_profile(profile_path(name), name)


def main_menu(scr, prog):
    """Returns True to switch user, False to quit."""
    set_layout(prog["layout"], prog["remap"])
    sel = 0
    while True:
        cur = lay(prog)["unlocked"]
        actions = [
            (f"Continue: lesson {cur + 1} - {LESSONS[cur]['title']}",
             lambda: play_lesson(scr, prog, lay(prog)["unlocked"])),
            ("Choose a lesson", lambda: pick_lesson(scr, prog)),
            ("Practise weak keys", lambda: play_weak(scr, prog)),
            ("Drill mixed-up key pairs", lambda: play_confusions(scr, prog)),
            ("Timed test (1, 2 or 5 minutes)", lambda: play_test(scr, prog)),
            ("Falling words game", lambda: play_game(scr, prog)),
            ("Free typing (full keyboard)", lambda: play_free(scr, prog)),
            ("Type your own text", lambda: play_custom(scr, prog)),
            ("Statistics", lambda: stats_screen(scr, prog)),
            (f"Keyboard layout: {layout_label(prog)}", lambda: choose_layout(scr, prog)),
            (f"Switch user (you're {prog['name']})", "switch"),
            ("Quit", None),
        ]
        choice = menu(scr, f"Typing Tutor - {prog['name']}", [(label, True) for label, _ in actions],
                      summary_lines(prog), sel, greeting_face())
        if choice is None or actions[choice][1] is None:
            return False
        if actions[choice][1] == "switch":
            return True
        sel = choice
        actions[choice][1]()


def main(scr, user=None):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    init_colors()
    while True:
        prog = open_profile(profile_path(user), user) if user else choose_profile(scr)
        user = None
        if prog is None or not main_menu(scr, prog):
            return


def cli():
    ap = argparse.ArgumentParser(description="Terminal touch-typing tutor (QWERTY, Dvorak, Colemak).")
    ap.add_argument("--user", metavar="NAME", help="start as this profile (created if new)")
    ap.add_argument("--reset", action="store_true", help="erase all saved progress for --user NAME")
    ap.add_argument("--seed", type=int, help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.reset:
        if not args.user:
            names = [p.get("name", f.stem) for f, p in list_profiles()]
            ap.error("--reset needs --user NAME" + (f" (profiles: {', '.join(names)})" if names else ""))
        path = profile_path(args.user)
        if not path.exists():
            print(f"No profile called {args.user!r}.")
        elif input(f"Erase all progress for {args.user} ({path})? [y/N] ").lower().startswith("y"):
            path.unlink()
            print("Progress erased.")
        return
    if args.seed is not None:
        random.seed(args.seed)
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    try:
        curses.wrapper(main, args.user)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
