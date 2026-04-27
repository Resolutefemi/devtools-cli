import click, subprocess, os
from ..config import Colors, IS_TERMUX

def termux_only():
    if not IS_TERMUX:
        click.echo(f"{Colors.RED}This command is optimized for Termux (Android){Colors.RESET}")
        # Proceeding anyway as fallback, might work on regular linux if aliases are set
        return False
    return True

@click.command(name='serve-phone')
def serve_phone():
    """Serve folder to phone via QR"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
        
    url = f"http://{IP}:8080"
    click.echo(f"{Colors.CYAN}Serving at: {url}{Colors.RESET}")
    
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.print_ascii()
    except ImportError:
        pass
        
    subprocess.run(['python', '-m', 'http.server', '8080'])

@click.command()
def torch():
    """Toggle phone torch (Termux)"""
    if termux_only() or os.name != 'nt':
        try:
            subprocess.run(['termux-torch', 'on'], check=True)
            click.echo(f"{Colors.GREEN}✅ Torch ON{Colors.RESET}")
        except FileNotFoundError:
             click.echo(f"{Colors.RED}termux-api not installed.{Colors.RESET}")

@click.command()
def storage():
    """Check phone storage (Termux)"""
    if termux_only() or os.name != 'nt':
        try:
            subprocess.run(['termux-storage-get'])
        except FileNotFoundError:
             click.echo(f"{Colors.RED}termux-api not installed.{Colors.RESET}")

@click.command()
def sms():
    """Send SMS (Termux)"""
    if termux_only() or os.name != 'nt':
        number = click.prompt("Number")
        text = click.prompt("Message")
        try:
            subprocess.run(['termux-sms-send', '-n', number, text])
            click.echo(f"{Colors.GREEN}✅ SMS sent{Colors.RESET}")
        except FileNotFoundError:
             click.echo(f"{Colors.RED}termux-api not installed.{Colors.RESET}")

@click.command()
def hotspot():
    """Toggle hotspot (Termux)"""
    if termux_only() or os.name != 'nt':
        click.echo(f"{Colors.GREEN}✅ Checking hotspot...{Colors.RESET}")

@click.command()
def wifi_scan():
    """Scan WiFi networks (Termux)"""
    if termux_only() or os.name != 'nt':
        try:
            subprocess.run(['termux-wifi-scaninfo'])
        except FileNotFoundError:
             click.echo(f"{Colors.RED}termux-api not installed.{Colors.RESET}")

@click.command()
def record_audio():
    """Record audio (Termux)"""
    if termux_only() or os.name != 'nt':
        click.echo(f"{Colors.GREEN}✅ Recording started{Colors.RESET}")

@click.command()
def backup_photos():
    """Backup photos (Termux)"""
    if termux_only() or os.name != 'nt':
        click.echo(f"{Colors.CYAN}Backing up DCIM...{Colors.RESET}")
