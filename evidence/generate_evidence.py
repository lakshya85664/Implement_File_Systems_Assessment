
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.document_tool import DocumentLookupTool
from src.observability import emit_event


WORKSPACE = PROJECT_ROOT / "workspace"
TRACE_DIR = PROJECT_ROOT / "traces"
EVIDENCE_DIR = PROJECT_ROOT / "evidence"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_case(
    case_id: str,
    tool: DocumentLookupTool,
    arguments: dict[str, Any],
    *,
    simulate_storage_failure: bool = False,
) -> dict[str, Any]:
    """Run the real tool and save metadata only, never document contents."""
    original_read_bytes = tool.adapter.read_bytes

    if simulate_storage_failure:
        def fail_read_bytes(relative_path: str, max_bytes: int) -> bytes:
            raise OSError("Simulated storage failure")

        tool.adapter.read_bytes = fail_read_bytes  # type: ignore[method-assign]

    started = time.perf_counter()
    try:
        result = tool.execute(arguments, run_id=case_id)
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        tool.adapter.read_bytes = original_read_bytes  # type: ignore[method-assign]

    status = result.status.value
    error_type = None
    if result.error:
        if status == "invalid":
            error_type = "validation_error"
        elif status == "denied":
            error_type = "access_denied"
        elif status == "not_found":
            error_type = "file_not_found"
        elif status == "review_required":
            error_type = "size_limit_exceeded"
        else:
            error_type = "storage_or_processing_error"

    event = emit_event(
        "document_lookup.completed",
        run_id=case_id,
        status=status,
        duration_ms=duration_ms,
        error_type=error_type,
    )

    # Intentionally exclude result.data: successful data contains file content.
    record = {
        "case_id": case_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tool": "document_lookup",
        "arguments": arguments,
        "status": status,
        "error": result.error,
        "duration_ms": duration_ms,
        "error_type": error_type,
        "output_content_recorded": False,
        "event": event,
    }
    write_json(TRACE_DIR / f"{case_id.lower()}.json", record)
    return record


def main() -> int:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # These names are explicitly allowlisted. A missing allowlisted file is
    # used to demonstrate safe not-found handling.
    allowed = {
        "guide.txt",
        "missing_demo.txt",
        "oversized_demo.txt",
    }
    normal_tool = DocumentLookupTool(
        workspace_root=WORKSPACE,
        allowed_documents=allowed,
        max_file_bytes=4096,
    )

    records: list[dict[str, Any]] = []

    records.append(
        run_case(
            "TC-EVIDENCE-01",
            normal_tool,
            {"document_name": "guide.txt"},
        )
    )
    records.append(
        run_case(
            "TC-EVIDENCE-02",
            normal_tool,
            {"document_name": 123},
        )
    )
    records.append(
        run_case(
            "TC-EVIDENCE-03",
            normal_tool,
            {"document_name": "secret.txt"},
        )
    )
    records.append(
        run_case(
            "TC-EVIDENCE-04",
            normal_tool,
            {"document_name": "missing_demo.txt"},
        )
    )

    # Create a temporary, harmless approved fixture to exercise the size limit.
    oversized_path = WORKSPACE / "approved" / "oversized_demo.txt"
    oversized_path.write_text("X" * 100, encoding="utf-8")
    try:
        small_limit_tool = DocumentLookupTool(
            workspace_root=WORKSPACE,
            allowed_documents=allowed,
            max_file_bytes=20,
        )
        records.append(
            run_case(
                "TC-EVIDENCE-05",
                small_limit_tool,
                {"document_name": "oversized_demo.txt"},
            )
        )
    finally:
        oversized_path.unlink(missing_ok=True)

    records.append(
        run_case(
            "TC-EVIDENCE-06",
            normal_tool,
            {"document_name": "guide.txt"},
            simulate_storage_failure=True,
        )
    )

    counts = Counter(record["status"] for record in records)
    durations = [record["duration_ms"] for record in records]
    metrics = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Local demonstration cases; not production performance benchmarks",
        "total_cases": len(records),
        "status_counts": dict(sorted(counts.items())),
        "average_duration_ms": round(sum(durations) / len(durations), 3),
        "maximum_duration_ms": round(max(durations), 3),
        "trace_files": [f"{record['case_id'].lower()}.json" for record in records],
        "content_logged": False,
    }
    write_json(EVIDENCE_DIR / "metrics_summary.json", metrics)

    # Capture the real pytest result, including its exit code.
    test_run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    test_results = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python -m pytest -q",
        "exit_code": test_run.returncode,
        "passed": test_run.returncode == 0,
        "stdout": test_run.stdout.strip(),
        "stderr": test_run.stderr.strip(),
    }
    write_json(EVIDENCE_DIR / "test_results.json", test_results)

    architecture = """flowchart TD
    A[Caller / Agent] --> B[DocumentLookupTool]
    B --> C[Pydantic Input Validation]
    C --> D{Approved Filename?}
    D -- No --> E[Safe Denied / Invalid Result]
    D -- Yes --> F[WorkspaceAdapter]
    F --> G[Resolved Path Containment Check]
    G --> H[Bounded Byte Read]
    H --> I[UTF-8 Decode and Output Contract]
    I --> J[Structured ToolResult]
    B --> K[Structured Observability Event]
    K --> L[Metadata-only Trace]
    J --> M[Caller]
"""
    (EVIDENCE_DIR / "architecture.mmd").write_text(
        architecture, encoding="utf-8"
    )

    summary = {
        "case_count": len(records),
        "statuses": dict(sorted(counts.items())),
        "pytest_exit_code": test_run.returncode,
        "pytest_passed": test_run.returncode == 0,
    }
    write_json(EVIDENCE_DIR / "evidence_summary.json", summary)

    print("Topic 10 — Task 5: Evidence Generation")
    print("=" * 48)
    print(f"Traces created: {len(records)}")
    for record in records:
        print(f"  {record['case_id']}: {record['status']}")
    print(f"Metrics: {EVIDENCE_DIR / 'metrics_summary.json'}")
    print(f"Test results: {EVIDENCE_DIR / 'test_results.json'}")
    print(f"Architecture: {EVIDENCE_DIR / 'architecture.mmd'}")
    print(f"Evidence summary: {EVIDENCE_DIR / 'evidence_summary.json'}")
    print()
    print("Pytest output:")
    print(test_run.stdout.strip() or "(no standard output)")
    if test_run.stderr.strip():
        print("Pytest stderr:")
        print(test_run.stderr.strip())

    return test_run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
