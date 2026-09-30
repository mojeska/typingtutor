#!/usr/bin/env python3
"""Terminal touch-typing tutor for QWERTY keyboards.

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
  * Per-key error and speed stats drive a "weak keys" practice mode.

WPM uses the standard definition: (characters typed / 5) per minute.
Progress is saved to $XDG_DATA_HOME/typing-tutor/progress.json.
"""
import argparse
import curses
import json
import locale
import os
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_FILE = (Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
             / "typing-tutor" / "progress.json")
PASS_ACCURACY = 95.0
EXERCISE_TOKENS = 30

LESSONS = [
    dict(title="Home row: f j", keys="fj", wpm=10,
         tip="Rest your index fingers on F and J - feel the bumps? That's home."),
    dict(title="Home row: d k", keys="dk", wpm=10,
         tip="Middle fingers rest on D and K, right beside your index fingers."),
    dict(title="Home row: s l", keys="sl", wpm=12,
         tip="Ring fingers rest on S and L."),
    dict(title="Home row: a ;", keys="a;", wpm=12,
         tip="Pinkies rest on A and ;. Thumbs float over the space bar."),
    dict(title="Home row: g h", keys="gh", wpm=13,
         tip="Index fingers reach sideways to G and H, then snap back home."),
    dict(title="Top row: e i", keys="ei", wpm=14,
         tip="Middle fingers reach up to E and I. Keep the other fingers anchored."),
    dict(title="Top row: r u", keys="ru", wpm=15,
         tip="Index fingers reach up to R and U."),
    dict(title="Top row: t y", keys="ty", wpm=15,
         tip="Index fingers stretch up and inward to T and Y."),
    dict(title="Top row: w o", keys="wo", wpm=16,
         tip="Ring fingers reach up to W and O."),
    dict(title="Top row: q p", keys="qp", wpm=16,
         tip="Pinkies reach up to Q and P."),
    dict(title="Bottom row: v m", keys="vm", wpm=17,
         tip="Index fingers curl down to V and M."),
    dict(title="Bottom row: c ,", keys="c,", wpm=17,
         tip="Middle fingers curl down to C and comma."),
    dict(title="Bottom row: x .", keys="x.", wpm=18,
         tip="Ring fingers curl down to X and period."),
    dict(title="Bottom row: z /", keys="z/", wpm=18,
         tip="Pinkies curl down to Z and slash."),
    dict(title="Bottom row: b n", keys="bn", wpm=18,
         tip="Index fingers reach down and inward to B and N."),
    dict(title="Capitals and '", keys="'", caps=True, wpm=18,
         tip="Hold Shift with the pinky of the OPPOSITE hand to the letter. "
             "The right pinky types '."),
    dict(title="Number row", keys="1234567890", wpm=15,
         tip="Reach straight up; each number uses the same finger as the letters below it."),
    dict(title="Punctuation: ? ! : -", keys="?!:-", wpm=18,
         tip="? ! and : need Shift. The hyphen is a right-pinky reach."),
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

FINGERS = {}
for _keys, _finger in [("`1qaz", "left pinky"), ("2wsx", "left ring"), ("3edc", "left middle"),
                       ("45rtfgvb", "left index"), ("67yuhjnm", "right index"),
                       ("8ik,", "right middle"), ("9ol.", "right ring"),
                       ("0-=p[];'/", "right pinky")]:
    for _k in _keys:
        FINGERS[_k] = _finger
FINGERS[" "] = "either thumb"

SHIFTED = dict(zip("~!@#$%^&*()_+{}:\"<>?", "`1234567890-=[];',./"))

KB_ROWS = [("`1234567890-=", 0), ("qwertyuiop[]", 6), ("asdfghjkl;'", 7), ("zxcvbnm,./", 9)]
KB_WIDTH = 56

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
    picks = random.sample(SENTENCES, len(SENTENCES))
    out = []
    while sum(len(s) + 1 for s in out) < min_len:
        out.append(picks[len(out)])
    return " ".join(out)


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
    data.setdefault("unlocked", 0)
    data.setdefault("lessons", {})
    data.setdefault("sessions", [])
    data.setdefault("keys", {})
    return data


def save_progress(prog):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(prog, indent=1))
    tmp.replace(DATA_FILE)


def record(prog, mode, lesson_idx, res):
    """Save a finished exercise. Returns pass/fail for lessons, else None."""
    prog["sessions"].append(dict(
        date=datetime.now().isoformat(timespec="seconds"), mode=mode, lesson=lesson_idx,
        wpm=round(res["wpm"], 1), accuracy=round(res["accuracy"], 1),
        seconds=round(res["seconds"], 1), chars=res["chars"], errors=res["errors"]))
    for k, (hits, errs, secs, timed) in res["keys"].items():
        s = prog["keys"].setdefault(k, {"hits": 0, "errors": 0, "time": 0.0, "timed": 0})
        s["hits"] += hits
        s["errors"] += errs
        s["time"] = round(s["time"] + secs, 3)
        s["timed"] += timed
    passed = None
    if mode == "lesson":
        passed = res["accuracy"] >= PASS_ACCURACY and res["wpm"] >= LESSONS[lesson_idx]["wpm"]
        rec = prog["lessons"].setdefault(str(lesson_idx), {
            "attempts": 0, "best_wpm": 0.0, "best_accuracy": 0.0, "passed": False})
        rec["attempts"] += 1
        rec["best_wpm"] = max(rec["best_wpm"], round(res["wpm"], 1))
        rec["best_accuracy"] = max(rec["best_accuracy"], round(res["accuracy"], 1))
        rec["passed"] = rec["passed"] or passed
        if passed:
            prog["unlocked"] = max(prog["unlocked"], min(lesson_idx + 1, len(LESSONS) - 1))
    save_progress(prog)
    return passed


def key_totals(prog):
    """Per-key [hits, errors, seconds, timed] merged by physical key."""
    agg = {}
    for k, s in prog["keys"].items():
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
    put(scr, scr.getmaxyx()[0] - 1, 2, "Press any key", curses.A_DIM)
    scr.refresh()
    wait_key(scr)


def menu(scr, title, items, header=(), sel=0):
    """Vertical menu. items: [(label, enabled)]. Returns index or None."""
    scr.timeout(-1)
    enabled = [i for i, (_, en) in enumerate(items) if en]
    if sel not in enabled:
        sel = enabled[0]
    top = 0
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
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
        put(scr, h - 1, 2, "Up/Down or j/k: move   Enter: select   Esc/q: back", curses.A_DIM)
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
        put(scr, h - 2, x0, "Enter/Space: start    Esc: back", curses.A_DIM)
        scr.refresh()
        ch = scr.get_wch()
        if ch in ("\n", "\r", " ", curses.KEY_ENTER):
            return True
        if ch == "\x1b":
            return False


def draw_exercise(scr, title, text, pos, wrong, missed, elapsed, errors):
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
    put(scr, 1, x0, f"{wpm:5.1f} WPM   {acc:5.1f}% accuracy   {fmt_time(elapsed)}   "
                    f"{100 * pos // len(text)}% done", curses.A_DIM)

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
    put(scr, h - 1, 2, "Esc: back to menu (this attempt is not saved)", curses.A_DIM)
    scr.refresh()


def run_exercise(scr, title, text):
    """Type `text`. Wrong keys must be corrected. Returns result dict or None."""
    scr.timeout(200)  # redraw periodically so the clock ticks
    pos = errors = 0
    start = last = None
    missed = False
    wrong = set()
    keys = {}  # char -> [hits, errors, seconds, timed]
    while pos < len(text):
        now = time.monotonic()
        draw_exercise(scr, title, text, pos, wrong, missed,
                      now - start if start else 0.0, errors)
        try:
            ch = scr.get_wch()
        except curses.error:
            continue
        if ch == "\x1b":
            return None
        if not isinstance(ch, str) or not ch.isprintable():
            continue
        now = time.monotonic()
        if start is None:
            start = last = now
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
            errors += 1
            wrong.add(pos)
            missed = True
    secs = max(last - start, 1.0)
    return dict(wpm=len(text) / 5 / (secs / 60), accuracy=100 * len(text) / (len(text) + errors),
                seconds=secs, chars=len(text), errors=errors, keys=keys)


def results(scr, heading, res, goal_wpm=None, passed=None, best=None, last_lesson=False):
    """Show results. Returns 'next', 'retry' or 'menu'."""
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
    trouble = sorted(((s[1], k) for k, s in res["keys"].items() if s[1]), reverse=True)[:5]
    if trouble:
        lines.append(("", 0))
        lines.append(("Trouble keys: " + ", ".join(
            f"{'space' if k == ' ' else k} ({n})" for n, k in trouble), 0))
    if res["accuracy"] < PASS_ACCURACY:
        lines.append(("Tip: slow down. Speed comes from accuracy, not the other way round.",
                      curses.A_DIM))
    can_advance = passed and not last_lesson
    enter = "next lesson" if can_advance else "try again"
    if passed is None:
        enter = "another round"

    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        x0 = center_x(scr, 64)
        put(scr, 1, x0, heading, curses.A_BOLD | C(MIDDLE))
        for i, (text, attr) in enumerate(lines):
            put(scr, 3 + i, x0, text, attr)
        put(scr, h - 2, x0, f"Enter: {enter}    r: retry    Esc: menu", curses.A_DIM)
        scr.refresh()
        ch = wait_key(scr)
        if ch in ("\n", "\r", curses.KEY_ENTER):
            return "next" if can_advance else "retry"
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
                         prog["lessons"][str(i)]["best_wpm"], i == len(LESSONS) - 1)
        if action == "menu":
            return
        if action == "next":
            i += 1


def play_weak(scr, prog):
    chars, caps = lesson_chars(prog["unlocked"])
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


def choose_lesson(scr, prog):
    items = []
    for i, lesson in enumerate(LESSONS):
        rec = prog["lessons"].get(str(i), {})
        mark = "✓" if rec.get("passed") else ("▸" if i == prog["unlocked"] else " ")
        best = f"best {rec['best_wpm']:4.1f} WPM" if rec.get("attempts") else ""
        items.append((f"{mark} {i + 1:2}. {lesson['title']:<22} goal {lesson['wpm']:2} WPM   {best}",
                      i <= prog["unlocked"]))
    return menu(scr, "Choose a lesson", items, sel=prog["unlocked"])


def sparkline(values):
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    return "".join(blocks[int((v - lo) / span * (len(blocks) - 1))] for v in values)


def summary_lines(prog):
    sessions = prog["sessions"]
    passed = sum(1 for r in prog["lessons"].values() if r.get("passed"))
    lines = [f"Lessons passed: {passed}/{len(LESSONS)}"]
    if sessions:
        recent = sessions[-10:]
        lines.append(f"Last {len(recent)} sessions: "
                     f"{sum(s['wpm'] for s in recent) / len(recent):.1f} WPM, "
                     f"{sum(s['accuracy'] for s in recent) / len(recent):.1f}% accuracy")
        today = date.today().isoformat()
        mins = sum(s["seconds"] for s in sessions if s["date"].startswith(today)) / 60
        lines.append(f"Today: {mins:.0f} min practised    streak: {practice_streak(sessions)} day(s)")
    return lines


def stats_screen(scr, prog):
    sessions = prog["sessions"]
    if not sessions:
        message(scr, "Statistics", ["No sessions yet - go type something!"])
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
    put(scr, 1, 2, "Statistics", curses.A_BOLD | C(MIDDLE))
    lines = summary_lines(prog) + [
        f"Sessions: {len(sessions)}    total time: {fmt_time(sum(s['seconds'] for s in sessions))}"
        f"    best: {max(s['wpm'] for s in sessions):.1f} WPM",
    ]
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
                     if h + e >= 5), reverse=True)[:6]
    if ranked:
        put(scr, y, x0, "Least accurate keys:", curses.A_BOLD)
        for i, (err, avg, k) in enumerate(ranked):
            put(scr, y + 1 + i, x0 + 2,
                f"{'space' if k == ' ' else k:>5}   {100 - err * 100:5.1f}% accurate   "
                f"{avg * 1000:4.0f} ms avg")
    put(scr, scr.getmaxyx()[0] - 1, 2, "Press any key", curses.A_DIM)
    scr.refresh()
    wait_key(scr)


def main(scr):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    init_colors()
    prog = load_progress()
    sel = 0
    while True:
        cur = prog["unlocked"]
        items = [(f"Continue: lesson {cur + 1} - {LESSONS[cur]['title']}", True),
                 ("Choose a lesson", True),
                 ("Practise weak keys", True),
                 ("Free typing (full keyboard)", True),
                 ("Statistics", True),
                 ("Quit", True)]
        choice = menu(scr, "Typing Tutor", items, summary_lines(prog), sel)
        if choice is None or choice == 5:
            return
        sel = choice
        if choice == 0:
            play_lesson(scr, prog, cur)
        elif choice == 1:
            i = choose_lesson(scr, prog)
            if i is not None:
                play_lesson(scr, prog, i)
        elif choice == 2:
            play_weak(scr, prog)
        elif choice == 3:
            play_free(scr, prog)
        elif choice == 4:
            stats_screen(scr, prog)


def cli():
    ap = argparse.ArgumentParser(description="Terminal touch-typing tutor (QWERTY).")
    ap.add_argument("--reset", action="store_true", help="erase all saved progress")
    ap.add_argument("--seed", type=int, help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.reset:
        if DATA_FILE.exists() and input(f"Erase {DATA_FILE}? [y/N] ").lower().startswith("y"):
            DATA_FILE.unlink()
            print("Progress erased.")
        return
    if args.seed is not None:
        random.seed(args.seed)
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
