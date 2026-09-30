# Typing Tutor

A terminal touch-typing tutor for QWERTY keyboards. Pure Python standard library (curses), no dependencies.

## Run

```
python3 typing_tutor.py          # start
python3 typing_tutor.py --reset  # erase saved progress
```

Needs a terminal of at least 60x20.

## Method

- Keys are introduced two at a time, starting from the home-row anchors (F/J) and working outward:
  home row, top row, bottom row, Shift/capitals, numbers, punctuation, then full sentences (19 lessons).
- Exercises only use keys you've already been taught.
- An on-screen keyboard is coloured by finger and highlights the next key, so you never need to look down.
- Accuracy first: wrong keys must be corrected before moving on. A lesson unlocks the next at
  95% accuracy plus a speed goal (10 → 25 WPM).

## Tracking

- WPM uses the standard (characters / 5) per minute.
- Every session and per-key accuracy/speed is saved to `~/.local/share/typing-tutor/progress.json`.
- **Weak-key practice** drills your three worst keys.
- **Statistics** shows a WPM trend, a per-key accuracy heatmap, your least accurate keys and your practice streak.
