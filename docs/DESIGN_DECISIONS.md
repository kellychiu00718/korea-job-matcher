# Design Decisions

The purpose of this document is not to describe every implementation detail. It records the decisions that changed **how the system reasons about the problem**.

## 1. Match the JD, Not the Job Title

**Problem**  
The same underlying work may appear under different titles, while similar titles can represent very different responsibilities.

**Decision**  
Use title keywords only for discovery / prefiltering. Ask the LLM to evaluate the actual JD responsibilities and requirements when producing the fit score.

**Why it matters**  
The system searches for transferable work patterns instead of overfitting to labels.

**Capability demonstrated:** problem reframing and requirement analysis.

---

## 2. Optimize for Actionable Recommendations, Not Maximum Volume

**Problem**  
Finding more jobs is not automatically useful because every shortlisted role still requires human review, resume tailoring, and application time.

**Decision**  
Search broadly but return no more than ten prioritized jobs per run.

**Why it matters**  
The limiting resource is human attention. The system therefore optimizes for **decision quality per unit of attention**.

**Capability demonstrated:** prioritization under resource constraints.

---

## 3. Use a Cheap Prefilter Before LLM Evaluation

**Problem**  
Sending every discovered posting to an LLM would increase API cost and latency without improving every decision.

**Decision**  
Use deterministic high / medium / negative keyword scoring before LLM evaluation.

**Trade-off**  
A prefilter can miss relevant jobs that use unfamiliar wording, so it is intentionally a coarse first stage rather than the final fit decision.

**Capability demonstrated:** cost / quality trade-off and staged decision design.

---

## 4. Separate Qualification from Preference

**Problem**  
A preferred employer should not appear to be a stronger skills match simply because the candidate prefers that company type.

**Decision**  
Keep the LLM-generated JD-fit score separate. Freshness and company-type preference are added later only for ranking.

**Additional guardrail**  
Company-type bonus is only applied when the classification has at least some supporting confidence; `unverified` classifications receive no bonus.

**Capability demonstrated:** metric definition and bias control.

---

## 5. Add Cross-Platform Canonical Deduplication

**Problem**  
Source IDs only solve duplicates within one platform. The same company-role combination can appear on JobKorea, Saramin, or other sources simultaneously.

**Decision**  
Normalize company + title and merge likely cross-platform duplicates before expensive evaluation.

**Trade-off**  
This is a heuristic. Official requisition IDs / ATS URLs would produce stronger identity resolution, so the current approach is documented rather than overstated.

**Capability demonstrated:** data quality and entity-resolution thinking.

---

## 6. Persist Data Instead of Treating Every Run as Disposable

**Problem**  
A daily email answers “what should I inspect today?” but cannot answer questions such as:

- Which source is producing better-fit jobs?
- Is recommendation yield changing?
- Which role families repeatedly score well?
- Is the pipeline becoming slower or more expensive?

**Decision**  
Move job and run history into SQLite and create reusable SQL views for daily and weekly analytics.

**Why it matters**  
This turns the workflow from a one-off automation script into an analyzable process.

**Capability demonstrated:** data modeling and closed-loop improvement.

---

## 7. Externalize SQL

**Problem**  
Keeping every query embedded inside Python makes analytical logic harder to inspect and reuse.

**Decision**  
Separate schema, operational queries, and analytical views under `sql/` and load them through `sql/loader.py`.

**Why it matters**  
SQL becomes a first-class analytical layer rather than a hidden implementation detail.

**Capability demonstrated:** query organization and maintainability.

---

## 8. Treat Run Logs + Failure Alerts as the Operational Heartbeat

**Problem**  
A workflow that “usually works” is not sufficient when it is supposed to run unattended.

**Decision**  
Use `pipeline_runs` as the run-level health record and pair it with email alerts for crashes / delivery failure plus source zero-result logging.

**Why not build a separate heartbeat service?**  
For a small personal system, a dedicated monitoring service would add complexity without materially improving the decision need. The practical questions are whether the run occurred, whether it produced data, whether sources failed, and whether delivery succeeded.

**Capability demonstrated:** proportionate monitoring design.

---

## 9. Keep Local Execution Primary and GitHub Actions as Backup

**Problem**  
The first pilot showed that successful manual execution did not guarantee scheduled execution. At the same time, always-on cloud execution was unnecessary for this personal workflow and could increase external API usage.

**Decision**  
Use macOS `launchd` as the primary scheduler and maintain GitHub Actions as a manual backup / recovery path.

**Capability demonstrated:** reliability / cost trade-off.

---

## 10. Be Explicit About Uncertainty

The system currently retains several imperfect signals:

- some sources do not expose reliable original posting dates,
- company classification may be verified, pattern-matched, or unverified,
- experience requirements are not normalized into one deterministic parser across every source,
- cross-platform identity is based on normalized company + title rather than universal requisition IDs.

Rather than hiding these limitations, the data model includes confidence fields and the documentation states where heuristics remain.

**Capability demonstrated:** responsible analytical judgment.
