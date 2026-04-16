---
name: rail-doc-reviewer
description: Structured review and summarisation of ETCS / rail signalling project documents for the Downer QTMP project.
---

# Rail Document Reviewer Skill

## Purpose

This skill provides a repeatable, structured process for reviewing rail signalling project documents. It is designed for an ETCS/RCS Interface Manager working across construct, test, and commission phases.

The skill:
1. Extracts raw text from PDFs, DOCX, and XLSX files via Python scripts.
2. Classifies each document into a taxonomy.
3. Produces a structured summary using category-specific extraction templates.
4. Maintains a persistent document register for cross-referencing and follow-up queries.

---

## Document Classification Taxonomy

When reviewing a document, classify it into ONE of the following categories:

| Tag | Category | Trigger Keywords / Patterns |
|---|---|---|
| `ICD` | Interface Control Document | "interface control", "ICD", interface schedules |
| `CONOPS` | Concept of Operations | "concept of operations", "ConOps", operational modes |
| `TEST` | Testing & Commissioning | "testing requirements", "test schedule", "commissioning" |
| `PERF` | Performance Specification | "performance specification", KPIs, thresholds |
| `ASSURANCE` | Assurance / Safety Plan | "assurance plan", "AS plan", "safety case", EN 50126/28/29 |
| `DESIGN` | Design Process / Review | "design process", "review procedures", design gates |
| `GSS` | General Signalling Specification | "GSS", "general signalling", departures, amendments |
| `RIM` | Rail Infrastructure Manager | "RIM", "boundaries", "handover", "fencing" |
| `DRAWING` | Layout / Arrangement Drawing | "DRG", "arrangement", "layout", schematic references |
| `CONTRACT` | Contractual Schedule | "schedule", "execution version", contractual obligations |
| `OPTION` | Design Option / Variant | "option", design variant, value engineering |

---

## Extraction Templates

### Common Header (all documents)

Extract these fields for EVERY document:

```
DOCUMENT METADATA
  Title:
  Document Number:
  Revision:
  Status: [Draft / Approved / For Review / Execution Version]
  Date:
  Author / Organisation:
  Classification Tag:
  Source File:
```

### ICD — Interface Control Document

```
INTERFACE SUMMARY
  Interface Parties: [System A] <-> [System B]
  Interface Description:
  Protocol / Data Format:
  Physical / Logical: [Physical / Logical / Both]

CHANGE HISTORY
  Current Revision:
  Key Changes from Previous:

OPEN ITEMS
  Open Actions / TBDs:
  Dependencies on Other ICDs:

COMPLIANCE
  Standards Referenced:
  GSS Alignment:
```

### CONOPS — Concept of Operations

```
OPERATIONAL CONCEPT
  System Scope:
  Operational Modes: [list all]
  Degraded Modes: [list all]
  Transitions Between Modes:

STAKEHOLDERS
  Key Parties:
  Roles and Responsibilities:

SYSTEM BOUNDARIES
  Geographic Scope:
  Interface Boundaries:

SAFETY / RISK
  Key Hazards Identified:
  Mitigations:
  Open Safety Items:
```

### TEST — Testing & Commissioning

```
TEST SCOPE
  Test Types: [GSFT / SIT / NIT / System Commissioning / Other]
  Test Phases:

PREREQUISITES
  Entry Criteria:
  Required Documentation:
  Required Approvals:

EXECUTION
  Pass / Fail Criteria:
  Witness Requirements:
  Re-test Provisions:

SCHEDULE
  Key Milestones:
  Dependencies:
```

### PERF — Performance Specification

```
PERFORMANCE REQUIREMENTS
  KPIs: [list with thresholds]
  Measurement Methods:
  Compliance Period:

TECHNICAL REQUIREMENTS
  System Requirements:
  Environmental Requirements:
  Reliability / Availability Targets:

COMPLIANCE
  Standards Referenced:
  Verification Method: [Analysis / Test / Inspection / Demonstration]
```

### ASSURANCE — Assurance / Safety Plan

```
ASSURANCE FRAMEWORK
  V-Model Stage:
  SIL Level:
  EN Standards: [50126 / 50128 / 50129 — state which apply]

ASSURANCE ACTIVITIES
  Activities: [list with responsible party]
  Evidence Required:
  Independent Assessment Needs:

LIFECYCLE
  Phase Coverage:
  Handover Requirements:
```

### DESIGN — Design Process / Review

```
DESIGN PROCESS
  Review Gates: [list]
  Submission Requirements:
  Approval Authorities:

SUBCONTRACTOR OBLIGATIONS
  Submission Format:
  Review Timeline:
  Non-Compliance Handling:
```

### GSS — General Signalling Specification

```
GSS SCOPE
  Applicable Specifications: [list]
  Mandatory Requirements:

DEPARTURES / AMENDMENTS
  Process for Departures:
  Risk Assessment Requirements:
  Approval Authority:

VERSION CONTROL
  Current Version:
  Change Log Summary:
```

### RIM — Rail Infrastructure Manager

```
RIM SCOPE
  Boundary Definitions:
  Geographic Extent:
  Interfacing Disciplines:

HANDOVER
  Handover Criteria:
  Documentation Requirements:
  Acceptance Process:
```

### CONTRACT — Contractual Schedule

```
CONTRACT SCOPE
  Obligations:
  Deliverables:
  Timelines:
  Penalties / Incentives:
```

### DRAWING — Layout / Arrangement Drawing

```
DRAWING SCOPE
  Drawing Number:
  Title:
  Area Covered:
  Key Equipment Shown:
  Revision Notes:
```

### OPTION — Design Option / Variant

```
OPTION SUMMARY
  Option Identifier:
  Scope of Change:
  Comparison to Baseline:
  Cost / Schedule Impact:
  Technical Risk:
```

---

## Summary Output Format

Each document summary MUST follow this structure:

```markdown
# [Document Title]

## Metadata
| Field | Value |
|---|---|
| Document Number | |
| Revision | |
| Status | |
| Date | |
| Author / Organisation | |
| Classification | |
| Source File | |

## Executive Summary
[3-5 sentences summarising the document purpose, scope, and key content]

## Key Findings
[Bulleted list of the most important items extracted using the category template above]

## Interface Dependencies
[List of cross-references to other documents in the register, with brief description of the dependency]

## Open Actions / Risks / Gaps
[Any TBDs, open items, risks, or gaps identified]

## Role Relevance
[Brief note on which aspects of the user's role this document is most relevant to:
- Commissioning strategy
- GSS compliance and departures
- Subcontractor review
- RIM handover planning
- ETCS/RCS interface management]
```

---

## Workflow

### Full Review Pass

1. Run the Python extraction script to convert all documents to raw text:
   ```
   python .agent/skills/rail-doc-reviewer/scripts/extract_text.py
   ```
2. For each extracted text file, classify the document using the taxonomy above.
3. Apply the appropriate extraction template.
4. Write the summary to `.agent/skills/rail-doc-reviewer/resources/summaries/[doc_name]_summary.md`.
5. Update the document register at `.agent/skills/rail-doc-reviewer/resources/document_register.md`.

### Incremental Review

When new documents are added to the workspace:
1. Re-run the extraction script (it will skip already-extracted files).
2. Review only the new extracted text files.
3. Generate summaries and update the register.

### Follow-Up Query

When the user returns to ask questions:
1. Read the document register to identify relevant documents.
2. Read the specific summary file(s).
3. If needed, read the raw extracted text for deeper detail.
4. Answer the user's question with citations to document number and section.

---

## File Locations

| Item | Path |
|---|---|
| Extraction script | `.agent/skills/rail-doc-reviewer/scripts/extract_text.py` |
| Raw text output | `.agent/skills/rail-doc-reviewer/resources/raw_text/` |
| Document summaries | `.agent/skills/rail-doc-reviewer/resources/summaries/` |
| Document register | `.agent/skills/rail-doc-reviewer/resources/document_register.md` |

---

## Notes

- RIM = Rail Infrastructure Manager
- GSS = General Signalling Specification (Downer-specific standards framework)
- GSFT = Generic Software Functional Test
- SIT = System Integration Test
- NIT = Network Integration Test
- ETCS = European Train Control System
- RCS = Radio Communication System
- ConOps = Concept of Operations
- ICD = Interface Control Document
