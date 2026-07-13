# Athlete Primary Coach Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store a validated primary coach on every athlete and make the SQL schema enforce the relationship.

**Architecture:** `athlete.coach_id` is the authoritative affiliation field. Flask validation resolves the selected coach from `COACHES` and derives the display name, while the schema uses an index and a restrictive foreign key to protect persisted data.

**Tech Stack:** Flask, in-memory demo data, MySQL DDL, pytest.

---

### Task 1: Cover the in-memory affiliation invariant

**Files:**
- Modify: `C:\Users\ztwx4\Desktop\乒乓球运动员综合训练监控管理系统\tests\test_players.py`
- Modify: `C:\Users\ztwx4\Desktop\乒乓球运动员综合训练监控管理系统\app.py`

- [ ] **Step 1: Write a failing test**

```python
def test_player_rejects_unknown_primary_coach():
    client = app.test_client()
    login(client)
    response = client.post(
        "/players/create",
        data=csrf_data(client, player_payload(coach_id="999")),
        follow_redirects=True,
    )
    assert "所属教练不存在" in response.get_data(as_text=True)
```

- [ ] **Step 2: Run the targeted test**

Run: `pytest tests/test_players.py::test_player_rejects_unknown_primary_coach -q`

Expected: FAIL until the validation message is added.

- [ ] **Step 3: Implement the minimum validation**

```python
coach = next((item for item in COACHES if item["id"] == coach_id), None)
if not coach:
    raise ValidationError("所属教练不存在。")
```

Use the resolved `coach` to populate `coach_id` and `coach_name` in the returned player dictionary.

- [ ] **Step 4: Run targeted player tests**

Run: `pytest tests/test_players.py -q`

Expected: PASS.

### Task 2: Persist the affiliation in the schema

**Files:**
- Modify: `C:\Users\ztwx4\Desktop\乒乓球运动员综合训练监控管理系统\sql\pingpang_db.sql`
- Test: `C:\Users\ztwx4\Desktop\乒乓球运动员综合训练监控管理系统\tests\test_delivery_quality.py`

- [ ] **Step 1: Add a failing schema assertion**

```python
def test_schema_defines_primary_coach_relation():
    schema = Path("sql/pingpang_db.sql").read_text(encoding="utf-8")
    assert "primary_coach_id" in schema
    assert "FOREIGN KEY (primary_coach_id) REFERENCES coach(id)" in schema
```

- [ ] **Step 2: Run the schema assertion**

Run: `pytest tests/test_delivery_quality.py::test_schema_defines_primary_coach_relation -q`

Expected: FAIL until the column and foreign key are present.

- [ ] **Step 3: Add the column and relation**

```sql
primary_coach_id INT NULL,
INDEX idx_athlete_primary_coach (primary_coach_id),
CONSTRAINT fk_athlete_primary_coach
    FOREIGN KEY (primary_coach_id) REFERENCES coach(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
```

Place the foreign key after the `coach` table definition or create it with `ALTER TABLE athlete` after both tables exist. Update the seed `INSERT INTO athlete` values to provide matching coach IDs.

- [ ] **Step 4: Run all data-layer tests**

Run: `pytest tests/test_players.py tests/test_delivery_quality.py -q`

Expected: PASS.
