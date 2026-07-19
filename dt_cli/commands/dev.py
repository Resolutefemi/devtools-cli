import click, os
from datetime import datetime
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, ensure_pip_module, BORDER_ROUNDED
from rich.panel import Panel
from rich import box


@click.command()
@click.argument('lang', type=click.Choice(['node', 'python', 'go', 'rust', 'flutter', 'java', 'c', 'cpp', 'swift', 'kotlin', 'dart', 'ruby', 'php']))
def ignore(lang):
    """Generate .gitignore for a language/framework"""
    if not ensure_pip_module('requests', display_name='requests'):
        return
    import requests
    console.print(f"[info]Fetching .gitignore for [bold]{lang}[/bold]...[/info]")
    try:
        url = f"https://raw.githubusercontent.com/github/gitignore/master/{lang.capitalize()}.gitignore"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            Path('.gitignore').write_text(res.text)
            console.print(f"[success].gitignore for {lang} created[/success]")
        else:
            # Try community gitignores
            url2 = f"https://raw.githubusercontent.com/github/gitignore/main/community/{lang.capitalize()}.gitignore"
            res2 = requests.get(url2, timeout=10)
            if res2.status_code == 200:
                Path('.gitignore').write_text(res2.text)
                console.print(f"[success].gitignore for {lang} created[/success]")
            else:
                console.print(f"[yellow]No .gitignore template found for {lang}.[/yellow]")
    except Exception as e:
        console.print(f"[red]Could not fetch gitignore: {e}[/red]")


@click.command(name='license')  # Using name to avoid Python keyword conflict
def license_cmd():
    """Add MIT License to project"""
    name = click.prompt("Your name")
    year = datetime.now().year
    mit = f"""MIT License

Copyright (c) {year} {name}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    Path('LICENSE').write_text(mit)
    console.print("[success]LICENSE (MIT) created[/success]")


@click.command()
def readme():
    """Generate a README template"""
    project_name = Path.cwd().name
    console.print(Panel(
        f"[bold brand]README GENERATOR[/bold brand]\n[dim]Creating README for: {project_name}[/dim]",
        border_style="brand", box=box.ROUNDED
    ))

    description = click.prompt("\n[info]Project description[/info]" if False else "Project description")
    install_cmd = click.prompt("Install command", default="pip install .")
    usage = click.prompt("Usage example", default="python main.py")

    content = f"""# {project_name}

{description}

## Installation

```bash
{install_cmd}
```

## Usage

```bash
{usage}
```

## Features

- Feature 1
- Feature 2
- Feature 3

## License

MIT
"""
    Path('README.md').write_text(content)
    console.print("[success]README.md created[/success]")