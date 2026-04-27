import click, subprocess, os
from pathlib import Path
from ..config import Colors

@click.command()
def ship():
    """Deploy application (Vercel/Netlify/Render)"""
    click.echo(f"{Colors.CYAN}🚀 Renance Deployment Engine{Colors.RESET}")
    provider = click.prompt(f"{Colors.BLUE}Choose provider (1: Vercel, 2: Netlify, 3: Render){Colors.RESET}", type=click.Choice(['1','2','3']))
    
    use_shell = os.name == 'nt'
    
    if provider == '1': # Vercel
        # Check login
        click.echo(f"{Colors.CYAN}Checking Vercel authentication... (this may take a moment on first run){Colors.RESET}")
        # Using --yes to bypass "Need to install..." prompt which causes hangs
        check = subprocess.run(['npx', '--yes', 'vercel', 'whoami'], shell=use_shell, capture_output=True)
        
        if check.returncode != 0:
            click.echo(f"{Colors.YELLOW}You are not logged in or Vercel is not initialized.{Colors.RESET}")
            subprocess.run(['npx', '--yes', 'vercel', 'login'], shell=use_shell)
        
        name = click.prompt(f"{Colors.BLUE}Project Name (leave blank for auto){Colors.RESET}", default="")
        click.echo(f"{Colors.CYAN}Deploying to Vercel...{Colors.RESET}")
        cmd = ['npx', '--yes', 'vercel', '--prod']
        if name: cmd.extend(['--name', name])
        subprocess.run(cmd, shell=use_shell)

    elif provider == '2': # Netlify
        # Check login
        click.echo(f"{Colors.CYAN}Checking Netlify authentication...{Colors.RESET}")
        check = subprocess.run(['npx', '--yes', 'netlify-cli', 'status'], shell=use_shell, capture_output=True)
        if b"Not logged in" in check.stdout or check.returncode != 0:
            click.echo(f"{Colors.YELLOW}You are not logged in to Netlify.{Colors.RESET}")
            subprocess.run(['npx', '--yes', 'netlify-cli', 'login'], shell=use_shell)
            
        name = click.prompt(f"{Colors.BLUE}Site Name (leave blank for auto){Colors.RESET}", default="")
        click.echo(f"{Colors.CYAN}Deploying to Netlify...{Colors.RESET}")
        cmd = ['npx', '--yes', 'netlify-cli', 'deploy', '--prod']
        if name: cmd.extend(['--site', name])
        subprocess.run(cmd, shell=use_shell)
        
    elif provider == '3': # Render
        hook = click.prompt(f"{Colors.BLUE}Enter Render Deploy Hook URL{Colors.RESET}", default="")
        if hook:
            subprocess.run(['curl', '-X', 'POST', hook], shell=use_shell)
            click.echo(f"\n{Colors.GREEN}✅ Deployment triggered on Render!{Colors.RESET}")
        else:
            click.echo(f"{Colors.YELLOW}Render requires a Deploy Hook.{Colors.RESET}")

@click.command()
def login():
    """Login to provider"""
    click.echo(f"{Colors.CYAN}Logging in to Vercel...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'login'], shell=os.name == 'nt')

@click.command()
def logout():
    """Logout from provider"""
    click.echo(f"{Colors.CYAN}Logging out of Vercel...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'logout'], shell=os.name == 'nt')
    click.echo(f"{Colors.GREEN}✅ Logged out{Colors.RESET}")

@click.command()
def live():
    """Check live status"""
    click.echo(f"{Colors.CYAN}Checking deployment status...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'ls'], shell=os.name == 'nt')

@click.command()
def env_push():
    """Push environment variables"""
    click.echo(f"{Colors.CYAN}Pushing .env to Vercel...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'env', 'pull'], shell=os.name == 'nt')
    click.echo(f"{Colors.GREEN}✅ Done{Colors.RESET}")

@click.command()
def logs():
    """View application logs"""
    click.echo(f"{Colors.CYAN}Tailing Vercel logs...{Colors.RESET}")
    subprocess.run(['npx', 'vercel', 'logs'], shell=os.name == 'nt')
