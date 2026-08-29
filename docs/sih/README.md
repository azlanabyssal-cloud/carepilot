# SIH documents — index

This directory holds the Smart India Hackathon (SIH) 2026 reference material CarePilot's plan now depends on, so the whole project can work from saved, dated copies instead of re-searching each session. Two files:

- **`SIH26047_Patient_Case_Taking_Software.md`** — the full, in-depth problem statement (Ministry of Ayush, "Patient Case-Taking Software") the project owner has directed CarePilot toward as a candidate flagship target. Read this first — it's the actual scope document.
- **`../../data/sih/sih26047.json`** — the same PS record as structured data (title, org, department, category, theme, deadline, full description), for anything that wants to read it programmatically rather than parse markdown.

## General SIH 2026 process — what's confirmed, and how

Same honesty standard as the rest of this repo (see `docs/INTERVIEW_NOTES.md`): the official portal, **sih.gov.in**, is not reachable from this build environment (outbound network access here is allow-listed and does not include it — confirmed by a direct fetch attempt returning `EGRESS_BLOCKED`, not assumed). Everything below is a `WebSearch`-tool summary of third-party blogs/guides describing the process, not a fetch of a primary SIH document — treat it as **plausible, not verified**, and confirm against the official portal or your institute's SPOC before relying on it for a real submission:

- **Two-stage process:** an Internal Hackathon at the participating institute (September 2026, per the sources below) selects a team, whose SPOC (Single Point of Contact) then nominates and uploads the team's idea submission (PPT + a project demonstration video) for national-level screening. Shortlisted teams go on to a 36-hour on-site Grand Finale hackathon at a nodal center (reported as December 2026).
- **Submission format:** a strict slide-count limit (6 slides, official AICTE-format template) is reported, with rules against altering the template's fonts/layout and against AI-generated narration or demo video content — submissions that don't comply risk disqualification. Typical sections: Problem, Proposed Solution, Technical Approach/Architecture, Feasibility & Viability, Impact & Benefits, and Research/References.
- **Team composition:** commonly reported as 6 students + 2 mentors per team, with at least one female team member required.

**Where to get the authoritative version of the above (not done here — blocked):** `sih.gov.in`, or your institute's own SIH SPOC/registration portal, which normally hosts the current year's official PPT template and rulebook PDF directly.

## Ministry of Ayush's other 2026 problem statements (context)

SIH26047 is one of five problem statements the Ministry of Ayush sponsored this year (SIH26044–SIH26048, from the same source dataset as SIH26047 — see the "Source and how this was retrieved" section in `SIH26047_Patient_Case_Taking_Software.md`). Listed here because a judge/mentor from the same sponsoring ministry is likely to know all five, and it's useful to know CarePilot isn't the only AYUSH-adjacent entry in the room:

| PS Number | Title | Theme |
|---|---|---|
| SIH26044 | Portal for Academia–Industry collaboration for Skill Mapping, Internships and Placement | Miscellaneous |
| SIH26045 | IP-SAKTI Sahayak — a multilingual, RAG-based (source-cited) AI assistant for Intellectual Property and regulatory guidance in Ayurveda | Toys & Games *(theme field looks mismatched in the source scrape — flagged, not corrected, since the title/theme pairing wasn't independently verifiable against the primary source)* |
| SIH26046 | AIIA Clinical Trials Dashboard — a real-time, cloud-based, GCP-compliant Clinical Trial Management System (CTMS) for Ayurveda research | Space Technology *(same caveat as above)* |
| **SIH26047** | **Patient Case-Taking Software** | Smart Automation |
| SIH26048 | iKwath — a pod-based smart Kwatha (Kadha) maker for AFI/API-standardized decoctions | Fitness & Sports *(same caveat as above)* |

The "theme" mismatches flagged above (a clinical trials dashboard tagged "Space Technology"?) are a real, visible data-quality issue in the third-party scrape used here — recorded plainly rather than silently trusted, same as every other honesty note in this project's docs. SIH26047's own theme ("Smart Automation") is corroborated by two independent search results (see `SIH26047_Patient_Case_Taking_Software.md`'s source section), so it's treated as reliable; the other four are not independently corroborated here and shouldn't be repeated as fact without checking the primary source.
