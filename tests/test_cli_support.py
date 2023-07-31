import os
import shutil
from pathlib import Path

import pytest
from contextlib_chdir import chdir

from src.pydal2sql_core.cli_support import (
    extract_file_versions_and_paths,
    find_git_root,
    get_absolute_path_info,
    get_file_for_version,
)
from src.pydal2sql_core.helpers import TempdirOrExistingDir
from tests.mock_git import mock_git


def test_extract_file_versions_and_paths():
    with pytest.raises(ValueError):
        extract_file_versions_and_paths("", "")

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("my.file", "")

    assert name1 == name2
    assert version1 == "latest"
    assert version2 == "current"

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("", "my.file")

    assert name1 == name2
    assert version1 == "latest"
    assert version2 == "current"

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("@development", "my.file@latest")

    assert name1 == name2
    assert version1 == "development"
    assert version2 == "latest"

    (version1, name1), (version2, name2) = extract_file_versions_and_paths("-", "my.file@latest")

    assert name1 != name2
    assert version1 == "stdin"
    assert version2 == "latest"


def test_git_support():
    with mock_git():
        file_contents = get_file_for_version("magic.py", "current")

        assert "this is the changed file" in file_contents

        file_contents = get_file_for_version("magic.py", "latest")

        assert "this is the original file" in file_contents

        file_contents = get_file_for_version("magic.py", "master")

        assert "this is the original file" in file_contents

        os.mkdir("nested")
        with chdir("nested"):
            exists, path = get_absolute_path_info("-", "stdin")
            assert exists
            exists, path = get_absolute_path_info("magic.py", "...")
            assert exists
            assert path and "nested" not in path

            exists, path = get_absolute_path_info(None, "")
            assert not exists

            exists, path = get_absolute_path_info("nested_magic.py", "...")
            assert not exists

            shutil.copy("../magic.py", "nested_magic.py")
            exists, path = get_absolute_path_info("nested_magic.py", "...")
            assert exists
            assert "nested/nested_magic.py" in path

    with TempdirOrExistingDir() as cwd, chdir(cwd):
        Path("pyproject.toml").touch()
        assert find_git_root() is None
