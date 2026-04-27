try:
    import click
except ImportError:

    import sys
    if "setup" not in sys.argv:
        print("❌ Error: Renance DevTools dependencies not found.")
        print("To fix this, please run the installer in the project folder:")
        print("   Windows: install.bat")
        print("   Unix:    bash install.sh")
    sys.exit(1)

from colorama import Fore, Style
from pathlib import Path

from .commands.files import send, clean, organize, find, big, duplicate, tree, backup, where, fcp
from .commands.media import join, music, shrink, clip, gif, extract, compress
from .commands.check import check, doctor
from .commands.git import gac, repo, undo, pr, branch_clean, stash_all, changelog, sync, git_install, gh_login
from .commands.deploy import ship, login, logout, live, env_push, logs
from .commands.system import ports, kill_port, wifi, ip, battery, space, info, health, update_all, setup, update
from .commands.phone import serve_phone, torch, storage, sms, hotspot, wifi_scan, record_audio, backup_photos
from .commands.utils import up, qr, todo, note, timer, convert, weather, paste, pomo, shorten, status
from .commands.net import ping, myip, dns, scan_network, speed, whois, ip_info
from .commands.crypto import passgen, hash, b64encode, b64decode
from .commands.dev import ignore, license, readme
from .commands.hacker import matrix, port_scan, sniff, vault
from .commands.pro import screenshot, joke, json_fmt, kill_all, search, links, rename
from .commands.extra import extra_cmds

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        show_help()

def show_help():
    from .config import IS_TERMUX
    platform = "📱 Termux" if IS_TERMUX else "💻"
    click.echo(f"\n{Fore.CYAN}{Style.BRIGHT}🚀 Renance DevTools v3.0 {platform}{Style.RESET_ALL}")
    click.echo(f"{Fore.WHITE}Built with ❤️ by Resolutefemi\n{Style.RESET_ALL}")
    
    all_commands = sorted(cli.list_commands(None))
    
    categories = {
        "📁 Files": ["fcp", "send", "clean", "organize", "find", "big", "duplicate", "tree", "backup", "where", "search", "rename", "touch2", "mkdir2", "rm2", "ls2", "pwd2", "size", "ext", "basename", "dirname", "exists", "isdir", "isfile", "count_files", "count_dirs", "md5_file", "sha1_file", "sha256_file"],
        "🎬 Media": ["join", "music", "shrink", "clip", "gif", "extract", "compress", "screenshot", "links", "coffee"],
        "🌐 Network": ["speed", "status", "ping", "dns", "whois", "scan-network", "myip", "ip2", "ip-info", "ip_loc", "http_get", "http_head", "http_options", "url_parse"],
        "🕶️ Hacker": ["matrix", "vault", "port-scan", "sniff", "kill-all", "mac_addr", "ipv4_gen", "port_gen", "user_agent", "password", "pin", "port_check"],
        "🚀 Deploy": ["deploy", "login", "logout", "live", "env-push", "logs"],
        "🐙 Git": ["git-install", "gh", "gac", "repo", "pr", "undo", "sync", "changelog", "branch-clean", "stash-all"],
        "💻 System": ["ports", "kill-port", "ip", "battery", "space", "info", "health", "update", "update-all", "setup", "cpu_count", "env_var", "path_list", "mem_total", "mem_avail", "disk_io", "net_io", "uptime", "whoami2", "clear2", "date2", "sleep2"],
        "📱 Phone": ["serve-phone", "torch", "storage", "sms", "hotspot", "wifi-scan", "record-audio", "backup-photos", "wifi"],
        "🛠️ Utils": ["shorten", "pomo", "weather", "qr", "todo", "note", "timer", "convert", "paste", "up", "json", "lorem", "hex_color", "rgb_color", "json_mock", "base64_img", "tz", "timestamp", "days_until", "week_num"],
        "🔐 Crypto": ["passgen", "hash", "b64enc", "b64encode", "b64dec", "b64decode", "hexenc", "hexdec", "rot13", "morse", "uuid"],
        "👨‍💻 Dev": ["ignore", "license", "readme", "check", "doctor", "github"],
        "🧮 Math": ["add", "sub", "mul", "div", "mod", "pow", "sqrt", "sin", "cos", "tan", "log", "log10", "ceil", "floor", "round", "abs", "fact", "c2f", "f2c", "bmi", "mortgage", "tip", "tax", "bin2dec", "dec2bin", "hex2dec", "dec2hex", "oct2dec", "dec2oct", "kg2lb", "lb2kg", "m2ft", "ft2m"],
        "🔤 Text": ["upper", "lower", "title", "reverse", "length", "wordcount", "slugify", "camelcase", "snakecase", "kebabcase", "urlenc", "urldec", "echo2"],
        "🎲 Fun": ["random", "randint", "choice", "shuffle", "coin", "dice", "magic8", "rps", "catfact", "dogfact", "chuck", "yesno", "nationalize", "genderize", "bored", "bitcoin", "riddles", "advice", "quote", "trump", "kanye", "pokefact", "name_gen", "joke"]
    }

    import shutil
    term_cols, _ = shutil.get_terminal_size()
    col_width = 18
    num_cols = max(1, term_cols // col_width)

    displayed_cmds = set()

    for cat_name, cmd_list in categories.items():
        # Filter to only include commands that actually exist in cli
        cmds = [c for c in cmd_list if c in all_commands]
        if cmds:
            click.echo(f"{Fore.MAGENTA}{Style.BRIGHT}{cat_name}{Style.RESET_ALL}")
            for i in range(0, len(cmds), num_cols):
                chunk = cmds[i:i + num_cols]
                line = "".join(f"{Fore.GREEN}{cmd:<{col_width}}{Style.RESET_ALL}" for cmd in chunk)
                click.echo(line)
            click.echo("") # Empty line between categories
            displayed_cmds.update(cmds)

    # Catch any missing commands
    remaining = sorted(list(set(all_commands) - displayed_cmds - {"help", "about"}))
    if remaining:
        click.echo(f"{Fore.MAGENTA}{Style.BRIGHT}📦 Uncategorized{Style.RESET_ALL}")
        for i in range(0, len(remaining), num_cols):
            chunk = remaining[i:i + num_cols]
            line = "".join(f"{Fore.GREEN}{cmd:<{col_width}}{Style.RESET_ALL}" for cmd in chunk)
            click.echo(line)
        click.echo("")

    click.echo(f"{Fore.YELLOW}Total Commands: {len(all_commands)}{Style.RESET_ALL}")
    click.echo(f"{Fore.YELLOW}Usage: dt COMMAND [ARGS]...{Style.RESET_ALL}")
    click.echo(f"{Fore.CYAN}Run 'dt about' for project information.\n{Style.RESET_ALL}")

@click.command()
def help_cmd():
    """Show the interactive help dashboard"""
    show_help()

@click.command()
def about():
    """About Renance DevTools"""
    click.echo(f"\n{Fore.CYAN}{Style.BRIGHT}🚀 Renance DevTools (renance-dt) v3.0{Style.RESET_ALL}")
    click.echo(f"{Fore.GREEN}Built by: {Fore.WHITE}Resolutefemi")
    click.echo(f"{Fore.GREEN}Email:    {Fore.WHITE}hello@renance.dev")
    click.echo(f"{Fore.GREEN}Status:   {Fore.WHITE}Production Ready")
    click.echo(f"\n{Fore.YELLOW}Renance DevTools is a unified CLI ecosystem designed to bridge the gap between")
    click.echo(f"standard OS tools and developer needs. From multi-threaded copying to")
    click.echo(f"one-click deployments and hacker-style diagnostics, it is the only")
    click.echo(f"command you will ever need.{Style.RESET_ALL}\n")

# Register all commands
commands_list = [
    send, clean, organize, find, big, duplicate, tree, backup, where, fcp,
    join, music, shrink, clip, gif, extract, compress,
    check, doctor,
    gac, repo, undo, pr, branch_clean, stash_all, changelog, sync, git_install, gh_login,
    ship, login, logout, live, env_push, logs,
    ports, kill_port, wifi, ip, battery, space, info, health, update_all, setup, update,
    serve_phone, torch, storage, sms, hotspot, wifi_scan, record_audio, backup_photos,
    up, qr, todo, note, timer, convert, weather, paste, pomo, shorten, status,
    ping, myip, dns, scan_network, speed, whois, ip_info,
    passgen, hash, b64encode, b64decode,
    ignore, license, readme, help_cmd, about,
    matrix, port_scan, sniff, vault,
    screenshot, joke, json_fmt, kill_all, search, links, rename
]

commands_list.extend(extra_cmds)

for cmd in commands_list:
    # Rename commands for better CLI naming
    if cmd == help_cmd:
        cli.add_command(cmd, name='help')
    elif cmd == ship:
        cli.add_command(cmd, name='deploy')
    elif cmd == json_fmt:
        cli.add_command(cmd, name='json')
    elif cmd == kill_all:
        cli.add_command(cmd, name='kill-all')
    elif cmd == port_scan:
        cli.add_command(cmd, name='port-scan')
    elif cmd == scan_network:
        cli.add_command(cmd, name='scan-network')
    else:
        cli.add_command(cmd)

if __name__ == "__main__":
    cli()
