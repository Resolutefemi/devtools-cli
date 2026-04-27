import click, subprocess, os
from pathlib import Path
from ..config import Colors

@click.command()
def ship():
    """Deploy application (Vercel/Netlify/Render)"""
    click.echo(f"{Colors.CYAN}🚀 Renance Deployment Engine{Colors.RESET}")
    provider = click.prompt(f"{Colors.BLUE}Choose provider (1: Vercel, 2: Netlify, 3: Render){Colors.RESET}", type=click.Choice(['1','2','3']))
    name = click.prompt(f"{Colors.BLUE}Project/Domain name (leave blank for auto){Colors.RESET}", default="")
    
    if provider == '1':
        click.echo(f"{Colors.CYAN}Deploying to Vercel...{Colors.RESET}")
        cmd = ['npx', 'vercel', '--prod']
        if name:
            cmd.extend(['--name', name])
        subprocess.run(cmd)
    elif provider == '2':
        click.echo(f"{Colors.CYAN}Deploying to Netlify...{Colors.RESET}")
        cmd = ['npx', 'netlify-cli', 'deploy', '--prod']
        if name:
            cmd.extend(['--site', name])
        subprocess.run(cmd)
    elif provider == '3':
        click.echo(f"{Colors.CYAN}Deploying to Render...{Colors.RESET}")
        hook = click.prompt(f"{Colors.BLUE}Enter Render Deploy Hook URL{Colors.RESET}", default="")
        if hook:
            subprocess.run(['curl', '-X', 'POST', hook])
            click.echo(f"\n{Colors.GREEN}✅ Deployment triggered on Render!{Colors.RESET}")
        else:
            click.echo(f"{Colors.YELLOW}Render requires a Deploy Hook. Set it up in your Render dashboard.{Colors.RESET}")

@click.command()
def login():
    """Login to provider"""
    click.echo(f"{Colors.CYAN}Logging in to Vercel...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'login'])

@click.command()
def logout():
    """Logout from provider"""
    click.echo(f"{Colors.CYAN}Logging out of Vercel...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'logout'])
    click.echo(f"{Colors.GREEN}✅ Logged out{Colors.RESET}")

@click.command()
def live():
    """Check live status"""
    click.echo(f"{Colors.CYAN}Checking deployment status...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'ls'])

@click.command()
def env_push():
    """Push environment variables"""
    click.echo(f"{Colors.CYAN}Pushing .env to Vercel...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'env', 'pull'])
    click.echo(f"{Colors.GREEN}✅ Done{Colors.RESET}")

@click.command()
def logs():
    """View application logs"""
    click.echo(f"{Colors.CYAN}Tailing Vercel logs...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'logs'])
