
from pathlib import Path

import pytest

from src.contracts import ToolStatus
from src.document_tool import DocumentLookupTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    approved = tmp_path / "approved"
    approved.mkdir()

    (approved / "guide.txt").write_text(
        "Approved evidence content",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def tool(workspace: Path) -> DocumentLookupTool:
    return DocumentLookupTool(
        workspace_root=workspace,
        allowed_documents={"guide.txt"},
        max_file_bytes=64,
    )


# TC-01: Valid request returns evidence-backed content.
def test_tc01_valid_request_returns_actual_file_content(tool):
    result = tool.execute(
        {"document_name": "guide.txt"},
        run_id="TC-01",
    )

    assert result.status == ToolStatus.OK
    assert result.data["content"] == "Approved evidence content"
    assert result.data["size_bytes"] == len(
        "Approved evidence content".encode("utf-8")
    )
    assert result.data["run_id"] == "TC-01"


# TC-02: Malformed input is rejected.
def test_tc02_malformed_input_is_rejected(tool):
    result = tool.execute(
        {
            "document_name": "guide.txt",
            "unexpected": "extra value",
        },
        run_id="TC-02",
    )

    assert result.status == ToolStatus.INVALID
    assert result.data == {}
    assert result.error == "Invalid document lookup request"


# TC-03: Unauthorized filename is denied without reading it.
def test_tc03_unauthorized_document_is_denied(tool, monkeypatch):
    def forbidden_read(*args, **kwargs):
        pytest.fail("Filesystem read should not occur for unauthorized names")

    monkeypatch.setattr(tool.adapter, "read_bytes", forbidden_read)

    result = tool.execute(
        {"document_name": "not-approved.txt"},
        run_id="TC-03",
    )

    assert result.status == ToolStatus.DENIED
    assert result.data == {}


# TC-04: Filesystem dependency failure returns a safe failure.
def test_tc04_filesystem_failure_is_safe(tool, monkeypatch):
    def failed_read(*args, **kwargs):
        raise OSError("Internal path and operating system details")

    monkeypatch.setattr(tool.adapter, "read_bytes", failed_read)

    result = tool.execute(
        {"document_name": "guide.txt"},
        run_id="TC-04",
    )

    assert result.status == ToolStatus.FAILED
    assert result.error == "Document storage is temporarily unavailable"
    assert "Internal path" not in str(result.data)
    assert "operating system details" not in str(result.data)


# TC-05: Exact size limit is accepted.
def test_tc05_file_at_size_limit_is_accepted(tmp_path: Path):
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "boundary.txt").write_bytes(b"A" * 8)

    boundary_tool = DocumentLookupTool(
        workspace_root=tmp_path,
        allowed_documents={"boundary.txt"},
        max_file_bytes=8,
    )

    result = boundary_tool.execute(
        {"document_name": "boundary.txt"},
        run_id="TC-05",
    )

    assert result.status == ToolStatus.OK
    assert result.data["size_bytes"] == 8


def test_tc05_oversized_file_is_rejected_without_content_leak(
    tmp_path: Path,
):
    approved = tmp_path / "approved"
    approved.mkdir()
    secret_content = "SENSITIVE-CONTENT-" * 10
    (approved / "large.txt").write_text(
        secret_content,
        encoding="utf-8",
    )

    limited_tool = DocumentLookupTool(
        workspace_root=tmp_path,
        allowed_documents={"large.txt"},
        max_file_bytes=16,
    )

    result = limited_tool.execute(
        {"document_name": "large.txt"},
        run_id="TC-05-LIMIT",
    )

    assert result.status == ToolStatus.REVIEW_REQUIRED
    assert secret_content not in str(result.data)
    assert secret_content not in str(result.error)
