# Conversion Walk-In — Extended Conversation Guide
**Date:** 2026-05-13 | **Contact:** Ishaan | **Location:** Conversion HQ

Use this if you get 20+ minutes of face time. The 90-second beat structure handles the lobby.
This handles the conference room.

---

## THE SETUP (first 2 minutes)

Before opening the laptop:

> "Before I show you anything — can I ask what your current pipeline for finding new customers looks like? 
> Do you attend conferences, or is it mostly inbound?"

**Listen for:**
- Conferences they attend → match against `conference_registration` signals
- Current outbound motion → positions SignalForce as the feed layer
- Pain about finding the right companies at the right time

Then: "Perfect. What I'm about to show you is directly relevant to that."

---

## THE DEMO (10 minutes)

### Beat 1 — The compiler framing (60 seconds, no laptop yet)

> "Every brief-generation tool out there — Jasper, Marketo Engage, even custom GPT wrappers — produces a 
> document that a human then translates into a campaign. 
> 
> SignalForce produces the artifact that goes directly into your platform's API. 
> Not a PDF. The actual JSON your agent layer ingests.
> 
> But the more important part is the top of this document."

Open `demo/hubspot-ceiling.html` OR run live: `python -m scripts.marops.cli hubspot-ceiling`

### Beat 2 — The Why Now block (90 seconds)

Point to the green banner at the top:

> "This company — Meridian Analytics — is in your ICP. Series B SaaS, 160 people, Snowflake + Salesforce.
> That's a standard ICP match. Half the tools out there would give you this company.
> 
> But look at what happened in the last 8 days."

Walk through each signal:
- "3 days ago, their VP Marketing left a 3-star G2 review on HubSpot. Not a 1-star. 
  A 3-star — they're not furious, they're *evaluating*. That's the moment."
- "5 days ago, they posted for a Marketing Data Engineer. The job description says 
  'build marketing attribution from scratch outside of a MAP.' That's a tell."
- "8 days ago, Jordan Kim — that's the VP Marketing — registered for SaaStr. 
  **You have a booth at SaaStr.**"

> "Three signals in 8 days. Buying window closes in 6 days. This isn't a lead — 
> it's a calendar event."

### Beat 3 — The JSON (60 seconds)

Open `out/hubspot-ceiling.json` or scroll below the HTML:

> "This is what your platform actually receives. Salesforce filters in SObject.Field__c syntax, 
> warehouse traits, three non-overlapping agent assignments — execution, QA, optimization — 
> exactly as your architecture expects. 
> 
> I didn't write this. The system generated it from the signal stack in about 30 seconds."

If running live: `python -m scripts.marops.cli hubspot-ceiling` and let it run. 
Point to the terminal output while it processes: "This is real-time."

### Beat 4 — The conference trigger (30 seconds)

Point to the optimization triggers section:

> "See this trigger: 'If prospect.conference_registration includes SaaStr → route to 
> booth-meet instead of email sequence.' 
> 
> Your team finds this person at SaaStr because the signal told us they'd be there."

---

## THEIR LIKELY QUESTIONS

**"How do you detect these signals?"**

> "Today, it's open data sources — G2's public review feed, LinkedIn job postings, conference 
> registration data from Eventbrite and Luma. The enrichment waterfall is Apollo first, 
> then Prospeo for anyone that comes back empty.
> 
> The scoring model uses recency decay: a G2 review from yesterday weights 10x a review 
> from 3 months ago. High/Medium/Low timing tiers, not a numerical score — LLMs don't 
> distinguish meaningfully between 77 and 78.
> 
> The interesting version is when your platform's own data feeds back in — who's visiting 
> your site, who's opening your emails. That's the version we'd build together if you 
> want to go further."

**"What's the shelf life / how do you handle signal decay?"**

> "14-day buying window, hard cutoff. A signal older than 14 days doesn't score.
> The shelf life you see in the brief is days remaining in the window — 
> after that, the account drops out of the active queue and re-enters if a new signal fires.
> That's the part most signal tools miss: they treat a funding round from 6 months ago 
> the same as one from last week."

**"How does this compare to Clay?"**

> "Clay is enrichment — it's very good at taking a list of companies and filling in 
> data fields. SignalForce is timing — it tells you which companies to put on that list 
> *right now* and why. They're complementary. You'd feed a SignalForce queue into Clay 
> enrichment if you wanted both."

**"What would it take to integrate this with our platform?"**

> "The brief schema already mirrors what your platform consumes — I built it from your 
> job descriptions and platform documentation. The actual integration work is a webhook: 
> SignalForce detects a signal stack, fires the brief to your API endpoint, your platform 
> picks it up. 
> 
> The question is whether you want a trial with your real ICP data — I can configure 
> SignalForce for your actual verticals and signal keywords in about an hour."

**"What's your pricing / how do you work with companies?"**

> "I'm open to how this works best for you. The fastest path is a trial week — 
> I configure SignalForce for your ICP, run it for a week, and you see which accounts 
> it surfaces. No commitment. 
> 
> If the accounts are good, we talk about a proper engagement."

---

## THE ASK (last 2 minutes)

When the conversation is winding down:

> "Here's what I'd propose: a one-week trial. I configure SignalForce for two of your 
> target verticals — you tell me which ones — run it for a week, and give you a report 
> of every account that hit a high-timing window during that period. 
> 
> You tell me if those are companies you'd actually want to reach. If yes, we go from there."

**If they ask about compensation / how you'd work together:**

> "I'm flexible. Could be a consulting engagement, could be something deeper if the 
> fit is right. The goal for this week is to prove the signal quality — everything else 
> is a conversation after that."

---

## IF THE DEMO BREAKS

If `python -m scripts.marops.cli hubspot-ceiling` fails:

1. Open `demo/hubspot-ceiling.html` directly in Chrome (pre-rendered fallback)
2. Open `demo/veriforce.html` as backup (supplier compliance use case — different vertical, same engine)
3. Open the JSON in a text editor and walk through it manually

Script: "The live run hit an API timeout — let me show you the pre-rendered version, 
same output, same schema." Don't apologize. Just redirect.

---

## AFTER THE MEETING

Same day:
- Send a follow-up with `demo/hubspot-ceiling.html` attached
- Include the trial week proposal in writing

Within 48 hours:
- If yes to trial: configure `config/config.yaml` for their stated verticals
- Run the scanner for 24 hours and send a sample output

---

*Generated by SignalForce marops branch · 2026-05-12*
