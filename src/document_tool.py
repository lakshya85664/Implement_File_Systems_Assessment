
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.contracts import ToolResult, ToolStatus
from src.filesystem_adapter import WorkspaceAdapter
from src.schemas import DocumentLookupInput, DocumentLookupOutput


class DocumentLookupTool:
    """Read only approved documents through a controlled adapter."""

    def __init__(
        self,
        workspace_root: str | Path,
        allowed_documents: set[str] | frozenset[str],
        max_file_bytes: int = 4096,
    ) -> None:
        if max_file_bytes < 1:
            raise ValueError("max_file_bytes must be positive")

        self.adapter = WorkspaceAdapter(workspace_root)
        self.allowed_documents = frozenset(allowed_documents)
        self.max_file_bytes = max_file_bytes

    def execute(self, arguments: dict[str, Any], run_id: str | None = None) -> ToolResult:
        actual_run_id = run_id or f"RUN-{uuid.uuid4().hex[:12].upper()}"

        try:
            request = DocumentLookupInput.model_validate(arguments)
        except ValidationError:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.INVALID,
                error="Invalid document lookup request",
            )

        document_name = request.document_name

        # The interface accepts a simple filename, not a path.
        if (
            document_name in {".", ".."}
            or "/" in document_name
            or "\\" in document_name
            or Path(document_name).is_absolute()
            or ":" in document_name
        ):
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.DENIED,
                error="Document name is not permitted",
            )

        # Check the allowlist before touching the filesystem.
        if document_name not in self.allowed_documents:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.DENIED,
                error="Document is not approved for lookup",
            )

        relative_path = f"approved/{document_name}"

        try:
            content_bytes = self.adapter.read_bytes(
                relative_path,
                self.max_file_bytes,
            )
        except FileNotFoundError:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.NOT_FOUND,
                error="Approved document was not found",
            )
        except PermissionError:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.DENIED,
                error="Document access was denied",
            )
        except ValueError:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.REVIEW_REQUIRED,
                error="Document exceeds the configured size limit",
            )
        except OSError:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.FAILED,
                error="Document storage is temporarily unavailable",
            )

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return ToolResult(
                run_id=actual_run_id,
                status=ToolStatus.FAILED,
                error="Document encoding is not supported",
            )

        output = DocumentLookupOutput(
            document_name=document_name,
            content=content,
            size_bytes=len(content_bytes),
            run_id=actual_run_id,
        )

        return ToolResult(
            run_id=actual_run_id,
            status=ToolStatus.OK,
            data=output.model_dump(),
        )
