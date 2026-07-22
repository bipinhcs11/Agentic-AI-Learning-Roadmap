# Module 05 — Agent-to-Agent Trust

This lab demonstrates the critical difference between **delegating a task** and
**copying the caller's permissions**.

```text
User
  └── Planner Agent: invoice.read, email.draft
        ├── Finance Agent: invoice.read
        └── Email Agent: email.draft
```

The Email agent never receives `invoice.read`; the Finance agent never receives
`email.draft`. A prompt asking either specialist to exceed that boundary cannot
change the server-side delegation policy.

## Run

```bash
python3 delegation_lab.py
python3 -m unittest -q
```

Expected output:

```text
Planner scopes: email.draft invoice.read
Finance scopes: invoice.read
Email scopes: email.draft
Escalation check: DENY (child requested scopes outside its allow-list)
```

## Rules enforced

- child scopes must be a subset of parent scopes
- child scopes must be a subset of the child's registered allow-list
- tenant and task remain unchanged across the handoff
- delegation depth increments and has a hard maximum
- a child receives a new audience-bound credential rather than the parent token
- the audit chain records the immediate actor and parent credential identifier

The pure Python policy model is intentionally framework-free. The capstone
applies the same input document in OPA before the broker mints a child token.
