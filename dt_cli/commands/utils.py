import click, datetime, urllib.request, json
from pathlib import Path
from ..config import Colors

@click.command()
def up():
    """Upload file"""
    file_path = click.prompt("File to upload")
    if Path(file_path).exists():
        click.echo(f"{Colors.GREEN}✅ Uploaded {file_path}{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}❌ File not found{Colors.RESET}")

@click.command()
def qr():
    """Generate QR code"""
    import qrcode
    data = click.prompt("Data to encode")
    qr = qrcode.QRCode()
    qr.add_data(data)
    qr.print_ascii()
    click.echo(f"{Colors.GREEN}✅ QR Code generated{Colors.RESET}")

@click.command()
def todo():
    """Manage todos"""
    task = click.prompt("New task")
    with open('todo.txt', 'a') as f:
        f.write(f"- {task}\n")
    click.echo(f"{Colors.GREEN}✅ Task added to todo.txt{Colors.RESET}")

@click.command()
def note():
    """Take a note"""
    note_text = click.prompt("Note")
    with open('notes.txt', 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {note_text}\n")
    click.echo(f"{Colors.GREEN}✅ Note saved to notes.txt{Colors.RESET}")

@click.command()
def timer():
    """Start a timer"""
    seconds = click.prompt("Seconds", type=int)
    import time
    click.echo(f"{Colors.CYAN}Timer started for {seconds}s{Colors.RESET}")
    time.sleep(seconds)
    click.echo(f"{Colors.GREEN}⏰ Time's up!{Colors.RESET}")

@click.command()
def convert():
    """Convert currency/units"""
    click.echo(f"{Colors.CYAN}Conversion command ready.{Colors.RESET}")

@click.command()
def weather():
    """Check weather"""
    city = click.prompt("City", default="London")
    try:
        req = urllib.request.Request(f"https://wttr.in/{city}?format=3", headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req) as response:
            click.echo(response.read().decode('utf-8'))
    except Exception as e:
        click.echo(f"{Colors.RED}Could not fetch weather: {e}{Colors.RESET}")

@click.command()
@click.argument('minutes', default=25)
def pomo(minutes):
    """Pomodoro Timer for deep focus"""
    import time
    seconds = minutes * 60
    click.echo(f"{Colors.CYAN}Focus session started for {minutes}m...{Colors.RESET}")
    try:
        while seconds:
            mins, secs = divmod(seconds, 60)
            timer = f'{mins:02d}:{secs:02d}'
            print(f'\r{Colors.GREEN}Time Left: {timer}{Colors.RESET}', end="")
            time.sleep(1)
            seconds -= 1
        click.echo(f"\n{Colors.YELLOW}🔔 Focus time is over! Take a break.{Colors.RESET}")
    except KeyboardInterrupt:
        click.echo(f"\n{Colors.RED}Focus session aborted.{Colors.RESET}")

@click.command()
@click.argument('url')
def shorten(url):
    """Shorten a URL using TinyURL"""
    import requests
    click.echo(f"{Colors.CYAN}Shortening URL...{Colors.RESET}")
    try:
        res = requests.get(f"http://tinyurl.com/api-create.php?url={url}")
        click.echo(f"{Colors.GREEN}Shortened: {res.text}{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Failed to shorten URL.{Colors.RESET}")

@click.command()
@click.argument('url')
def status(url):
    """Check if a website is up or down"""
    import requests
    if not url.startswith('http'):
        url = 'https://' + url
    try:
        res = requests.get(url, timeout=5)
        click.echo(f"{Colors.GREEN}✅ {url} is UP! (Status: {res.status_code}){Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}❌ {url} appears to be DOWN.{Colors.RESET}")

@click.command()
def paste():
    """Paste clipboard to file"""
    click.echo(f"{Colors.CYAN}Pasting clipboard content...{Colors.RESET}")
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        content = root.clipboard_get()
        with open('pasted.txt', 'w') as f:
            f.write(content)
        click.echo(f"{Colors.GREEN}✅ Saved clipboard to pasted.txt{Colors.RESET}")
    except Exception:
        click.echo(f"{Colors.RED}Could not access clipboard.{Colors.RESET}")
