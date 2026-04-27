import click, subprocess
from pathlib import Path
from ..config import Colors

@click.command()
def gac():
    """Git add, commit, push"""
    msg = click.prompt(f"{Colors.BLUE}Commit message{Colors.RESET}", default="update")

    cmds = [
        ['git', 'add', '.'],
        ['git', 'commit', '-m', msg],
        ['git', 'push']
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and 'nothing to commit' not in result.stderr:
            click.echo(f"{Colors.RED}Error: {result.stderr}{Colors.RESET}")
            return

    click.echo(f"{Colors.GREEN}✅ Pushed: {msg}{Colors.RESET}")

@click.command()
def repo():
    """Create GitHub repo"""
    name = click.prompt(f"{Colors.BLUE}Repo name{Colors.RESET}", default=Path.cwd().name)
    private = click.confirm(f"{Colors.BLUE}Private repo?{Colors.RESET}", default=False)
    vis = '--private' if private else '--public'

    click.echo(f"{Colors.CYAN}Creating GitHub repo...{Colors.RESET}")

    # Check gh CLI
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except:
        click.echo(f"{Colors.YELLOW}Installing GitHub CLI...{Colors.RESET}")
        try:
            subprocess.run(['npm', 'install', '-g', '@github/cli'], capture_output=True)
        except Exception:
            click.echo(f"{Colors.RED}❌ Could not install gh. Please install it manually.{Colors.RESET}")
            return

    # Create repo
    result = subprocess.run(['gh', 'repo', 'create', name, vis, '--source=.', '--push'],
                          capture_output=True, text=True)

    if result.returncode == 0:
        try:
            user = subprocess.check_output(['gh', 'api', 'user', '--jq', '.login'], text=True).strip()
            url = f"https://github.com/{user}/{name}"
            click.echo(f"{Colors.GREEN}✅ Repo created: {url}{Colors.RESET}")
        except Exception:
            click.echo(f"{Colors.GREEN}✅ Repo created successfully!{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Error: {result.stderr}{Colors.RESET}")

@click.command()
def pr():
    """Create pull request"""
    title = click.prompt(f"{Colors.BLUE}PR title{Colors.RESET}")
    body = click.prompt(f"{Colors.BLUE}Description{Colors.RESET}", default="")

    # Push current branch
    try:
        branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
        subprocess.run(['git', 'push', '-u', 'origin', branch], capture_output=True)
    except Exception as e:
        click.echo(f"{Colors.RED}Error determining branch or pushing: {e}{Colors.RESET}")
        return

    # Create PR
    result = subprocess.run(['gh', 'pr', 'create', '--title', title, '--body', body],
                          capture_output=True, text=True)

    if result.returncode == 0:
        click.echo(f"{Colors.GREEN}✅ PR created: {result.stdout.strip()}{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}Error: {result.stderr}{Colors.RESET}")

@click.command()
def undo():
    """Undo last commit"""
    choice = click.prompt(f"{Colors.BLUE}Undo what?{Colors.RESET}\n1) Last commit (keep changes)\n2) Last commit (discard)\n3) Last push", type=click.Choice(['1','2','3']))

    if choice == '1':
        subprocess.run(['git', 'reset', '--soft', 'HEAD~1'])
        click.echo(f"{Colors.GREEN}✅ Undid commit, changes kept{Colors.RESET}")
    elif choice == '2':
        subprocess.run(['git', 'reset', '--hard', 'HEAD~1'])
        click.echo(f"{Colors.GREEN}✅ Undid commit, changes discarded{Colors.RESET}")
    else:
        try:
            branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
            subprocess.run(['git', 'push', '-f', 'origin', f'HEAD~1:{branch}'])
            click.echo(f"{Colors.GREEN}✅ Undid push{Colors.RESET}")
        except Exception:
             click.echo(f"{Colors.RED}Failed to determine branch for undoing push.{Colors.RESET}")

@click.command()
def branch_clean():
    """Delete merged branches"""
    result = subprocess.run(['git', 'branch', '--merged'], capture_output=True, text=True)
    branches = [b.strip() for b in result.stdout.split('\n') if b.strip() and b.strip() != '* main' and b.strip() != '* master']

    if branches:
        click.echo(f"{Colors.YELLOW}Deleting {len(branches)} merged branches...{Colors.RESET}")
        for branch in branches:
            subprocess.run(['git', 'branch', '-d', branch.replace('* ', '')])
        click.echo(f"{Colors.GREEN}✅ Cleaned{Colors.RESET}")
    else:
        click.echo(f"{Colors.GREEN}No branches to clean{Colors.RESET}")

@click.command()
def stash_all():
    """Stash all changes including untracked"""
    msg = click.prompt(f"{Colors.BLUE}Stash message{Colors.RESET}", default="wip")
    subprocess.run(['git', 'stash', 'push', '-u', '-m', msg])
    click.echo(f"{Colors.GREEN}✅ Stashed: {msg}{Colors.RESET}")

@click.command()
def changelog():
    """Generate changelog from commits"""
    result = subprocess.run(['git', 'log', '--pretty=format:%s', '-10'], capture_output=True, text=True)
    commits = result.stdout.split('\n')

    changelog = "# Changelog\n\n"
    for commit in commits:
        if commit:
            changelog += f"- {commit}\n"

    Path('CHANGELOG.md').write_text(changelog)
    click.echo(f"{Colors.GREEN}✅ CHANGELOG.md created{Colors.RESET}")

@click.command()
def sync():
    """Sync fork with upstream"""
    subprocess.run(['git', 'fetch', 'upstream'])
    subprocess.run(['git', 'checkout', 'main'])
    subprocess.run(['git', 'merge', 'upstream/main'])
    subprocess.run(['git', 'push'])
    click.echo(f"{Colors.GREEN}✅ Synced with upstream{Colors.RESET}")
