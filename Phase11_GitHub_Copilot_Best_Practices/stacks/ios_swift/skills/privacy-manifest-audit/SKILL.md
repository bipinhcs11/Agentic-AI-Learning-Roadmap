---
name: privacy-manifest-audit
description: "Use when adding data collection, touching UserDefaults/file-timestamp/boot-time/disk-space/keyboard APIs, adding a third-party SDK, or preparing an App Store submission: audits PrivacyInfo.xcprivacy declarations against what the code actually does."
---

# Privacy Manifest Audit

App Store submissions fail on manifests the way builds fail on syntax — except
weeks later, in review, with a release train waiting. When a task touches data
collection, a required-reason API, or a third-party SDK, run this audit BEFORE
declaring the task complete.

## Checklist

1. **Manifest exists** — the app target (and every first-party framework target
   that ships) has a `PrivacyInfo.xcprivacy`. A missing manifest is finding #1;
   do not proceed to nuance.
2. **Required-reason APIs** — search the diff (and the target, on a full audit)
   for the API families Apple gates, and confirm each used family has a
   `NSPrivacyAccessedAPITypes` entry with an approved reason code:
   - `UserDefaults` (`NSPrivacyAccessedAPICategoryUserDefaults`)
   - file timestamps — `creationDate`, `modificationDate`, `fileModificationDate`,
     `getattrlist`/`stat` usage (`…CategoryFileTimestamp`)
   - system boot time — `systemUptime`, `mach_absolute_time`
     (`…CategorySystemBootTime`)
   - disk space — `volumeAvailableCapacity*`, `systemFreeSize`
     (`…CategoryDiskSpace`)
   - active keyboards — `activeInputModes` (`…CategoryActiveKeyboards`)
   Usage with no declaration, or a reason code that does not match how the code
   actually uses the API, are both findings.
3. **Collected data types** — anything the diff starts collecting, linking, or
   sending off-device appears in `NSPrivacyCollectedDataTypes` with honest
   linked/tracking flags and purposes. The manifest describes behavior, not
   intentions — analytics events count.
4. **Tracking** — if any SDK or code path does tracking, `NSPrivacyTracking` is
   true and every tracking domain is listed in `NSPrivacyTrackingDomains`;
   verify those domains are not contacted before ATT authorization.
5. **Third-party SDKs** — every SDK on Apple's commonly-used-SDK list ships its
   own signed manifest; an SDK added without one is a dependency-audit failure
   too (route through that skill). New SDK versions can add API usage — re-check
   on upgrades, not just additions.
6. **No contradictions** — the union of all manifests must not contradict the
   App Store privacy questionnaire ("nutrition label"). Flag mismatches for
   whoever owns the store listing; do not silently "fix" either side.

## Output shape

A verdict block in the PR description:

```
Privacy manifest: <present | MISSING at <target>>
Required-reason APIs used: <family: file/line … | none>
Declared: <family: reason code | UNDECLARED — finding>
Collected data types touched by this diff: <list | none>
Tracking: <unchanged | new domains: …>
Third-party SDK manifests: <all present | missing: …>
Verdict: <clean | findings above — block submission until resolved>
```

If a line cannot be verified with available tools (e.g., what an opaque SDK
actually collects), write "UNVERIFIED" and name what a human must check — do
not guess a reason code to make the table green. A wrong reason code is worse
than a missing one: it survives review until an audit.
