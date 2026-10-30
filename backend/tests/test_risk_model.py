from app.models.risk_model import RiskEngine
from app.utils.geometry import DIR_APPROACHING, DIR_INSIDE, DIR_MOVING_AWAY


def test_risk_calculation_low() -> None:
    engine = RiskEngine()
    # Deer far away from boundary, moving away, slow
    assessment = engine.calculate_risk(
        species="deer",
        species_confidence=0.85,
        detection_confidence=0.90,
        distance_px=350.0,
        is_inside_farm=False,
        direction=DIR_MOVING_AWAY,
        average_speed_px_sec=5.0,
        duration_seconds=3.0,
        behavior="WALKING",
    )
    assert 0 <= assessment.risk_score <= 25
    assert assessment.risk_level == "LOW"
    assert len(assessment.factors) > 0


def test_risk_calculation_high_and_critical() -> None:
    engine = RiskEngine()
    # Elephant very close to boundary, approaching rapidly, high persistence
    assessment = engine.calculate_risk(
        species="elephant",
        species_confidence=0.92,
        detection_confidence=0.95,
        distance_px=30.0,
        is_inside_farm=False,
        direction=DIR_APPROACHING,
        average_speed_px_sec=45.0,
        duration_seconds=20.0,
        behavior="POSSIBLE RAPID APPROACH",
    )
    assert assessment.risk_score > 75
    assert assessment.risk_level in ("HIGH", "CRITICAL")
    assert any("elephant" in f.lower() for f in assessment.factors)
    assert any("proximity" in f.lower() for f in assessment.factors)
    assert any("approach" in f.lower() for f in assessment.factors)


def test_risk_inside_farm_boosts_score() -> None:
    engine = RiskEngine()
    assessment = engine.calculate_risk(
        species="wild_boar",
        species_confidence=0.85,
        detection_confidence=0.90,
        distance_px=0.0,
        is_inside_farm=True,
        direction=DIR_INSIDE,
        average_speed_px_sec=25.0,
        duration_seconds=10.0,
        behavior="APPROACHING",
    )
    assert assessment.is_inside_farm is True
    assert assessment.risk_score >= 50
    assert any("inside" in f.lower() for f in assessment.factors)
