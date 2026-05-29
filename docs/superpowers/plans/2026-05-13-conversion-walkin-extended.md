# Conversion Walk-In — Extended Conversation Guide
**Date:** 2026-05-26 | **Contact:** Ishaan | **Location:** Conversion HQ

Use this if you get 20+ minutes of face time. The 90-second beat structure handles the lobby.
This handles the conference room.

---

## THE SETUP (first 2 minutes)

Before opening the laptop:

> "Before I show you anything — can I ask what your current pipeline for finding new customers looks like? 
> Do you attend conferences, or is it mostly inbound?"

**Listen for:**
- Conferences they attend → match against `conference_registration` signals (Snowflake Summit, Dreamforce, etc.)
- Current outbound motion → positions SignalForce as the feed layer
- Pain about finding the right companies at the right time

Then: "Perfect. What I'm about to show you is directly relevant to that."

---

## THE DEMO (10 minutes)

### Beat 1 — The live scan (90 seconds, open terminal)

Run this first, while you're still talking:

```bash
python -m scripts.demo_scan --lookback-days 30 --min-grade B
```

While it runs (~30 seconds):

> "What I just kicked off is a live scan across GitHub, job boards, and funding data — 
> configured for your exact ICP. Marketo and HubSpot migration signals, MOPs hiring, 
> warehouse-native stack indicators."

When the table prints, point to the top company (whatever appears — results change daily):

> "These are companies showing intent right now. Each one has at least one signal 
> that fired in the last 30 days — a MOPs hire, a GitHub repo with MAP integration code, 
> a funding event.
>
> These are all B-grades. One signal each. B is 'worth a sequence.' 
> A is 'get on a plane.' To get to A, signals need to stack."

### Beat 2 — The signal behind the grade (90 seconds)

Pick the top company from the table. Click the source URL from the signal (it's a live Greenhouse or Ashby job posting). Show them the actual job title in the browser.

> "This is the signal. Not a keyword match on the company name — the scanner hit the 
> live job board API, pulled the posting, matched the title against a MOPs keyword table. 
> 'Lifecycle Marketing Automation Manager' — that's a MAP hire. Named explicitly.
>
> The scoring formula is ICP fit times 0.45, plus intent times 0.55, with recency decay. 
> A posting from yesterday outweighs one from three weeks ago by design. 
> When this posting closes, the signal decays off the list automatically."

### Beat 3 — The multi-signal account and what A looks like (90 seconds)

Open `demo/hubspot-ceiling.html` or run: `python -m scripts.marops.cli hubspot-ceiling`

> "This is what an A-grade looks like — three signals in 8 days on the same account.
> The live scan shows B-grades because we're running four signal sources right now. 
> A-grade requires stacking: job posting plus a G2 review plus a conference trigger 
> in the same window. That's what this example shows."

Walk through each signal:
- "3 days ago — 3-star G2 review on HubSpot. Not a 1-star. A 3-star means they're 
  *evaluating*, not just venting. That's the moment."
- "5 days ago — Marketing Data Engineer posting. JD says 'build attribution from scratch 
  outside of a MAP.' That's the tell."
- "8 days ago — VP Marketing registered for Snowflake Data Cloud Summit. 
  **You have a booth there. She's already decided on the data stack — 
  the question is which MAP runs on top of it.**"

> "Three signals in 8 days is an A. The system gives you 6 days before the window closes.
> This isn't a lead — it's a calendar event.
>
> The G2 signal is the hardest to automate at scale — G2 has bot protection. 
> So right now I pull those manually and seed them in. Takes 20 minutes. 
> The production version uses a headless browser to do it automatically."

### Beat 4 — The output artifact (60 seconds)

Open `out/hubspot-ceiling.json` or scroll below the HTML:

> "This is what your platform actually receives. Salesforce filters in SObject.Field__c 
> syntax, warehouse traits, agent assignments — execution, QA, optimization — 
> exactly as your architecture expects.
> 
> I built the brief schema from your job descriptions and platform documentation. 
> The integration is a webhook — SignalForce fires this JSON to your API endpoint 
> when a signal stack hits threshold."

---

## THEIR LIKELY QUESTIONS

**"How do you detect G2 signals? I thought G2 was behind a login."**

> "It is. G2 uses DataDome for bot protection — it fingerprints the browser, 
> so a Python client with a session cookie won't pass it even if you're logged in.
> 
> There are two real options. First: a headless browser like Playwright that passes 
> the fingerprint check — that's a one-day build. Second, which is what I use for the 
> demo today: I pull the reviews manually in the browser, note the companies and 
> snippets, and feed them into the scoring engine as pre-seeded signals. Same weight, 
> same decay, different collection step.
> 
> For a production version you'd want the Playwright approach, or a scraping proxy 
> service — about $50/month — to handle the fingerprinting automatically."

**"How do you detect these signals at scale?"**

> "Five scanners running in parallel: GitHub repos with MAP integration keywords, 
> SerpAPI job board search across Greenhouse, Lever, and Ashby, Crunchbase funding 
> events, LinkedIn content, and G2 reviews. Each scanner emits a Signal object — 
> same schema regardless of source. The aggregator groups by company, the intent 
> scorer applies weights and recency decay, and the grader cuts at configurable thresholds.
> 
> The whole thing reconfigures by swapping a YAML file. Different ICP, same engine."

**"What's the shelf life / how do you handle signal decay?"**

> "Each signal type has a half-life in days — job postings decay over 14 days, 
> G2 reviews over 21, LinkedIn posts over 3. The intent score at detection time 
> is multiplied by e^(-ln2 × days_elapsed / half_life). So a job posting from 
> yesterday scores roughly 2x a posting from two weeks ago.
> 
> Companies drop out of the active queue when their combined score falls below the 
> C-grade threshold. They re-enter automatically if a new signal fires."

**"How does this compare to Clay?"**

> "Clay is enrichment — you bring a list, Clay fills in the fields. 
> SignalForce is timing — it generates the list and tells you why each company 
> is on it right now. They're complementary. You'd feed a SignalForce queue into 
> Clay for contact enrichment if you wanted both layers."

**"What would it take to configure this for our actual ICP?"**

> "About an hour. The ICP is defined in a YAML file — target titles, 
> disqualifiers, signal keywords, scoring thresholds. I'd ask you five questions 
> about your best current customers and translate the answers directly into config.
> 
> The scanner picks it up on the next run. No redeployment."

**"What's your pricing / how do you work with companies?"**

> "The fastest path is a trial week — I configure SignalForce for two of your 
> target verticals, run it for 7 days, and send you a report of every account 
> that hit a high-timing window. You tell me if those are companies you'd actually 
> want to reach.
> 
> If the signal quality is there, we talk about what an ongoing engagement looks like. 
> I'm open to how that's structured."

---

## THE ASK (last 2 minutes)

When the conversation is winding down:

> "Here's what I'd propose: a one-week trial. You pick two verticals — 
> I configure the ICP, run the scanners, and give you a ranked list of every 
> account that hit threshold during that period.
> 
> You tell me if those are companies you'd want to reach. If yes, we go from there."

**If they ask about a role / working together more deeply:**

> "I'd be interested in that conversation. What I built here is essentially 
> a GTM engineering stack — signal detection, scoring, enrichment, brief generation, 
> CRM output. If Conversion is thinking about who owns that infrastructure internally, 
> that's the work I want to be doing."

---

## IF THE DEMO BREAKS

**If `python -m scripts.demo_scan` returns no results:**
- Check `.env` has `SERPAPI_KEY` set — that's the job scanner
- Run `python -m scripts.scanners.job_scanner --help` to isolate
- Fallback: open `demo/hubspot-ceiling.html` and skip Beat 1

**If `python -m scripts.marops.cli hubspot-ceiling` fails:**
1. Open `demo/hubspot-ceiling.html` directly in Chrome (pre-rendered fallback)
2. Open the JSON in a text editor and walk through it manually

Script: "The live run hit an API timeout — let me show you the pre-rendered version, 
same output." Don't apologize. Just redirect.

**If they ask to run it against a specific company live:**
- Drop the company into `config/g2_seeds.yaml` with their relevant signals
- Rerun `python -m scripts.demo_scan` — takes 30 seconds
- Or: pull up the Greenhouse/Ashby job board for that company and show the posting directly

---

## AFTER THE MEETING

Same day:
- Send follow-up with `demo/hubspot-ceiling.html` attached
- Include the trial week proposal in writing
- Note which verticals they mentioned → pre-configure `config/config.yaml` before they reply

Within 48 hours:
- If yes to trial: swap `config/config.yaml` for their ICP, run 24-hour scan, send sample output
- If interested in a role: send GitHub link to SignalForce repo as a work sample

---

*Updated 2026-05-26 · reflects live scan output (23 B-grade prospects), manual G2 seeding, real job posting signals*
