"""Regression tests for the bugs fixed in v3.3.1.

Covers:
- truncated command modules (hacker/extra/download) that broke `import dt_cli.cli`
- missing `_download_images` (NameError on `dt dm --type image`)
- version drift between pyproject.toml and dt_cli.__version__ (broke PyPI publish)
"""

import re
import tomllib
from pathlib import Path

from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]


def test_all_sources_compile():
    for path in sorted((ROOT / "dt_cli").rglob("*.py")):
        compile(path.read_bytes(), str(path), "exec")


def test_versions_agree():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    init = (ROOT / "dt_cli" / "__init__.py").read_text(encoding="utf-8")
    init_version = re.search(r'__version__\s*=\s*"([^"]+)"', init).group(1)
    assert pyproject["project"]["version"] == init_version


def test_cli_registers_restored_commands():
    from dt_cli.cli import cli

    names = set(cli.list_commands(None))
    # Restored from truncated / missing code
    for name in ("vault", "sniff", "port-scan", "dm", "pin", "size", "cpu_count"):
        assert name in names


def test_download_images_helper_exists():
    from dt_cli.commands import download

    assert callable(download._download_images)


def test_negative_number_argument():
    from dt_cli.cli import cli

    result = CliRunner().invoke(cli, ["abs", "-5"])
    assert result.exit_code == 0, result.output
    assert "5" in result.output


def test_every_command_help_works():
    from dt_cli.cli import cli

    runner = CliRunner()
    for name in cli.list_commands(None):
        result = runner.invoke(cli, [name, "--help"])
        assert result.exit_code == 0, f"{name}: {result.output}"
