import click, datetime, urllib.request, json, time, sys
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, BORDER_ROUNDED
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich import box


@click.command()
@click.argument('file_path', required=False)
def up(file_path):
    """Copy a file to your Downloads folder"""
    if not file_path:
        file_path = Prompt.ask("[info]File to copy to Downloads[/info]")

    src = Path(file_path)
    if not src.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return

    dest = get_save_path('downloads') / src.name
    import shutil
    shutil.copy2(src, dest)
    console.print(f"[success]Copied to Downloads: {dest.name}[/success]")


@click.command()
def qr():
    """Generate QR code in terminal"""
    import qrcode
    data = Prompt.ask("[info]Data to encode[/info]")

    qr = qrcode.QRCode(box_size=1, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    console.print(f"\n[dim]Encoded: {data[:50]}{'...' if len(data) > 50 else ''}[/dim]")


@click.command()
@click.argument('task_text', required=False)
def todo(task_text):
    """Add a task to your todo list"""
    if not task_text:
        task_text = Prompt.ask("[info]New task[/info]")
    todo_file = Path.home() / '.dt' / 'todo.txt'
    todo_file.parent.mkdir(exist_ok=True)
    with open(todo_file, 'a') as f:
        f.write(f"- [ ] {task_text}\n")
    console.print(f"[success]Task added to todo list[/success]")


@click.command()
@click.argument('note_text', required=False)
def note(note_text):
    """Take a quick note"""
    if not note_text:
        note_text = Prompt.ask("[info]Note[/info]")
    note_file = Path.home() / '.dt' / 'notes.txt'
    note_file.parent.mkdir(exist_ok=True)
    with open(note_file, 'a') as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] {note_text}\n")
    console.print(f"[success]Note saved[/success]")


@click.command()
@click.argument('seconds', required=False, type=int)
def timer(seconds):
    """Start a visual countdown timer"""
    if seconds is None:
        seconds = IntPrompt.ask("[info]Timer duration in seconds[/info]")

    console.print()
    with Live(console=console, refresh_per_second=10, transient=True) as live:
        for remaining in range(seconds, -1, -1):
            mins, secs = divmod(remaining, 60)
            hours, mins = divmod(mins, 60)

            if hours > 0:
                time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
            else:
                time_str = f"{mins:02d}:{secs:02d}"

            # Color changes as time runs out
            if remaining <= 5:
                style = "bold red"
            elif remaining <= 15:
                style = "bold yellow"
            elif remaining <= 30:
                style = "bold warn"
            else:
                style = "bold success"

            # Progress bar
            progress_val = (seconds - remaining) / seconds if seconds > 0 else 0
            bar_len = 40
            filled = int(progress_val * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)

            live.update(Panel(
                f"[{style}]{time_str}[/{style}]\n\n"
                f"[dim]{bar}[/dim]",
                title="[brand]TIMER[/brand]",
                border_style="brand",
                box=box.ROUNDED,
            ))
            time.sleep(1)

    console.print()
    console.print(Panel("[bold warn]TIME'S UP![/bold warn]", border_style="warn", box=box.DOUBLE_EDGE))


@click.command()
def weather():
    """Check weather for any city"""
    city = Prompt.ask("[info]City[/info]", default="London")
    try:
        console.print(f"[info]Fetching weather for {city}...[/info]")
        req = urllib.request.Request(
            f"https://wttr.in/{city}?format=j1",
            headers={'User-Agent': 'curl/7.68.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            current = data['current_condition'][0]

            table = Table(box=box.ROUNDED, border_style="info", show_header=False, padding=(0, 2))
            table.add_column(style="dim", ratio=1)
            table.add_column(style="white", ratio=2)
            table.add_row("Location", f"{data['nearest_area'][0]['areaName'][0]['value']}, {data['nearest_area'][0]['country'][0]['value']}")
            table.add_row("Temperature", f"[bold]{current['temp_C']}°C[/bold] / {current['temp_F']}°F")
            table.add_row("Feels Like", f"{current['FeelsLikeC']}°C")
            table.add_row("Condition", current['weatherDesc'][0]['value'])
            table.add_row("Humidity", f"{current['humidity']}%")
            table.add_row("Wind", f"{current['windspeedKmph']} km/h {current['winddir16Point']}")
            table.add_row("Visibility", f"{current['visibility']} km")
            table.add_row("Pressure", f"{current['pressure']} mb")

            console.print(table)
    except Exception as e:
        # Fallback to simple format
        try:
            req2 = urllib.request.Request(f"https://wttr.in/{city}?format=4", headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req2, timeout=10) as resp:
                console.print(f"[white]{resp.read().decode().strip()}[/white]")
        except Exception:
            console.print(f"[red]Could not fetch weather: {e}[/red]")


@click.command()
@click.argument('minutes', default=25)
def pomo(minutes):
    """Pomodoro Timer with live display"""
    total_seconds = minutes * 60
    console.print()
    console.print(Panel(
        f"[bold brand]POMODORO FOCUS[/bold brand]\n"
        f"[dim]{minutes} minute focus session[/dim]",
        border_style="brand", box=box.DOUBLE_EDGE
    ))

    try:
        with Live(console=console, refresh_per_second=2, transient=True) as live:
            for remaining in range(total_seconds, -1, -1):
                mins, secs = divmod(remaining, 60)
                elapsed = total_seconds - remaining
                progress = elapsed / total_seconds

                # Visual progress bar
                bar_len = 30
                filled = int(progress * bar_len)
                bar = "🔥" * filled + "  " * (bar_len - filled)

                # Determine phase
                if progress < 0.75:
                    phase = "[bold success]FOCUS[/bold success]"
                    border = "success"
                elif progress < 0.9:
                    phase = "[bold warn]ALMOST THERE[/bold warn]"
                    border = "warn"
                else:
                    phase = "[bold red]FINAL PUSH[/bold red]"
                    border = "red"

                time_display = f"[bold white]{mins:02d}:{secs:02d}[/bold white]"

                live.update(Panel(
                    f"\n{phase}\n\n"
                    f"  {time_display}\n\n"
                    f"  {bar}\n\n"
                    f"  [dim]{int(progress * 100)}% complete[/dim]\n",
                    title=f"[brand]POMODORO[/brand]",
                    border_style=border,
                    box=box.ROUNDED,
                ))
                time.sleep(1)

        console.print()
        console.print(Panel(
            "[bold warn]Focus session complete! Take a break.[/bold warn]\n"
            "[dim]Stand up, stretch, and hydrate.[/dim]",
            border_style="warn", box=box.DOUBLE_EDGE
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Focus session aborted.[/yellow]")


@click.command()
@click.argument('url')
def shorten(url):
    """Shorten a URL using TinyURL"""
    import requests
    console.print("[info]Shortening URL...[/info]")
    try:
        res = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=10)
        if res.status_code == 200 and res.text.startswith('http'):
            table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
            table.add_column(style="dim", ratio=1)
            table.add_column(style="white", ratio=2)
            table.add_row("Original", url)
            table.add_row("Short", f"[success]{res.text}[/success]")
            console.print(table)
        else:
            console.print("[red]Failed to shorten URL.[/red]")
    except Exception:
        console.print("[red]Failed to shorten URL.[/red]")


@click.command()
@click.argument('url')
def status(url):
    """Check if a website is up or down"""
    import requests
    if not url.startswith('http'):
        url = 'https://' + url

    console.print(f"[info]Checking {url}...[/info]")
    try:
        start = time.time()
        res = requests.get(url, timeout=10)
        elapsed = (time.time() - start) * 1000

        status_color = "success" if res.status_code < 400 else "red"
        table = Table(box=box.ROUNDED, border_style="success", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)
        table.add_row("URL", url)
        table.add_row("Status", f"[{status_color}]{res.status_code} {res.reason}[/{status_color}]")
        table.add_row("Response Time", f"{elapsed:.0f} ms")
        console.print(table)
    except requests.exceptions.Timeout:
        console.print("[red]Timeout - server took too long to respond.[/red]")
    except requests.exceptions.ConnectionError:
        console.print("[red]Connection refused - website appears to be DOWN.[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@click.command()
def paste():
    """Save clipboard content to a file"""
    import platform
    system = platform.system()

    console.print("[info]Reading clipboard...[/info]")
    content = None

    try:
        if system == "Windows":
            import subprocess
            content = subprocess.run(['powershell', '-command', 'Get-Clipboard'], capture_output=True, text=True).stdout
        elif system == "Darwin":
            import subprocess
            content = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout
        elif "TERMUX" in os.environ.get('PREFIX', ''):
            import subprocess
            content = subprocess.run(['termux-clipboard-get'], capture_output=True, text=True).stdout
        else:
            # Try xclip or xsel on Linux
            for cmd in [['xclip', '-selection', 'clipboard', '-o'], ['xsel', '--clipboard', '--output']]:
                try:
                    content = subprocess.run(cmd, capture_output=True, text=True).stdout
                    if content:
                        break
                except FileNotFoundError:
                    continue
    except Exception:
        pass

    if not content or not content.strip():
        console.print("[red]Could not read clipboard. Make sure you have text copied.[/red]")
        return

    filename = ask_filename("pasted")
    output = get_save_path('downloads') / f"{filename}.txt"
    output.write_text(content)

    console.print(f"[dim]Saved {len(content)} characters[/dim]")
    confirm_save(output)