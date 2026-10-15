
from __future__ import annotations

from pathlib import Path


class WorkspaceAdapter:
    """Filesystem boundary for reading files within a controlled root."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve(strict=True)

        if not self.workspace_root.is_dir():
            raise ValueError("Workspace root must be a directory")

    def resolve_file(self, relative_path: str) -> Path:
        """Resolve a relative path and reject paths outside the workspace."""
        requested = Path(relative_path)

        if requested.is_absolute():
            raise PermissionError("Absolute paths are not permitted")

        candidate = (self.workspace_root / requested).resolve(strict=True)

        try:
            candidate.relative_to(self.workspace_root)
        except ValueError as exc:
            raise PermissionError("Path is outside the workspace") from exc

        if not candidate.is_file():
            raise FileNotFoundError("Document was not found")

        return candidate

    def read_bytes(self, relative_path: str, max_bytes: int) -> bytes:
        """Read at most max_bytes plus one byte to detect oversized files."""
        path = self.resolve_file(relative_path)

        with path.open("rb") as file:
            content = file.read(max_bytes + 1)

        if len(content) > max_bytes:
            raise ValueError("Document exceeds the configured size limit")

        return content
