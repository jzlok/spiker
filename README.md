# Spiker

This toolkit clones any git repo (your original repo) into a spike repo: a
sandbox for experimentation. It is intended for agentic workflows and/or to keep
experimental spikes and noisy history out of your original repo.

## Contents

- [Workflow](#workflow)
- [Spiker Layout](#spiker-layout)
- [New Spike Repo Layout](#new-spike-repo-layout)
- [Preparing Your Original Repo](#preparing-your-original-repo)
- [Making a Spike Repo](#making-a-spike-repo)
- [Day-to-Day Use](#day-to-day-use)
- [Submodules](#submodules)
- [SCons](#scons)
- [Agents](#agents)
- [gitignore](#gitignore)
- [Caveats](#caveats)
- [License](#license)

## Workflow

The following workflow may give you a better idea:

1. Prepare your original repo (see [Preparing Your Original Repo](#preparing-your-original-repo)).
2. If your original repo has submodules you'll want to change in spikes, create
   a spike repo for each of those submodules first (see [Submodules](#submodules)).
3. Create the spike repo, pointing those submodules at their spike repos (see
   [Making a Spike Repo](#making-a-spike-repo)).
4. Add a `# Spike` section to your spike repo's `.gitignore` for anything you
   don't want committed (optional; see [gitignore](#gitignore)).
5. For each experiment, create a `spike/<name>` branch and write the code in
   `spikes/<name>/`. If the spike changes a submodule that has its own spike
   repo, use a `spike/<name>` branch in the submodule too.
6. Commit and push the spike branch to the spike repo as you go, pushing any
   submodule changes first. Its history stays in the spike repo; it never
   reaches your original repo.
7. Use the spikes as references to make new updates to your original repo. You
   can do this manually or with agents working to stricter conventions and
   rules, refactoring to production-level code as necessary.
8. Submit your production-level code to your original repo, taking advantage of
   code review and CI/CD.
9. Update the spike repo from the original repo (so new spikes build on your
   approved code), updating any submodule spike repos first.
10. Repeat from #5.

The git commands for these steps are listed in
[Day-to-Day Use](#day-to-day-use) and [Submodules](#submodules), and in full in
each spike repo's `SPIKE.md`. See [SCons](#scons) for a one-command shortcut
for updating the spike repo.

Before you start, read [Caveats](#caveats): Spiker makes a few assumptions
about your original repo.

## Spiker Layout

```
spiker/
  README.md             this file
  LICENSE               MIT license
  new-spike.py          run this (Windows, macOS, Linux)
  overlay/              copied into the spike repo; @PROJECT@ and @BRANCH@
                        are replaced with the project and branch names
    SPIKE.md            spike rules (CLAUDE.md defers to it)
    .claude/settings.json   asks Claude Code to refuse edits to ../<project>
    notes/_template.md  spike notes template
    spikes/README.md    how spikes are laid out
    spikes/SConscript   optional SCons shortcut and spike-only build targets
    outputs/.gitignore  keeps outputs/ (screenshots, captures) out of git
```

## New Spike Repo Layout

What `new-spike.py` produces: a full clone of your original repo, with the
overlay committed on top.

```
widget-spike/
  ...                   everything from your original repo, with its history
  SPIKE.md              spike rules for people and agents
  .claude/settings.json   asks Claude Code to refuse edits to ../widget
  notes/
    _template.md        copy to notes/<name>.md for each spike
  spikes/
    README.md           how spikes are laid out
    SConscript          optional SCons shortcut (scons fetch-dev)
    <name>/             one folder per spike, on branch spike/<name>
  outputs/              screenshots, captures, agent output (never committed)
    .gitignore
```

Remotes:

| Remote | Points At | Use |
|---|---|---|
| `origin` | the spike repo | fetch and push |
| `widget-dev` | your original repo | fetch only (push is `DISABLED`) |

## Preparing Your Original Repo

Do this once, in your original repo, and push it before making a spike repo.
The spike repo can't make these changes itself, because `SPIKE.md` forbids
editing `CLAUDE.md` there.

1. Add this line to your original repo's `CLAUDE.md` (or your agents'
   equivalent, such as `AGENTS.md`), creating the file if needed:

   ```md
   If SPIKE.md exists, follow it; it overrides these rules.
   ```

   Without it, agents in the spike repo never read `SPIKE.md`. The line does
   nothing in the original repo, where `SPIKE.md` doesn't exist.
2. If you want the SCons shortcut, add the `SConstruct` hook described in
   [SCons](#scons).

## Making a Spike Repo

1. Create an empty repo on your git host to hold the spikes, with no README,
   license or `.gitignore`. If it already has a commit, git will reject the
   script's push.
2. From the folder that holds your original repo checkout, run the script. It
   works from any terminal (PowerShell, cmd, bash, zsh) and needs Python 3.8+
   and git on your PATH:

   ```sh
   python path/to/spiker/new-spike.py git@git.example.com:alice/widget.git git@git.example.com:alice/widget-spike.git
   ```

   On Windows, `py new-spike.py ...` also works; on macOS and Linux, use
   `python3` if `python` isn't found.
3. Answer its questions:
   - **Branch to track in the original repo.** Press Enter for the original
     repo's default branch. The spike repo uses the same branch name, and it's
     written into `SPIKE.md` and `spikes/SConscript`.
   - **A spike repo URL for each submodule,** if there are any. Enter the URL of
     the submodule's spike repo to point it there, or press Enter to keep using
     the original submodule repo (see [Submodules](#submodules)).

For an original repo called `widget`, the script clones it to `./widget-spike`
(next to your `widget` checkout), renames its remote to `widget-dev` with
pushing disabled, adds the spike repo as `origin`, sets up the submodules,
copies the overlay, commits it and pushes. It warns you if it can't find
`widget` next to the new spike repo. Any URL git accepts works: SSH, HTTPS or a
local path.

Options:

| Option | Does |
|---|---|
| `--branch <name>` | branch to track, without asking |
| `--submodule <path>=<url>` | point the submodule at `<path>` at its spike repo, without asking (repeat for each) |
| `--yes` | accept the defaults for anything not given, without asking |
| `--project <name>` | override the project name (default: the original repo's name) |
| `--no-push` | do everything except the final push |
| third argument | where to clone (default: `./<project>-spike`) |

## Day-to-Day Use

To update the spike repo's main branch from your original repo, run these from
inside the spike repo. The examples use `main` and the `widget-dev` remote;
your spike repo's `SPIKE.md` has the branch and remote names you chose.

```sh
git switch --recurse-submodules main
git status                                # must show no uncommitted changes
git fetch widget-dev
git merge --no-edit widget-dev/main
git submodule update --init --recursive
git push origin main
```

Then, to bring those changes into a spike in progress:

```sh
git switch --recurse-submodules spike/<name>
git merge main
git submodule update --init --recursive
```

If any submodules have their own spike repos, update those first (see
[Submodules](#submodules)).

The full workflow (spike branches, notes, porting diffs, merge conflicts) is in
each spike repo's `SPIKE.md`.

## Submodules

Each submodule in the spike repo either keeps using the original submodule
repo, or points at a spike repo of its own.

**Keeping the original submodule repo.** Choose this for submodules your spikes
only read and build. If the submodule's URL in `.gitmodules` is relative (such
as `../other.git`), the script rewrites it as an absolute URL, so anyone who
clones the spike repo can still fetch it. A relative URL would otherwise be
looked up next to the spike repo. Don't commit changes inside such a submodule: there's nowhere to
push them, so the spike repo would record a commit nobody else can fetch.

**Giving the submodule its own spike repo.** Choose this for submodules your
spikes will change.

1. Make the submodule's spike repo first, with `new-spike.py` and the
   submodule's original URL, just like any other spike repo:

   ```sh
   python path/to/spiker/new-spike.py git@git.example.com:alice/other.git git@git.example.com:alice/other-spike.git
   ```

2. Make the parent spike repo, and give the submodule's spike repo URL when
   asked (or pass `--submodule ext/other=git@git.example.com:alice/other-spike.git`).
   The script points the submodule at its spike repo in `.gitmodules`, and adds
   an `other-dev` fetch-only remote inside the submodule for the original
   submodule repo.
3. In a spike, use the same `spike/<name>` branch in both repos. Commit and push
   inside the submodule first, then `git add` the submodule in the parent and
   commit and push there. The parent records a submodule commit, which must
   already be in the submodule's spike repo.
4. When updating, update the submodule's spike repo from its original first,
   then the parent. The original parent repo may now record a submodule commit
   the submodule's spike repo hasn't got yet. `scons fetch-dev` in the parent
   does both in that order (see [SCons](#scons)); with git alone, follow the
   steps in `SPIKE.md`.

To give a submodule its own spike repo after the parent spike repo exists, see
the steps in `SPIKE.md`.

## SCons

[SCons](https://scons.org) is a make-like build utility that uses Python
scripting.

If you wish to use SCons and avoid having to remember the git commands, each
spike repo's `spikes/SConscript` adds a shortcut:

```sh
scons fetch-dev     # same as the update commands above
```

It refuses to run unless you're on the main branch with no uncommitted changes
(in the spike repo or its submodules). For each submodule with its own spike
repo, it first merges the original submodule repo into that spike repo and
pushes it, then updates the spike repo itself, so the order is always right.
The submodules don't need SCons for this.

In order to use this:

1. Install SCons ([download link](https://scons.org/pages/download.html)) if
   you don't already have it.
2. In the root of your original repo, add the hook below to the end of your
   `SConstruct`, after `env` is defined. If you don't have a `SConstruct`,
   create one containing just this:

   ```python
   # This snippet adds spike-specific SCons commands to your spike repo,
   # while keeping such spike-specific commands out of your original repo.
   env = Environment()          # omit if your SConstruct already defines env
   Export('env')

   spike = File('#spikes/SConscript')
   if spike.exists():
       SConscript(spike)
   ```

3. Push it to the original repo.
4. Create the spike repo, or update an existing spike repo from your original
   repo.

## Agents

`SPIKE.md` is pre-configured to do experimental work, avoid creating PRs and
avoid updating your original repo (pushing from your spike repo to your
original repo is `DISABLED` via git as an extra precaution). It only takes
effect once your original repo's `CLAUDE.md` points to it (see
[Preparing Your Original Repo](#preparing-your-original-repo)).

`.claude/settings.json` additionally asks Claude Code to refuse edits to your
original repo checkout. Other agents ignore it.

You can change and add rules as you like.

## gitignore

If you wish to add extra assets, tools, code, etc. into your spike repo but
don't want them committed, then it is okay to edit the `.gitignore` that is
fetched from the original repo.

It is recommended to add a `# Spike` section somewhere in the middle of the
`.gitignore` for this. Adding entries in the middle of the `.gitignore` will
make merging updates to the `.gitignore` from the original repo much easier.

## Caveats

Spiker assumes a few things about your original repo. If any of these don't
hold, you may need to change the files listed.

- **The original repo is checked out next to the spike repo,** in a folder named
  after the project (for example `widget/` beside `widget-spike/`).
  `.claude/settings.json` and the path examples in `spikes/README.md` rely on
  this. Run the script from the folder holding your checkout, or edit those
  files.
- **Claude Code is started from the spike repo's root.** The deny rules in
  `.claude/settings.json` (`Edit(../widget/**)`) are relative to the folder
  Claude Code was started in. Started from a subfolder, they protect the wrong
  place.
- **Only Claude Code reads `.claude/settings.json`.** Other agents rely on
  `SPIKE.md` alone, through your `CLAUDE.md` or `AGENTS.md`.
- **Only top-level submodules are set up.** Submodules inside submodules keep
  their original URLs; if they're relative, they may not resolve in the spike
  repo.
- **The spike repo's `.gitmodules` differs from the original's** wherever the
  script changed a URL. If the original repo later changes the same lines, the
  update merge will conflict there; keep the spike repo's URLs when resolving.
- **The fetch-only remote is named `<project>-dev`.** The name comes from the
  original URL or `--project`. Rename it with `git remote rename` if you like,
  but then update `spikes/SConscript` (`DEV_REMOTE`) to match.
- **The SCons hook needs `env` defined and exported** before it runs, and it
  looks for `spikes/SConscript` relative to the `SConstruct`. If your
  `SConstruct` isn't in the repo root, change the path (for example
  `'#/../spikes/SConscript'`).
- **Windows cmd has no `cp`.** `SPIKE.md` gives the `copy` equivalent; the other
  commands are git and work in any terminal.

## License

See [the LICENSE file](LICENSE) in this repo for the open-source license and
copyright.
