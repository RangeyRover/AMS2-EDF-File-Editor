---
description: Boot the Athena system and load context
---

# /start — Initialize a New Bid

This workflow creates a new bid working folder and bootstraps the orchestrator.

## Steps

1. **Ask the user for project details:**
   - Project Name (e.g., "ARTC Inland Rail ETCS")
   - Client Name (e.g., "ARTC")
   - RFT Reference (e.g., "RFT-2026-0042")
   - Due Date (e.g., "2026-04-15")

2. **Create the working folder structure:**
   Use the project name to create a folder. Replace spaces with underscores, e.g., `ARTC_Inland_Rail_ETCS/`.
   Create the following structure inside the project root:

   ```
   [Project_Name]/
   ├── Bid folder/           ← User places client documents here
   ├── bid_status.md         ← Copied from templates/00_Bid_Status_Checklist.md
   └── (empty — submission files will be generated here)
   ```

   // turbo
3. **Copy the bid status template:**
   Copy `templates/00_Bid_Status_Checklist.md` into the new folder as `bid_status.md`.

4. **Fill in the project details:**
   In `bid_status.md`, replace:
   - `[CLIENT]` → with the Client Name provided
   - `[PROJECT]` → with the Project Name provided
   - `[RFT REF]` → with the RFT Reference provided
   - `[DATE]` → with the Due Date provided

5. **Read the Orchestrator:**
   Read `Bid_Project_Artifacts/RailBid_Orchestrator_AU_Strict.md` to load the full rule set.

6. **Read Master Headings:**
   Read `templates/Master_Tender_Headings.md` to anchor the 14-section structure.

7. **Present the user with a confirmation:**

   ```
   ═══ BID INITIALIZED ═══
   Project:  [Project Name]
   Client:   [Client Name]
   RFT:      [RFT Reference]
   Due Date: [Due Date]
   Folder:   [Folder Path]

   NEXT STEP:
   Place all client documents (RFT, Specs, Contracts, Addenda)
   into the "Bid folder/" subdirectory.

   When ready, say "GO" to begin Stage 0 (Context Ingestion).
   ═════════════════════════
   ```

8. **Wait for user approval.** Do NOT proceed until the user says "GO".
