from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def empty_module_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.rattle]\nroot=true\nformatter="none"\nenable=[".rules"]\n'
    )
    (tmp_path / "rules.py").write_text(
        "import libcst as cst\n"
        "from rattle import LintRule\n"
        "class EmptyModule(LintRule):\n"
        "    def visit_Module(self, node):\n"
        "        if node.body:\n"
        "            self.report(node, 'Empty the module.', replacement=cst.Module(\n"
        "                body=[], has_trailing_newline=False))\n"
    )
    return tmp_path
