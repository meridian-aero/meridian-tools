"""Tests for the analysis database."""

from __future__ import annotations

from hangar.omd.db import (
    init_analysis_db,
    record_entity,
    record_activity,
    add_prov_edge,
    record_run_case,
    record_run_cases_batch,
    query_run_results,
    query_provenance_dag,
    query_entity,
)


def test_init_creates_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_analysis_db(db_path)
    assert db_path.exists()


def test_record_and_query_entity(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    record_entity(
        entity_id="plan-test/v1",
        entity_type="plan",
        created_by="test",
        plan_id="plan-test",
        version=1,
        content_hash="abc123",
    )

    entity = query_entity("plan-test/v1")
    assert entity is not None
    assert entity["entity_type"] == "plan"
    assert entity["version"] == 1
    assert entity["content_hash"] == "abc123"


def test_record_activity(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    record_activity(
        activity_id="act-draft-001",
        activity_type="draft",
        agent="test",
        status="completed",
    )
    # No query function for activities yet, but should not raise
    # We can verify via provenance DAG


def test_add_prov_edge(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    record_entity("plan-test/v1", "plan", "test", plan_id="plan-test")
    record_activity("act-001", "draft", "test")
    add_prov_edge("wasGeneratedBy", "plan-test/v1", "act-001")


def test_record_and_query_run_cases(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    record_entity("run-001", "run_record", "omd", plan_id="plan-test")

    record_run_case("run-001", 0, "driver", {"x": 1.0, "y": 2.0})
    record_run_case("run-001", 1, "driver", {"x": 1.5, "y": 1.8})
    record_run_case("run-001", 2, "final", {"x": 2.0, "y": 1.5})

    results = query_run_results("run-001")
    assert len(results) == 3
    assert results[0]["iteration"] == 0
    assert results[0]["data"]["x"] == 1.0
    assert results[2]["case_type"] == "final"


def test_query_run_results_with_variable_filter(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    record_run_case("run-002", 0, "final", {"x": 1.0, "y": 2.0, "z": 3.0})

    results = query_run_results("run-002", variables=["x", "z"])
    assert len(results) == 1
    assert set(results[0]["data"].keys()) == {"x", "z"}


def test_record_run_cases_batch(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    cases = [
        {"iteration": 0, "case_type": "driver", "data": {"x": 1.0}},
        {"iteration": 1, "case_type": "driver", "data": {"x": 2.0}},
        {"iteration": 2, "case_type": "final", "data": {"x": 3.0}},
    ]
    record_run_cases_batch("run-003", cases)

    results = query_run_results("run-003")
    assert len(results) == 3


def test_query_provenance_dag(tmp_path):
    init_analysis_db(tmp_path / "test.db")

    # Create a simple DAG: plan -> execute -> run_record
    record_entity("plan-dag/v1", "plan", "have-agent", plan_id="plan-dag", version=1)
    record_activity("act-exec-001", "execute", "omd")
    record_entity("run-dag-001", "run_record", "omd", plan_id="plan-dag")

    add_prov_edge("used", "act-exec-001", "plan-dag/v1")
    add_prov_edge("wasGeneratedBy", "run-dag-001", "act-exec-001")

    dag = query_provenance_dag("plan-dag")
    assert len(dag["entities"]) == 2
    assert len(dag["activities"]) == 1
    assert len(dag["edges"]) == 2


def test_query_empty_provenance(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    dag = query_provenance_dag("nonexistent")
    assert dag["entities"] == []
    assert dag["activities"] == []
    assert dag["edges"] == []
