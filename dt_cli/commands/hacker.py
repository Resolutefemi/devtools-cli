import click, time, random, socket
from ..config import Colors

@click.command()
def matrix():
    """Enter the Matrix (Hacker effect)"""
    import shutil
    columns, rows = shutil.get_terminal_size()
    
    # Character set
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890@#$%^&*()+-="
    
    # Initialize column positions
    drops = [0] * columns
    
    click.echo(f"{Colors.GREEN}")
    try:
        while True:
            line = ""
            for i in range(columns):
                if drops[i] == 0 and random.random() > 0.95:
                    drops[i] = 1
                
                if drops[i] > 0:
                    line += random.choice(chars)
                    drops[i] += 1
                    if drops[i] > rows or random.random() > 0.95:
                        drops[i] = 0
                else:
                    line += " "
            
            click.echo(line)
            time.sleep(0.05)
    except KeyboardInterrupt:
        click.echo(f"{Colors.RESET}Exited the Matrix.")

@click.command()
@click.argument('host')
@click.option('--start', default=1, help='Start port')
@click.option('--end', default=1024, help='End port')
def port_scan(host, start, end):
    """Scan for open ports on a host"""
    click.echo(f"{Colors.CYAN}Scanning {host} from port {start} to {end}...{Colors.RESET}")
    
    open_ports = []
    try:
        for port in range(start, end + 1):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            result = s.connect_ex((host, port))
            if result == 0:
                click.echo(f"{Colors.GREEN}Port {port} is OPEN{Colors.RESET}")
                open_ports.append(port)
            s.close()
            
        if not open_ports:
            click.echo(f"{Colors.YELLOW}No open ports found in range.{Colors.RESET}")
        else:
            click.echo(f"\n{Colors.GREEN}Scan Complete. Found {len(open_ports)} open ports.{Colors.RESET}")
    except KeyboardInterrupt:
        click.echo(f"{Colors.YELLOW}Scan aborted by user.{Colors.RESET}")
    except Exception as e:
        click.echo(f"{Colors.RED}Scan failed: {e}{Colors.RESET}")

@click.command()
@click.argument('file_path')
def vault(file_path):
    """Encrypt or Decrypt a file with a password (Toggle)"""
    import base64
    from pathlib import Path
    p = Path(file_path)
    if not p.exists():
        click.echo(f"{Colors.RED}File not found.{Colors.RESET}")
        return
        
    password = click.prompt("Enter vault password", hide_input=True)
    # Simple XOR cipher for "hacker" feel without heavy dependencies
    key = sum(ord(c) for c in password)
    
    click.echo(f"{Colors.CYAN}Processing vault...{Colors.RESET}")
    content = p.read_bytes()
    processed = bytes([b ^ (key % 256) for b in content])
    p.write_bytes(processed)
    
    click.echo(f"{Colors.GREEN}✅ Vault processing complete for {file_path}{Colors.RESET}")

@click.command()
def sniff():
    """Simulate network sniffing (Hacker feel)"""
    import random
    click.echo(f"{Colors.RED}[!] WARNING: SNIFFER MODE ACTIVE{Colors.RESET}")
    click.echo(f"{Colors.YELLOW}[*] Listening on all interfaces...{Colors.RESET}")
    
    protocols = ["TCP", "UDP", "HTTP", "HTTPS", "DNS", "SSH", "FTP"]
    
    try:
        while True:
            ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            proto = random.choice(protocols)
            size = random.randint(40, 1500)
            
            click.echo(f"{Colors.GREEN}[{time.strftime('%H:%M:%S')}] {Colors.WHITE}{proto:5} {Colors.CYAN}{ip:15} {Colors.WHITE}-> {Colors.GREEN}{size} bytes{Colors.RESET}")
            time.sleep(random.uniform(0.1, 0.5))
    except KeyboardInterrupt:
        click.echo(f"\n{Colors.RESET}Sniffing stopped.")
