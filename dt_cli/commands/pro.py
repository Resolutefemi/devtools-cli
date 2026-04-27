import click, os, subprocess, json, re
from pathlib import Path
from ..config import Colors, get_save_path

@click.command()
def screenshot():
    """Take a screenshot of the entire screen"""
    import mss
    save_dir = get_save_path('images')
    filename = save_dir / f"screenshot_{os.getpid()}.png"
    
    click.echo(f"{Colors.CYAN}Capturing screen...{Colors.RESET}")
    with mss.mss() as sct:
        sct.shot(output=str(filename))
    
    click.echo(f"{Colors.GREEN}✅ Screenshot saved to: {filename}{Colors.RESET}")

@click.command()
def joke():
    """Get a random geek joke"""
    import pyjokes
    joke = pyjokes.get_joke()
    click.echo(f"\n{Colors.YELLOW}{joke}{Colors.RESET}\n")

@click.command()
@click.argument('file_path')
def json_fmt(file_path):
    """Format and prettify a JSON file"""
    p = Path(file_path)
    if not p.exists():
        click.echo(f"{Colors.RED}File not found.{Colors.RESET}")
        return
    try:
        data = json.loads(p.read_text())
        p.write_text(json.dumps(data, indent=4))
        click.echo(f"{Colors.GREEN}✅ JSON formatted.{Colors.RESET}")
    except Exception as e:
        click.echo(f"{Colors.RED}Error: {e}{Colors.RESET}")

@click.command()
@click.argument('process_name')
def kill_all(process_name):
    """Kill all processes matching a name"""
    import psutil
    count = 0
    for proc in psutil.process_iter(['name']):
        if process_name.lower() in proc.info['name'].lower():
            try:
                proc.terminate()
                count += 1
            except:
                pass
    click.echo(f"{Colors.GREEN}✅ Terminated {count} processes matching '{process_name}'{Colors.RESET}")

@click.command()
@click.argument('pattern')
@click.argument('path', default='.')
def search(pattern, path):
    """Search for text inside files (recursive)"""
    p = Path(path)
    click.echo(f"{Colors.CYAN}Searching for '{pattern}' in {p.absolute()}...{Colors.RESET}")
    count = 0
    try:
        for f in p.rglob('*'):
            if f.is_file() and not any(d in str(f) for d in {'.git', 'node_modules', '__pycache__'}):
                try:
                    content = f.read_text(errors='ignore')
                    if pattern in content:
                        click.echo(f"{Colors.GREEN}{f.relative_to(p)}{Colors.RESET}")
                        count += 1
                except:
                    pass
    except KeyboardInterrupt:
        pass
    click.echo(f"{Colors.CYAN}Found in {count} files.{Colors.RESET}")

@click.command()
@click.argument('url')
def links(url):
    """Extract all links from a website URL"""
    import requests
    click.echo(f"{Colors.CYAN}Fetching links from {url}...{Colors.RESET}")
    try:
        res = requests.get(url, timeout=10)
        found = re.findall(r'href="(https?://.*?)"', res.text)
        for link in set(found):
            click.echo(f"{Colors.WHITE}- {link}{Colors.RESET}")
        click.echo(f"{Colors.CYAN}Total unique links found: {len(set(found))}{Colors.RESET}")
    except Exception as e:
        click.echo(f"{Colors.RED}Error: {e}{Colors.RESET}")

@click.command()
@click.argument('pattern')
@click.argument('replacement')
def rename(pattern, replacement):
    """Bulk rename files in current folder using string replacement"""
    count = 0
    for f in Path.cwd().iterdir():
        if f.is_file() and pattern in f.name:
            new_name = f.name.replace(pattern, replacement)
            f.rename(f.parent / new_name)
            count += 1
    click.echo(f"{Colors.GREEN}✅ Renamed {count} files.{Colors.RESET}")
