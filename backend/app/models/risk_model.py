from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Sequence

from app.core.config import get_settings
from app.utils.geometry import DIR_APPROACHING, DIR_INSIDE, DIR_MOVING_AWAY, DIR_PARALLEL, DIR_STATIONARY
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Base encounter sensitivity by species (purely for agricultural encounter risk estimation)
SPECIES_SENSITIVITY_SCORES = {
    "elephant": 24,
    "tiger": 24,
    "leopard": 22,
    "wild_boar": 18,
    "bison": 18,
    "bear": 18,
    "deer": 10,
    "monkey": 9,
    "cattle": 7,
    "unknown": 10,
}


@dataclass
class RiskAssessment:
    risk_score: int                 # 0 to 100
    risk_level: str                 # "LOW", "MODERATE", "HIGH", "CRITICAL"
    factors: list[str]              # Transparent list of evidence reasons
    confidence: float               # 0.0 to 1.0 overall assessment confidence
    species: str
    behavior: str
    direction: str
    distance_image_space: float
    is_inside_farm: bool


class BaseRiskEngine(abc.ABC):
    @abc.abstractmethod
    def calculate_risk(
        self,
        species: str,
        species_confidence: float,
        detection_confidence: float,
        distance_px: float,
        is_inside_farm: bool,
        direction: str,
        average_speed_px_sec: float,
        duration_seconds: float,
        behavior: str,
    ) -> RiskAssessment:
        """Calculate encounter-risk assessment from observable inputs."""
        pass


class RiskEngine(BaseRiskEngine):
    """
    Configurable encounter-risk assessment engine.
    Computes a 0–100 score based on 5 transparent, observable physical factors:
    1. Species base sensitivity (0-25)
    2. Boundary proximity & inside status (0-30)
    3. Movement approach direction (0-20)
    4. Observable movement speed (0-15)
    5. Presence persistence over time (0-10)
    """

    def __init__(
        self,
        low_max: int | None = None,
        moderate_max: int | None = None,
        high_max: int | None = None,
    ) -> None:
        settings = get_settings()
        self.low_max = low_max or settings.risk_low_max
        self.moderate_max = moderate_max or settings.risk_moderate_max
        self.high_max = high_max or settings.risk_high_max

    def calculate_risk(
        self,
        species: str,
        species_confidence: float,
        detection_confidence: float,
        distance_px: float,
        is_inside_farm: bool,
        direction: str,
        average_speed_px_sec: float,
        duration_seconds: float,
        behavior: str,
    ) -> RiskAssessment:
        factors: list[str] = []
        raw_score = 0.0

        canonical_species = (species or "unknown").lower()
        base_species_score = SPECIES_SENSITIVITY_SCORES.get(canonical_species, 10)
        # Scale species factor by classifier certainty
        species_pts = base_species_score * max(0.6, species_confidence)
        raw_score += species_pts
        if base_species_score >= 18:
            factors.append(f"Identified high-impact species: {species.replace('_', ' ').title()} ({species_pts:.0f} pts)")
        elif canonical_species != "unknown":
            factors.append(f"Identified species: {species.replace('_', ' ').title()} ({species_pts:.0f} pts)")

        # 2. Proximity factor (0-30)
        if is_inside_farm:
            raw_score += 30.0
            factors.append("Animal is located INSIDE the farm boundary (+30 pts)")
        elif distance_px < 60.0:
            raw_score += 26.0
            factors.append(f"Immediate proximity to farm boundary: {distance_px:.1f} px (+26 pts)")
        elif distance_px < 150.0:
            raw_score += 18.0
            factors.append(f"Close proximity to farm boundary: {distance_px:.1f} px (+18 pts)")
        elif distance_px < 300.0:
            raw_score += 10.0
            factors.append(f"Moderate distance from boundary: {distance_px:.1f} px (+10 pts)")
        else:
            raw_score += 3.0
            factors.append(f"Distant from boundary: {distance_px:.1f} px (+3 pts)")

        # 3. Approach factor (0-20)
        if direction == DIR_APPROACHING:
            raw_score += 20.0
            factors.append("Trajectory vector is actively approaching farm boundary (+20 pts)")
        elif is_inside_farm:
            raw_score += 14.0
            factors.append("Active movement within farm premises (+14 pts)")
        elif direction == DIR_PARALLEL:
            raw_score += 8.0
            factors.append("Moving along farm perimeter (+8 pts)")
        elif direction == DIR_STATIONARY:
            raw_score += 4.0
            factors.append("Stationary posture near boundary (+4 pts)")
        elif direction == DIR_MOVING_AWAY:
            raw_score = max(0.0, raw_score - 5.0)
            factors.append("Trajectory moving away from farm boundary (-5 pts)")

        # 4. Movement speed factor (0-15)
        if average_speed_px_sec >= 40.0 or "RAPID" in behavior:
            raw_score += 15.0
            factors.append(f"Elevated movement speed ({average_speed_px_sec:.1f} px/s) (+15 pts)")
        elif average_speed_px_sec >= 18.0:
            raw_score += 10.0
            factors.append(f"Moderate movement speed ({average_speed_px_sec:.1f} px/s) (+10 pts)")
        elif average_speed_px_sec >= 6.0:
            raw_score += 5.0
        else:
            raw_score += 1.0

        # 5. Persistence factor (0-10)
        if duration_seconds >= 15.0:
            raw_score += 10.0
            factors.append(f"Sustained presence ({duration_seconds:.1f}s persistence) (+10 pts)")
        elif duration_seconds >= 5.0:
            raw_score += 6.0
            factors.append(f"Observable presence over {duration_seconds:.1f}s (+6 pts)")
        else:
            raw_score += 2.0

        # Normalize score to [0, 100]
        final_score = int(round(max(0.0, min(100.0, raw_score))))

        # Determine risk level based on configurable thresholds
        if final_score <= self.low_max:
            level = "LOW"
        elif final_score <= self.moderate_max:
            level = "MODERATE"
        elif final_score <= self.high_max:
            level = "HIGH"
        else:
            level = "CRITICAL"

        # Overall confidence combining detection & species certainty
        combined_confidence = round(0.5 * detection_confidence + 0.5 * species_confidence, 2)

        return RiskAssessment(
            risk_score=final_score,
            risk_level=level,
            factors=factors,
            confidence=combined_confidence,
            species=species,
            behavior=behavior,
            direction=direction,
            distance_image_space=round(distance_px, 1),
            is_inside_farm=is_inside_farm,
        )


def get_risk_engine() -> BaseRiskEngine:
    return RiskEngine()
