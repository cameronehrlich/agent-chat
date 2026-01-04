from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Iterable

from .words import ADJECTIVES, NOUNS

CHANNEL_PATTERN = re.compile(r"^#")
DM_PATTERN = re.compile(r"^@")


def is_channel(target: str) -> bool:
    return bool(CHANNEL_PATTERN.match(target))


def is_direct(target: str) -> bool:
    return bool(DM_PATTERN.match(target))


def generate_nick() -> str:
    first = random.choice(ADJECTIVES)
    second = random.choice(NOUNS)
    return f"{first}{second}"


def ensure_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | 0o111)
