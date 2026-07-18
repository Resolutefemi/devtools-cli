import click, time, random, socket, shutil, os, base64
from ..config import console, bar_width, BORDER_ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live
from rich.text import Text
from rich import box


@click.command()
def matrix():
    """Enter the Matrix (Hacker rain effect)"""
    columns, rows = shutil.get_terminal_size()
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()+-="

    # Initialize drops with random positions for immediate visual
    drops = [random.randint(0, rows) for _ in range(columns)]
    bright = [False] * columns

    # Hide cursor
    console.print("\033[?25l", end="")

    try:
        with Live(console=console, refresh_per_second=20, transient=False) as live:
            while True:
                lines = []
                for _ in range(rows):
                    line = Text()
                    for x in range(columns):
                        if drops[x] > 0:
                            ch = random.choice(chars)
                            if drops[x] == 1:
                                # Head of the drop - bright white
                                line.append(ch, style="bold white")
                            elif bright[x] and random.random() > 0.95:
                                # Occasional bright green flash
                                line.append(ch, style="bold #00FF88")
                            else:
                                line.append(ch, style="green")
                            drops[x] += 1
                            if drops[x] > rows or random.random() > 0.98:
                                drops[x] = 0
                                bright[x] = random.random() > 0.5
                        else:
                            line.append(" ", style="black on black")
                    lines.append(line)

                # Randomly start new drops
                for x in range(columns):
                    if drops[x] == 0 and random.random() > 0.97:
                        drops[x] = 1
                        bright[x] = random.random() > 0.3

                live.update(Text("\n").join(lines))
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        # Show cursor again
        console.print("\033[?25h", end="")
        console.print("[dim]Exited the Matrix.[/dim]")


@click.command()
@click.argument('host')
@click.option('--start', default=1, help='Start port')
@click.option('--end', default=1024, help='End port')
def port_scan(host, start, end):
    """Scan for open ports with live progress"""
    console.print()
    console.print(Panel(
        f"[bold brand]PORT SCANNER[/bold brand]\n"
        f"[dim]Scanning {host} from port {start} to {end}[/dim]",
        border_style="brand", box=box.ROUNDED
    ))

    open_ports = []
    total = end - start + 1

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("[info]Scanning...[/info]", total=total)

            for port in range(start, end + 1):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.1)
                result = s.connect_ex((host, port))
                if result == 0:
                    open_ports.append(port)
                    # Common port names
                    services = {
                        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
                        80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 445: 'SMB',
                        993: 'IMAPS', 995: 'POP3S', 3306: 'MySQL', 3389: 'RDP',
                        5432: 'PostgreSQL', 5900: 'VNC', 6379: 'Redis', 8080: 'HTTP-Alt',
                        8443: 'HTTPS-Alt', 27017: 'MongoDB',
                    }
                    svc = services.get(port, '')
                    label = f"[success]OPEN[/success]  :{port:<6} {f'({svc})' if svc else ''}"
                    console.print(label)
                s.close()
                progress.advance(task)

        console.print()
        if open_ports:
            table = Table(box=box.ROUNDED, border_style="success", show_header=True, padding=(0, 2))
            table.add_column("Port", style="success", justify="right")
            table.add_column("Status", style="white")
            table.add_column("Service", style="dim")
            services = {
                21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
                80: 'HTTP', 110: 'POP3', 143: 'IMAP', 443: 'HTTPS', 445: 'SMB',
                993: 'IMAPS', 995: 'POP3S', 3306: 'MySQL', 3389: 'RDP',
                5432: 'PostgreSQL', 5900: 'VNC', 6379: 'Redis', 8080: 'HTTP-Alt',
                8443: 'HTTPS-Alt', 27017: 'MongoDB',
            }
            for p in sorted(open_ports):
                table.add_row(str(p), "[green]OPEN[/green]", services.get(p, 'Unknown'))
            console.print(table)
            console.print(f"\n[dim]Found {len(open_ports)} open port(s) out of {total} scanned.[/dim]")
        else:
            console.print("[yellow]No open ports found in range.[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan aborted by user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Scan failed: {e}[/red]")


@click.command()
@click.argument('file_path')
def vault(file_path):
    """Encrypt or decrypt a file with a password (XOR toggle)"""
    from pathlib import Path
    from ..config import ask_filename, get_save_path

    p = Path(file_path)
    if not p.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return

    password = click.prompt("Enter vault password", hide_input=True)
    # XOR cipher
    key = sum(ord(c) for c in password)

    console.print(f"[info]Processing vault...[/info]")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=bar_width()),
        console=console, transient=True,
    ) as progress:
        progress.add_task("[info]Encrypting/Decrypting...[/info]", total=None)
        content = p.read_bytes()
        processed = bytes([b ^ (key % 256) for b in content])

        # Save to Downloads
        output = get_save_path('downloads') / f"{p.stem}_vaulted{p.suffix}"
        output.write_bytes(processed)

    confirm_save(output)


@click.command()
def sniff():
    """Simulate network packet sniffing (visual hacker feel)"""
    console.print()
    console.print(Panel(
        "[bold red]SNIFFER MODE ACTIVE[/bold red]\n"
        "[dim]Simulated packet capture for visual effect[/dim]\n"
        "[dim]Press Ctrl+C to stop[/dim]",
        border_style="red", box=box.DOUBLE_EDGE
    ))

    protocols = ["TCP", "UDP", "HTTP", "HTTPS", "DNS", "SSH", "FTP", "TLS", "QUIC", "ICMP"]
    flags_list = ["SYN", "ACK", "PSH,ACK", "FIN,ACK", "SYN,ACK", "RST", "URG,PSH"]

    try:
        with Live(console=console, refresh_per_second=4, transient=True) as live:
            packets = []
            while True:
                ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                proto = random.choice(protocols)
                size = random.randint(40, 1500)
                port = random.randint(1, 65535)
                flag = random.choice(flags_list) if proto in ("TCP", "TLS") else ""
                ts = time.strftime('%H:%M:%S')

                color = {
                    "HTTPS": "green", "SSH": "green", "TLS": "green",
                    "HTTP": "yellow", "DNS": "cyan", "FTP": "red",
                }.get(proto, "white")

                line = f"[dim]{ts}[/dim] [{color}]{proto:<6}[/{color}] {ip}:{port:<6} [dim]{size}B[/dim] {flag}"
                packets.append(line)

                # Keep last 15 lines
                if len(packets) > 15:
                    packets = packets[-15:]

                output = Text("\n").join(Text(p) for p in packets)
                live.update(Panel(
                    output,
                    title="[bold red]PACKET CAPTURE[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                ))
                time.sleep(random.uniform(0.2, 0.6))
    except KeyboardInterrupt:
        console.print("\n[dim]Sniffing stopped.[/dim]")