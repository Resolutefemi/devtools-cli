import click, subprocess, os
from pathlib import Path
from ..config import console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box


def is_git_installed():
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def is_gh_logged_in():
    try:
        result = subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


@click.command(name='git-install')
def git_install():
    """Install Git and GitHub CLI automatically"""
    console.print("[info]Starting Git & GitHub CLI installation...[/info]")

    if os.name == 'nt':
        console.print("[dim]Detecting Windows...[/dim]")
        try:
            subprocess.run('winget --version', shell=True, capture_output=True, check=True)
            console.print("[info]Installing Git...[/info]")
            subprocess.run('winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements', shell=True, check=True)
            console.print("[info]Installing GitHub CLI...[/info]")
            subprocess.run('winget install --id GitHub.cli -e --source winget --accept-source-agreements --accept-package-agreements', shell=True, check=True)
        except subprocess.CalledProcessError:
            console.print("[red]Winget not found. Install manually from git-scm.com[/red]")
        except Exception as e:
            console.print(f"[red]Installation failed: {e}[/red]")
    elif 'com.termux' in os.environ.get('PREFIX', ''):
        console.print("[dim]Detecting Termux...[/dim]")
        subprocess.run(['pkg', 'install', 'git', 'gh', '-y'])
    else:
        console.print("[dim]Use your package manager: apt install git gh / brew install git gh[/dim]")

    console.print("[success]Installation triggered. Restart your terminal.[/success]")


@click.command(name='gh')
def gh_login():
    """Login to GitHub"""
    try:
        subprocess.run(['gh', 'auth', 'login'], check=True)
        console.print("[success]Logged in successfully![/success]")
    except FileNotFoundError:
        console.print("[red]GitHub CLI (gh) not installed. Run 'dt git-install' first.[/red]")
    except Exception as e:
        console.print(f"[red]Login failed: {e}[/red]")


@click.command()
def gac():
    """Git add, commit, push (with auto-setup checks)"""
    if not is_git_installed():
        console.print("[red]Git is not installed.[/red]")
        if Confirm.ask("[info]Install Git and GitHub CLI now?[/info]"):
            git_install()
        return

    if not is_gh_logged_in():
        console.print("[yellow]You are not logged into GitHub.[/yellow]")
        if Confirm.ask("[info]Login now?[/info]"):
            gh_login()
        else:
            console.print("[red]Login required to push.[/red]")
            return

    if not Path('.git').exists():
        if Confirm.ask("[yellow]Git not initialized. Initialize now?[/yellow]"):
            subprocess.run(['git', 'init'])
        else:
            return

    msg = Prompt.ask("[info]Commit message[/info]", default="update")

    cmds = [['git', 'add', '.'], ['git', 'commit', '-m', msg], ['git', 'push']]

    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            if 'nothing to commit' in result.stderr:
                console.print("[yellow]Nothing to commit, working tree clean.[/yellow]")
                return
            if 'no upstream branch' in result.stderr:
                console.print("[info]Setting upstream and pushing...[/info]")
                subprocess.run(['git', 'push', '-u', 'origin', 'HEAD'])
                break
            console.print(f"[red]Error: {result.stderr}[/red]")
            return

    console.print(f"[success]Pushed: {msg}[/success]")


@click.command()
def repo():
    """Create GitHub repo from current directory"""
    name = Prompt.ask("[info]Repo name[/info]", default=Path.cwd().name)
    private = Confirm.ask("[info]Private repo?[/info]", default=False)
    vis = '--private' if private else '--public'

    console.print("[info]Creating GitHub repo...[/info]")
    result = subprocess.run(['gh', 'repo', 'create', name, vis, '--source=.', '--push'], capture_output=True, text=True)

    if result.returncode == 0:
        try:
            user = subprocess.check_output(['gh', 'api', 'user', '--jq', '.login'], text=True).strip()
            console.print(f"[success]Repo created: https://github.com/{user}/{name}[/success]")
        except Exception:
            console.print("[success]Repo created successfully![/success]")
    else:
        console.print(f"[red]Error: {result.stderr}[/red]")


@click.command()
def pr():
    """Create pull request"""
    title = Prompt.ask("[info]PR title[/info]")
    body = Prompt.ask("[info]Description[/info]", default="")

    try:
        branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
        subprocess.run(['git', 'push', '-u', 'origin', branch], capture_output=True)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    result = subprocess.run(['gh', 'pr', 'create', '--title', title, '--body', body], capture_output=True, text=True)

    if result.returncode == 0:
        console.print(f"[success]PR created: {result.stdout.strip()}[/success]")
    else:
        console.print(f"[red]Error: {result.stderr}[/red]")


@click.command()
def undo():
    """Undo last commit or push"""
    console.print("[bold]Undo what?[/bold]")
    console.print("  [accent]1[/accent]. Last commit (keep changes)")
    console.print("  [accent]2[/accent]. Last commit (discard changes)")
    console.print("  [accent]3[/accent]. Last push")
    choice = Prompt.ask("[info]Choose[/info]", choices=["1", "2", "3"])

    if choice == '1':
        subprocess.run(['git', 'reset', '--soft', 'HEAD~1'])
        console.print("[success]Undid commit, changes kept.[/success]")
    elif choice == '2':
        subprocess.run(['git', 'reset', '--hard', 'HEAD~1'])
        console.print("[success]Undid commit, changes discarded.[/success]")
    else:
        try:
            branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
            subprocess.run(['git', 'push', '-f', 'origin', f'HEAD~1:{branch}'])
            console.print("[success]Undid push.[/success]")
        except Exception:
            console.print("[red]Failed to determine branch.[/red]")


@click.command(name='branch-clean')
def branch_clean():
    """Delete merged branches"""
    result = subprocess.run(['git', 'branch', '--merged'], capture_output=True, text=True)
    branches = [b.strip() for b in result.stdout.split('\n') if b.strip() and b.strip() not in ('* main', '* master', 'main', 'master')]

    if branches:
        console.print(f"[info]Deleting {len(branches)} merged branches...[/info]")
        for branch in branches:
            subprocess.run(['git', 'branch', '-d', branch.replace('* ', '')])
        console.print("[success]Cleaned![/success]")
    else:
        console.print("[success]No branches to clean.[/success]")


@click.command(name='stash-all')
def stash_all():
    """Stash all changes including untracked files"""
    msg = Prompt.ask("[info]Stash message[/info]", default="wip")
    subprocess.run(['git', 'stash', 'push', '-u', '-m', msg])
    console.print(f"[success]Stashed: {msg}[/success]")


@click.command()
def changelog():
    """Generate CHANGELOG.md from last 10 commits"""
    result = subprocess.run(['git', 'log', '--pretty=format:%s', '-10'], capture_output=True, text=True)
    commits = [c for c in result.stdout.split('\n') if c.strip()]

    content = "# Changelog\n\n"
    for commit in commits:
        content += f"- {commit}\n"

    Path('CHANGELOG.md').write_text(content)
    console.print(f"[success]CHANGELOG.md created ({len(commits)} commits)[/success]")


@click.command()
def sync():
    """Sync fork with upstream"""
    console.print("[info]Syncing with upstream...[/info]")
    subprocess.run(['git', 'fetch', 'upstream'], capture_output=True)
    subprocess.run(['git', 'checkout', 'main'], capture_output=True)
    subprocess.run(['git', 'merge', 'upstream/main'], capture_output=True)
    subprocess.run(['git', 'push'], capture_output=True)
    console.print("[success]Synced with upstream.[/success]")