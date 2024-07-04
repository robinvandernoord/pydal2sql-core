import os
import sys
import textwrap
from pathlib import Path

from contextlib_chdir import chdir

from src.pydal2sql_core import core_create
from src.pydal2sql_core.helpers import TempdirOrExistingDir


def test_local_pythonpath():
    with TempdirOrExistingDir() as temp_dir, chdir(temp_dir):
        temp_path = Path(temp_dir)
        with open("dependency.py", "w") as f:
            f.write('def helper(): return "test"')

        code_dir = temp_path / "code"
        code_dir.mkdir()

        db_file = code_dir / "db.py"

        db_file.write_text(textwrap.dedent("""
            from dependency import helper
            db.define_table(helper())
        """))

        # by default, this code will not work
        assert core_create(
            str(db_file),
            magic=True,
            db_type="postgres",
            _update_path=False,
        ) is False

        # but if the pythonpath is updated, it should work:
        # sys.path.append(os.getcwd())

        assert core_create(
            str(db_file),
            magic=True,
            db_type="postgres",
            _update_path=True,
        ) is True
