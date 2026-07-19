import click, subprocess, socket, os, platform, shutil, time
from ..config import console, BORDER_ROUNDED, IS_TERMUX, ensure_pip_module
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box


def _make_bar(value, max_val=100, width=25):
    """Create a colored bar."""
    pct = min(value / max_val, 1.0) if max_val > 0 else 0
    filled = int(pct * width)
    empty = width - filled
    if pct > 0.8:
        color = "red"
    elif pct > 0.6:
        color = "warn"
    else:
        color = "success"
    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


@click.command()
def ports():
    """List all open/listening ports"""
    if not ensure_pip_module('psutil', display_name='psutil'):
        return
    import psutil
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
    if not ensure_pip_module('psutil', display_name='psutil'):
        return
    import psutil
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
    """Show battery status with animated display"""
    if not ensure_pip_module('psutil', display_name='psutil'):
        return
    import psutil
    if hasattr(psutil, 'sensors_battery'):
        bat = psutil.sensors_battery()
        if bat:
            console.print()
            with Live(console=console, refresh_per_second=2, transient=True) as live:
                for frame in range(8):
                    pct = bat.percent
                    plugged = "Plugged In" if bat.power_plugged else "Discharging"
                    status_style = "success" if bat.power_plugged else ("warn" if pct < 20 else "info")

                    # Animated battery icon
                    bar_len = 20
                    filled = int(pct / 100 * bar_len)

                    # Pulsing effect
                    pulse = "█" if frame % 2 == 0 else "▓"
                    empty_char = "░"
                    bar = f"[{status_style}]{pulse * filled}{empty_char * (bar_len - filled)}[/{status_style}]"

                    table = Table(box=box.ROUNDED, border_style=status_style, show_header=False, padding=(0, 2))
                    table.add_column(style="dim", ratio=1)
                    table.add_column(ratio=2)
                    table.add_row("Battery", f"{bar} {pct}%")
                    table.add_row("Status", plugged)
                    if bat.secsleft > 0:
                        hours, mins = divmod(bat.secsleft // 60, 60)
                        table.add_row("Remaining", f"{hours}h {mins}m")
                    live.update(table)
                    time.sleep(0.3)

            # Final static display
            console.print(table)
        else:
            console.print("[yellow]No battery info available (desktop/server?).[/yellow]")
    else:
        console.print("[yellow]Battery info not supported on this platform.[/yellow]")


@click.command()
def space():
    """Check disk space usage with animated bars"""
    if not ensure_pip_module('psutil', display_name='psutil'):
        return
    import psutil
    console.print()
    console.print(Panel("[bold brand]DISK SPACE[/bold brand]", border_style="brand", box=box.ROUNDED))

    try:
        usage = psutil.disk_usage('/')
        free = usage.free / (1024**3)
        total = usage.total / (1024**3)
        used = usage.used / (1024**3)
        pct = usage.percent

        table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(ratio=3)
        table.add_row("Disk", f"{_make_bar(pct)} {pct}%")
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

    console.print()
    console.print(Panel("[bold brand]SYSTEM INFO[/bold brand]", border_style="brand", box=box.ROUNDED))

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

    # RAM
    try:
        import psutil as _ps
        ram = _ps.virtual_memory()
        table.add_row("Total RAM", f"{ram.total / (1024**3):.1f} GB")
        table.add_row("Available RAM", f"{ram.available / (1024**3):.1f} GB")
    except Exception:
        pass

    console.print(table)


@click.command()
def health():
    """System health with live animated CPU/RAM/Disk monitor"""
    if not ensure_pip_module('psutil', display_name='psutil'):
        return
    import psutil, random

    console.print()
    console.print(Panel(
        "[bold brand]SYSTEM HEALTH - LIVE MONITOR[/bold brand]\n"
        "[dim]Monitoring for 5 seconds... Press Ctrl+C to exit early[/dim]",
        border_style="brand", box=box.DOUBLE_EDGE
    ))

    cpu_history = []
    ram_history = []

    try:
        with Live(console=console, refresh_per_second=2, transient=False) as live:
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3),
            )

            start = time.time()
            while time.time() - start < 5:
                cpu = psutil.cpu_percent(interval=0.5)
                ram = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                cpu_history.append(cpu)
                ram_history.append(ram.percent)
                if len(cpu_history) > 20:
                    cpu_history.pop(0)
                if len(ram_history) > 20:
                    ram_history.pop(0)

                elapsed = time.time() - start
                remaining = max(0, 5 - elapsed)

                # Header
                header = Text()
                header.append("  SYSTEM HEALTH", style="bold brand")
                header.append(f"  |  {remaining:.0f}s remaining", style="dim")
                layout["header"].update(Panel(header, box=box.SIMPLE))

                # Build sparklines
                def sparkline(values, width=30):
                    if not values:
                        return "░" * width
                    mx = max(values) if max(values) > 0 else 1
                    chars = "▁▂▃▄▅▆▇█"
                    line = ""
                    for v in values:
                        idx = int((v / mx) * (len(chars) - 1))
                        line += chars[min(idx, len(chars) - 1)]
                    return line

                # Body
                body = Text()

                # CPU
                cpu_style = "success" if cpu < 50 else ("warn" if cpu < 80 else "red")
                body.append("\n  CPU Usage\n", style="bold")
                body.append(f"  {_make_bar(cpu)}  ")
                body.append(f"[{cpu_style}]{cpu:.1f}%[/{cpu_style}]  ")
                body.append(f"[dim]{os.cpu_count()} cores[/dim]\n")
                body.append(f"  [dim]{sparkline(cpu_history)}[/dim]")

                # RAM
                ram_pct = ram.percent
                ram_style = "success" if ram_pct < 70 else ("warn" if ram_pct < 90 else "red")
                body.append(f"\n\n  RAM Usage\n", style="bold")
                body.append(f"  {_make_bar(ram_pct)}  ")
                body.append(f"[{ram_style}]{ram_pct:.1f}%[/{ram_style}]  ")
                body.append(f"[dim]{ram.used // (1024**3)}/{ram.total // (1024**3)} GB[/dim]\n")
                body.append(f"  [dim]{sparkline(ram_history)}[/dim]")

                # Disk
                disk_pct = disk.percent
                disk_style = "success" if disk_pct < 70 else ("warn" if disk_pct < 90 else "red")
                body.append(f"\n\n  Disk Usage\n", style="bold")
                body.append(f"  {_make_bar(disk_pct)}  ")
                body.append(f"[{disk_style}]{disk_pct:.0f}%[/{disk_style}]  ")
                body.append(f"[dim]{disk.free // (1024**3)} GB free[/dim]")

                layout["body"].update(Panel(body, box=box.ROUNDED, border_style="border"))
                layout["footer"].update(Text("  [dim]Ctrl+C to exit[/dim]  ", justify="center"))
                live.update(layout)

        # Final summary
        avg_cpu = sum(cpu_history) / len(cpu_history) if cpu_history else 0
        console.print()
        table = Table(box=box.ROUNDED, border_style="success", show_header=False, padding=(0, 2))
        table.add_column("Metric", style="dim", ratio=1)
        table.add_column("Avg", style="white", ratio=1)
        table.add_column("Peak", style="white", ratio=1)

        peak_cpu = max(cpu_history) if cpu_history else 0
        peak_ram = max(ram_history) if ram_history else 0
        avg_ram = sum(ram_history) / len(ram_history) if ram_history else 0

        table.add_row("CPU", f"{avg_cpu:.1f}%", f"{peak_cpu:.1f}%")
        table.add_row("RAM", f"{avg_ram:.1f}%", f"{peak_ram:.1f}%")
        table.add_row("Disk", f"{disk.percent:.0f}%", f"{disk.free // (1024**3)} GB free")

        console.print(Panel(
            table,
            title="[bold success]HEALTH SUMMARY[/bold success]",
            border_style="success", box=box.DOUBLE_EDGE
        ))
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped.[/dim]")


@click.command()
def sysmon():
    """Real-time system monitor (continuous)"""
    if not ensure_pip_module('psutil', display_name='psutil'):
        return
    import psutil
    console.print()
    console.print(Panel(
        "[bold brand]SYSTEM MONITOR[/bold brand]\n[dim]Real-time resource monitoring - Press Ctrl+C to exit[/dim]",
        border_style="brand", box=box.DOUBLE_EDGE
    ))

    cpu_history = []
    ram_history = []
    net_history = []

    try:
        prev_net = psutil.net_io_counters()

        with Live(console=console, refresh_per_second=2, transient=True) as live:
            while True:
                cpu = psutil.cpu_percent(interval=0.3)
                ram = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                # Network delta
                curr_net = psutil.net_io_counters()
                net_sent = (curr_net.bytes_sent - prev_net.bytes_sent) / 1024
                net_recv = (curr_net.bytes_recv - prev_net.bytes_recv) / 1024
                prev_net = curr_net

                cpu_history.append(cpu)
                ram_history.append(ram.percent)
                net_history.append(net_sent + net_recv)
                if len(cpu_history) > 40:
                    cpu_history.pop(0)
                if len(ram_history) > 40:
                    ram_history.pop(0)
                if len(net_history) > 40:
                    net_history.pop(0)

                def sparkline(values, width=35):
                    if not values:
                        return "░" * width
                    mx = max(values) if max(values) > 0 else 1
                    chars = "▁▂▃▄▅▆▇█"
                    return "".join(chars[min(int((v / mx) * (len(chars) - 1)), len(chars) - 1)] for v in values)

                # Top processes
                top_procs = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        info = proc.info
                        if info['cpu_percent'] and info['cpu_percent'] > 0.5:
                            top_procs.append(info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                top_procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
                top_procs = top_procs[:5]

                text = Text()
                text.append(f"\n  CPU  {_make_bar(cpu)} ", style="")
                cpu_s = "success" if cpu < 50 else ("warn" if cpu < 80 else "red")
                text.append(f"[{cpu_s}]{cpu:.1f}%[/{cpu_s}]", style="")
                text.append(f"  [dim]{sparkline(cpu_history)}[/dim]")

                text.append(f"\n  RAM  {_make_bar(ram.percent)} ", style="")
                ram_s = "success" if ram.percent < 70 else ("warn" if ram.percent < 90 else "red")
                text.append(f"[{ram_s}]{ram.percent:.1f}%[/{ram_s}]", style="")
                text.append(f"  [dim]{ram.used // (1024**3)}/{ram.total // (1024**3)} GB[/dim]")

                text.append(f"\n  Disk {_make_bar(disk.percent)} ", style="")
                text.append(f"[dim]{disk.free // (1024**3)} GB free[/dim]")

                text.append(f"\n  NET  [dim]↑{net_sent:.0f} KB/s  ↓{net_recv:.0f} KB/s[/dim]")

                if top_procs:
                    text.append(f"\n\n  [bold]Top Processes:[/bold]")
                    for p in top_procs:
                        name = (p.get('name') or '?')[:15]
                        cpu_v = p.get('cpu_percent') or 0
                        mem_v = p.get('memory_percent') or 0
                        text.append(f"\n  [dim]{name:<16} CPU:{cpu_v:5.1f}%  MEM:{mem_v:5.1f}%[/dim]")

                live.update(Panel(text, box=box.ROUNDED, border_style="border"))
                time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped.[/dim]")


@click.command()
def update_all():
    """Update all outdated pip packages"""
    console.print("[info]Checking for outdated packages...[/info]\n")

    result = subprocess.run(
        ['pip', 'list', '--outdated', '--format=json'],
        capture_output=True, text=True
    )

    if result.returncode != 0:
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