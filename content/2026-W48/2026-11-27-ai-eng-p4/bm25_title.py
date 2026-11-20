"""Toy example: BM25 retrieval that runs locally, with and without the title in each chunk.

Run: python bm25_title.py   (standard library only, no API key, no vector database)

The handbook below is made up. Each "## " section is split into paragraph chunks. A chunk cut
out of its document loses the words that were only in the headings, so BM25 cannot match them.
Copying the document title and the section name into the chunk text before indexing fixes part
of that, for free.
"""
import math
import re
from collections import Counter

HANDBOOK = {
    "Rain gauge calibration": {
        "Tools": ["Use the 100 ml test bottle and a level. Keep a notebook for the readings."],
        "Steps": [
            "Level the funnel. Pour 100 ml slowly and count the bucket tips.",
            "Compare the count with the expected value and adjust the screw by a quarter turn.",
        ],
        "Schedule": ["Repeat after every 500 mm of water, after moving the funnel, and each season."],
    },
    "Thermometer calibration": {
        "Steps": ["Put the probe in an ice bath for five minutes. It should read 0.0 C."],
        "Schedule": ["Check how often the reading drifts. Most probes need a check every month."],
    },
    "Rain gauge cleaning": {
        "Steps": [
            "Remove leaves from the funnel and wash the gauge with clean water.",
            "Check the rain gauge filter for insects and dry it before refitting.",
        ],
    },
    "Station power": {
        "Battery": ["The battery lasts about two weeks. How often you replace it depends on the sun."],
    },
}

TOKEN = re.compile(r"\w+(?:[-.]\w+)*")


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def chunks() -> list[tuple[str, str, str]]:
    return [(title, section, para)
            for title, sections in HANDBOOK.items()
            for section, paras in sections.items()
            for para in paras]


def with_context(title: str, section: str, chunk: str) -> str:
    return f"Document: {title}. Section: {section}.\n{chunk}"


def bm25_scores(docs: list[list[str]], query: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / n_docs
    df = Counter(w for d in docs for w in set(d))
    scores = []
    for d in docs:
        tf, s = Counter(d), 0.0
        for w in set(query):
            if tf[w]:
                idf = math.log(1 + (n_docs - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    return scores


QUERY = "how often is rain gauge calibration needed"
RIGHT = ("Rain gauge calibration", "Schedule")

if __name__ == "__main__":
    all_chunks = chunks()
    right = next(i for i, (t, s, _) in enumerate(all_chunks) if (t, s) == RIGHT)
    print(f"{len(all_chunks)} chunks, query: {QUERY!r}")
    for label, texts in [
        ("chunk text only", [c for _, _, c in all_chunks]),
        ("title + section first", [with_context(*c) for c in all_chunks]),
    ]:
        scores = bm25_scores([tokens(t) for t in texts], tokens(QUERY))
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        if scores[right] == 0:
            print(f"{label:<22} right chunk scores 0: none of the query words is in it")
        else:
            print(f"{label:<22} right chunk at rank {order.index(right) + 1} of {len(all_chunks)}")
        for i in order[:3]:
            print(f"    {scores[i]:5.2f}  {all_chunks[i][0]} / {all_chunks[i][1]}")
