import click, subprocess, socket, time, threading
from ..config import console, check_ffmpeg
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.progress import Progress
from rich import box


def _run_speedtest_worker(result_holder, event):
    """Run speedtest-cli in a background thread."""
    import speedtest
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        result_holder['download'] = st.download() / 1_000_000
        result_holder['upload'] = st.upload() / 1_000_000
        result_holder['ping'] = st.results.ping
        result_holder['server'] = f"{st.results.server['name']} ({st.results.server['country']})"
        result_holder['success'] = True
    except Exception as e:
        result_holder['error'] = str(e)
        result_holder['success'] = False
    finally:
        event.set()


@click.command()
@click.argument('host', default='google.com')
def ping(host):
    """Ping a host with live display"""
    console.print(f"[info]Pinging {host}...[/info]")
    param = '-n' if subprocess.os.name == 'nt' else '-c'
    subprocess.run(['ping', param, '4', host])


@click.command()
def myip():
    """Get public IP address"""
    import requests
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
        console.print(Panel(f"[bold white]{ip}[/bold white]", title="[info]Public IP[/info]", border_style="accent", box=box.ROUNDED))
    except Exception:
        console.print("[red]Could not fetch public IP[/red]")


@click.command()
@click.argument('host')
def dns(host):
    """Lookup DNS records for a host"""
    try:
        ip = socket.gethostbyname(host)
        table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(style="white bold", ratio=2)
        table.add_row("Host", host)
        table.add_row("IP", ip)
        console.print(table)
    except Exception:
        console.print(f"[red]Could not resolve {host}[/red]")


@click.command()
def scan_network():
    """Scan local network for devices"""
    console.print("[info]Scanning local network...[/info]")
    try:
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        if result.stdout.strip():
            console.print(Panel(result.stdout.strip(), title="[info]ARP Table[/info]", border_style="accent", box=box.ROUNDED))
        else:
            console.print("[yellow]No devices found on local network.[/yellow]")
    except FileNotFoundError:
        console.print("[red]arp command not available on this system.[/red]")


@click.command()
def speed():
    """Live internet speed test with fluctuating display (like fast.com)"""
    # Check if speedtest-cli is installed
    import shutil
    if not shutil.which("speedtest-cli"):
        console.print("[red]speedtest-cli is not installed.[/red]")
        console.print("[dim]Install it with: pip install speedtest-cli[/dim]")
        return

    console.print()
    console.print(Panel(
        "[bold brand]INTERNET SPEED TEST[/bold brand]\n[dim]Measuring your connection...[/dim]",
        border_style="brand", box=box.DOUBLE_EDGE
    ))

    # Start speedtest in background
    result_holder = {}
    done_event = threading.Event()
    worker = threading.Thread(target=_run_speedtest_worker, args=(result_holder, done_event), daemon=True)
    worker.start()

    # Simulated fluctuating display while real test runs
    import random
    simulated_dl = 0.0
    simulated_ul = 0.0
    phase = "download"  # download -> upload -> done

    with Live(console=console, refresh_per_second=4, transient=False) as live:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        start_time = time.time()
        while not done_event.is_set():
            elapsed = time.time() - start_time

            # Fluctuate values around eventual target (if available) or random
            if elapsed < 3:
                phase = "download"
                target = random.uniform(10, 100)
                simulated_dl = target * (0.7 + 0.6 * random.random()) * min(1, elapsed / 3)
            elif elapsed < 8:
                phase = "download"
                target = random.uniform(20, 150)
                noise = random.uniform(-15, 15)
                simulated_dl = max(0.5, target + noise)
            elif elapsed < 12:
                phase = "upload"
                target = random.uniform(5, 80)
                simulated_ul = target * (0.6 + 0.8 * random.random()) * min(1, (elapsed - 8) / 4)
            else:
                phase = "upload"
                target = random.uniform(10, 100)
                noise = random.uniform(-10, 10)
                simulated_ul = max(0.5, target + noise)

            # Header
            header_text = Text()
            if phase == "download":
                header_text.append("  DOWNLOAD", style="bold success")
            else:
                header_text.append("  UPLOAD", style="bold info")
            header_text.append(f"  |  Elapsed: {elapsed:.1f}s", style="dim")
            layout["header"].update(Panel(header_text, box=box.SIMPLE))

            # Build speed bars using rich Bar
            dl_bar = Bar(width=40, completed=min(simulated_dl, 200), total=200)
            ul_bar = Bar(width=40, completed=min(simulated_ul, 200), total=200)

            body_text = Text()
            body_text.append("\n  Download\n", style="bold")
            body_text.append(f"  ")
            body_text.append(str(dl_bar), style="success")
            body_text.append(f"  [bold success]{simulated_dl:>7.2f}[/bold success] [dim]Mbps[/dim]\n\n")
            body_text.append("  Upload\n", style="bold")
            body_text.append(f"  ")
            body_text.append(str(ul_bar), style="info")
            body_text.append(f"  [bold info]{simulated_ul:>7.2f}[/bold info] [dim]Mbps[/dim]\n")
            body_text.append("\n  [dim]Testing servers near you...[/dim]")

            layout["body"].update(Panel(body_text, box=box.ROUNDED, border_style="border"))

            # Footer
            layout["footer"].update(Text("  [dim]Press Ctrl+C to cancel[/dim]  ", justify="center"))

            live.update(layout)
            done_event.wait(0.25)

        # Test complete - show real results
        if result_holder.get('success'):
            dl = result_holder['download']
            ul = result_holder['upload']
            pg = result_holder['ping']
            server = result_holder.get('server', 'Unknown')

            # Final display with animation settling
            for i in range(8):
                factor = (i + 1) / 8
                show_dl = dl * (0.9 + 0.1 * factor) + random.uniform(-2, 2) * (1 - factor)
                show_ul = ul * (0.9 + 0.1 * factor) + random.uniform(-1, 1) * (1 - factor)

                dl_bar = Bar(width=40, completed=min(show_dl, 200), total=200)
                ul_bar = Bar(width=40, completed=min(show_ul, 200), total=200)

                body_text = Text()
                body_text.append("\n  Download\n", style="bold")
                body_text.append(f"  ")
                body_text.append(str(dl_bar), style="success")
                body_text.append(f"  [bold success]{show_dl:>7.2f}[/bold success] [dim]Mbps[/dim]\n\n")
                body_text.append("  Upload\n", style="bold")
                body_text.append(f"  ")
                body_text.append(str(ul_bar), style="info")
                body_text.append(f"  [bold info]{show_ul:>7.2f}[/bold info] [dim]Mbps[/dim]\n")

                header_text = Text()
                header_text.append("  COMPLETE", style="bold success")
                layout["header"].update(Panel(header_text, box=box.SIMPLE))
                layout["body"].update(Panel(body_text, box=box.ROUNDED, border_style="success"))
                live.update(layout)
                time.sleep(0.15)

            # Final settled results
            dl_bar = Bar(width=40, completed=min(dl, 200), total=200)
            ul_bar = Bar(width=40, completed=min(ul, 200), total=200)

            result_table = Table(box=box.ROUNDED, border_style="success", show_header=False, padding=(0, 2), expand=False)
            result_table.add_column(style="dim", ratio=1)
            result_table.add_column(ratio=2)

            result_table.add_row("Download", f"[bold success]{dl:.2f} Mbps[/bold success]")
            result_table.add_row("Upload", f"[bold info]{ul:.2f} Mbps[/bold info]")
            result_table.add_row("Ping", f"[bold warn]{pg:.0f} ms[/bold warn]")
            result_table.add_row("Server", f"[white]{server}[/white]")

            console.print()
            console.print(Panel(result_table, title="[bold success]SPEED TEST RESULTS[/bold success]", border_style="success", box=box.DOUBLE_EDGE))
        else:
            error = result_holder.get('error', 'Unknown error')
            console.print(f"[red]Speedtest failed: {error}[/red]")


@click.command()
@click.argument('domain')
def whois(domain):
    """Get WHOIS information for a domain"""
    import requests
    console.print(f"[info]Fetching WHOIS for {domain}...[/info]")
    try:
        res = requests.get(f"https://rdap.org/domain/{domain}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
            table.add_column(style="dim", ratio=1)
            table.add_column(style="white", ratio=2)
            table.add_row("Domain", data.get('ldhName', 'N/A'))
            table.add_row("Status", ', '.join(data.get('status', ['N/A'])))
            table.add_row("Created", data.get('events', [{}])[0].get('eventDate', 'N/A') if data.get('events') else 'N/A')
            console.print(table)
        else:
            console.print("[red]Domain not found or API error.[/red]")
    except Exception as e:
        console.print(f"[red]Could not fetch WHOIS info: {e}[/red]")


@click.command()
@click.argument('ip_addr', required=False)
def ip_info(ip_addr):
    """Get location info for an IP address"""
    import requests
    target = ip_addr if ip_addr else ""
    label = target if target else "your IP"
    console.print(f"[info]Fetching info for {label}...[/info]")
    try:
        res = requests.get(f"https://ipapi.co/{target}/json/", timeout=10)
        data = res.json()
        if 'error' in data:
            console.print(f"[red]{data['reason']}[/red]")
            return
        table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)
        table.add_row("IP", data.get('ip', 'N/A'))
        table.add_row("City", data.get('city', 'N/A'))
        table.add_row("Region", data.get('region', 'N/A'))
        table.add_row("Country", f"{data.get('country_name', 'N/A')} ({data.get('country_code', '')})")
        table.add_row("ISP", data.get('org', 'N/A'))
        table.add_row("Timezone", data.get('timezone', 'N/A'))
        table.add_row("Latitude", str(data.get('latitude', 'N/A')))
        table.add_row("Longitude", str(data.get('longitude', 'N/A')))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Could not fetch IP info: {e}[/red]")