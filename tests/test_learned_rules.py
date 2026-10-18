from sthira import api, store
from sthira.models import Entry, SourceRef


def _e(statement):
    return Entry(id=store.new_id("e"), kind="decision", title=statement[:20], statement=statement, status="proposed",
                 trust="quarantined", recorded_at=store.now(), source=SourceRef(id="s", type="chatgpt"))


def test_learned_rules_dedupes_and_counts(tmp_path):
    con = store.connect(tmp_path / "t.db")
    a, b = store.insert_entry(con, _e("Kitten is named Miso")), store.insert_entry(con, _e("Trip to Coorg"))
    api.review(a.id, "reject", "Personal life is not a project decision.", con=con)
    api.review(b.id, "reject", "Personal life is not a project decision.", con=con)
    api.correct_check("Add a Redis cache", "A cache in front of a store doesn't change the store.", con=con)
    rules = api.learned_rules(con=con)
    assert [r["applies_to"] for r in rules] == ["contradiction checks", "extraction"]
    assert rules[1]["examples"] == 2 and rules[1]["rule"] == "Personal life is not a project decision."
