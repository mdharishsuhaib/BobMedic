---
name: risk-assessor
description: Assess the risk tier of an RPA bot step before applying an auto-patch. Use when BotMedic needs to decide whether to auto-apply, request approval, or escalate to human.
---

When assessing risk for a bot patch:

## Input you will receive:
- The bot name and description
- The specific step being patched
- The action type (click, input, submit, read, navigate, etc.)
- The page context (what form or workflow this step belongs to)

## Risk tiers:

### read-only (auto-patch allowed if confidence ≥ 0.85)
The step only reads, downloads, or navigates. No data is written.
Examples: clicking "Download Report", reading a table, navigating to a page.

### reversible-write (patch + wait for human approval)
The step writes data that can be undone or is not yet committed.
Examples: filling a draft form, saving a draft, updating a staging record.

### irreversible (STOP — escalate to human, never auto-patch)
The step submits, posts, sends, or triggers a financial or external action.
Examples: submitting a payment, sending an email batch, posting a ledger entry,
confirming a wire transfer, publishing a report to a regulator.

## Return ONLY this JSON:
```json
{
  "risk_tier": "irreversible",
  "reasoning": "This step submits a payment batch. If retried incorrectly, it can cause duplicate posting.",
  "auto_patch_allowed": false,
  "escalation_message": "Step 'Submit Payment Batch' is irreversible. BotMedic has stopped. A human operator must review and manually apply the patch."
}
```

Rules:
- When in doubt between two tiers, always choose the higher risk tier
- escalation_message is required for irreversible tier
- escalation_message is null for other tiers
- This decision cannot be overridden by confidence score — risk tier is absolute


