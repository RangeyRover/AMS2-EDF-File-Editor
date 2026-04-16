---
description: Full or incremental review of ETCS/rail signalling project documents in the Downer QTMP workspace.
---

# Review Documents Workflow

// turbo-all

## Steps

1. Run the text extraction script to convert all documents to raw text:
```
python "c:\Users\markn\OneDrive - IXL Signalling\Sigtech\Downer QTMP\.agent\skills\rail-doc-reviewer\scripts\extract_text.py"
```

2. Read the SKILL.md for review instructions:
```
Read: c:\Users\markn\OneDrive - IXL Signalling\Sigtech\Downer QTMP\.agent\skills\rail-doc-reviewer\SKILL.md
```

3. For each raw text file in `.agent/skills/rail-doc-reviewer/resources/raw_text/`:
   - Read the extracted text.
   - Classify the document using the taxonomy in SKILL.md.
   - Apply the appropriate extraction template from SKILL.md.
   - Write the structured summary to `.agent/skills/rail-doc-reviewer/resources/summaries/[doc_name]_summary.md`.

4. After all summaries are written, update the document register:
   - Path: `.agent/skills/rail-doc-reviewer/resources/document_register.md`
   - List every document with: title, document number, revision, classification tag, summary path, and any cross-references.

5. Notify the user that the review is complete and present the document register for review.
