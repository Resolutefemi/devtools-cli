import click, os, subprocess, json, re
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, BORDER_ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich import box


@click.command()
def screenshot():
    """Take a screenshot of the entire screen"""
    try:
        import mss
        save_dir = get_save_path('images')
        filename = ask_filename("screenshot")
        filepath = save_dir / f"{filename}.png"

        console.print("[info]Capturing screen...[/info]")
        with mss.mss() as sct:
            sct.shot(output=str(filepath))

        if filepath.exists():
            size = filepath.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Size: {size:.2f} MB[/dim]")
            confirm_save(filepath)
    except ImportError:
        console.print("[red]mss not installed. pip install mss[/red]")
    except Exception as e:
        console.print(f"[red]Screenshot failed: {e}[/red]")


@click.command()
def joke():
    """Get a random developer joke"""
    try:
        import pyjokes
        joke_text = pyjokes.get_joke()
        console.print()
        console.print(Panel(
            f"[white]{joke_text}[/white]",
            title="[warn]JOKE[/warn]",
            border_style="warn",
            box=box.ROUNDED,
        ))
    except ImportError:
        console.print("[red]pyjokes not installed. pip install pyjokes[/red]")


@click.command()
@click.argument('file_path')
def json_fmt(file_path):
    """Format and prettify a JSON file"""
    p = Path(file_path)
    if not p.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return
    try:
        data = json.loads(p.read_text())
        formatted = json.dumps(data, indent=4, ensure_ascii=False)
        p.write_text(formatted)
        console.print(f"[success]JSON formatted: {file_path}[/success]")
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@click.command()
@click.argument('process_name')
def kill_all(process_name):
    """Kill all processes matching a name"""
    import psutil
    count = 0
    for proc in psutil.process_iter(['name']):
        try:
            if process_name.lower() in (proc.info.get('name') or '').lower():
                proc.terminate()
                count += 1
                console.print(f"  [dim]Terminated: {proc.info['name']} (PID: {proc.pid})[/dim]")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if count > 0:
        console.print(f"\n[success]Terminated {count} process(es) matching '{process_name}'[/success]")
    else:
        console.print(f"[yellow]No processes found matching '{process_name}'[/yellow]")


@click.command()
@click.argument('pattern')
@click.argument('path', default='.')
def search(pattern, path):
    """Search for text inside files recursively"""
    p = Path(path)
    console.print(f"[info]Searching for '[white]{pattern}[/white]' in {p.absolute()}...[/info]")

    found_files = []
    try:
        for f in p.rglob('*'):
            if f.is_file() and not any(d in str(f) for d in {'.git', 'node_modules', '__pycache__', '.dt'}):
                try:
                    content = f.read_text(errors='ignore')
                    if pattern in content:
                        found_files.append(f)
                except Exception:
                    pass
    except KeyboardInterrupt:
        pass

    if found_files:
        table = Table(box=box.SIMPLE, padding=(0, 1))
        table.add_column("File", style="white")
        for f in found_files[:30]:
            table.add_row(str(f.relative_to(p)))
        console.print(table)
        console.print(f"\n[success]Found in {len(found_files)} file(s)[/success]")
    else:
        console.print("[yellow]Pattern not found in any files.[/yellow]")


@click.command()
@click.argument('url')
def links(url):
    """Extract all links from a website"""
    import requests
    console.print(f"[info]Extracting links from {url}...[/info]")
    try:
        res = requests.get(url, timeout=10)
        found = re.findall(r'href="(https?://.*?)"', res.text)
        unique = sorted(set(found))
        if unique:
            table = Table(box=box.SIMPLE, padding=(0, 1))
            table.add_column("#", style="dim", justify="right", width=4)
            table.add_column("URL", style="white")
            for i, link in enumerate(unique, 1):
                table.add_row(str(i), link)
            console.print(table)
            console.print(f"\n[dim]{len(unique)} unique links found[/dim]")
        else:
            console.print("[yellow]No links found.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@click.command()
@click.argument('pattern')
@click.argument('replacement')
def rename(pattern, replacement):
    """Bulk rename files using string replacement"""
    count = 0
    for f in Path.cwd().iterdir():
        if f.is_file() and pattern in f.name:
            new_name = f.name.replace(pattern, replacement)
            new_path = f.parent / new_name
            console.print(f"  [dim]{f.name} -> {new_name}[/dim]")
            f.rename(new_path)
            count += 1

    if count > 0:
        console.print(f"\n[success]Renamed {count} file(s)[/success]")
    else:
        console.print("[yellow]No files matched the pattern.[/yellow]")