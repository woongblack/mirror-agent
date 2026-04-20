"""환경 변수 기반 설정.

.env 파일에서 값을 읽어 기본값과 함께 제공한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv 없어도 os.environ은 동작
    pass


@dataclass(frozen=True)
class Settings:
    """Mirror Agent 런타임 설정."""

    anthropic_api_key: str
    model_matcher: str
    model_generator: str
    model_defender: str
    match_confidence_threshold: float
    display_top_n: int

    @classmethod
    def from_env(cls) -> Settings:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 미설정. .env 파일 확인 또는 환경 변수 설정 필요."
            )

        return cls(
            anthropic_api_key=api_key,
            model_matcher=os.getenv(
                "MIRROR_MODEL_MATCHER", "claude-haiku-4-5-20251001"
            ),
            model_generator=os.getenv(
                "MIRROR_MODEL_GENERATOR", "claude-sonnet-4-6"
            ),
            model_defender=os.getenv(
                "MIRROR_MODEL_DEFENDER", "claude-sonnet-4-6"
            ),
            match_confidence_threshold=float(
                os.getenv("MIRROR_MATCH_CONFIDENCE_THRESHOLD", "0.7")
            ),
            display_top_n=int(os.getenv("MIRROR_DISPLAY_TOP_N", "3")),
        )


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RULES_DIR = DATA_DIR / "rules" / "manual-v0.1"
DEFENSE_PATTERNS_PATH = DATA_DIR / "defense-patterns" / "patterns.json"
REPORTS_DIR = DATA_DIR / "reports"
