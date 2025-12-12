# src/history_store.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, List, Literal

Role = Literal["user", "assistant"]

@dataclass
class HistoryItem:
    role: Role
    content: str

_history: DefaultDict[str, List[HistoryItem]] = defaultdict(list)

def append(session_id: str, role: Role, content: str) -> None:
    _history[session_id].append(HistoryItem(role=role, content=content))

def get(session_id: str) -> List[HistoryItem]:
    return list(_history.get(session_id, []))

def clear(session_id: str) -> None:
    _history.pop(session_id, None)
