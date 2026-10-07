# Design Decisions

This is not a tour of the code. It lists the decisions that changed how the system thinks about the problem.

## 1. Match the JD, not the job title

**Problem.** The same work appears under different titles. Similar titles can hide very different responsibilities.

**Decision.** Title keywords are used only for discovery and prefiltering. The LLM judges the responsibilities and requirements in the posting when it gives the fit score.

**Why.** I want roles with similar work, not roles with similar labels.

---

## 2. Return a short list, not the maximum

**Problem.** Finding more jobs does not help by itself. Every shortlisted role still costs me review time, resume tailoring and application time.

**Decision.** Search broadly, but return at most ten prioritized jobs per run.

**Why.** My attention is the limit, so the system aims for the best decisions per hour I spend reading.

---

## 3. Use a cheap prefilter before the LLM

**Problem.** Sending every posting to an LLM adds API cost and delay, and does not improve every decision.

**Decision.** Score postings first with plain keyword lists (high, medium and negative).

**Trade-off.** A prefilter can miss relevant jobs that use unfamiliar wording. It is a coarse first cut, not the fit decision.

---

## 4. Keep qualification and preference apart

**Problem.** A company I prefer should not look like a better skill match just because I prefer it.

**Decision.** The LLM's JD-fit score stays untouched. Freshness and company-type preference are added later, only for ranking.

**Guardrail.** The company-type bonus applies only when the classification has some supporting confidence. Classifications marked `unverified` get no bonus.

---

## 5. Merge duplicates across platforms

**Problem.** Source IDs only catch duplicates within one platform. The same company and role can appear on JobKorea and Saramin at the same time.

**Decision.** Normalize company and title, and merge likely duplicates before the expensive LLM step.

**Trade-off.** This is a heuristic. A requisition ID or ATS URL would identify a posting more reliably, so the README says the current method is a heuristic.

---

## 6. Keep the history

**Problem.** A daily email says what to read today. It cannot say which source gives better-fit jobs, whether the number of recommendations is changing, which role families keep scoring well, or whether the pipeline is getting slower or more expensive.

**Decision.** Store job and run history in SQLite, and build reusable SQL views for daily and weekly analysis.

**Why.** The workflow stops being a one-off script and becomes something I can analyze.

---

## 7. Keep SQL out of the Python code

**Problem.** Queries embedded in Python are hard to read and hard to reuse.

**Decision.** Schema, operational queries and analytical views live under `sql/`, and `sql/loader.py` loads them.

**Why.** SQL is part of the analysis, so it should be easy to find and read.

---

## 8. Use run logs and failure alerts as the heartbeat

**Problem.** A workflow that usually works is not good enough when it runs without me.

**Decision.** `pipeline_runs` records the health of each run. Email alerts cover crashes and delivery failures, and sources that return zero results are logged.

**Why not a separate heartbeat service?** For a small personal system it adds complexity and little else. I only need to know four things: did the run happen, did it produce data, did a source fail, and did the email arrive.

---

## 9. Run locally first, with GitHub Actions as backup

**Problem.** In the first pilot, a run that worked by hand did not always work on schedule. An always-on cloud run was also unnecessary for a personal workflow, and it could raise external API usage.

**Decision.** macOS `launchd` is the main scheduler. GitHub Actions stays as a manual backup and recovery path.

---

## 10. Say what is uncertain

The system still keeps several imperfect signals:

- Some sources do not give a reliable original posting date.
- Company classification can be verified, pattern-matched or unverified.
- Experience requirements are not turned into one hard rule across every source.
- Cross-platform identity relies on normalized company and title, not a universal requisition ID.

The data model has confidence fields, and the documentation says where heuristics remain.
