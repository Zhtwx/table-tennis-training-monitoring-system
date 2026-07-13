from app import FITNESS_TESTS, INTENSITY_LABELS, TRAINING_SYNC_LOGS, app, build_fitness_summary
from tests.helpers import csrf_data

def test_fitness_summary_orders_players_by_score():
    records = []
    for index in range(6):
        score = 60 + index
        records.append(
            {
                "risk_label": "稳定",
                "test_date": f"2026-07-{index + 1:02d}",
                "fitness_score": score,
                "sprint_30m": score,
                "abdominal_endurance": score,
                "back_endurance": score,
                "lateral_slide": score,
                "a_footwork": score,
                "double_under": score,
                "seated_rotation_throw": score,
                "standing_long_jump": score,
                "plan_hours": 1.0,
                "player_name": f"队员{index + 1}",
            }
        )

    summary = build_fitness_summary(records)

    assert summary["player_names"][:5] == ["队员6", "队员5", "队员4", "队员3", "队员2"]
    assert summary["player_scores"][:5] == [65, 64, 63, 62, 61]
