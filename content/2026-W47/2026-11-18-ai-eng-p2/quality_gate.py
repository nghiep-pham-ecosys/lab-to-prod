"""Toy example behind the post: precision and recall of a quality gate.

Run: python quality_gate.py
100 answers, 13 are bad (reviewer labels). The gate flags 10; 8 of them are really bad.
"""

def precision_recall(true_positive: int, flagged: int, actually_bad: int) -> tuple[float, float]:
    return true_positive / flagged, true_positive / actually_bad


if __name__ == "__main__":
    total, bad, flagged, tp = 100, 13, 10, 8
    p, r = precision_recall(tp, flagged, bad)
    print(f"precision = {tp}/{flagged} = {p:.2f}")
    print(f"recall    = {tp}/{bad} = {r:.2f}")
    print(f"bad answers that passed the gate: {bad - tp} of {bad} ({(bad - tp) / bad:.0%})")
    print(f"good answers blocked by mistake:  {flagged - tp} of {total - bad}")
