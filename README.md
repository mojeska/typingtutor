# Typing Tutor

A terminal touch-typing tutor for QWERTY, Dvorak and Colemak keyboards. Pure Python standard library (curses), no dependencies.

## Run

```
python3 typing_tutor.py          # start
python3 typing_tutor.py --reset  # erase saved progress
```

Needs a terminal of at least 60x20.

## Method

- Keys are introduced two at a time, starting from the home-row index-finger keys and working outward:
  home row, top row, bottom row, Shift/capitals, numbers, punctuation, then full sentences (19 lessons).
- Exercises only use keys you've already been taught.
- An on-screen keyboard is coloured by finger and highlights the next key, so you never need to look down.
- Accuracy first: wrong keys must be corrected before moving on. A lesson unlocks the next at
  95% accuracy plus a speed goal (10 → 25 WPM).

## Practice modes

- **Weak-key practice** drills your three slowest / least accurate keys.
- **Mixed-up key pairs**: every wrong keystroke records which key you meant and which you hit.
  Pairs that keep happening (e.g. `e` → `r`) get contrast drills (`ere rer eerr`) plus words
  containing both keys. Forgotten Shifts and space slips are ignored.
- **Timed tests** of 1, 2 or 5 minutes, with a personal best for each. Uses real sentences once
  you've finished the course, otherwise only the keys you've learned.
- **Falling Words game**: type items before they hit the ground; five misses ends the game.
  Type an item's first key to lock onto it (Backspace lets go). It adapts to you:
  - only keys you've been taught fall, and your weak keys turn up more often;
  - the starting pace comes from your recent WPM;
  - every 10 items cleared is a new level: faster, busier, and it adds words (once you know
    enough letters), then capitals, numbers and punctuation (once the course has taught them).
  - Score = item length × level × combo multiplier (up to x4 for a streak without a mistake or
    miss). High score per layout; an extra life every 5 levels.
  Game keystrokes feed your key stats and mix-ups, but games are left out of WPM averages.

## Mascot

A little ASCII mascot keeps you company: it greets you on the main menu (sleepily, late at night),
reacts on results screens, and lives on the ground in Falling Words, where it watches the item you're
typing `(<_°)` `(°_>)`, cheers clears `(^_^)` and combos `♪(^_^)♪`, winces at mistakes `(>_<)`,
cries when something lands `(T_T)`, naps while paused `(˘_˘)zzZ` and flips the table at game over
`(╯°□°)╯`. Faces come from the reference sheet of
[fp-bits/mascota-ascii](https://github.com/fp-bits/mascota-ascii) (MIT licence).
- **Free typing**: random real sentences using the full keyboard.
- **Type your own text**: point it at any plain-text file (Tab completes paths). Curly quotes, dashes and
  accents are simplified, and it works through the file ~300 characters at a time, remembering
  your place in each file.

## Keyboard layouts

Choose QWERTY, Dvorak or Colemak from the menu. The course is defined by physical key position,
so each layout gets the same lesson sequence built from its own keys (Dvorak starts with U/H,
Colemak with T/N). Lesson progress, key stats and mix-ups are tracked separately per layout.

For Dvorak and Colemak you can say your system is still set to QWERTY; the tutor then translates
your keystrokes, so you can learn a new layout without changing any system settings.

## Tracking

- WPM uses the standard (characters / 5) per minute.
- Everything is saved to `~/.local/share/typing-tutor/progress.json` (progress files from older
  versions are migrated automatically into the QWERTY course).
- **Statistics** shows a WPM trend, timed-test bests, game high score, common mix-ups, a per-key accuracy heatmap,
  your least accurate keys and your practice streak.
