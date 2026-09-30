# Product-owner demo

Use fictional data only. Start `python app.py`, then open the printed localhost URL. The demo can run without Copilot installed. Say explicitly that **Fictional offline demo** assembles text; actual AI drafting requires the org's configured Copilot SDK runtime. No live Confluence connector is active.

## 1. Meeting → minutes

Select **Minutes of meeting (MOM)**, then **Load sample**. The sample contains a date, ten fictional attendees, agenda, decision, named action owners and missing due dates. Click **Find business context**, explain the fictional Cobra/FHP definitions, and confirm the sources. Click **Generate draft**.

Show the readable meeting details, agenda, business context, decisions/actions and takeaways. Missing dates remain unconfirmed. Use **Edit section**, then **Save changes**. Download Word. There is no JSON task for the product owner.

## 2. Minutes → BRD 1.0

Choose **Create another document from an existing one** and select the minutes. Choose **Business requirements**, enter a clear BRD title, and paste:

> Create business requirements from the previous discussion. Cobra should remind the facilities coordinator when the FHP checklist is incomplete. Keep the existing booking window unchanged.

Retrieve and confirm context, then generate. Explain that this BRD has its own 1.0 version and cites the saved minutes. Offline mode shows the supplied record plus proposed input, not an AI interpretation.

## 3. BRD 1.0 → 1.1

Choose **Create a new version of an existing document** and select the BRD 1.0. Add:

> Add a proposed requirement: stop Cobra reminders once the FHP checklist is complete. The facilities coordinator reviews wording. Delivery date remains undecided.

Retrieve and confirm context; generate a small update. Show **Version 1.1**, expand **What changed from the previous document?**, and open 1.0 from **Document versions**. Its content is preserved and can still be exported. A same-version edit increments the edit number; creating another business version produces 1.2. Major revision produces 2.0. Creating a second successor from a stale version is rejected.

## 4. Existing architecture → revised architecture

Expand **Start from an existing Confluence document**, click **Load fictional architecture**, then **Preserve original document**. This pastes a snapshot; it does not fetch Confluence. The app selects the new-version workflow. Add:

> Propose a reminder component for Cobra that checks FHP readiness. Keep reservation confirmation blocked while handover is pending. Operational ownership remains undecided.

Find/confirm context and generate version 1.1. Compare it with the preserved original. In production the API connector will supply the page snapshot and remote version number instead of pasted text.

## 5. Review and share

Review sources and open questions, approve the saved edit, and **Publish to demo space**. The readable page is local. Word export is real. Production publishing will offer **Update existing page** or **Create new page**, show a reviewable change preview, and use remote version checks. It is not implemented in this demo.

If Copilot is configured in the organization, repeat these same steps with **Generate with Copilot**. No extra prompt-copy step appears. Do not describe offline output as Copilot output.
