
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class StrictInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class DocumentLookupInput(StrictInput):
    document_name: StrictStr = Field(
        min_length=1,
        max_length=120,
        description="Name of an approved document",
    )


class DocumentLookupOutput(BaseModel):
    document_name: str
    content: str
    size_bytes: int = Field(ge=0)
    run_id: str
