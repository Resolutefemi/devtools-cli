import click, subprocess, socket, psutil, os, platform, shutil
from ..config import console, BORDER_ROUNDED, IS_TERMUX
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich import box


@click.command()
def ports():
    """List all open/listening ports"""
    console.print(Panel("[bold brand]OPEN PORTS[/bold brand]", border_style="brand", box=box.ROUNDED))

    try:
        table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
        table.add_column("Port", style="success", justify="right")
        table.add_column("PID", style="white", justify="right")
        table.add_column("Process", style="info")
        table.add_column("Status", style="dim")

        found = False
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN':
                found = True
                try:
                    p = psutil.Process(conn.pid)
                    name = p.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    name = "Unknown"
                table.add_row(str(conn.laddr.port), str(conn.pid or '?'), name, conn.status)

        if found:
            console.print(table)
        else:
            console.print("[yellow]No listening ports found (or access denied).[/yellow]")
    except psutil.AccessDenied:
        console.print("[red]Access Denied. Run as administrator/root to see all ports.[/red]")


@click.command()
def kill_port():
    """Kill process on a specific port"""
    from rich.prompt import IntPrompt
    port = IntPrompt.ask("[info]Port to kill[/info]")

    killed = False
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.pid:
                try:
                    p = psutil.Process(conn.pid)
                    p.terminate()
                    console.print(f"[success]Killed process {conn.pid} ({p.name()}) on port {port}[/success]")
                    killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    console.print(f"[red]Failed: {e}[/red]")
                return
    except psutil.AccessDenied:
        console.print("[red]Access Denied. Run as administrator/root.[/red]")
        return

    if not killed:
        console.print(f"[yellow]No process found on port {port}.[/yellow]")


@click.command()
def wifi():
    """Show saved WiFi passwords (Windows only)"""
    import re
    if os.name == 'nt':
        console.print("[info]Fetching WiFi profiles...[/info]")
        try:
            data = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], shell=True).decode('utf-8', errors='ignore')
            profiles = re.findall(r"All User Profile\s*:\s*(.*)", data)
            if not profiles:
                profiles = [line.split(":")[1].strip() for line in data.split('\n') if ":" in line and "Profile" in line]

            table = Table(box=box.ROUNDED, border_style="accent", show_header=True, padding=(0, 2))
            table.add_column("Network", style="white")
            table.add_column("Password", style="warn")

            for name in profiles:
                name = name.strip('\r').strip()
                try:
                    res = subprocess.check_output(f'netsh wlan show profile name="{name}" key=clear', shell=True).decode('utf-8', errors='ignore')
                    password_match = re.search(r"(?:Key Content|Contenu de la cl|Contenido de la clave|Schlsselinhalt)\s*:\s*(.*)", res)
                    if password_match:
                        password = password_match.group(1).strip('\r').strip()
                        table.add_row(name, password)
                    elif "Absent" in res:
                        table.add_row(name, "[dim][OPEN NETWORK][/dim]")
                    else:
                        table.add_row(name, "[red][ENCRYPTED][/red]")
                except Exception:
                    table.add_row(name, "[red][READ ERROR][/red]")

            if table.rows:
                console.print(table)
            else:
                console.print("[yellow]No WiFi profiles found.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    else:
        console.print("[yellow]WiFi password extraction is only available on Windows.[/yellow]")
        if IS_TERMUX:
            console.print("[dim]On Termux, use: dt wifi-scan[/dim]")


@click.command()
def ip():
    """Show local IP addresses"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
    table.add_column(style="dim", ratio=1)
    table.add_column(style="white bold", ratio=2)
    table.add_row("Local IP", local_ip)
    table.add_row("Hostname", socket.gethostname())
    console.print(table)


@click.command()
def battery():
    """Show battery status"""
    if hasattr(psutil, 'sensors_battery'):
        battery = psutil.sensors_battery()
        if battery:
            plugged = "Plugged In" if battery.power_plugged else "Discharging"
            status_style = "success" if battery.power_plugged else ("warn" if battery.percent < 20 else "info")

            # Battery bar
            bar_len = 20
            filled = int(battery.percent / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)

            table = Table(box=box.ROUNDED, border_style=status_style, show_header=False, padding=(0, 2))
            table.add_column(style="dim", ratio=1)
            table.add_column(ratio=2)
            table.add_row("Battery", f"[{status_style}]{bar}[/{status_style}] {battery.percent}%")
            table.add_row("Status", plugged)
            if battery.secsleft > 0:
                hours, mins = divmod(battery.secsleft // 60, 60)
                table.add_row("Remaining", f"{hours}h {mins}m")
            console.print(table)
        else:
            console.print("[yellow]No battery info available (desktop/server?).[/yellow]")
    else:
        console.print("[yellow]Battery info not supported on this platform.[/yellow]")


@click.command()
def space():
    """Check disk space usage"""
    try:
        usage = psutil.disk_usage('/')
        free = usage.free / (1024**3)
        total = usage.total / (1024**3)
        used = usage.used / (1024**3)
        pct = usage.percent

        bar_len = 30
        filled = int(pct / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        style = "success" if pct < 70 else ("warn" if pct < 90 else "red")

        table = Table(box=box.ROUNDED, border_style=style, show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(ratio=3)
        table.add_row("Disk", f"[{style}]{bar}[/{style}] {pct}%")
        table.add_row("Total", f"{total:.1f} GB")
        table.add_row("Used", f"{used:.1f} GB")
        table.add_row("Free", f"{free:.1f} GB")
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@click.command()
def info():
    """Detailed system information"""
    import sys

    table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
    table.add_column(style="dim", ratio=1)
    table.add_column(style="white", ratio=2)
    table.add_row("OS", f"{platform.system()} {platform.release()}")
    table.add_row("Platform", sys.platform)
    table.add_row("Architecture", platform.machine())
    table.add_row("Processor", platform.processor() or "N/A")
    table.add_row("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    table.add_row("Hostname", socket.gethostname())
    try:
        table.add_row("User", os.getlogin())
    except OSError:
        import getpass
        table.add_row("User", getpass.getuser())
    table.add_row("Home", str(os.path.expanduser("~")))
    table.add_row("Shell", os.environ.get('SHELL', os.environ.get('COMSPEC', 'N/A')))
    table.add_row("CPU Cores", str(os.cpu_count()))
    console.print(table)


@click.command()
def health():
    """System health with live CPU monitor"""
    console.print(Panel("[bold brand]SYSTEM HEALTH[/bold brand]", border_style="brand", box=box.ROUNDED))

    # Sample CPU over 1 second for accuracy
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # CPU bar
    cpu_bar_len = 30
    cpu_filled = int(cpu / 100 * cpu_bar_len)
    cpu_bar = "█" * cpu_filled + "░" * (cpu_bar_len - cpu_filled)
    cpu_style = "success" if cpu < 50 else ("warn" if cpu < 80 else "red")

    # RAM bar
    ram_pct = ram.percent
    ram_bar_len = 30
    ram_filled = int(ram_pct / 100 * ram_bar_len)
    ram_bar = "█" * ram_filled + "░" * (ram_bar_len - ram_filled)
    ram_style = "success" if ram_pct < 70 else ("warn" if ram_pct < 90 else "red")

    # Disk bar
    disk_pct = disk.percent
    disk_bar_len = 30
    disk_filled = int(disk_pct / 100 * disk_bar_len)
    disk_bar = "█" * disk_filled + "░" * (disk_bar_len - disk_filled)
    disk_style = "success" if disk_pct < 70 else ("warn" if disk_pct < 90 else "red")

    table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
    table.add_column("Metric", style="dim", ratio=1)
    table.add_column("Usage", ratio=3)
    table.add_column("Details", style="muted", ratio=2)

    table.add_row("CPU", f"[{cpu_style}]{cpu_bar}[/{cpu_style}] {cpu}%", f"{os.cpu_count()} cores")
    table.add_row("RAM", f"[{ram_style}]{ram_bar}[/{ram_style}] {ram_pct}%", f"{ram.used//(1024**3)}/{ram.total//(1024**3)} GB")
    table.add_row("Disk", f"[{disk_style}]{disk_bar}[/{disk_style}] {disk_pct}%", f"{disk.free//(1024**3)} GB free")
    console.print(table)


@click.command()
def update_all():
    """Update all outdated pip packages"""
    console.print("[info]Checking for outdated packages...[/info]\n")

    result = subprocess.run(
        ['pip', 'list', '--outdated', '--format=json'],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        # Fallback
        result = subprocess.run(['pip', 'list', '--outdated'], capture_output=True, text=True)
        if result.stdout.strip():
            console.print(Panel(result.stdout.strip(), title="[info]Outdated Packages[/info]", border_style="warn", box=box.ROUNDED))
        else:
            console.print("[success]All packages are up to date![/success]")
        return

    import json
    try:
        packages = json.loads(result.stdout)
        if not packages:
            console.print("[success]All packages are up to date![/success]")
            return

        table = Table(box=box.ROUNDED, border_style="warn", title="[warn]Outdated Packages[/warn]")
        table.add_column("Package", style="white")
        table.add_column("Current", style="dim")
        table.add_column("Latest", style="success")
        for pkg in packages:
            table.add_row(pkg['name'], pkg['version'], pkg['latest_version'])
        console.print(table)

        from rich.prompt import Confirm
        if Confirm.ask("[info]Update all?[/info]", default=False):
            for pkg in packages:
                console.print(f"[dim]Updating {pkg['name']}...[/dim]")
                subprocess.run(['pip', 'install', '--upgrade', pkg['name']], capture_output=True)
            console.print("[success]All packages updated![/success]")
    except Exception:
        console.print(result.stdout or "[yellow]Could not parse package list.[/yellow]")


@click.command()
def update():
    """Update Renance DevTools to latest version"""
    console.print("[info]Updating Renance DevTools...[/info]")
    try:
        result = subprocess.run(['pip', 'install', '--upgrade', 'renance-dt'], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[success]Renance DevTools updated to latest version![/success]")
        else:
            console.print("[yellow]pip update completed. Try: pip install -e . in the project folder.[/yellow]")
    except Exception:
        console.print("[red]Update failed. Try: pip install --upgrade renance-dt[/red]")


@click.command()
def setup():
    """Add dt to system PATH automatically"""
    import sys, site
    from pathlib import Path

    paths_to_add = []
    scripts_dir = os.path.join(sys.prefix, "Scripts") if os.name == 'nt' else os.path.join(sys.prefix, "bin")
    paths_to_add.append(scripts_dir)

    if hasattr(site, 'getuserbase'):
        user_base = site.getuserbase()
        if user_base:
            user_scripts = os.path.join(user_base, "Scripts") if os.name == 'nt' else os.path.join(user_base, "bin")
            paths_to_add.append(user_scripts)

    console.print("[info]Configuring system PATH...[/info]")

    if os.name == 'nt':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
            try:
                current_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path = ""
        except Exception:
            current_path = ""

        updated = False
        new_path_entries = [p for p in current_path.split(';') if p]

        for s_dir in paths_to_add:
            if s_dir and os.path.exists(s_dir):
                if not any(s_dir.lower() == existing.lower() for existing in new_path_entries):
                    new_path_entries.append(s_dir)
                    updated = True
                    console.print(f"[success]Found: {s_dir}[/success]")

        if updated:
            new_path = ";".join(new_path_entries)
            ps_cmd = f'[Environment]::SetEnvironmentVariable("Path", "{new_path}", "User")'
            subprocess.run(['powershell', '-Command', ps_cmd], check=True, capture_output=True)
            console.print("[warn]Restart your terminal for changes to take effect.[/warn]")
        else:
            console.print("[success]All paths already configured.[/success]")
    else:
        home = Path.home()
        shell_files = [home / '.bashrc', home / '.zshrc', home / '.profile', home / '.bash_profile']
        updated = False
        for scripts_dir in paths_to_add:
            if scripts_dir and os.path.exists(scripts_dir):
                export_cmd = f'\nexport PATH="$PATH:{scripts_dir}"\n'
                for shell_file in shell_files:
                    if shell_file.exists():
                        content = shell_file.read_text()
                        if scripts_dir not in content:
                            with shell_file.open('a') as f:
                                f.write(export_cmd)
                            console.print(f"[success]Added to {shell_file.name}[/success]")
                            updated = True
        if updated:
            console.print("[warn]Restart your terminal or run: source ~/.bashrc[/warn]")
        else:
            console.print("[success]All paths already configured.[/success]")