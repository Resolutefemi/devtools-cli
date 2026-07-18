import click, subprocess, shutil
from pathlib import Path
from ..config import console, BORDER_ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich import box


@click.command()
def check():
    """Run basic project checks"""
    console.print()
    console.print(Panel("[bold brand]PROJECT CHECK[/bold brand]", border_style="brand", box=box.ROUNDED))

    table = Table(box=box.SIMPLE, padding=(0, 2))
    table.add_column("Check", style="dim")
    table.add_column("Result", ratio=2)

    checks = [
        ("Node.js", "package.json"),
        ("Python", "requirements.txt"),
        ("Rust", "Cargo.toml"),
        ("Go", "go.mod"),
        ("Git", ".git"),
        ("Docker", "Dockerfile"),
        ("CI/CD", ".github"),
    ]

    detected = []
    for name, marker in checks:
        if Path(marker).exists() or (marker.startswith('.') and Path(marker).is_dir()):
            table.add_row(name, "[success]Detected[/success]")
            detected.append(name)

    if not detected:
        table.add_row("Project", "[yellow]No specific config detected[/yellow]")

    console.print(table)


@click.command()
def doctor():
    """Run comprehensive system diagnostic"""
    console.print()
    console.print(Panel("[bold brand]SYSTEM DOCTOR[/bold brand]", border_style="brand", box=box.ROUNDED))

    # Check external tools
    console.print("\n[bold]External Tools[/bold]")
    tools = [
        ('git', ['git', '--version']),
        ('node', ['node', '--version']),
        ('python', ['python', '--version']),
        ('pip', ['pip', '--version']),
        ('ffmpeg', ['ffmpeg', '-version']),
        ('gh', ['gh', '--version']),
        ('docker', ['docker', '--version']),
    ]

    tool_table = Table(box=box.SIMPLE, padding=(0, 2))
    tool_table.add_column("Tool", style="dim")
    tool_table.add_column("Status", ratio=2)
    tool_table.add_column("Version", style="muted")

    for name, cmd in tools:
        if shutil.which(cmd[0]):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                version = result.stdout.strip().split('\n')[0][:50]
                tool_table.add_row(name, "[success]Installed[/success]", version)
            except Exception:
                tool_table.add_row(name, "[success]Installed[/success]", "")
        else:
            tool_table.add_row(name, "[red]Missing[/red]", "")

    console.print(tool_table)

    # Check Python dependencies
    console.print("\n[bold]Python Dependencies[/bold]")
    deps = [
        ('click', 'click'),
        ('rich', 'rich'),
        ('requests', 'requests'),
        ('qrcode', 'qrcode'),
        ('Pillow', 'PIL'),
        ('psutil', 'psutil'),
        ('mss', 'mss'),
        ('pyjokes', 'pyjokes'),
    ]

    dep_table = Table(box=box.SIMPLE, padding=(0, 2))
    dep_table.add_column("Package", style="dim")
    dep_table.add_column("Status", ratio=2)

    for name, module in deps:
        try:
            __import__(module)
            dep_table.add_row(name, "[success]OK[/success]")
        except ImportError:
            dep_table.add_row(name, "[red]Missing[/red]")

    console.print(dep_table)

    # Platform info
    console.print("\n[bold]Platform[/bold]")
    import platform
    info_table = Table(box=box.SIMPLE, padding=(0, 2))
    info_table.add_column("Key", style="dim")
    info_table.add_column("Value", style="white")
    info_table.add_row("OS", f"{platform.system()} {platform.release()}")
    info_table.add_row("Python", platform.python_version())
    info_table.add_row("Architecture", platform.machine())
    console.print(info_table)
    console.print()