import click, shutil, os, datetime, hashlib, concurrent.futures
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, IGNORE_DIRS, bar_width, BORDER_ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt
from rich import box


@click.command()
def send():
    """Zip current folder and save to Desktop/Downloads"""
    folder = Path.cwd()
    default_name = folder.name
    name = ask_filename(default_name)

    zip_path = get_save_path('desktop') / f"{name}.zip"

    console.print(f"[info]Creating zip archive...[/info]")
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        progress.add_task("[info]Zipping...[/info]", total=None)
        shutil.make_archive(
            str(zip_path.with_suffix('')), 'zip', folder,
            ignore=lambda d, files: [f for f in files if f in IGNORE_DIRS]
        )

    if zip_path.exists():
        size = zip_path.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.1f} MB[/dim]")
        confirm_save(zip_path)
    else:
        console.print("[red]Failed to create zip.[/red]")


@click.command()
def clean():
    """Clean junk files from current directory"""
    patterns = ['*.pyc', '*.log', '*.tmp', '.DS_Store', 'Thumbs.db', '*.egg-info']
    count = 0
    size_freed = 0

    for pattern in patterns:
        for f in Path.cwd().rglob(pattern):
            if not any(d in str(f) for d in IGNORE_DIRS):
                try:
                    size_freed += f.stat().st_size
                    f.unlink()
                    count += 1
                except Exception:
                    pass

    for d in Path.cwd().rglob('__pycache__'):
        if d.is_dir() and not any(ignore in str(d) for ignore in IGNORE_DIRS):
            try:
                for f in d.rglob('*'):
                    size_freed += f.stat().st_size
                shutil.rmtree(d)
                count += 1
            except Exception:
                pass

    if count > 0:
        console.print(f"[success]Cleaned {count} files/folders[/success]")
        console.print(f"[dim]Freed {size_freed / 1024:.1f} KB[/dim]")
    else:
        console.print("[success]Already clean![/success]")


@click.command()
def organize():
    """Organize Downloads folder by file type"""
    downloads = get_save_path('downloads')
    moved = 0

    types = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'],
        'videos': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.3gp'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'],
        'music': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    }

    console.print(f"[info]Organizing {downloads}...[/info]")
    for f in downloads.iterdir():
        if f.is_file():
            for folder, exts in types.items():
                if f.suffix.lower() in exts:
                    dest = get_save_path(folder) / f.name
                    try:
                        shutil.move(str(f), str(dest))
                        console.print(f"  [dim]{f.name} -> {folder}/[/dim]")
                        moved += 1
                    except Exception:
                        pass
                    break

    console.print(f"[success]Organized {moved} files[/success]")


@click.command()
@click.argument('name')
def find(name):
    """Find file by name (searches home directory)"""
    console.print(f"[info]Searching for '{name}'...[/info]")
    found = []

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        progress.add_task("[info]Searching...[/info]", total=None)
        for f in Path.home().rglob(f'*{name}*'):
            if f.is_file() and not any(d in str(f) for d in IGNORE_DIRS):
                found.append(f)
                if len(found) >= 15:
                    break

    if found:
        table = Table(box=box.SIMPLE, padding=(0, 1))
        table.add_column("Path", style="white")
        for f in found:
            table.add_row(str(f))
        console.print(table)
        console.print(f"[dim]Found {len(found)} result(s)[/dim]")
    else:
        console.print("[yellow]No files found.[/yellow]")


@click.command()
def big():
    """Show top 10 biggest files in current directory"""
    console.print("[info]Scanning for large files...[/info]")
    files = []
    for f in Path.cwd().rglob('*'):
        if f.is_file() and not any(d in str(f) for d in IGNORE_DIRS):
            try:
                files.append((f, f.stat().st_size))
            except Exception:
                pass

    files.sort(key=lambda x: x[1], reverse=True)

    if files:
        table = Table(box=box.ROUNDED, border_style="warn", title="[warn]TOP 10 BIGGEST FILES[/warn]")
        table.add_column("Size", style="warn", justify="right")
        table.add_column("File", style="white")
        for f, size in files[:10]:
            if size > 1024 * 1024 * 1024:
                size_str = f"{size / (1024**3):.1f} GB"
                style = "red"
            elif size > 1024 * 1024 * 100:
                size_str = f"{size / (1024**2):.1f} MB"
                style = "yellow"
            else:
                size_str = f"{size / 1024:.1f} KB"
                style = "white"
            table.add_row(size_str, str(f.relative_to(Path.cwd())), style=style)
        console.print(table)
    else:
        console.print("[yellow]No files found.[/yellow]")


@click.command()
def duplicate():
    """Find duplicate files by hash"""
    console.print("[info]Scanning for duplicates...[/info]")
    seen = {}
    dups = []

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        progress.add_task("[info]Hashing files...[/info]", total=None)
        for f in Path.cwd().rglob('*'):
            if f.is_file() and f.stat().st_size < 100 * 1024 * 1024:
                if any(d in str(f) for d in IGNORE_DIRS):
                    continue
                try:
                    h = hashlib.md5(f.read_bytes()).hexdigest()
                    if h in seen:
                        dups.append((f, seen[h]))
                    else:
                        seen[h] = f
                except Exception:
                    pass

    if dups:
        table = Table(box=box.ROUNDED, border_style="warn", title="[warn]DUPLICATES FOUND[/warn]")
        table.add_column("Duplicate", style="red")
        table.add_column("Original", style="white")
        for f1, f2 in dups[:10]:
            table.add_row(f1.name, f2.name)
        console.print(table)
        console.print(f"[dim]Found {len(dups)} duplicate(s)[/dim]")
    else:
        console.print("[success]No duplicates found![/success]")


@click.command()
def tree():
    """Show folder tree"""
    from rich.tree import Tree
    from rich import Tree as RichTree

    tree_obj = Tree(f"[bold]{Path.cwd().name}[/bold]")
    _build_tree(tree_obj, Path.cwd(), 0)

    with console.pager():
        console.print(tree_obj)


def _build_tree(tree, path, depth, max_depth=4):
    if depth > max_depth:
        return
    try:
        entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return

    # Filter ignored
    entries = [e for e in entries if e.name not in IGNORE_DIRS and not e.name.startswith('.')]

    for i, entry in enumerate(entries[:20]):  # Limit per directory
        if entry.is_dir():
            branch = tree.add(f"[info]{entry.name}/[/info]")
            _build_tree(branch, entry, depth + 1, max_depth)
        else:
            tree.add(entry.name)


@click.command()
def backup():
    """Create timestamped backup of current folder"""
    name = f"{Path.cwd().name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
    dest = get_save_path('documents') / f"{name}.zip"

    console.print(f"[info]Creating backup...[/info]")
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        progress.add_task("[info]Backing up...[/info]", total=None)
        shutil.make_archive(str(dest.with_suffix('')), 'zip', '.',
                           ignore=lambda d, files: [f for f in files if f in IGNORE_DIRS])

    if dest.exists():
        size = dest.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Backup size: {size:.1f} MB[/dim]")
        confirm_save(dest)


@click.command()
@click.argument('src')
@click.argument('dest')
def fcp(src, dest):
    """High-speed multi-threaded file copy"""
    src_path = Path(src)
    dest_path = Path(dest)

    if not src_path.exists():
        console.print(f"[red]Source does not exist: {src}[/red]")
        return

    console.print(f"[info]Starting high-speed copy...[/info]")

    if src_path.is_file():
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            console=console,
        ) as progress:
            task = progress.add_task("[info]Copying...[/info]", total=src_path.stat().st_size)
            # Chunked copy for large files
            chunk_size = 1024 * 1024 * 8  # 8MB chunks
            with open(src_path, 'rb') as f_in, open(dest_path, 'wb') as f_out:
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    progress.advance(task, len(chunk))
        console.print(f"[success]Copied {src_path.name}[/success]")
    else:
        files = [f for f in src_path.rglob('*') if f.is_file()]

        def copy_file(f):
            rel = f.relative_to(src_path)
            target = dest_path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            console=console,
        ) as progress:
            task = progress.add_task(f"[info]Copying {len(files)} files (8 threads)...[/info]", total=len(files))
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(copy_file, f) for f in files]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
                    progress.advance(task)

        console.print(f"[success]Fast-copied {len(files)} files[/success]")


@click.command()
def where():
    """Show current location with git branch"""
    cwd = Path.cwd()
    table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
    table.add_column(style="dim", ratio=1)
    table.add_column(style="white", ratio=2)
    table.add_row("Path", str(cwd))
    table.add_row("Folder", cwd.name)

    if (cwd / '.git').exists():
        try:
            branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True, stderr=subprocess.PIPE).strip()
            table.add_row("Git", f"[success]{branch}[/success]")
        except Exception:
            pass
    console.print(table)