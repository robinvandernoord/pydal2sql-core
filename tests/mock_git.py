import shutil
from contextlib import contextmanager
from pathlib import Path

from contextlib_chdir import chdir
from plumbum import local

from src.pydal2sql_core.helpers import TempdirOrExistingDir


@contextmanager
def mock_git():
    git = local["git"]
    pytest_examples = Path("./pytest_examples").resolve()
    assert pytest_examples.exists()
    with TempdirOrExistingDir() as cwd, chdir(cwd):
        git("init")
        git("config", "--local", "user.email", "bot@su6.nl")
        git("config", "--local", "user.name", "PyTest")
        git("config", "--local", "commit.gpgsign", "false")

        shutil.copy(pytest_examples / "magic_pre.py", "magic.py")
        git("add", "magic.py")
        git("commit", "-m", "initial commit")
        shutil.copy(pytest_examples / "magic_post.py", "magic.py")
        yield
