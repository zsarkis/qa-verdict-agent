"""Central paths and model configuration (env-driven)."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# Loaded at import: every entry point (CLI, evals, ad-hoc one-liners) imports
# settings, making this the single choke point for env loading. Anchored to the
# repo root so it works regardless of cwd. Real env vars win over .env values.
load_dotenv(ROOT / ".env")
DATA_DIR = ROOT / "data"
TICKETS_DIR = DATA_DIR / "tickets"
DIFFS_DIR = DATA_DIR / "diffs"
KB_DIR = DATA_DIR / "kb"
REPO_DIR = DATA_DIR / "repo"
OUTBOX_DIR = DATA_DIR / "board" / "outbox"
EXPECTED_VERDICTS = DATA_DIR / "expected" / "verdicts.json"
CHECKPOINT_DB = ROOT / "checkpoints.db"

REVIEW_MODEL = os.environ.get("QA_REVIEW_MODEL", "anthropic:claude-sonnet-4-6")
JUDGE_MODEL = os.environ.get("QA_JUDGE_MODEL", "openai:gpt-5.5")
EMBEDDINGS_MODEL = os.environ.get("QA_EMBEDDINGS_MODEL", "text-embedding-3-small")
