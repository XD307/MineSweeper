import random
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Event:
    type: str
    message: str
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "message": self.message,
            "payload": self.payload,
        }


# События
_EVENTS = [
    Event(
        type="flip_board",
        message="Поле перевернулось вверх дном!",
        payload={"flip": True},
    ),
    Event(
        type="ded_gif",
        message="С новым годом!",
        payload={
            "gif_url": "/static/Ded.gif"
        },
    ),
    Event(
        type="mirror_board",
        message="Все теперь зеркально!!",
        payload={"mirror": True},
    ),
    Event(
        type="rickroll",
        message="😁😁",
        payload={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        },
    ),
    Event(
        type="roman_numbers",
        message="Все цифры стали римскими!",
        payload={"roman": True},
    ),
]


def random_event(prev_type: Optional[str]) -> Event:
    # Случайный выбор (без повторов)
    candidates = [e for e in _EVENTS if e.type != prev_type]
    if not candidates:
        candidates = _EVENTS
    return random.choice(candidates)

