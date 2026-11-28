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

Check `AGENTS.md` / `CLAUDE.md` first for continuity or hub rules, then locate these paths. In start mode, use only file names and Git metadata for discovery. Defer reading project docs or discovering a hub from their contents until start step 0 clears the source.

| Role | Look for (first match) | If missing |
|---|---|---|
| **Handoff/status doc** | `docs/HANDOFF.md`, `HANDOFF.md`, `STATUS.md`, `docs/STATUS.md`, `docs/project/STATUS.md` | Create `docs/HANDOFF.md` (end mode only) |
| **Master plan** (optional) | `PROJECT_MASTER.md`, `ROADMAP.md`, `PLAN.md`, `docs/project/PLAN.md` | Skip. Fold decisions into the handoff doc |
| **Progress log** (optional) | `docs/build-progress.md`, `CHANGELOG.md`-style progress file | Skip |
| **Hub** (optional) | An artifact URL (`claude.ai/artifact/...`) named in `AGENTS.md`, `CLAUDE.md` or the docs as a hub/dashboard | **No hub: handoff/status doc is the only sync target.** Don't create a hub unless asked |

For a non-Git project or a project with no docs, use `HANDOFF.md` in the working directory. In start mode with a remote, check the fetched branches before deciding there is no handoff.

Repo docs are truth; a hub is only a dashboard over them. Never record in a hub a result that isn't in a repo doc.

## Start mode

0. **Verify the handoff source before reading any project docs.** Run this check from the Git root when a remote exists. Use `origin` when present. Otherwise use the sole remote, or ask which remote to check if there are several. Skip the remote check outside Git or in a repo without remotes.
   - Run `git fetch origin --prune '+refs/heads/*:refs/remotes/origin/*'`. The explicit refspec also fetches all branches in single-branch clones. Substitute the selected remote for `origin` throughout. Add `--unshallow` if `git rev-parse --is-shallow-repository` returns `true`. If the fetch or commit comparison fails, report the failure and pause before reading any project docs.
   - Use the configured or discovered repo-relative handoff path. If none is present in `HEAD`, look for the supported paths in the fetched branch trees by name before falling back to the no-handoff case. Set `handoff_doc` to that path, then compare the latest commit touching it on each remote branch with the one on `HEAD`:

     ```bash
     set -o pipefail
     git log -1 --format='%ct %cI %H' HEAD -- "$handoff_doc" || exit 1
     git for-each-ref --format='%(refname) %(symref)' refs/remotes/origin/ |
       while read -r branch symref; do
         [ -z "$symref" ] || continue
         entry=$(git log -1 --format='%ct %cI %H' "$branch" -- "$handoff_doc") || exit 1
         [ -z "$entry" ] || printf '%s %s\n' "$entry" "${branch#refs/remotes/}"
       done | sort -k1,1nr
     ```

     Check the command status before continuing. Rank by the numeric committer time (`%ct`) so offsets in the ISO dates do not affect the ordering. Compare all branches and show up to the five newest if useful. A remote handoff commit takes precedence over a missing HEAD handoff commit. If the top timestamp ties HEAD but a different handoff commit at that timestamp is absent from HEAD's history, treat it as ambiguous and pause for confirmation too.
   - If a remote branch has a newer handoff commit or there is a tie that needs confirmation, stop before reading any project docs. Name the branch and report the number of commits it has that HEAD lacks (`git rev-list --count HEAD..<branch>`). If several branch tips have equally fresh handoffs, name them. Check `git merge-base --is-ancestor HEAD <branch>`. If HEAD is an ancestor, propose fast-forwarding the session branch with `git merge --ff-only <branch>` and wait for approval. Otherwise ask which branch to use, noting whether the histories diverged. A choice to read from a remote branch does not by itself authorize a checkout or merge.
   - When this check clears, use HEAD. When the check pauses, use only the branch the user confirms. Pin the chosen ref to its commit with `git rev-parse --verify '<ref>^{commit}'` and read the project docs from that snapshot with `git show "<commit>:<path>"`. Use the working-directory handoff for non-Git projects and for local-only docs in repos without a remote. If there is no handoff in the selected source, follow step 1's no-handoff case.
1. Read the handoff/status doc, then the master plan's current priorities (if one exists). Use `README.md` for setup and read the progress log only for historical evidence.
   - No handoff doc yet: say so in one line, glance at `git log -5` and `git status`, and carry on.
2. **Hub only:** load `ArtifactData` (ToolSearch `select:ArtifactData`) and query the `steer` and `notes` collections for docs where `handled != true`. None: say so in one line. For each one: act on it, record any decision in the master plan (or handoff doc), then `update` the doc with `handled: true` and a short `reply`. **Never read or republish the hub page to update it**; its state lives in the artifact database.
3. Report where things stand, the next action, and any steer/notes handled. Always include a handoff source line with the branch and snapshot commit used, for example `Handoff source — origin/claude/session (abc1234)`. Say `detached HEAD` for a detached checkout, and use `working directory (no Git commit)` for an unversioned handoff. If no handoff was read, say so.

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
7. Report the docs changed, hub version written (or "no hub" / skipped), and uncommitted state. In a repo with a remote, identify its default branch from `git ls-remote --symref origin HEAD` (use the project remote if it differs). If the work is on a different branch, name both branches and ask whether to merge into the default branch or record the work branch for the next session. If the branch is only local or its handoff changes have yet to be pushed, say so and ask for push approval before treating those changes as available to another session. If the default branch cannot be resolved, report the current branch and say the default is unknown. Always wait for explicit approval before merging.
