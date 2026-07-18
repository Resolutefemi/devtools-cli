import click, random, string, hashlib, base64
from ..config import console
from rich.panel import Panel
from rich.table import Table
from rich import box


@click.command()
@click.option('--length', default=16, help='Length of password')
def passgen(length):
    """Generate a strong password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = ''.join(random.choice(chars) for _ in range(length))
    console.print(Panel(pwd, title="[success]GENERATED PASSWORD[/success]", border_style="success", box=box.ROUNDED))


@click.command()
@click.argument('text')
def hash(text):
    """Generate MD5 and SHA256 hashes"""
    md5 = hashlib.md5(text.encode()).hexdigest()
    sha256 = hashlib.sha256(text.encode()).hexdigest()

    table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
    table.add_column(style="dim", ratio=1)
    table.add_column(style="white", ratio=3)
    table.add_row("MD5", md5)
    table.add_row("SHA256", sha256)
    console.print(table)


@click.command()
@click.argument('text')
def b64encode(text):
    """Base64 encode text"""
    encoded = base64.b64encode(text.encode()).decode()
    console.print(f"[success]{encoded}[/success]")


@click.command()
@click.argument('data')
def b64decode(data):
    """Base64 decode text"""
    try:
        decoded = base64.b64decode(data).decode()
        console.print(f"[success]{decoded}[/success]")
    except Exception:
        console.print("[red]Invalid Base64 data.[/red]")