# Spike Rules

This is **@PROJECT@-spike**, a clone of **@PROJECT@** (the original repo) for
fast, agentic prototyping. It tracks the original repo's `@BRANCH@` branch.
These rules override `CLAUDE.md` wherever they conflict.

## Purpose

Find out whether an idea works, quickly. Nothing here ships. Code from the spike
repo is never merged into the original repo; good ideas are reimplemented there
by hand, using the spike's diff (see [Porting a Spike](#porting-a-spike)) as a
reference.

## Allowed Here (Unlike the Original Repo)

- Stubs, `TODO` placeholders, hardcoded values, copy-paste and dead code.
- Changing any module, the build, or a submodule if the spike needs it (see
  [Submodules](#submodules)).
- New dependencies, if they're noted in the spike's notes.
- Skipping tests, docs and tidy-up, unless the spike is about them.

## Hard Rules

- **Never push to `@PROJECT@-dev`** (the original repo) **or any other `*-dev`
  remote.** Push only to `origin`.
- **Never open pull requests against the original repo.** Spike code reaches it
  only by being reimplemented there.
- Never run the original repo's release or publish scripts, and never add a
  remote for any public mirror of it.
- Don't edit `CLAUDE.md`. It's shared with the original repo and holds the
  agent instructions.
- In `.gitmodules`, only change a submodule's `url`, and only to point it at
  that submodule's own spike repo (see [Submodules](#submodules)).
  `new-spike.py` may also have made relative URLs absolute. Any other change
  can quietly point a submodule somewhere else, and conflicts on syncs.
- Only run `git submodule sync` straight after such a `url` change.
- `.gitignore` may be edited, but keep spike-only rules in a `# Spike` section
  in the middle of the file, away from the top and bottom where the original
  repo usually adds lines, so syncs merge cleanly. Rules for one folder can
  instead go in a `.gitignore` inside that folder (as `outputs/` does).
- Work on a `spike/<name>` branch. The only commits on `@BRANCH@` are merges
  from the original repo (see below) and submodule `url` changes.
- Never commit secrets, keys or credentials, even in throwaway code.

## Remotes

| Remote | Points At | Use |
|---|---|---|
| `origin` | the spike repo | fetch and push |
| `@PROJECT@-dev` | the original repo | fetch only (push URL is `DISABLED`) |

Check with `git remote -v`.

## Update `@BRANCH@` From the Original Repo

Do this before starting a spike. If a submodule has its own spike repo, update
that spike repo first (see [Submodules](#submodules)), or use
`scons fetch-dev`, which does both.

```sh
git switch --recurse-submodules @BRANCH@
git status                                # must show no uncommitted changes
git fetch @PROJECT@-dev
git merge --no-edit @PROJECT@-dev/@BRANCH@
git submodule update --init --recursive
git push origin @BRANCH@
```

`--recurse-submodules` moves submodules to the commit each branch records;
without it, a submodule left on another branch's commit shows as a change.

If the merge conflicts, fix the files, then `git add <files>` and
`git commit --no-edit`, or back out with `git merge --abort`.

## Each Spike

1. Update `@BRANCH@` from the original repo (above).
2. Create the branch and the notes:

   ```sh
   git switch -c spike/<name>
   ```

   Copy the notes template. In bash, zsh or PowerShell:

   ```sh
   cp notes/_template.md notes/<name>.md
   ```

   In Windows cmd:

   ```bat
   copy notes\_template.md notes\<name>.md
   ```

   Put the code in `spikes/<name>/` (see `spikes/README.md`) and fill in
   `notes/<name>.md` as you go: question, approach, result, what to port.
3. Commit often with short messages, and push the branch to keep its history.
   Messy history is fine.

   ```sh
   git add -A
   git commit -m "<what changed>"
   git push -u origin spike/<name>          # -u only needed the first time
   ```

4. To pick up newer changes from the original repo partway through:

   ```sh
   # update @BRANCH@ first (see above), then:
   git switch --recurse-submodules spike/<name>
   git merge @BRANCH@
   git submodule update --init --recursive
   ```

5. Screenshots and captures go in `outputs/`. Its own `.gitignore` keeps
   everything in it out of git, in every clone of the spike repo.

## Submodules

Each submodule is in one of two states. `git config -f .gitmodules --list`
shows which: a submodule pointing at a `-spike` URL has its own spike repo.

**Pointing at the original submodule repo.** Use it as it is: read and build
it, but don't commit changes inside it. You can't push them anywhere, so the
spike repo would record a submodule commit that nobody else can fetch.

**Pointing at its own spike repo** (for example `other-spike`). You can change
it as part of a spike. Inside the submodule, `origin` is its spike repo and
`<submodule>-dev` is the original submodule repo, fetch only.

1. Work on a branch with the same name in both repos:

   ```sh
   cd path/to/submodule
   git switch -c spike/<name>
   # ...change, then:
   git add -A
   git commit -m "<what changed>"
   git push -u origin spike/<name>
   ```

2. Then, in this repo on its own `spike/<name>` branch, record the new
   submodule commit. Do this **after** the push above, so the recorded commit
   exists in the submodule's spike repo:

   ```sh
   cd <back to this repo's root>
   git add path/to/submodule
   git commit -m "Update <submodule> for <name>"
   git push
   ```

3. When updating from the original repo, update the submodule's own spike repo
   first. Otherwise `git submodule update` here can't find the submodule commit
   the original repo now records. `scons fetch-dev` does this for you; with
   git alone, run this before the update above (`main` here is the
   submodule's spike repo branch):

   ```sh
   cd path/to/submodule
   git fetch origin
   git fetch <submodule>-dev
   git switch main                         # first time: git switch -c main --track origin/main
   git merge --ff-only origin/main
   git merge --no-edit <submodule>-dev/main
   git push origin main
   cd <back to this repo's root>
   git submodule update
   ```

To give a submodule its own spike repo later: create it with `new-spike.py`
from the submodule's original URL, then here, on `@BRANCH@`:

```sh
git config -f .gitmodules submodule.<name>.url <submodule-spike-url>
git submodule sync
git submodule update --init
git -C path/to/submodule remote add <submodule>-dev <original-submodule-url>
git -C path/to/submodule remote set-url --push <submodule>-dev DISABLED
git add .gitmodules
git commit -m "Point <submodule> at its spike repo"
git push
```

## Porting a Spike

To see only what a spike changed, without the spike repo's own files or the
merges from the original repo:

```sh
git diff @BRANCH@...spike/<name>
```

For a submodule with its own spike repo, run the same command inside it.

Reimplement what's worth keeping in the original repo, following its own
rules, and record what you ported in `notes/<name>.md`.

## SCons

If you wish to use SCons and avoid having to remember the git commands, the
spike repo adds a target for the update above. It's defined in
`spikes/SConscript`, which the original repo's `SConstruct` loads only when it
exists.

| Command | Does |
|---|---|
| `scons fetch-dev` | Updates the spike repo's `@BRANCH@` from the original repo: checks you're on a clean `@BRANCH@`, updates the spike repo of each submodule that has one, then fetches, merges `@PROJECT@-dev/@BRANCH@`, updates submodules and pushes to `origin`. |

`scons fetch-dev` stops without changing anything if you're not on `@BRANCH@`
or have uncommitted changes. If the merge conflicts it stops and tells you;
finish or abort the merge with git as described above (inside the submodule,
if that's where it stopped).

If the original repo builds with SCons, a plain `scons` here builds the same
targets, plus any spike-only targets added to `spikes/SConscript`.

## When in Doubt

Choose the fastest path to an answer, and write down in the notes what you
skipped.
