---
description: Analyzes the current bid stage and instructs the user on what to do next to unblock the process.
---

1. Read the `[Project_Name]/bid_status.md` file (or wherever it currently resides) to determine the currently active stage of the bid process.
2. Read the `RailBid_Orchestrator_AU_Strict.md` to understand what inputs and conditions are required to pass the active stage.
3. If Stage 1.5 or later is active, read the `105_Compliance_Gap_Report.md` to look for any missing Tier 2 (User Blocked) items.
4. Check which `1XX_*.md` files exist in the project folder vs the 14 expected in `Master_Tender_Headings.md`. List any that are missing.
5. Respond to the user with a clearly structured guidance block:

```
═══ BID STATUS ═══
Current Stage: [X — Name]
Stage Status:  [IN PROGRESS / AWAITING APPROVAL / COMPLETE]

WHAT YOU NEED TO DO:
1. [Specific action — e.g., "Review 125_Design_Methodology.md and confirm it reflects your project approach"]
2. [Specific action — e.g., "Provide pricing data for Schedule 9"]
3. [Specific action — e.g., "Say 'GO' to approve Stage 4 and move to Commercials"]

WHAT I CAN DO WITHOUT YOU:
- [List any Tier 1 agent-actionable items remaining]

FILES STILL MISSING:
- [List any 1XX_ files not yet generated]

MARKDOWN REVIEW TIPS:
- Open the file in your editor — you can edit it directly
- Check technical accuracy, especially project-specific claims
- Look for placeholder text like [CLIENT] or [PROJECT] that needs replacing
- If content is wrong, describe what to change and I will fix it
- When satisfied with a file, say "GO" or "LGTM"
═════════════════
```

6. If the user has no pending actions (all gates cleared, no Tier 2 items), tell them: "No blockers found. I can continue working autonomously. Say 'Continue' to proceed."
