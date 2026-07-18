try:
    import click
except ImportError:
    import sys
    if "setup" not in sys.argv:
        print("Error: Renance DevTools dependencies not found.")
        print("Install with:  pip install renance-dt")
        sys.exit(1)

from .config import console, DT_THEME, IS_TERMUX
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box

# ── Import all command modules ─────────────────────────────────────
from .commands.files import send, clean, organize, find, big, duplicate, tree, backup, where, fcp
from .commands.media import (
    join, music, shrink, clip, gif, extract, compress,
    trim_audio, merge_audio, audio_speed, video_speed,
    reverse_video, add_audio, mute_video, watermark,
    thumbnail, audio_info, video_info,
)
from .commands.check import check, doctor
from .commands.git import gac, repo, undo, pr, branch_clean, stash_all, changelog, sync, git_install, gh_login
from .commands.deploy import ship, login, logout, live, env_push, logs
from .commands.system import ports, kill_port, wifi, ip, battery, space, info, health, update_all, setup, update, sysmon
from .commands.phone import serve_phone, torch, storage, sms, hotspot, wifi_scan, record_audio, backup_photos
from .commands.utils import up, qr, todo, note, timer, weather, paste, pomo, shorten, status
from .commands.net import ping, myip, dns, scan_network, speed, whois, ip_info, ip_loc
from .commands.crypto import passgen, hash, b64encode, b64decode
from .commands.dev import ignore, license_cmd, readme
from .commands.hacker import matrix, port_scan, sniff, vault
from .commands.pro import screenshot, joke, json_fmt, kill_all, search, links, rename
from .commands.extra import extra_cmds
from .commands.convert import convert
from .commands.download import dm


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Renance DevTools - One command to rule them all."""
    if ctx.invoked_subcommand is None:
        show_help()


def show_help():
    """Render the beautiful help dashboard using Rich."""
    from rich import box

    platform = "Termux" if IS_TERMUX else "Desktop"

    # Build the header
    header = Text()
    header.append("  R E N A N C E   D E V T O O L S\n", style="bold brand")
    header.append(f"  v3.1.0  |  {platform}  |  ", style="dim")
    header.append("by Resolutefemi", style="muted")
    header.append("\n  One command to rule them all\n", style="dim")

    console.print(Panel(header, border_style="brand", box=box.DOUBLE_EDGE, padding=(1, 2)))

    all_commands = sorted(cli.list_commands(None))
    categories = {
        "Files": ["fcp", "send", "clean", "organize", "find", "big", "duplicate", "tree", "backup", "where", "search", "rename", "touch2", "mkdir2", "rm2", "ls2", "pwd2", "size", "ext", "basename", "dirname", "exists", "isdir", "isfile", "count_files", "count_dirs", "md5_file", "sha1_file", "sha256_file"],
        "Media": ["join", "music", "shrink", "clip", "gif", "extract", "compress", "screenshot", "convert", "dm", "trim-audio", "merge-audio", "audio-speed", "video-speed", "reverse-video", "add-audio", "mute-video", "watermark", "thumbnail", "audio-info", "video-info"],
        "Network": ["speed", "status", "ping", "dns", "whois", "scan-network", "myip", "ip-info", "ip-loc", "ip2", "http_get", "http_head", "http_options", "url_parse"],
        "Hacker": ["matrix", "vault", "port-scan", "sniff", "kill-all", "mac_addr", "ipv4_gen", "port_gen", "user_agent", "password", "pin", "port_check"],
        "Deploy": ["deploy", "login", "logout", "live", "env-push", "logs"],
        "Git": ["git-install", "gh", "gac", "repo", "pr", "undo", "sync", "changelog", "branch-clean", "stash-all"],
        "System": ["ports", "kill-port", "ip", "battery", "space", "info", "health", "sysmon", "update", "update-all", "setup", "cpu_count", "env_var", "path_list", "mem_total", "mem_avail", "disk_io", "net_io", "uptime", "whoami2", "clear2", "date2", "sleep2"],
        "Phone": ["serve-phone", "torch", "storage", "sms", "hotspot", "wifi-scan", "record-audio", "backup-photos", "wifi"],
        "Utils": ["shorten", "pomo", "weather", "qr", "todo", "note", "timer", "paste", "up", "json", "lorem", "hex_color", "rgb_color", "json_mock", "base64_img", "tz", "timestamp", "days_until", "week_num"],
        "Crypto": ["passgen", "hash", "b64enc", "b64encode", "b64dec", "b64decode", "hexenc", "hexdec", "rot13", "morse", "uuid"],
        "Dev": ["ignore", "license", "readme", "check", "doctor", "github"],
        "Math": ["add", "sub", "mul", "div", "mod", "pow", "sqrt", "sin", "cos", "tan", "log", "log10", "ceil", "floor", "round", "abs", "fact", "c2f", "f2c", "bmi", "mortgage", "tip", "tax", "bin2dec", "dec2bin", "hex2dec", "dec2hex", "oct2dec", "dec2oct", "kg2lb", "lb2kg", "m2ft", "ft2m"],
        "Text": ["upper", "lower", "title", "reverse", "length", "wordcount", "slugify", "camelcase", "snakecase", "kebabcase", "urlenc", "urldec", "echo2"],
        "Fun": ["random", "randint", "choice", "shuffle", "coin", "dice", "magic8", "rps", "catfact", "dogfact", "chuck", "yesno", "nationalize", "genderize", "bored", "bitcoin", "riddles", "advice", "quote", "trump", "kanye", "pokefact", "name_gen", "joke", "coffee"],
    }

    # Build a 3-column table per category
    displayed = set()
    for cat_name, cmd_list in categories.items():
        cmds = [c for c in cmd_list if c in all_commands]
        if not cmds:
            continue
        displayed.update(cmds)

        # Create mini-table for this category
        table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
        table.add_column(style="cmd", ratio=1)
        table.add_column(style="cmd", ratio=1)
        table.add_column(style="cmd", ratio=1)

        # Pad to multiple of 3
        while len(cmds) % 3 != 0:
            cmds.append("")
        for i in range(0, len(cmds), 3):
            row = cmds[i:i+3]
            table.add_row(*row)

        console.print(f"  [bold cat]{cat_name}[/bold cat]")
        console.print(table)
        console.print()

    remaining = sorted(set(all_commands) - displayed - {"help", "about"})
    if remaining:
        table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
        table.add_column(style="cmd", ratio=1)
        table.add_column(style="cmd", ratio=1)
        table.add_column(style="cmd", ratio=1)
        while len(remaining) % 3 != 0:
            remaining.append("")
        for i in range(0, len(remaining), 3):
            table.add_row(*remaining[i:i+3])
        console.print(f"  [bold cat]Other[/bold cat]")
        console.print(table)

    footer = Text()
    footer.append(f"\n  {len(all_commands)} commands available", style="bold")
    footer.append("  |  ", style="dim")
    footer.append("dt COMMAND [ARGS]", style="info")
    footer.append("  |  ", style="dim")
    footer.append("dt help", style="info")
    console.print(footer)
    console.print()


@click.command()
def help_cmd():
    """Show the interactive help dashboard"""
    show_help()


@click.command()
def about():
    """About Renance DevTools"""
    table = Table(box=box.ROUNDED, border_style="brand", show_header=False, padding=(0, 2))
    table.add_column(style="info", ratio=1)
    table.add_column(style="white", ratio=2)
    table.add_row("Name", "[bold brand]Renance DevTools (renance-dt)[/bold brand]")
    table.add_row("Version", "3.1.0")
    table.add_row("Author", "[white]Resolutefemi[/white]")
    table.add_row("Email", "[info]hello@renance.dev[/info]")
    table.add_row("License", "[success]MIT[/success]")
    table.add_row("Status", "[success]Production Ready[/success]")
    console.print(table)
    console.print()
    console.print("[dim]Renance DevTools is a unified CLI ecosystem designed to bridge the gap between[/dim]")
    console.print("[dim]standard OS tools and developer needs. From multi-threaded copying to[/dim]")
    console.print("[dim]one-click deployments and hacker-style diagnostics, it is the only[/dim]")
    console.print("[dim]command you will ever need.[/dim]")
    console.print()


# ── Register all commands ──────────────────────────────────────────
commands_list = [
    send, clean, organize, find, big, duplicate, tree, backup, where, fcp,
    join, music, shrink, clip, gif, extract, compress,
    trim_audio, merge_audio, audio_speed, video_speed,
    reverse_video, add_audio, mute_video, watermark,
    thumbnail, audio_info, video_info,
    check, doctor,
    gac, repo, undo, pr, branch_clean, stash_all, changelog, sync, git_install, gh_login,
    ship, login, logout, live, env_push, logs,
    ports, kill_port, wifi, ip, battery, space, info, health, sysmon, update_all, setup, update,
    serve_phone, torch, storage, sms, hotspot, wifi_scan, record_audio, backup_photos,
    up, qr, todo, note, timer, weather, paste, pomo, shorten, status,
    ping, myip, dns, scan_network, speed, whois, ip_info, ip_loc,
    passgen, hash, b64encode, b64decode,
    ignore, license_cmd, readme, help_cmd, about,
    matrix, port_scan, sniff, vault,
    screenshot, joke, json_fmt, kill_all, search, links, rename,
    convert, dm,
]

commands_list.extend(extra_cmds)

for cmd in commands_list:
    if cmd is help_cmd:
        cli.add_command(cmd, name='help')
    elif cmd is ship:
        cli.add_command(cmd, name='deploy')
    elif cmd is json_fmt:
        cli.add_command(cmd, name='json')
    elif cmd is kill_all:
        cli.add_command(cmd, name='kill-all')
    elif cmd is port_scan:
        cli.add_command(cmd, name='port-scan')
    elif cmd is scan_network:
        cli.add_command(cmd, name='scan-network')
    elif cmd is license_cmd:
        cli.add_command(cmd, name='license')
    elif cmd is ip_loc:
        cli.add_command(cmd, name='ip-loc')
    else:
        cli.add_command(cmd)

if __name__ == "__main__":
    cli()