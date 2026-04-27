import click, subprocess
from pathlib import Path
from ..config import Colors

import click, subprocess, os
from pathlib import Path
from ..config import Colors

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
    click.echo(f"{Colors.CYAN}🚀 Starting Git & GitHub CLI installation...{Colors.RESET}")
    
    if os.name == 'nt':
        click.echo(f"{Colors.YELLOW}Detecting Windows environment...{Colors.RESET}")
        try:
            # Check for winget
            subprocess.run('winget --version', shell=True, capture_output=True, check=True)
            
            click.echo(f"{Colors.CYAN}Installing Git...{Colors.RESET}")
            subprocess.run('winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements', shell=True, check=True)
            
            click.echo(f"{Colors.CYAN}Installing GitHub CLI...{Colors.RESET}")
            subprocess.run('winget install --id GitHub.cli -e --source winget --accept-source-agreements --accept-package-agreements', shell=True, check=True)
            
        except subprocess.CalledProcessError:
            click.echo(f"{Colors.RED}❌ Winget (Windows Package Manager) not found or failed.{Colors.RESET}")
            click.echo(f"Please install manually from: https://git-scm.com/ and https://cli.github.com/")
        except Exception as e:
            click.echo(f"{Colors.RED}Installation failed: {e}{Colors.RESET}")
            click.echo(f"Please install manually from: https://git-scm.com/ and https://cli.github.com/")
    elif 'com.termux' in os.environ.get('PREFIX', ''):
        click.echo(f"{Colors.YELLOW}Detecting Termux...{Colors.RESET}")
        subprocess.run(['pkg', 'install', 'git', 'gh', '-y'])
    else:
        click.echo(f"{Colors.YELLOW}Detecting Unix-like OS...{Colors.RESET}")
        click.echo("Please use your package manager (apt, brew, dnf) to install 'git' and 'gh'.")

    click.echo(f"{Colors.GREEN}✅ Installation process triggered. Please RESTART your terminal.{Colors.RESET}")

@click.command(name='gh')
def gh_login():
    """Login to GitHub"""
    try:
        subprocess.run(['gh', 'auth', 'login'], check=True)
        click.echo(f"{Colors.GREEN}✅ Logged in successfully!{Colors.RESET}")
    except FileNotFoundError:
        click.echo(f"{Colors.RED}❌ GitHub CLI (gh) is not installed. Run 'dt git-install' first.{Colors.RESET}")
    except Exception as e:
        click.echo(f"{Colors.RED}❌ Login failed: {e}{Colors.RESET}")

@click.command()
def gac():
    """Git add, commit, push (with auto-setup checks)"""
    # 1. Check for Git
    if not is_git_installed():
        click.echo(f"{Colors.RED}❌ Git is not installed on this system.{Colors.RESET}")
        if click.confirm(f"{Colors.CYAN}Would you like to install Git and GitHub CLI now?{Colors.RESET}"):
            ctx = click.get_current_context()
            ctx.invoke(git_install)
        return

    # 2. Check for login
    if not is_gh_logged_in():
        click.echo(f"{Colors.YELLOW}⚠️ You are not logged into GitHub.{Colors.RESET}")
        if click.confirm(f"{Colors.CYAN}Would you like to login now?{Colors.RESET}"):
            ctx = click.get_current_context()
            ctx.invoke(gh_login)
        else:
            click.echo(f"{Colors.RED}Aborting gac: Login required to push.{Colors.RESET}")
            return

    # 3. Check if repo is initialized
    if not Path('.git').exists():
        if click.confirm(f"{Colors.YELLOW}Git not initialized in this folder. Initialize now?{Colors.RESET}"):
            subprocess.run(['git', 'init'])
        else:
            return

    msg = click.prompt(f"{Colors.BLUE}Commit message{Colors.RESET}", default="update")

    cmds = [
        ['git', 'add', '.'],
        ['git', 'commit', '-m', msg],
        ['git', 'push']
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            if 'nothing to commit' in result.stderr:
                click.echo(f"{Colors.YELLOW}Nothing to commit, working tree clean.{Colors.RESET}")
                return
            if 'no upstream branch' in result.stderr:
                click.echo(f"{Colors.YELLOW}Setting upstream and pushing...{Colors.RESET}")
                subprocess.run(['git', 'push', '-u', 'origin', 'HEAD'])
                break
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
