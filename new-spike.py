#!/usr/bin/env python3
"""Create a spike repo from an original repo and apply the spike overlay.

Works on Windows, macOS and Linux (Python 3.8+ and git on PATH).

    python new-spike.py <original-url> <spike-url> [dir]

    original-url  any git URL, e.g. git@git.example.com:alice/widget.git
                  or https://git.example.com/alice/widget.git
    spike-url     an EMPTY repo to hold the spikes, e.g. git@git.example.com:alice/widget-spike.git
    dir           where to clone (default: ./<project>-spike in the current folder)

Run it from the folder that holds your original repo checkout, so the spike
repo ends up next to it.

It asks which branch of the original repo to track (default: its default
branch) and, for each submodule, whether to point it at a spike repo of its
own. Use --branch and --submodule to answer in advance, or --yes to accept
the defaults without asking.

On Windows, `py new-spike.py ...` also works.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent


def die(msg):
    sys.exit(f'new-spike: {msg}')


def git(*args, cwd=None):
    print('git ' + ' '.join(args))
    try:
        subprocess.run(['git', *args], cwd=cwd, check=True)
    except FileNotFoundError:
        die('git not found on PATH')
    except subprocess.CalledProcessError as e:
        die(f'git {args[0]} failed (exit {e.returncode})')


def git_out(*args, cwd=None, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        die(f'git {args[0]} failed: {r.stderr.strip()}')
    return r.stdout.strip()


def project_name(url):
    """widget from git@host:alice/widget.git, https://host/alice/widget, C:\\repos\\widget.git"""
    last = re.split(r'[/\\:]', url.rstrip('/\\'))[-1]
    return last[:-4] if last.endswith('.git') else last


def is_relative(url):
    return url.startswith('./') or url.startswith('../')


def ask(question, default, interactive):
    if not interactive:
        return default
    answer = input(f'{question} [{default}]: ' if default else f'{question}: ').strip()
    return answer or default


def submodules(repo):
    """[(name, path, url-in-.gitmodules)] for the top-level submodules."""
    if not (repo / '.gitmodules').exists():
        return []
    out = git_out('config', '-f', '.gitmodules', '--get-regexp', r'^submodule\..*\.path$',
                  cwd=repo, check=False)
    result = []
    for line in out.splitlines():
        key, path = line.split(' ', 1)
        name = key[len('submodule.'):-len('.path')]
        url = git_out('config', '-f', '.gitmodules', f'submodule.{name}.url', cwd=repo)
        result.append((name, path, url))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('original_url', metavar='original-url')
    p.add_argument('spike_url', metavar='spike-url')
    p.add_argument('dir', nargs='?')
    p.add_argument('--project', help='project name (default: original repo name)')
    p.add_argument('--branch', help="original repo branch to track (default: its default branch)")
    p.add_argument('--submodule', action='append', default=[], metavar='PATH=URL',
                   help="point the submodule at PATH at its spike repo URL (repeatable)")
    p.add_argument('--yes', action='store_true', help='accept defaults instead of asking')
    p.add_argument('--no-push', action='store_true', help='do everything except the final push')
    a = p.parse_args()
    sys.stdout.reconfigure(line_buffering=True)   # keep our output in order with git's
    interactive = sys.stdin.isatty() and not a.yes

    sub_spikes = {}
    for item in a.submodule:
        path, sep, url = item.partition('=')
        if not sep or not path or not url:
            die(f'--submodule expects PATH=URL, got "{item}"')
        sub_spikes[path.strip('/\\')] = url

    project = a.project or project_name(a.original_url)
    if not project:
        die('could not work out the project name; pass --project')
    dev_remote = f'{project}-dev'
    target = Path(a.dir) if a.dir else Path.cwd() / f'{project}-spike'
    if target.exists():
        die(f'{target} already exists')

    git('clone', a.original_url, str(target))

    # Branch to track.
    default_branch = git_out('branch', '--show-current', cwd=target)
    branch = a.branch or ask('Branch to track in the original repo', default_branch, interactive)
    if branch != default_branch:
        if not git_out('rev-parse', '--verify', '--quiet', f'refs/remotes/origin/{branch}',
                       cwd=target, check=False):
            die(f'the original repo has no branch "{branch}"')
        git('switch', branch, cwd=target)

    # Record submodule URLs while origin still points at the original repo, so
    # relative URLs (../other.git) resolve next to it rather than the spike repo.
    git('submodule', 'init', cwd=target)

    # Remotes: the original repo becomes fetch-only (<project>-dev), the spike repo becomes origin.
    git('remote', 'rename', 'origin', dev_remote, cwd=target)
    git('remote', 'set-url', '--push', dev_remote, 'DISABLED', cwd=target)
    git('remote', 'add', 'origin', a.spike_url, cwd=target)

    # Submodules: point each at its own spike repo, or at the original's absolute URL.
    to_commit = []
    spiked = []          # (path, original absolute URL)
    subs = submodules(target)
    for name, path, url in subs:
        original_url = git_out('config', f'submodule.{name}.url', cwd=target)
        spike = sub_spikes.pop(path, None)
        if spike is None:
            spike = ask(f'Spike repo URL for submodule {path} (Enter to keep using {original_url})',
                        '', interactive)
        new_url = spike or original_url
        if spike:
            spiked.append((path, original_url))
        if new_url != url:
            git('config', '-f', '.gitmodules', f'submodule.{name}.url', new_url, cwd=target)
            if '.gitmodules' not in to_commit:
                to_commit.append('.gitmodules')
    if sub_spikes:
        die('no submodule at: ' + ', '.join(sub_spikes))
    if subs:
        git('submodule', 'sync', cwd=target)
        git('submodule', 'update', '--init', cwd=target)
        for path, original_url in spiked:
            sub = target / path
            sub_remote = f'{project_name(original_url)}-dev'
            git('remote', 'add', sub_remote, original_url, cwd=sub)
            git('remote', 'set-url', '--push', sub_remote, 'DISABLED', cwd=sub)

    # Copy the overlay, filling in the names. Never overwrite the original repo's files.
    fills = {'@PROJECT@': project, '@BRANCH@': branch}
    overlay = KIT / 'overlay'
    for src in sorted(s for s in overlay.rglob('*') if s.is_file()):
        rel = src.relative_to(overlay)
        dest = target / rel
        if dest.exists():
            print(f'new-spike: skipping {rel.as_posix()} (already in the original repo)')
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding='utf-8')
        for key, value in fills.items():
            text = text.replace(key, value)
        dest.write_text(text, encoding='utf-8', newline='\n')
        to_commit.append(rel.as_posix())
    if not to_commit:
        die('nothing to add')

    git('add', '-f', '--', *to_commit, cwd=target)   # -f: commit overlay files even if the spike repo's inherited .gitignore matches them
    git('commit', '-m', 'Spike overlay', cwd=target)

    if a.no_push:
        print(f"new-spike: --no-push given; run 'git push -u origin {branch}' when ready.")
    else:
        git('push', '-u', 'origin', branch, cwd=target)   # -u: track the spike repo, not the original

    original = target.resolve().parent / project
    if not original.is_dir():
        print(f'\nnew-spike: note: no original repo checkout found at {original}.')
        print('  .claude/settings.json and spikes/README.md assume it sits next to the spike repo.')

    print(f'\nSpike repo ready in {target} (tracking {dev_remote}/{branch})')
    subprocess.run(['git', 'remote', '-v'], cwd=target)
    for path, _ in spiked:
        print(f'\nSubmodule {path}:')
        subprocess.run(['git', 'remote', '-v'], cwd=target / path)


if __name__ == '__main__':
    main()
