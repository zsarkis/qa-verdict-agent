"""Diff-source port.

Same ports-and-adapters shape as the board: the graph asks a DiffSource for the
ticket's diff, and the default adapter reads local fixtures. A GitHub adapter
(compare API) is the swap-in — stretch goal only.
"""

from pathlib import Path
from typing import Protocol


class DiffSource(Protocol):
    def get_diff(self, diff_ref: str) -> str: ...


class FixtureDiffs:
    def __init__(self, diffs_dir: Path):
        self.diffs_dir = Path(diffs_dir)

    def get_diff(self, diff_ref: str) -> str:
        path = self.diffs_dir / diff_ref
        if not path.is_file():
            known = sorted(p.name for p in self.diffs_dir.glob("*.diff"))
            raise KeyError(f"unknown diff {diff_ref!r}; known diffs: {known}")
        return path.read_text()
