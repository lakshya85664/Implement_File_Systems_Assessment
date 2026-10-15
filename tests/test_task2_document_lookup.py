from pathlib import Path

import pytest

from src.contracts import ToolStatus
from src.document_tool import DocumentLookupTool


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    approved = tmp_path / "approved"
    private = tmp_path / "private"
    approved.mkdir()
    private.mkdir()

    (approved / "guide.txt").write_text(
        "Approved guide content",
        encoding="utf-8",
    )
    (private / "secret.txt").write_text(
        "Private secret content",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def tool(workspace: Path) -> DocumentLookupTool:
    return DocumentLookupTool(
        workspace_root=workspace,
        allowed_documents={"guide.txt", "missing.txt", "large.txt"},
        max_file_bytes=64,
    )


def test_valid_request_reads_approved_document(tool):
    result = tool.execute(
        {"document_name": "guide.txt"},
        run_id="RUN-TC01",
    )

    assert result.status == ToolStatus.OK
    assert result.data["content"] == "Approved guide content"
    assert result.data["document_name"] == "guide.txt"
    assert result.data["run_id"] == "RUN-TC01"


def test_unknown_document_is_denied(tool):
    result = tool.execute({"document_name": "secret.txt"})

    assert result.status == ToolStatus.DENIED
    assert "Private secret content" not in str(result.data)


@pytest.mark.parametrize(
    "name",
    [
        "../private/secret.txt",
        "..\\private\\secret.txt",
        "subfolder/guide.txt",
        "C:\\Windows\\win.ini",
    ],
)
def test_path_traversal_and_absolute_paths_are_denied(tool, name):
    result = tool.execute({"document_name": name})

    assert result.status == ToolStatus.DENIED


def test_malformed_request_is_rejected(tool):
    result = tool.execute(
        {"document_name": "guide.txt", "extra": "unexpected"}
    )

    assert result.status == ToolStatus.INVALID


def test_missing_approved_file_returns_safe_not_found(tool):
    result = tool.execute({"document_name": "missing.txt"})

    assert result.status == ToolStatus.NOT_FOUND
    assert "Traceback" not in str(result.data)


def test_oversized_file_is_not_returned(tool, workspace):
    (workspace / "approved" / "large.txt").write_text(
        "X" * 65,
        encoding="utf-8",
    )

    result = tool.execute({"document_name": "large.txt"})

    assert result.status == ToolStatus.REVIEW_REQUIRED
    assert "X" * 65 not in str(result.data)


def test_private_file_is_not_read_or_exposed(tool):
    result = tool.execute({"document_name": "secret.txt"})

    assert result.status == ToolStatus.DENIED
    assert "Private secret content" not in str(result.data)
