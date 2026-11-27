---
name: session-sync
argument-hint: "start | end"
description: Use at the start or end of a work session in any project to sync continuity docs (and the project hub, if the project has one). Start mode reads the handoff/status doc and triages unhandled hub steer/notes; end mode updates the handoff/status doc, master plan, progress log and hub. Trigger on "session-sync", "start/end of session", "wrap up", "update the docs and hub", "handoff".
---

# session-sync

Keeps a project's continuity docs (and hub, where one exists) in step with the work. Works in any repo; adapts to what the project already has.

**Precedence:** project instructions (`AGENTS.md`, `CLAUDE.md`, a project-level `session-sync` skill) win over this skill. If they disagree, follow the project and tell the user about the conflict.

Pick the mode from the user's words or the moment: session just starting = **start**; work done / user wrapping up = **end**. If unclear, ask.

## Step 0: Discover the project's setup (both modes)

Look, don't assume. Check `AGENTS.md` / `CLAUDE.md` first for continuity or hub rules, then the repo for these:

| Role | Look for (first match) | If missing |
|---|---|---|
| **Handoff/status doc** | `docs/HANDOFF.md`, `HANDOFF.md`, `STATUS.md`, `docs/STATUS.md` | Create `docs/HANDOFF.md` (end mode only) |
| **Master plan** (optional) | `PROJECT_MASTER.md`, `ROADMAP.md`, `PLAN.md` | Skip. Fold decisions into the handoff doc |
| **Progress log** (optional) | `docs/build-progress.md`, `CHANGELOG.md`-style progress file | Skip |
| **Hub** (optional) | An artifact URL (`claude.ai/artifact/...`) named in `AGENTS.md`, `CLAUDE.md` or the docs as a hub/dashboard | **No hub: handoff/status doc is the only sync target.** Don't create a hub unless asked |

Not a git repo, or no project docs at all: use `HANDOFF.md` in the working directory.

Repo docs are truth; a hub is only a dashboard over them. Never record in a hub a result that isn't in a repo doc.

## Start mode

1. Read the handoff/status doc, then the master plan's current priorities (if one exists). Use `README.md` for setup; read the progress log only for historical evidence.
   - No handoff doc yet: say so in one line, glance at `git log -5` and `git status`, and carry on.
2. **Hub only:** load `ArtifactData` (ToolSearch `select:ArtifactData`) and query the `steer` and `notes` collections for docs where `handled != true`. None: say so in one line. For each one: act on it, record any decision in the master plan (or handoff doc), then `update` the doc with `handled: true` and a short `reply`. **Never read or republish the hub page to update it**; its state lives in the artifact database.
3. Report in a few lines: where things stand, next action, and any steer/notes handled.

## End mode

1. Review what actually changed (`git status`, `git diff --stat`, your own work). Record only checks you actually ran and their real results.
2. Update the handoff/status doc: current work, next action, blockers, checks run, uncommitted local changes. Replace stale status; don't accumulate duplicate history. When creating one, keep it short, with these headings: *Current state*, *Next action*, *Blockers*, *Checks run*, *Uncommitted changes*.
3. Update the master plan only if task status or a decision changed. (No master plan: record the decision in the handoff doc.)
4. Append significant delivery evidence to the progress log (skip if none exists or nothing significant was delivered).
5. **Hub only, and only if the handoff doc or master plan changed this session** (otherwise skip and say so). Use the hub's own schema. Read the current `meta` first, then:
   - Update only the changed `hub` docs (`meta` headline/recommendation/version/updated, and the items docs for milestones/tasks/backlog/decisions/roadmap).
   - Add one `hublog` doc `v<n>` with `{v, date, t, items}`, and bump `meta.version`.
   - Use one `batch` write for several docs.
   - If the hub's collections don't match these names, follow the project's own hub instructions instead of guessing.
6. Don't commit or push unless the user authorizes it. Keep credentials, local config, captures, databases and bulk data out of Git.
7. Report in a few lines: docs changed, hub version written (or "no hub" / skipped), uncommitted state.
