from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DetectionResult:
    detector: str       # "pii" | "injection"
    type: str           # EMAIL_ADDRESS, INSTRUCTION_OVERRIDE, etc.
    text: str           # matched span
    redacted: str       # replacement token e.g. "[EMAIL]"
    start: int          # character offset in original text
    end: int
    confidence: float   # 0.0 – 1.0
    severity: str       # low / medium / high / critical


class Detector(ABC):
    name: str = ""

    @abstractmethod
    def scan(self, text: str, config: dict) -> list[DetectionResult]:
        ...

    def warm_up(self) -> None:
        """Called at app startup to pre-load models."""
