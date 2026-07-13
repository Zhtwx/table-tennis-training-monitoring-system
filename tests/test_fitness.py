from app import build_fitness_summary


def test_fitness_score_chart_limits_to_top_five_players():
    records = []
    for index in range(6):
        score = 60 + index
        records.append(
            {
                "risk_label": "稳定",
                "test_date": f"2026-07-{index + 1:02d}",
                "fitness_score": score,
                "speed": score,
                "plan_hours": 1.0,
                "player_name": f"队员{index + 1}",
            }
        )

    summary = build_fitness_summary(records)

    assert summary["player_names"] == ["队员6", "队员5", "队员4", "队员3", "队员2"]
    assert summary["player_scores"] == [65, 64, 63, 62, 61]
