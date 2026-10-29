#!/usr/bin/env python3
"""Create a spike repo from an original repo and apply the spike overlay.

Works on Windows, macOS and Linux (Python 3.8+ and git on PATH).

    python new-spike.py

Run it from the folder that holds your original repo checkout (for example
repos/development), so the spike repo ends up next to it. It asks for the
original and spike repo URLs, the branch to track and what to do with each
submodule, shows a summary, and only makes changes once you confirm.
"""
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent


class Abort(Exception):
    pass


def git(*args, cwd=None):
    print('git ' + ' '.join(args), flush=True)
    try:
        subprocess.run(['git', *args], cwd=cwd, check=True)
    except FileNotFoundError:
        raise Abort('git not found on PATH')
    except subprocess.CalledProcessError as e:
        raise Abort(f'git {args[0]} failed (exit {e.returncode})')


def git_out(*args, cwd=None, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise Abort(f'git {args[0]} failed: {r.stderr.strip()}')
    return r.stdout.strip()


def ask(question, default=''):
    prompt = f'{question} [{default}]: ' if default else f'{question}: '
    try:
        answer = input(prompt).strip()
    except EOFError:
        raise Abort('no answer given')
    return answer or default


def ask_url(question):
    while True:
        url = ask(question)
        url = re.sub(r'^git\s+clone\s+', '', url).strip()   # pasted from a "git clone" copy button
        if url:
            return url
        print('  Please enter a URL.')


def project_name(url):
    """widget from git@host:alice/widget.git, https://host/alice/widget, C:\\repos\\widget.git"""
    last = re.split(r'[/\\:]', url.rstrip('/\\'))[-1]
    return last[:-4] if last.endswith('.git') else last


def remove_tree(path):
    """Delete a folder, including git's read-only files on Windows."""
    def make_writable(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=make_writable)


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


def gather(plan):
    """Ask everything, clone the original locally, and fill in the plan."""
    print('This creates a spike repo from your original repo. Nothing is changed\n'
          'until you confirm the summary at the end.\n')
    original_url = ask_url('Original repo URL')
    spike_url = ask_url('Spike repo URL (an empty repo)')
    project = ask('Project name', project_name(original_url))
    target = Path(ask('Folder to create', f'{project}-spike')).resolve()
    if target.exists():
        raise Abort(f'{target} already exists')

    print(f'\nReading the original repo (a local clone into {target}, removed if you cancel)...')
    plan.update(original_url=original_url, spike_url=spike_url, project=project, target=target)
    plan['cloned'] = True
    git('clone', original_url, str(target))

    default_branch = git_out('branch', '--show-current', cwd=target)
    branches = [b.split('/', 1)[1] for b in
                git_out('branch', '-r', '--format=%(refname:short)', cwd=target).split()
                if '/' in b and not b.endswith('/HEAD')]
    print('\nBranches: ' + ', '.join(branches))
    while True:
        branch = ask('Branch to track in the original repo', default_branch)
        if branch in branches:
            break
        print(f'  The original repo has no branch "{branch}".')
    plan['branch'] = branch
    if branch != default_branch:
        git('switch', branch, cwd=target)

    # Resolve submodule URLs (relative ones against the original repo) for the questions.
    git('submodule', 'init', cwd=target)
    subs = []
    found = submodules(target)
    if found:
        print('\nFor each submodule, enter the URL of its own spike repo if you want to\n'
              'change it in spikes, or press Enter to keep using the original.')
    for name, path, url in found:
        resolved = git_out('config', f'submodule.{name}.url', cwd=target)
        spike = ask_url_optional(f'Spike repo URL for submodule {path}')
        subs.append(dict(name=name, path=path, url=url, original=resolved, spike=spike))
    plan['submodules'] = subs


def ask_url_optional(question):
    url = ask(question + ' (Enter to keep the original)')
    return re.sub(r'^git\s+clone\s+', '', url).strip()


def summary(plan):
    p = plan
    lines = [
        '',
        'About to create the spike repo:',
        f'  Original repo:  {p["original_url"]}',
        f'  Spike repo:     {p["spike_url"]}  (must be empty)',
        f'  Folder:         {p["target"]}',
        f'  Branch:         {p["branch"]}',
        f'  Remotes:        origin = the spike repo; {p["project"]}-dev = the original, fetch only',
    ]
    if p['submodules']:
        lines.append('  Submodules:')
        for s in p['submodules']:
            if s['spike']:
                lines.append(f'    {s["path"]}: its spike repo {s["spike"]}'
                             f'  ({project_name(s["original"])}-dev = the original, fetch only)')
            elif s['url'] != s['original']:
                lines.append(f'    {s["path"]}: the original, with its relative URL made absolute'
                             f' ({s["original"]})')
            else:
                lines.append(f'    {s["path"]}: the original ({s["original"]})')
    lines.append('  Then commit the spike overlay and push it to the spike repo.')
    print('\n'.join(lines))
    original = p['target'].parent / p['project']
    if not original.is_dir():
        print(f'\n  Note: no original repo checkout found at {original}. The .claude deny rule\n'
              f'  and the spikes/README.md path examples assume it sits next to the spike repo.')


def apply(plan):
    p = plan
    target, project, branch = p['target'], p['project'], p['branch']
    dev_remote = f'{project}-dev'

    git('remote', 'rename', 'origin', dev_remote, cwd=target)
    git('remote', 'set-url', '--push', dev_remote, 'DISABLED', cwd=target)
    git('remote', 'add', 'origin', p['spike_url'], cwd=target)

    to_commit = []
    for s in p['submodules']:
        new_url = s['spike'] or s['original']
        if new_url != s['url']:
            git('config', '-f', '.gitmodules', f'submodule.{s["name"]}.url', new_url, cwd=target)
            if '.gitmodules' not in to_commit:
                to_commit.append('.gitmodules')
    if p['submodules']:
        git('submodule', 'sync', cwd=target)
        git('submodule', 'update', '--init', cwd=target)
        for s in p['submodules']:
            if s['spike']:
                sub = target / s['path']
                sub_remote = f'{project_name(s["original"])}-dev'
                git('remote', 'add', sub_remote, s['original'], cwd=sub)
                git('remote', 'set-url', '--push', sub_remote, 'DISABLED', cwd=sub)

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

    git('add', '-f', '--', *to_commit, cwd=target)   # -f: commit overlay files even if the inherited .gitignore matches them
    git('commit', '-m', 'Spike overlay', cwd=target)
    git('push', '-u', 'origin', branch, cwd=target)   # -u: track the spike repo, not the original

    print(f'\nSpike repo ready in {target} (tracking {dev_remote}/{branch})')
    subprocess.run(['git', 'remote', '-v'], cwd=target)
    for s in p['submodules']:
        if s['spike']:
            print(f'\nSubmodule {s["path"]}:', flush=True)
            subprocess.run(['git', 'remote', '-v'], cwd=target / s['path'])


def main():
    sys.stdout.reconfigure(line_buffering=True)   # keep our output in order with git's
    plan = {}
    confirmed = False
    try:
        gather(plan)
        summary(plan)
        confirmed = ask('\nGo ahead? (y/n)', 'n').lower() in ('y', 'yes')
        if not confirmed:
            raise Abort('cancelled; nothing was changed')
        apply(plan)
    except (Abort, KeyboardInterrupt) as e:
        if plan.get('cloned') and not confirmed and plan['target'].exists():
            remove_tree(plan['target'])
            print(f'\nRemoved the local clone {plan["target"]}.')
        msg = 'cancelled; nothing was changed' if isinstance(e, KeyboardInterrupt) else str(e)
        if confirmed:
            msg += f'\nThe spike repo folder {plan["target"]} is left as it is, so you can see what happened.'
        sys.exit(f'new-spike: {msg}')


if __name__ == '__main__':
    main()
