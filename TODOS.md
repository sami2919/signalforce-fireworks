# TODOS

## P1: Extended Conversation Mode — Script the 20-Minute Walk-In

**What:** If Ishaan gives 20+ minutes of face time at the walk-in, the 90-second beat structure doesn't cover it. Write an extended conversation guide: what to show when the laptop is actually open on a desk, how to run `cli.py` live, what questions to ask about Conversion's current GTM stack, and how to close toward the trial week.

**Why:** The extended conversation is the highest-value scenario and the highest-improvisation-risk scenario. Unscripted = rambling. A 20-minute guide takes 30 minutes to write and is only needed post-Monday if the walk-in succeeds.

**Pros:** Eliminates the highest-variance failure mode of the walk-in. Makes the "success state" as scripted as the pitch itself.

**Cons:** Post-Monday prep item — no value if walk-in doesn't get face time.

**Context:** Identified during CEO review (2026-05-04) as a gap in the v5 walk-in script. The 90-second beat structure handles the lobby scenario; the extended conversation handles the conference room scenario.

**Effort:** S (human: ~30 min / CC: ~5 min)

**Depends on:** Walk-in getting face time with Ishaan

---

## P2: Community Config Repository

**What:** Create a separate GitHub repo (e.g., signalforce-configs) for community-contributed ICP configurations.

**Why:** Network effects — new users browse configs for their vertical instead of starting from scratch.

**Pros:** Viral adoption, reduced onboarding friction, community engagement.

**Cons:** Maintenance burden, quality control of submitted configs.

**Context:** Accepted as P2 during CEO review (2026-03-18). Depends on configurable ICP refactor shipping first. Users would submit PRs with their `config.yaml` + `gtm-context.md` + templates for their vertical.

**Effort:** M (human: ~1 week / CC: ~2 hours)

**Depends on:** Configurable ICP feature (this refactor)
