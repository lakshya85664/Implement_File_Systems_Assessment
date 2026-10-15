# Topic 10 — Implement File Systems Assessment

## Project Overview
This project implements a controlled document-lookup tool for an agent/tool-calling workflow. It reads explicitly allowlisted filenames from an approved workspace, validates input, restricts resolved paths to the workspace, limits file reads, and returns structured results.

## Learning Objectives
- Define typed tool contracts and strict input/output schemas.
- Reject malformed requests and unexpected arguments.
- Restrict access to approved documents in a controlled workspace.
- Prevent absolute-path and path-traversal access.
- Bound file reads and handle missing, oversized, unreadable, or unsupported-encoding documents safely.
- Record operational metadata without logging document contents.
- Verify behavior with automated tests and evidence traces.

## Project Structure
```text
Implement_File_Systems_Assessment/
├── src/
│   ├── contracts.py
│   ├── schemas.py
│   ├── filesystem_adapter.py
│   ├── document_tool.py
│   └── observability.py
├── tests/
│   ├── test_task1_contracts.py
│   ├── test_task2_document_lookup.py
│   ├── test_task3_mandatory.py
│   └── test_task4_reliability.py
├── workspace/approved/guide.txt
├── workspace/private/secret.txt
├── traces/
└── evidence/
    ├── generate_evidence.py
    ├── metrics_summary.json
    ├── test_results.json
    ├── evidence_summary.json
    └── architecture.mmd
```

## Implementation Details

### 1. Typed Contracts and Validation
`contracts.py` defines tool status values and structured call/result dataclasses. `schemas.py` uses Pydantic to validate the document name and define output fields. Extra input fields are forbidden, and the document name must be a strict string.

### 2. Controlled Filesystem Access
`filesystem_adapter.py` resolves requested paths against a configured workspace root and verifies that the resolved path remains inside that root. It rejects absolute paths, paths outside the workspace, and non-files. Reads are capped at a configured byte limit.

### 3. Document Lookup Tool
`document_tool.py` accepts an allowlist of filenames and rejects unapproved names before reading. It maps common failures to explicit statuses: `ok`, `invalid`, `denied`, `not_found`, `failed`, and `review_required`. Successful output includes the document name, content, byte size, and run ID.

### 4. Reliability and Observability
`observability.py` provides structured JSON events and an operation timer. Evidence traces record request metadata, status, timing, and error classification. The evidence generator deliberately excludes returned result data from trace records so document contents are not copied into traces.

## How to Run
Run these commands from the project root with the virtual environment activated:

```cmd
python -m pytest -q
python evidence\generate_evidence.py
```

The test suite covers contracts, normal lookup behavior, access restrictions, mandatory security/failure cases, and reliability. The evidence generator creates six local demonstration traces, a metrics summary, a test-results record, an evidence summary, and a Mermaid architecture diagram.

## Verification Results
- Full automated test suite: **29 passed**.
- Evidence scenarios: **6 generated**.
- Demonstrated statuses: `ok`, `invalid`, `denied`, `not_found`, `review_required`, and `failed`.
- Test command recorded by the generator: `python -m pytest -q`.

These results represent a local demonstration, not a production load or performance benchmark. The storage failure is deliberately simulated to exercise safe failure handling.

## Security Considerations
- Only explicitly allowlisted document names are eligible for lookup.
- Absolute paths and path traversal are rejected.
- Resolved paths are checked against the workspace root.
- Reads are bounded to avoid unbounded file loading.
- Trace records omit returned document content.
- Caller-facing errors are concise and do not expose private fixture content.

## Reflection (Approximately 300 Words)
Building this assessment helped me connect tool-calling concepts with practical filesystem security. A document lookup tool may appear simple, but it creates a boundary between an agent's request and the local environment. The implementation therefore needs more than a file read: it needs a strict contract, input validation, an allowlist, path containment checks, bounded reads, and predictable error handling.

The typed contracts and Pydantic schemas make the interface explicit. Rejecting extra fields and non-string document names reduces ambiguity before a filesystem operation begins. The allowlist adds a separate authorization check, so a validly formatted filename is not automatically an authorized request. The filesystem adapter then resolves paths and checks that they remain under the configured workspace. These controls work together rather than relying on a single filename check.

I also learned that failure behavior is part of the tool's interface. Missing files, unauthorized requests, oversized documents, and storage errors should not all look like successful empty responses. Distinct status values make the outcome easier for a caller to interpret and allow tests to verify each branch. The automated suite covers contracts, normal lookup, boundary cases, and safe failure behavior; the final run completed with 29 passing tests.

The evidence-generation step adds an operational perspective. Six representative scenarios are recorded with status, timing, and error classification. The traces intentionally omit result data, because successful results contain document text and traces should not become another place where private content is stored. The metrics demonstrate this local run, but should not be treated as production performance measurements.

If I extended this project, I would add stronger race-condition protections around filesystem operations, more platform-specific symlink tests, configurable structured logging, and tests for unusual encodings and permissions. I would also integrate the tool into a small agent loop with explicit policy checks and approval gates for any future write-capable operations. The key lesson is that safe tools need clear contracts, least-privilege access, observable outcomes, and tests for both expected and adversarial inputs.
