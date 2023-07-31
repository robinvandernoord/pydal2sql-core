"""
CLI-Agnostic support.
"""
import contextlib
import io
import os
import select
import string
import sys
import textwrap
import typing
from pathlib import Path
from typing import Optional

import rich
from black.files import find_project_root
from git.objects.blob import Blob
from git.objects.commit import Commit
from git.repo import Repo

from .helpers import flatten
from .magic import (
    add_function_call,
    find_defined_variables,
    find_function_to_call,
    find_local_imports,
    find_missing_variables,
    generate_magic_code,
    remove_import,
    remove_local_imports,
    remove_specific_variables,
)


def has_stdin_data() -> bool:  # pragma: no cover
    """
    Check if the program starts with cli data (pipe | or redirect ><).

    See Also:
        https://stackoverflow.com/questions/3762881/how-do-i-check-if-stdin-has-some-data
    """
    return any(
        select.select(
            [
                sys.stdin,
            ],
            [],
            [],
            0.0,
        )[0]
    )


AnyCallable = typing.Callable[..., typing.Any]


def print_if_interactive(*args: typing.Any, pretty: bool = True, **kwargs: typing.Any) -> None:  # pragma: no cover
    is_interactive = not has_stdin_data()
    _print = typing.cast(AnyCallable, rich.print if pretty else print)  # make mypy happy
    if is_interactive:
        kwargs["file"] = sys.stderr
        _print(
            *args,
            **kwargs,
        )


def find_git_root(at: str = None) -> Optional[Path]:
    folder, reason = find_project_root((at or os.getcwd(),))
    if reason != ".git directory":
        return None
    return folder


def find_git_repo(repo: Repo = None, at: str = None) -> Repo:
    if repo:
        return repo

    root = find_git_root(at)
    return Repo(str(root))


def latest_commit(repo: Repo = None) -> Commit:
    repo = find_git_repo(repo)
    return repo.head.commit


def commit_by_id(commit_hash: str, repo: Repo = None) -> Commit:
    repo = find_git_repo(repo)
    return repo.commit(commit_hash)


@contextlib.contextmanager
def open_blob(file: Blob) -> typing.Generator[io.BytesIO, None, None]:
    yield io.BytesIO(file.data_stream.read())


def read_blob(file: Blob) -> str:
    with open_blob(file) as f:
        return f.read().decode()


def get_file_for_commit(filename: str, commit_version: str = "latest", repo: Repo = None) -> str:
    repo = find_git_repo(repo, at=filename)
    commit = latest_commit(repo) if commit_version == "latest" else commit_by_id(commit_version, repo)

    file_path = str(Path(filename).resolve())
    # relative to the .git folder:
    relative_file_path = file_path.removeprefix(f"{repo.working_dir}/")

    file_at_commit = commit.tree / relative_file_path
    return read_blob(file_at_commit)


def get_file_for_version(filename: str, version: str, prompt_description: str = "") -> str:
    if version == "current":
        return Path(filename).read_text()
    elif version == "stdin":  # pragma: no cover
        print_if_interactive(
            f"[blue]Please paste your define tables ({prompt_description}) code below "
            f"and press ctrl-D when finished.[/blue]",
            file=sys.stderr,
        )
        result = sys.stdin.read()
        print_if_interactive("[blue]---[/blue]", file=sys.stderr)
        return result
    else:
        return get_file_for_commit(filename, version)


def extract_file_version_and_path(
    file_path_or_git_tag: Optional[str], default_version: str = "stdin"
) -> tuple[str, str | None]:
    """

    Examples:
        myfile.py (implies @current)

        myfile.py@latest
        myfile.py@my-branch
        myfile.py@b3f24091a9

        @latest (implies no path, e.g. in case of ALTER to copy previously defined path)
    """
    if not file_path_or_git_tag:
        return default_version, ""

    if file_path_or_git_tag == "-":
        return "stdin", "-"

    if file_path_or_git_tag.startswith("@"):
        file_version = file_path_or_git_tag.strip("@")
        file_path = None
    elif "@" in file_path_or_git_tag:
        file_path, file_version = file_path_or_git_tag.split("@")
    else:
        file_version = default_version  # `latest` for before; `current` for after.
        file_path = file_path_or_git_tag

    return file_version, file_path


def extract_file_versions_and_paths(
    filename_before: Optional[str], filename_after: Optional[str]
) -> tuple[tuple[str, str | None], tuple[str, str | None]]:
    version_before, filepath_before = extract_file_version_and_path(
        filename_before,
        default_version="current"
        if filename_after and filename_before and filename_after != filename_before
        else "latest",
    )
    version_after, filepath_after = extract_file_version_and_path(filename_after, default_version="current")

    if not (filepath_before or filepath_after):
        raise ValueError("Please supply at least one file name.")
    elif not filepath_after:
        filepath_after = filepath_before
    elif not filepath_before:
        filepath_before = filepath_after

    return (version_before, filepath_before), (version_after, filepath_after)


def get_absolute_path_info(filename: Optional[str], version: str, git_root: Optional[Path] = None) -> tuple[bool, str]:
    if version == "stdin":
        return True, ""
    elif filename is None:
        # can't deal with this, not stdin and no file should show file missing error later.
        return False, ""

    if git_root is None:
        git_root = find_git_root() or Path(os.getcwd())

    path = Path(filename)
    path_via_git = git_root / filename

    if path.exists():
        exists = True
        absolute_path = str(path.resolve())
    elif path_via_git.exists():
        exists = True
        absolute_path = str(path_via_git.resolve())
    else:
        exists = False
        absolute_path = ""

    return exists, absolute_path


def ensure_no_migrate_on_real_db(
    code: str, db_names: typing.Iterable[str] = ("db", "database"), fix: typing.Optional[bool] = False
) -> str:
    variables = find_defined_variables(code)

    found_variables = set()

    for db_name in db_names:
        if db_name in variables:
            if fix:
                code = remove_specific_variables(code, db_names)
            else:
                found_variables.add(db_name)

    if found_variables:
        if len(found_variables) == 1:
            var = next(iter(found_variables))
            message = f"Variable {var} defined in code! "
        else:  # pragma: no cover
            var = ", ".join(found_variables)
            message = f"Variables {var} defined in code! "
        raise ValueError(
            f"{message} Please remove this or use --magic to prevent performing actual migrations on your database."
        )

    if find_local_imports(code):
        if fix:
            code = remove_local_imports(code)
        else:
            raise ValueError("Local imports are used in this file! Please remove these or use --magic.")

    return code


MAX_RETRIES = 20


def handle_cli(
    code_before: str,
    code_after: str,
    db_type: Optional[str] = None,
    tables: Optional[list[str] | list[list[str]]] = None,
    verbose: Optional[bool] = False,
    noop: Optional[bool] = False,
    magic: Optional[bool] = False,
    function_name: Optional[str] = "define_tables",
) -> bool:
    """
    Handle user input.
    """
    # todo: prefix (e.g. public.)

    to_execute = string.Template(
        textwrap.dedent(
            """
        from pydal import *
        from pydal.objects import *
        from pydal.validators import *

        from pydal2sql import generate_sql

        db = database = DAL(None, migrate=False)

        tables = $tables
        db_type = '$db_type'

        $extra

        $code_before

        db_old = db
        db_new = db = database = DAL(None, migrate=False)

        $code_after

        if not tables:
            tables = set(db_old._tables + db_new._tables)

        if not tables:
            raise ValueError('no-tables-found')


        for table in tables:
            print('--', table)
            if table in db_old and table in db_new:
                print(generate_sql(db_old[table], db_new[table], db_type=db_type))
            elif table in db_old:
                print(f'DROP TABLE {table};')
            else:
                print(generate_sql(db_new[table], db_type=db_type))
    """
        )
    )

    code_before = ensure_no_migrate_on_real_db(code_before, fix=magic)
    code_after = ensure_no_migrate_on_real_db(code_after, fix=magic)

    generated_code = to_execute.substitute(
        {
            "tables": flatten(tables or []),
            "db_type": db_type or "",
            "code_before": textwrap.dedent(code_before),
            "code_after": textwrap.dedent(code_after),
            "extra": "",
        }
    )
    if verbose or noop:
        rich.print(generated_code, file=sys.stderr)

    if not noop:
        err: typing.Optional[Exception] = None
        retry_counter = MAX_RETRIES
        while retry_counter > 0:
            retry_counter -= 1
            try:
                exec(generated_code)  # nosec: B102
                return True  # success!
            except ValueError as e:
                err = e

                if str(e) != "no-tables-found":
                    raise e

                if function_name:
                    define_tables = find_function_to_call(generated_code, function_name)

                    # if define_tables function is found, add call to it at end of code
                    if define_tables is not None:
                        generated_code = add_function_call(generated_code, function_name)
                        continue

                # else: no define_tables or other method to use found.

                print(f"No tables found in the top-level or {function_name} function!", file=sys.stderr)
                print(
                    "Please use `db.define_table` or `database.define_table`, "
                    "or if you really need to use an alias like my_db.define_tables, "
                    "add `my_db = db` at the top of the file or pass `--db-name mydb`.",
                    file=sys.stderr,
                )
                print(f"You can also specify a --function to use something else than {function_name}.", file=sys.stderr)

                return False

            except NameError as e:
                err = e
                # something is missing!
                missing_vars = find_missing_variables(generated_code)
                if not magic:
                    rich.print(
                        f"Your code is missing some variables: {missing_vars}. Add these or try --magic",
                        file=sys.stderr,
                    )
                    return False

                extra_code = generate_magic_code(missing_vars)

                generated_code = to_execute.substitute(
                    {
                        "tables": flatten(tables or []),
                        "db_type": db_type or "",
                        "extra": extra_code,
                        "code_before": textwrap.dedent(code_before),
                        "code_after": textwrap.dedent(code_after),
                    }
                )

                if verbose:
                    rich.print(generated_code, file=sys.stderr)
            except ImportError as e:
                err = e
                # if we catch an ImportError, we try to remove the import and retry
                generated_code = remove_import(generated_code, e.name)

        if retry_counter < 1:  # pragma: no cover
            rich.print(f"[red]Code could not be fixed automagically![/red]. Error: {err or '?'}", file=sys.stderr)
            return False

    return True
