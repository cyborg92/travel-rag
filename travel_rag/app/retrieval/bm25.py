import re
import math
from collections import Counter

from numpy import greater

PATTERN_1 = r"[a-z0-9]+"
PATTERN_2 = r"[a-z0-9]+(?:-[a-z0-9]+)*"
PATTERN_3 = r"\d{1,3}(?:,\d{3})+|[a-z0-9]+(?:-[a-z0-9]+)*"


def tokenize(text: str, pattern: str) -> list[str]:
    """Lowercase the text and pull out tokens using the given regex."""
    return re.findall(pattern, text.lower())


class BM25:
    def __init__(self, chunks: list[dict], pattern: str = PATTERN_2,
                 k1: float = 1.5, b: float = 0.75) -> None:
        """chunks is the list of chunk dicts (source, chunk_index, chunk)."""
        self.pattern = pattern
        self.k1 = k1
        self.b = b

        # Per-chunk data: chunk_id -> {"counter": ..., "length": ...}
        self.index: dict[str, dict] = {}
        for chunk in chunks:
            chunk_id = f"{chunk['source']}:{chunk['chunk_index']}"
            tokens = tokenize(chunk["chunk"], self.pattern)
            self.index[chunk_id] = {
                "counter": Counter(tokens),
                "length": len(tokens),
            }

        # Corpus-wide stats
        self.N = len(self.index)
        total_len = sum(c["length"] for c in self.index.values())
        self.avg_len = total_len / self.N if self.N else 0

        # doc_freq: in how many chunks does each term appear?
        self.doc_freq: Counter = Counter()
        for chunk_data in self.index.values():
            self.doc_freq.update(chunk_data["counter"].keys())  # keys, so +1 per chunk

    def idf(self, term: str) -> float:
        n = self.doc_freq[term]
        if n == 0:
            return 0.0
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def score(self, query_tokens, chunk_id) -> float:
        data = self.index[chunk_id]
        counter,length = data["counter"], data["length"]
        norm = 1 - self.b + self.b * length / self.avg_len
        total = 0.0

        for token in query_tokens:
            tf = counter[token]
            if tf == 0:
                continue
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * norm
            total += self.idf(token) * numerator / denominator
        return total

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        query_tokens = tokenize(query, self.pattern)
        if (self.N == 0 or not query_tokens):
            return []
        results = []
        for key in self.index.keys():
            chunk_score = self.score(query_tokens, chunk_id=key)
            if chunk_score>0:
                results.append((key,chunk_score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
