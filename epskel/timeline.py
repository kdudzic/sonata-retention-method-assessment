"""Timestamps for the corpus (plan 6.5): 12-week window, realistic diurnal and weekly rhythm per author.

Background/hard-negative posts: the author's posting rhythm comes from the persona card
(`schedule_occupation` free text -> coarse rhythm class) and `posts_per_week`.
Arc posts: the PI's day offsets are kept exactly; the arc is placed at a random start inside the window
so that it fits, and each post gets a time of day drawn from the author's rhythm.
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta

WINDOW_WEEKS = 12

# Hour weights (0..23) for a few rhythm classes. Values are relative; they encode when a person is
# free to post, not when they are awake. Tuned by hand to look like aggregate social-media activity.
RHYTHMS = {
    "day_worker":  [1, 1, 0, 0, 0, 1, 4, 6, 4, 2, 2, 3, 6, 4, 2, 3, 5, 8, 9, 10, 10, 9, 6, 3],
    "shift_early": [2, 1, 0, 0, 2, 5, 3, 2, 2, 2, 3, 4, 7, 8, 7, 6, 6, 7, 8, 8, 7, 5, 3, 2],
    "night_shift": [8, 8, 7, 6, 4, 3, 3, 2, 1, 1, 1, 1, 2, 3, 4, 5, 6, 6, 5, 5, 5, 6, 7, 8],
    "student":     [4, 2, 1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 7, 6, 6, 7, 8, 9, 10, 10, 10, 9, 7],
    "home":        [1, 0, 0, 0, 0, 1, 3, 5, 6, 7, 8, 8, 7, 6, 6, 6, 6, 6, 6, 7, 8, 8, 5, 2],
    "retired":     [0, 0, 0, 0, 0, 1, 3, 6, 8, 9, 9, 8, 7, 6, 6, 7, 7, 7, 7, 7, 6, 4, 2, 1],
    "gig":         [3, 2, 1, 0, 0, 1, 2, 3, 4, 5, 6, 6, 6, 6, 6, 6, 6, 7, 8, 8, 8, 7, 6, 4],
}
# Weekday weights Mon..Sun (slight weekend lift for most, weekend dip for shift/gig workers)
WEEKDAY = {
    "default":   [1.0, 1.0, 1.0, 1.0, 1.05, 1.15, 1.2],
    "shift":     [1.0, 1.0, 1.0, 1.0, 1.0, 0.9, 0.9],
}


def rhythm_class(card: dict) -> str:
    t = (card.get("schedule_occupation", "") + " " + card.get("life_situation", "")).lower()
    if re.search(r"nocn|noc[ąa]\b|na noc|do rana|24h", t):
        return "night_shift"
    if re.search(r"student|studi|uczelni|sesj|wykład|licea|szko[łl]y średniej|matur|klas[aeyę]\b", t):
        return "student"
    if re.search(r"emeryt|rencist|na emeryturze", t):
        return "retired"
    if re.search(r"zlecen|dorywcz|z aplikacji|kurier|glovo|uber|bolt|dostaw", t):
        return "gig"
    if re.search(r"w domu z|macierzyń|rodzicielsk|opiek|dzieć|dziec|niemowl", t) and not re.search(r"pracuj|etat", t):
        return "home"
    if re.search(r"zmian|od 6|od 5|6-14|5:|o 5|wstaje o [45]", t):
        return "shift_early"
    return "day_worker"


class Timeline:
    def __init__(self, start: datetime, seed: int = 0) -> None:
        self.start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        self.end = self.start + timedelta(weeks=WINDOW_WEEKS)
        self.rng = random.Random(seed)

    def _hour(self, rc: str) -> tuple[int, int, int]:
        w = RHYTHMS[rc]
        h = self.rng.choices(range(24), weights=w)[0]
        return h, self.rng.randrange(60), self.rng.randrange(60)

    def _day(self, rc: str) -> int:
        """Day index within the window, weighted by weekday pattern."""
        wk = WEEKDAY["shift"] if rc in ("shift_early", "night_shift", "gig") else WEEKDAY["default"]
        days = list(range(WINDOW_WEEKS * 7))
        weights = [wk[(self.start + timedelta(days=d)).weekday()] for d in days]
        return self.rng.choices(days, weights=weights)[0]

    def author_timestamps(self, card: dict, n: int, min_gap_hours: float = 3.0) -> list[datetime]:
        """n timestamps for an ordinary author, sorted, with bursty-but-spread behaviour."""
        rc = rhythm_class(card)
        out: list[datetime] = []
        tries = 0
        while len(out) < n and tries < n * 50:
            tries += 1
            d = self._day(rc)
            h, m, s = self._hour(rc)
            ts = self.start + timedelta(days=d, hours=h, minutes=m, seconds=s)
            if all(abs((ts - o).total_seconds()) >= min_gap_hours * 3600 for o in out):
                out.append(ts)
        return sorted(out)

    def arc_timestamps(self, card: dict, day_offsets: list[int]) -> list[datetime]:
        """Place the arc inside the window keeping the PI's day offsets; jitter each day by at most +-1 day
        only if it keeps the order, never the first post."""
        rc = rhythm_class(card)
        span = max(day_offsets)
        latest_start = WINDOW_WEEKS * 7 - span - 1
        start_day = self.rng.randint(0, max(0, latest_start))
        out = []
        for d in day_offsets:
            h, m, s = self._hour(rc)
            out.append(self.start + timedelta(days=start_day + d, hours=h, minutes=m, seconds=s))
        return out


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%S")
