import click, random, string, hashlib, base64
from ..config import Colors

@click.command()
@click.option('--length', default=16, help='Length of password')
def passgen(length):
    """Generate a strong password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = ''.join(random.choice(chars) for _ in range(length))
    click.echo(f"{Colors.GREEN}Generated Password: {pwd}{Colors.RESET}")

@click.command()
@click.argument('text')
def hash(text):
    """Generate MD5 and SHA256 hashes"""
    md5 = hashlib.md5(text.encode()).hexdigest()
    sha256 = hashlib.sha256(text.encode()).hexdigest()
    click.echo(f"{Colors.CYAN}MD5: {md5}{Colors.RESET}")
    click.echo(f"{Colors.CYAN}SHA256: {sha256}{Colors.RESET}")

@click.command()
@click.argument('text')
def b64encode(text):
    """Base64 encode text"""
    encoded = base64.b64encode(text.encode()).decode()
    click.echo(f"{Colors.GREEN}{encoded}{Colors.RESET}")

@click.command()
@click.argument('data')
def b64decode(data):
    """Base64 decode text"""
    try:
        decoded = base64.b64decode(data).decode()
        click.echo(f"{Colors.GREEN}{decoded}{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Invalid Base64 data{Colors.RESET}")
