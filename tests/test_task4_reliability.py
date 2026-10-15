
import json
import logging
from pathlib import Path

from src.contracts import ToolStatus
from src.document_tool import DocumentLookupTool
from src.observability import (
    OperationTimer,
    configure_logging,
    emit_event,
)


def test_structured_event_contains_required_fields(caplog):
    configure_logging()

    with caplog.at_level(logging.INFO, logger="document_lookup"):
        event = emit_event(
            "document_lookup",
            run_id="RUN-001",
            status="ok",
            duration_ms=12.34567,
        )

    assert event["event"] == "document_lookup"
    assert event["run_id"] == "RUN-001"
    assert event["status"] == "ok"
    assert event["duration_ms"] == 12.346

    captured = json.loads(caplog.records[-1].message)
    assert captured["run_id"] == "RUN-001"


def test_event_records_error_classification(caplog):
    configure_logging()

    with caplog.at_level(logging.INFO, logger="document_lookup"):
        event = emit_event(
            "document_lookup",
            run_id="RUN-002",
            status="failed",
            error_type="OSError",
        )

    assert event["error_type"] == "OSError"


def test_event_does_not_log_file_content(caplog):
    configure_logging()

    with caplog.at_level(logging.INFO, logger="document_lookup"):
        emit_event(
            "document_lookup",
            run_id="RUN-003",
            status="ok",
        )

    message = caplog.records[-1].message
    assert "SENSITIVE-CONTENT" not in message
    assert "secret.txt" not in message


def test_operation_timer_measures_nonnegative_duration():
    with OperationTimer() as timer:
        sum(range(1000))

    assert timer.duration_ms >= 0


def test_repeated_lookup_returns_same_content(tmp_path: Path):
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "guide.txt").write_text(
        "Stable document",
        encoding="utf-8",
    )

    tool = DocumentLookupTool(
        workspace_root=tmp_path,
        allowed_documents={"guide.txt"},
        max_file_bytes=64,
    )

    first = tool.execute(
        {"document_name": "guide.txt"},
        run_id="RUN-FIRST",
    )
    second = tool.execute(
        {"document_name": "guide.txt"},
        run_id="RUN-SECOND",
    )

    assert first.status == ToolStatus.OK
    assert second.status == ToolStatus.OK
    assert first.data["content"] == second.data["content"]
    assert first.run_id != second.run_id


def test_filesystem_failure_does_not_leak_internal_details(
    tmp_path: Path,
    monkeypatch,
):
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "guide.txt").write_text("Safe content", encoding="utf-8")

    tool = DocumentLookupTool(
        workspace_root=tmp_path,
        allowed_documents={"guide.txt"},
    )

    def fail_read(*args, **kwargs):
        raise OSError("C:\\internal\\sensitive\\path")

    monkeypatch.setattr(tool.adapter, "read_bytes", fail_read)

    result = tool.execute({"document_name": "guide.txt"})

    assert result.status == ToolStatus.FAILED
    assert "sensitive" not in str(result.error).lower()
    assert "sensitive" not in str(result.data).lower()
