import click, subprocess, os
from pathlib import Path
from ..config import console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box


@click.command()
def ship():
    """Deploy application (Vercel/Netlify/Render)"""
    console.print()
    console.print(Panel("[bold brand]DEPLOYMENT ENGINE[/bold brand]", border_style="brand", box=box.DOUBLE_EDGE))

    console.print("\n[bold]Choose provider:[/bold]")
    console.print("  [accent]1[/accent]. Vercel")
    console.print("  [accent]2[/accent]. Netlify")
    console.print("  [accent]3[/accent]. Render")
    provider = Prompt.ask("[info]Provider[/info]", choices=["1", "2", "3"])

    use_shell = os.name == 'nt'

    if provider == '1':
        console.print("[info]Checking Vercel authentication...[/info]")
        check = subprocess.run(['npx', '--yes', 'vercel', 'whoami'], shell=use_shell, capture_output=True)

        if check.returncode != 0:
            console.print("[yellow]Not logged in. Starting login...[/yellow]")
            subprocess.run(['npx', '--yes', 'vercel', 'login'], shell=use_shell)

        name = Prompt.ask("[info]Project name (blank for auto)[/info]", default="")
        console.print("[info]Deploying to Vercel...[/info]")
        cmd = ['npx', '--yes', 'vercel', '--prod']
        if name:
            cmd.extend(['--name', name])
        subprocess.run(cmd, shell=use_shell)

    elif provider == '2':
        console.print("[info]Checking Netlify authentication...[/info]")
        check = subprocess.run(['npx', '--yes', 'netlify-cli', 'status'], shell=use_shell, capture_output=True)
        if b"Not logged in" in check.stdout or check.returncode != 0:
            console.print("[yellow]Not logged in. Starting login...[/yellow]")
            subprocess.run(['npx', '--yes', 'netlify-cli', 'login'], shell=use_shell)

        name = Prompt.ask("[info]Site name (blank for auto)[/info]", default="")
        console.print("[info]Deploying to Netlify...[/info]")
        cmd = ['npx', '--yes', 'netlify-cli', 'deploy', '--prod']
        if name:
            cmd.extend(['--site', name])
        subprocess.run(cmd, shell=use_shell)

    elif provider == '3':
        hook = Prompt.ask("[info]Render Deploy Hook URL[/info]", default="")
        if hook:
            console.print("[info]Triggering Render deployment...[/info]")
            subprocess.run(['curl', '-X', 'POST', hook], shell=use_shell)
            console.print("[success]Deployment triggered on Render![/success]")
        else:
            console.print("[yellow]Render requires a Deploy Hook URL.[/yellow]")


@click.command()
def login():
    """Login to Vercel"""
    console.print("[info]Logging in to Vercel...[/info]")
    subprocess.run(['npx', 'vercel', 'login'], shell=os.name == 'nt')


@click.command()
def logout():
    """Logout from Vercel"""
    console.print("[info]Logging out of Vercel...[/info]")
    subprocess.run(['npx', 'vercel', 'logout'], shell=os.name == 'nt')
    console.print("[success]Logged out.[/success]")


@click.command()
def live():
    """Check deployment status"""
    console.print("[info]Checking deployment status...[/info]")
    subprocess.run(['npx', 'vercel', 'ls'], shell=os.name == 'nt')


@click.command(name='env-push')
def env_push():
    """Pull environment variables from Vercel"""
    console.print("[info]Pulling .env from Vercel...[/info]")
    subprocess.run(['npx', 'vercel', 'env', 'pull'], shell=os.name == 'nt')
    console.print("[success]Done.[/success]")


@click.command()
def logs():
    """View application logs"""
    console.print("[info]Tailing Vercel logs...[/info]")
    subprocess.run(['npx', 'vercel', 'logs'], shell=os.name == 'nt')