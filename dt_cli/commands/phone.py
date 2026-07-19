import click, subprocess, os, time, shutil
from ..config import console, get_save_path, ask_filename, confirm_save, IS_TERMUX, bar_width, BORDER_ROUNDED, ensure_pip_module
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.prompt import Prompt
from rich import box


def _require_termux(cmd_name="This"):
    """Check if running on Termux, warn if not."""
    if not IS_TERMUX:
        console.print(f"[yellow]{cmd_name} command works best on Termux (Android).[/yellow]")
        console.print("[dim]Install termux-api: pkg install termux-api[/dim]\n")
        return False
    return True


@click.command(name='serve-phone')
def serve_phone():
    """Serve current folder via HTTP (accessible on phone)"""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()

    port = 8080
    url = f"http://{IP}:{port}"

    console.print()
    console.print(Panel(
        f"[bold brand]FILE SERVER[/bold brand]\n\n"
        f"  Serving: [white]{os.getcwd()}[/white]\n"
        f"  URL:     [info]{url}[/info]\n"
        f"  Network: [dim]Any device on the same WiFi can access this[/dim]",
        border_style="brand", box=box.ROUNDED
    ))

    try:
        if ensure_pip_module('qrcode', display_name='qrcode'):
            import qrcode
            qr = qrcode.QRCode(box_size=1)
            qr.add_data(url)
            qr.make(fit=True)
            console.print(qr.print_ascii(invert=True))
    except Exception:
        pass

    console.print(f"\n[dim]Press Ctrl+C to stop the server.[/dim]\n")

    try:
        subprocess.run(['python', '-m', 'http.server', str(port)])
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped.[/yellow]")


@click.command()
def torch():
    """Toggle phone flashlight (Termux)"""
    _require_termux("Torch")
    console.print("[info]Toggling flashlight...[/info]")
    try:
        # Check current state
        result = subprocess.run(['termux-torch', 'on'], capture_output=True, text=True)
        console.print("[success]Torch ON[/success]")
    except FileNotFoundError:
        console.print("[red]termux-api not installed. Run: pkg install termux-api[/red]")


@click.command()
@click.argument('file_path', required=False)
def storage(file_path):
    """Access phone storage / copy file to Downloads (Termux)"""
    _require_termux("Storage")

    if file_path:
        # Copy specific file to Downloads
        src = os.path.expanduser(file_path)
        if os.path.exists(src):
            dest = get_save_path('downloads') / os.path.basename(src)
            shutil.copy2(src, dest)
            console.print(f"[success]Copied to Downloads: {dest.name}[/success]")
        else:
            console.print(f"[red]File not found: {file_path}[/red]")
    else:
        # Show storage info
        console.print("[info]Phone storage info:[/info]")
        try:
            result = subprocess.run(['df', '-h', '/storage/emulated'], capture_output=True, text=True)
            if result.returncode == 0:
                console.print(Panel(result.stdout.strip(), title="[info]Storage[/info]", border_style="accent", box=box.ROUNDED))
            else:
                result = subprocess.run(['df', '-h'], capture_output=True, text=True)
                console.print(Panel(result.stdout.strip(), title="[info]Storage[/info]", border_style="accent", box=box.ROUNDED))
        except FileNotFoundError:
            console.print("[red]df command not available.[/red]")


@click.command()
@click.argument('number', required=False)
@click.argument('message', required=False)
def sms(number, message):
    """Send SMS message (Termux)"""
    _require_termux("SMS")

    if not number:
        number = Prompt.ask("[info]Phone number[/info]")
    if not message:
        message = Prompt.ask("[info]Message[/info]")

    console.print(f"[info]Sending SMS to {number}...[/info]")
    try:
        result = subprocess.run(['termux-sms-send', '-n', number, message], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[success]SMS sent![/success]")
        else:
            console.print(f"[red]Failed to send SMS: {result.stderr}[/red]")
    except FileNotFoundError:
        console.print("[red]termux-api not installed. Run: pkg install termux-api[/red]")


@click.command()
def hotspot():
    """Toggle WiFi hotspot (Termux)"""
    _require_termux("Hotspot")
    console.print("[info]Toggling hotspot...[/info]")
    try:
        result = subprocess.run(['termux-wifi-enable', 'hotspot'], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[success]Hotspot enabled![/success]")
        else:
            # Fallback - show instructions
            console.print(Panel(
                "[bold]WiFi Hotspot Setup[/bold]\n\n"
                "Enable hotspot via Android Settings:\n"
                "[dim]Settings > Network & Internet > Hotspot & tethering[/dim]\n\n"
                "Then use [info]dt wifi-scan[/info] to verify.",
                border_style="accent", box=box.ROUNDED
            ))
    except FileNotFoundError:
        console.print(Panel(
            "[bold]WiFi Hotspot[/bold]\n\n"
            "Enable hotspot via Android Settings:\n"
            "[dim]Settings > Network & Internet > Hotspot & tethering[/dim]",
            border_style="accent", box=box.ROUNDED
        ))


@click.command(name='wifi-scan')
def wifi_scan():
    """Scan WiFi networks (Termux)"""
    _require_termux("WiFi Scan")
    console.print("[info]Scanning WiFi networks...[/info]")
    try:
        result = subprocess.run(['termux-wifi-scaninfo'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            try:
                import json
                networks = json.loads(result.stdout)
                if networks:
                    table = Table(box=box.ROUNDED, border_style="accent", title="[info]WiFi Networks[/info]")
                    table.add_column("SSID", style="white")
                    table.add_column("BSSID", style="dim")
                    table.add_column("Level", style="warn")
                    table.add_column("Freq", style="info")
                    for net in networks:
                        ssid = net.get('ssid', '[Hidden]')
                        table.add_row(
                            ssid,
                            net.get('bssid', ''),
                            f"{net.get('level', '?')} dBm",
                            str(net.get('frequency', '?')) + " MHz"
                        )
                    console.print(table)
                else:
                    console.print("[yellow]No networks found.[/yellow]")
            except json.JSONDecodeError:
                console.print(result.stdout)
        else:
            console.print("[yellow]No results. Make sure location is enabled.[/yellow]")
    except FileNotFoundError:
        console.print("[red]termux-api not installed. Run: pkg install termux-api[/red]")


@click.command(name='record-audio')
def record_audio():
    """Record audio on Android (Termux)"""
    _require_termux("Audio Recording")

    filename = ask_filename("recording")
    output = get_save_path('music') / f"{filename}.aac"

    console.print(f"[info]Recording audio... Press Ctrl+C to stop.[/info]")
    console.print(f"[dim]Saving to: {output}[/dim]\n")

    try:
        process = subprocess.Popen(
            ['termux-microphone-record', '-f', str(output), '-r', '44100', '-c', '2', '-b', '256'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        # Wait for user to stop
        process.wait()
    except FileNotFoundError:
        console.print("[red]termux-api not installed. Run: pkg install termux-api[/red]")
        return

    # Stop recording
    console.print("[info]Stopping recording...[/info]")
    subprocess.run(['termux-microphone-record', '-q'], capture_output=True)

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Duration: ~recording time[/dim]")
        console.print(f"[dim]Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[yellow]Recording may not have saved properly.[/yellow]")


@click.command(name='backup-photos')
def backup_photos():
    """Backup photos from DCIM to dt-cli folder (Termux)"""
    _require_termux("Photo Backup")

    source = Path.home() / 'storage' / 'shared' / 'DCIM' / 'Camera'
    if not source.exists():
        # Try alternative paths
        source = Path.home() / 'storage' / 'shared' / 'DCIM'
    if not source.exists():
        console.print(f"[red]No photos found at {source}[/red]")
        console.print("[dim]Make sure storage permission is granted: termux-setup-storage[/dim]")
        return

    dest = get_save_path('images') / 'photo_backup'
    dest.mkdir(parents=True, exist_ok=True)

    photos = list(source.rglob('*')) + list(Path.home().glob('storage/shared/Pictures/Screenshots/*'))
    image_files = [f for f in photos if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.mp4') and f.is_file()]

    if not image_files:
        console.print("[yellow]No photos found to backup.[/yellow]")
        return

    console.print(f"[info]Found {len(image_files)} files to backup...[/info]\n")

    copied = 0
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=bar_width()),
        console=console,
    ) as progress:
        task = progress.add_task("[info]Backing up photos...[/info]", total=len(image_files))
        for photo in image_files:
            dest_file = dest / photo.name
            if not dest_file.exists():
                import shutil
                shutil.copy2(photo, dest_file)
                copied += 1
            progress.advance(task)

    total_size = sum(f.stat().st_size for f in dest.iterdir() if f.is_file()) / (1024 * 1024)
    console.print(f"\n[success]Backed up {copied} files ({total_size:.1f} MB) to {dest}[/success]")