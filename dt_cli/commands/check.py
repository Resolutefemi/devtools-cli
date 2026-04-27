import click, sys, subprocess, os
from pathlib import Path
from ..config import Colors

@click.command()
def check():
    """Run basic project checks"""
    click.echo(f"{Colors.CYAN}Running basic checks...{Colors.RESET}")
    
    if Path('package.json').exists():
        click.echo(f"{Colors.GREEN}✅ Node.js project detected{Colors.RESET}")
    elif Path('requirements.txt').exists():
        click.echo(f"{Colors.GREEN}✅ Python project detected{Colors.RESET}")
    elif Path('Cargo.toml').exists():
        click.echo(f"{Colors.GREEN}✅ Rust project detected{Colors.RESET}")
    elif Path('go.mod').exists():
        click.echo(f"{Colors.GREEN}✅ Go project detected{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}⚠️ No specific project configuration found (Node/Python/Rust/Go){Colors.RESET}")

    if Path('.git').exists():
        click.echo(f"{Colors.GREEN}✅ Git initialized{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}⚠️ Git not initialized{Colors.RESET}")

@click.command()
def doctor():
    """Run comprehensive system diagnostic"""
    click.echo(f"{Colors.CYAN}Running diagnostics...{Colors.RESET}")
    tools = ['git', 'node', 'python', 'npm', 'pip']
    all_good = True
    for tool in tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            click.echo(f"{Colors.GREEN}✅ {tool} is installed{Colors.RESET}")
        except FileNotFoundError:
            click.echo(f"{Colors.RED}❌ {tool} is missing{Colors.RESET}")
            all_good = False
            
    if all_good:
        click.echo(f"{Colors.CYAN}✅ Everything looks good!{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}⚠️ Some tools are missing.{Colors.RESET}")
