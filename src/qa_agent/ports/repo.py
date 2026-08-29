"""Repository-context port — backs the review LLM's get_file_context tool.

This is the one tool the model calls of its own accord, which makes it the one
place model output influences filesystem access. Security therefore lives at
this boundary: paths resolve strictly inside the fixture repo root, and anything
else (traversal, absolute paths, symlink escapes) is rejected with an error the
model can read and correct — the error lists what IS available rather than just
saying no, so a wrong guess costs one bounded retry instead of a dead end.
"""

from pathlib import Path
from typing import Protocol


class RepoSource(Protocol):
    def get_file(self, path: str) -> str: ...

    def list_files(self) -> list[str]: ...


class FixtureRepo:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def list_files(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.root))
            for p in self.root.rglob("*.py")
            if p.is_file()
        )

    def get_file(self, path: str) -> str:
        resolved = (self.root / path).resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError(
                f"path {path!r} escapes the repository root; available files: {self.list_files()}"
            )
        if not resolved.is_file():
            raise FileNotFoundError(
                f"no file {path!r} in the repository; available files: {self.list_files()}"
            )
        return resolved.read_text()
