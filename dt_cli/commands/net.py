import click, subprocess, socket
from ..config import Colors

@click.command()
@click.argument('host', default='google.com')
def ping(host):
    """Ping a host"""
    click.echo(f"{Colors.CYAN}Pinging {host}...{Colors.RESET}")
    param = '-n' if subprocess.os.name == 'nt' else '-c'
    subprocess.run(['ping', param, '4', host])

@click.command()
def myip():
    """Get public IP address"""
    import requests
    try:
        ip = requests.get('https://api.ipify.org').text
        click.echo(f"{Colors.GREEN}Public IP: {ip}{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Could not fetch public IP{Colors.RESET}")

@click.command()
@click.argument('host')
def dns(host):
    """Lookup DNS records"""
    try:
        ip = socket.gethostbyname(host)
        click.echo(f"{Colors.GREEN}{host} -> {ip}{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Could not resolve {host}{Colors.RESET}")

@click.command()
def scan_network():
    """Scan local network for devices"""
    click.echo(f"{Colors.CYAN}Scanning local network...{Colors.RESET}")
    # Simple implementation using arp -a
    subprocess.run(['arp', '-a'])

@click.command()
def speed():
    """Real internet speed test (Download/Upload)"""
    import speedtest
    click.echo(f"{Colors.CYAN}Initializing Speedtest...{Colors.RESET}")
    try:
        st = speedtest.Speedtest()
        click.echo(f"{Colors.CYAN}Testing download speed...{Colors.RESET}")
        download_speed = st.download() / 1_000_000
        click.echo(f"{Colors.CYAN}Testing upload speed...{Colors.RESET}")
        upload_speed = st.upload() / 1_000_000
        ping = st.results.ping
        
        click.echo(f"\n{Colors.GREEN}Speedtest Results:{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Download: {Colors.GREEN}{download_speed:.2f} Mbps{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Upload:   {Colors.GREEN}{upload_speed:.2f} Mbps{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Ping:     {Colors.YELLOW}{ping} ms{Colors.RESET}")
    except Exception as e:
        click.echo(f"{Colors.RED}Speedtest failed: {e}{Colors.RESET}")

@click.command()
@click.argument('domain')
def whois(domain):
    """Get WHOIS information for a domain"""
    import requests
    click.echo(f"{Colors.CYAN}Fetching WHOIS for {domain}...{Colors.RESET}")
    try:
        # Using a free API for whois to avoid dependency on binary tools
        res = requests.get(f"https://rdap.org/domain/{domain}")
        if res.status_code == 200:
            data = res.json()
            click.echo(f"{Colors.GREEN}Domain: {data.get('ldhName')}{Colors.RESET}")
            click.echo(f"{Colors.WHITE}Status: {', '.join(data.get('status', []))}{Colors.RESET}")
        else:
            click.echo(f"{Colors.RED}Domain not found or API error.{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Could not fetch WHOIS info.{Colors.RESET}")

@click.command()
@click.argument('ip_addr', required=False)
def ip_info(ip_addr):
    """Get location info for an IP address"""
    import requests
    target = ip_addr if ip_addr else ""
    click.echo(f"{Colors.CYAN}Fetching info for {target if target else 'your IP'}...{Colors.RESET}")
    try:
        res = requests.get(f"https://ipapi.co/{target}/json/")
        data = res.json()
        click.echo(f"{Colors.GREEN}IP: {data.get('ip')}{Colors.RESET}")
        click.echo(f"{Colors.WHITE}City: {data.get('city')}{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Region: {data.get('region')}{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Country: {data.get('country_name')}{Colors.RESET}")
        click.echo(f"{Colors.WHITE}ISP: {data.get('org')}{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Could not fetch IP info.{Colors.RESET}")
