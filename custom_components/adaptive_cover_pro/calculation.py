"""Cover-geometry re-exports for backward compatibility.

Geometry classes live in engine/covers/:
  AdaptiveGeneralCover  → engine/covers/base.py
  AdaptiveVerticalCover → engine/covers/vertical.py
  AdaptiveHorizontalCover → engine/covers/horizontal.py
  AdaptiveTiltCover     → engine/covers/tilt.py

Re-exported here for backward compatibility with existing consumers.
"""

from __future__ import annotations

from .engine.covers import (
    AdaptiveGeneralCover,
    AdaptiveHorizontalCover,
    AdaptiveTiltCover,
    AdaptiveVerticalCover,
)

__all__ = [
    "AdaptiveGeneralCover",
    "AdaptiveHorizontalCover",
    "AdaptiveTiltCover",
    "AdaptiveVerticalCover",
]
