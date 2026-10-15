
import pytest
from pydantic import ValidationError

from src.contracts import ToolCall, ToolResult, ToolSpec, ToolStatus
from src.schemas import DocumentLookupInput, DocumentLookupOutput


def test_document_lookup_input_accepts_valid_name():
    request = DocumentLookupInput(document_name="guide.txt")
    assert request.document_name == "guide.txt"


def test_document_lookup_rejects_empty_name():
    with pytest.raises(ValidationError):
        DocumentLookupInput(document_name="")


def test_document_lookup_rejects_extra_fields():
    with pytest.raises(ValidationError):
        DocumentLookupInput(
            document_name="guide.txt",
            workspace="C:/",
        )


def test_document_lookup_rejects_non_string_name():
    with pytest.raises(ValidationError):
        DocumentLookupInput(document_name=123)


def test_document_lookup_output_accepts_valid_result():
    result = DocumentLookupOutput(
        document_name="guide.txt",
        content="Example document",
        size_bytes=16,
        run_id="RUN-001",
    )
    assert result.size_bytes == 16


def test_document_lookup_output_rejects_negative_size():
    with pytest.raises(ValidationError):
        DocumentLookupOutput(
            document_name="guide.txt",
            content="Example",
            size_bytes=-1,
            run_id="RUN-001",
        )


def test_tool_contract_objects():
    spec = ToolSpec(
        name="document_lookup",
        version="1.0",
        description="Read an approved workspace document",
        max_output_bytes=4096,
    )
    call = ToolCall(
        run_id="RUN-001",
        tool_name="document_lookup",
        arguments={"document_name": "guide.txt"},
    )
    result = ToolResult(
        run_id=call.run_id,
        status=ToolStatus.OK,
    )

    assert spec.name == call.tool_name
    assert result.status == ToolStatus.OK
