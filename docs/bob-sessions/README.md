# IBM Bob task session summaries

## One report, or one per person?

**One per person, all collected here.** Capture is individual; storage is
shared.

The submission deliverables ask for *"each team member's screenshots of IBM Bob
task session summaries for your project"*, and the Official Rules ask for *"an
exported IBM Bob report of all relevant tasks/sessions used for the contest"*.

Nobody can produce a single merged report for the whole team: your Bob sessions
live in your own Bob account, and only you can export or screenshot them. So
every member who used Bob captures their own, and all of them go into this one
folder.

## What to add

One file per person, named for them:

```
docs/bob-sessions/mohammedsuhaib-01.png
docs/bob-sessions/mohammedsuhaib-02.png
docs/bob-sessions/ahmed-elshikh-01.png
docs/bob-sessions/sheikmohammedirfan-01.png
docs/bob-sessions/zara-01.png
docs/bob-sessions/ammar-01.png
```

The hackathon guide has the capture steps.

## Out of Bobcoins? You can still do this

Exporting your history costs nothing. Bobcoins are spent on Bob's AI
interactions; reading back sessions you already had is not one. Two ways:

**Export the full report** — `tools/export-bob-report.py` reads your own local
Bob database at `~/.bob/db/bob.db` and writes an HTML report. It never contacts
Bob's service, so an empty balance makes no difference:

```powershell
python tools/export-bob-report.py --all --out docs/bob-sessions/bob-session-report-<your-name>.html
```

Run it on your own machine — it can only see your sessions, which is exactly
why every member has to run it themselves.

**Screenshots** — opening Bob and looking at a task session summary spends
nothing either. Screenshot what is already there.

Include both forms if you have them:

- **Screenshots** — named explicitly in the deliverables, and the automated
  submission advisor checks for them specifically
- **Exported HTML session reports** — what the Official Rules wording asks for

An exported report does not replace the screenshots, and one person's report
does not cover the team.

## Who needs to appear here

Everyone who used Bob on the project. The advisor looks for evidence that Bob
was used *throughout the development process*, so a folder holding one member's
sessions reads as an incomplete submission even when the code is finished.
