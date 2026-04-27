import click, subprocess, socket, psutil, os
from ..config import Colors

@click.command()
def ports():
    """List open ports"""
    click.echo(f"{Colors.CYAN}Open ports:{Colors.RESET}")
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN':
                try:
                    p = psutil.Process(conn.pid)
                    name = p.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    name = "Unknown"
                click.echo(f"Port {conn.laddr.port} (PID: {conn.pid}, Name: {name})")
    except psutil.AccessDenied:
        click.echo(f"{Colors.RED}Access Denied. Run as administrator/root to see all ports.{Colors.RESET}")

@click.command()
def kill_port():
    """Kill process on port"""
    port = click.prompt("Port to kill", type=int)
    killed = False
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.pid:
                try:
                    p = psutil.Process(conn.pid)
                    p.terminate()
                    click.echo(f"{Colors.GREEN}✅ Killed process {conn.pid} ({p.name()}) on port {port}{Colors.RESET}")
                    killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    click.echo(f"{Colors.RED}Failed to kill process: {e}{Colors.RESET}")
                return
    except psutil.AccessDenied:
        click.echo(f"{Colors.RED}Access Denied. Run as administrator/root.{Colors.RESET}")
        return
        
    if not killed:
        click.echo(f"{Colors.YELLOW}No accessible process found on port {port}{Colors.RESET}")
@click.command()
def wifi():
    """Show saved wifi passwords"""
    import re
    if os.name == 'nt':
        click.echo(f"{Colors.CYAN}Fetching WiFi profiles...{Colors.RESET}")
        try:
            # Get profiles using a more robust encoding
            data = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], shell=True).decode('utf-8', errors='ignore')
            profiles = re.findall(r"All User Profile\s*:\s*(.*)", data)

            if not profiles:
                # Try fallback for non-English systems (filtering for the colon structure)
                profiles = [line.split(":")[1].strip() for line in data.split('\n') if ":" in line and "Profile" in line]

            for name in profiles:
                name = name.strip('\r').strip()
                try:
                    # Get profile details including key
                    res = subprocess.check_output(f'netsh wlan show profile name="{name}" key=clear', shell=True).decode('utf-8', errors='ignore')

                    # Search for password in common languages (Key Content / Contenu de la clé / Contenido de la clave, etc.)
                    # Or better: search for the specific line structure
                    password_match = re.search(r"(?:Key Content|Contenu de la cl|Contenido de la clave|Schlsselinhalt)\s*:\s*(.*)", res)

                    if password_match:
                        password = password_match.group(1).strip('\r').strip()
                        click.echo(f"{Colors.GREEN}{name:25} : {Colors.YELLOW}{password}{Colors.RESET}")
                    else:
                        # Check if it's an open network
                        if "Security key           : Absent" in res or "Cl de scurit           : Absente" in res:
                            click.echo(f"{Colors.GREEN}{name:25} : {Colors.CYAN}[OPEN NETWORK]{Colors.RESET}")
                        else:
                            click.echo(f"{Colors.GREEN}{name:25} : {Colors.RED}[NOT FOUND/ENCRYPTED]{Colors.RESET}")
                except Exception:
                    click.echo(f"{Colors.GREEN}{name:25} : {Colors.RED}[READ ERROR]{Colors.RESET}")
        except Exception as e:
            click.echo(f"{Colors.RED}Fatal Error: {e}{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}WiFi password extraction is currently only supported on Windows.{Colors.RESET}")


@click.command()
def ip():
    """Show IP addresses"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    click.echo(f"{Colors.CYAN}Local IP: {IP}{Colors.RESET}")

@click.command()
def battery():
    """Show battery status"""
    if hasattr(psutil, 'sensors_battery'):
        battery = psutil.sensors_battery()
        if battery:
            plugged = "Plugged In" if battery.power_plugged else "Discharging"
            click.echo(f"{Colors.GREEN}Battery: {battery.percent}% ({plugged}){Colors.RESET}")
        else:
            click.echo(f"{Colors.YELLOW}No battery found{Colors.RESET}")
    else:
        click.echo(f"{Colors.YELLOW}Battery info not available{Colors.RESET}")

@click.command()
def space():
    """Check disk space"""
    usage = psutil.disk_usage('/')
    free = usage.free / (1024**3)
    total = usage.total / (1024**3)
    click.echo(f"{Colors.GREEN}Free space: {free:.1f} GB out of {total:.1f} GB ({usage.percent}% used){Colors.RESET}")

@click.command()
def info():
    """System information"""
    click.echo(f"{Colors.CYAN}OS: {os.name}{Colors.RESET}")
    click.echo(f"{Colors.CYAN}Platform: {os.sys.platform}{Colors.RESET}")
    
@click.command()
def health():
    """System health"""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    click.echo(f"{Colors.GREEN}CPU Usage: {cpu}%{Colors.RESET}")
    click.echo(f"{Colors.GREEN}RAM Usage: {ram}%{Colors.RESET}")

@click.command()
def update_all():
    """Update system packages"""
    click.echo(f"{Colors.CYAN}Updating global python packages...{Colors.RESET}")
    subprocess.run('pip list --outdated --format=json', shell=True)

@click.command()
def update():
    """Update Renance DevTools to latest version"""
    click.echo(f"{Colors.CYAN}Checking for updates...{Colors.RESET}")
    try:
        subprocess.run(['pip', 'install', '--upgrade', 'renance-dt'], check=True)
        click.echo(f"{Colors.GREEN}✅ Renance DevTools updated!{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}❌ Update failed. Try running 'pip install -e .' in the project folder.{Colors.RESET}")

@click.command()
def setup():
    """Add dt to system PATH automatically"""
    import sys, os, subprocess, sysconfig, site
    from pathlib import Path

    # Get multiple possible scripts directories
    paths_to_add = []
    
    # 1. System-wide scripts
    paths_to_add.append(sysconfig.get_path('scripts'))
    
    # 2. User-specific scripts (where pip install --user goes)
    if hasattr(site, 'getuserbase'):
        user_base = site.getuserbase()
        if os.name == 'nt':
            # Handle Microsoft Store / AppData pathing
            paths_to_add.append(os.path.join(user_base, "Scripts"))
            # Specifically for Python 3.11 Store version
            paths_to_add.append(os.path.join(os.environ.get('APPDATA', ''), "Python", "Python311", "Scripts"))
            paths_to_add.append(os.path.join(os.environ.get('LOCALAPPDATA', ''), "Packages", "PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0", "LocalCache", "local-packages", "Python311", "Scripts"))
        else:
            paths_to_add.append(os.path.join(user_base, "bin"))

    click.echo(f"{Colors.CYAN}Configuring system PATH...{Colors.RESET}")
    
    if os.name == 'nt':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except Exception:
            current_path = ""

        updated = False
        new_path_entries = current_path.split(';')
        
        for scripts_dir in paths_to_add:
            if scripts_dir and os.path.exists(scripts_dir) and scripts_dir.lower() not in current_path.lower():
                new_path_entries.append(scripts_dir)
                updated = True
                click.echo(f"{Colors.GREEN}✅ Found and adding: {scripts_dir}{Colors.RESET}")

        if updated:
            new_path = ";".join(new_path_entries)
            ps_cmd = f'[Environment]::SetEnvironmentVariable("Path", "{new_path}", "User")'
            subprocess.run(['powershell', '-Command', ps_cmd], check=True)
            click.echo(f"\n{Colors.YELLOW}👉 CRITICAL: You must RESTART your terminal (close and reopen) for this to work.{Colors.RESET}")
        else:
            click.echo(f"{Colors.GREEN}✅ All detected Python script paths are already in PATH.{Colors.RESET}")
            click.echo(f"{Colors.YELLOW}If 'dt' still doesn't work, please restart your terminal or computer.{Colors.RESET}")
    else:
        # Unix/Linux/Termux
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
                            click.echo(f"{Colors.GREEN}✅ Added {scripts_dir} to {shell_file.name}{Colors.RESET}")
                            updated = True
        
        if updated:
            click.echo(f"{Colors.YELLOW}👉 Please restart your terminal or run 'source ~/.bashrc'{Colors.RESET}")
