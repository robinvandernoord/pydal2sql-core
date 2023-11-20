"""
CLI-Agnostic support.
"""
import contextlib
import io
import os
import re
import select
import string
import sys
import textwrap
import traceback
import typing
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import git
import gitdb.exc
import rich
from black.files import find_project_root
from git.objects.blob import Blob
from git.objects.commit import Commit
from git.repo import Repo
from witchery import (
    add_function_call,
    find_defined_variables,
    find_function_to_call,
    find_missing_variables,
    generate_magic_code,
    has_local_imports,
    remove_if_falsey_blocks,
    remove_import,
    remove_local_imports,
    remove_specific_variables,
)

from .helpers import excl, flatten, uniq
from .types import (
    _SUPPORTED_OUTPUT_FORMATS,
    DEFAULT_OUTPUT_FORMAT,
    SUPPORTED_DATABASE_TYPES_WITH_ALIASES,
    SUPPORTED_OUTPUT_FORMATS,
    DummyDAL,
    DummyTypeDAL,
)


def has_stdin_data() -> bool:  # pragma: no cover
    """
    Check if the program starts with cli data (pipe | or redirect <).

    Returns:
        bool: True if the program starts with cli data, False otherwise.

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


AnyCallable = typing.Callable[..., Any]


def print_if_interactive(*args: Any, pretty: bool = True, **kwargs: Any) -> None:  # pragma: no cover
    """
    Print the given arguments if running in an interactive session.

    Args:
        *args: Variable length list of arguments to be printed.
        pretty (bool): If True, print using rich library's rich.print, otherwise use the built-in print function.
        **kwargs: Optional keyword arguments to be passed to the print function.

    Returns:
        None
    """
    is_interactive = not has_stdin_data()
    _print = typing.cast(AnyCallable, rich.print if pretty else print)  # make mypy happy
    if is_interactive:
        kwargs["file"] = sys.stderr
        _print(
            *args,
            **kwargs,
        )


def find_git_root(at: str = None) -> Optional[Path]:
    """
    Find the root directory of the Git repository.

    Args:
        at (str, optional): The directory path to start the search. Defaults to the current working directory.

    Returns:
        Optional[Path]: The root directory of the Git repository if found, otherwise None.
    """
    folder, reason = find_project_root((at or os.getcwd(),))
    if reason != ".git directory":
        return None
    return folder


def find_git_repo(repo: Repo = None, at: str = None) -> Repo:
    """
    Find the Git repository instance.

    Args:
        repo (Repo, optional): An existing Git repository instance. If provided, returns the same instance.
        at (str, optional): The directory path to start the search. Defaults to the current working directory.

    Returns:
        Repo: The Git repository instance.
    """
    if repo:
        return repo

    root = find_git_root(at)
    return Repo(str(root))


def latest_commit(repo: Repo = None) -> Commit:
    """
    Get the latest commit in the Git repository.

    Args:
        repo (Repo, optional): An existing Git repository instance. If provided, uses the given instance.

    Returns:
        Commit: The latest commit in the Git repository.
    """
    repo = find_git_repo(repo)
    return repo.head.commit


def commit_by_id(commit_hash: str, repo: Repo = None) -> Commit:
    """
    Get a specific commit in the Git repository by its hash or name.

    Args:
        commit_hash (str): The hash of the commit to retrieve. Can also be e.g. a branch name.
        repo (Repo, optional): An existing Git repository instance. If provided, uses the given instance.

    Returns:
        Commit: The commit object corresponding to the given commit hash.
    """
    repo = find_git_repo(repo)
    return repo.commit(commit_hash)


@contextlib.contextmanager
def open_blob(file: Blob) -> typing.Generator[io.BytesIO, None, None]:
    """
    Open a Git Blob object as a context manager, providing access to its data.

    Args:
        file (Blob): The Git Blob object to open.

    Yields:
        io.BytesIO: A BytesIO object providing access to the Blob data.
    """
    yield io.BytesIO(file.data_stream.read())


def read_blob(file: Blob) -> str:
    """
    Read the contents of a Git Blob object and decode it as a string.

    Args:
        file (Blob): The Git Blob object to read.

    Returns:
        str: The contents of the Blob as a string.
    """
    with open_blob(file) as f:
        return f.read().decode()


def get_file_for_commit(filename: str, commit_version: str = "latest", repo: Repo = None) -> str:
    """
    Get the contents of a file in the Git repository at a specific commit version.

    Args:
        filename (str): The path of the file to retrieve.
        commit_version (str, optional): The commit hash or branch name. Defaults to "latest" (latest commit).
        repo (Repo, optional): An existing Git repository instance. If provided, uses the given instance.

    Returns:
        str: The contents of the file as a string.
    """
    repo = find_git_repo(repo, at=filename)
    commit = latest_commit(repo) if commit_version == "latest" else commit_by_id(commit_version, repo)

    file_path = str(Path(filename).resolve())
    # relative to the .git folder:
    relative_file_path = file_path.removeprefix(f"{repo.working_dir}/")

    file_at_commit = commit.tree / relative_file_path
    return read_blob(file_at_commit)


def get_file_for_version(filename: str, version: str, prompt_description: str = "", with_git: bool = True) -> str:
    """
    Get the contents of a file based on the version specified.

    Args:
        filename (str): The path of the file to retrieve.
        version (str): The version specifier, which can be "current", "stdin", or a commit hash/branch name.
        prompt_description (str, optional): A description to display when asking for input from stdin.

    Returns:
        str: The contents of the file as a string.
    """
    if not with_git or version == "current":
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
    elif with_git:
        try:
            return get_file_for_commit(filename, version)
        except (git.exc.GitError, gitdb.exc.ODBError) as e:
            raise FileNotFoundError(f"{filename}@{version}") from e


def extract_file_version_and_path(
    file_path_or_git_tag: Optional[str], default_version: str = "stdin"
) -> tuple[str, str | None]:
    """
    Extract the file version and path from the given input.

    Args:
        file_path_or_git_tag (str, optional): The input string containing the file path and/or Git tag.
        default_version (str, optional): The default version to use if no version is specified. Defaults to "stdin".

    Returns:
        tuple[str, str | None]: A tuple containing the extracted version and file path (or None if not specified).

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
    """
    Extract the file versions and paths based on the before and after filenames.

    Args:
        filename_before (str, optional): The path of the file before the change (or None).
        filename_after (str, optional): The path of the file after the change (or None).

    Returns:
        tuple[tuple[str, str | None], tuple[str, str | None]]:
            A tuple of two tuples, each containing the version and path of the before and after files.
    """
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
    """
    Get absolute path information for the file based on the version and Git root.

    Args:
        filename (str, optional): The path of the file to check (or None).
        version (str): The version specifier, which can be "stdin", "current", or a commit hash/branch name.
        git_root (Path, optional): The root directory of the Git repository. If None, it will be determined.

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating if the file exists and the absolute path to the file.
    """
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
    """
    Ensure that the code does not contain actual migrations on a real database.

    It does this by removing definitions of 'db' and database. This can be changed by customizing `db_names`.
    It also removes local imports to prevent irrelevant code being executed.

    Args:
        code (str): The code to check for database migrations.
        db_names (Iterable[str], optional): Names of variables representing the database.
            Defaults to ("db", "database").
        fix (bool, optional): If True, removes the migration code. Defaults to False.

    Returns:
        str: The modified code with migration code removed if fix=True, otherwise the original code.
    """
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

    if has_local_imports(code):
        if fix:
            code = remove_local_imports(code)
        else:
            raise ValueError("Local imports are used in this file! Please remove these or use --magic.")

    return code


MAX_RETRIES = 30

# todo: overload more methods

TEMPLATE_PYDAL = """
from pydal import *
from pydal.objects import *
from pydal.validators import *

from pydal2sql_core import generate_sql


# from pydal import DAL
db = database = DummyDAL(None, migrate=False)

tables = $tables
db_type = '$db_type'

$extra

$code_before

db_old = db
db_new = db = database = DummyDAL(None, migrate=False)

$extra

$code_after

if not tables:
    tables = _uniq(db_old._tables + db_new._tables)
    tables = _excl(tables, _special_tables)

if not tables:
    raise ValueError('no-tables-found')

for table in tables:
    print('-- start ', table, '--', file=_file)
    if table in db_old and table in db_new:
        print(generate_sql(db_old[table], db_new[table], db_type=db_type), file=_file)
    elif table in db_old:
        print(f'DROP TABLE {table};', file=_file)
    else:
        print(generate_sql(db_new[table], db_type=db_type), file=_file)
    print('-- END OF MIGRATION --', file=_file)
    """

TEMPLATE_TYPEDAL = """
from pydal import *
from pydal.objects import *
from pydal.validators import *
from typedal import *

from pydal2sql_core import generate_sql


# from typedal import TypeDAL as DAL
db = database = DummyDAL(None, migrate=False)

tables = $tables
db_type = '$db_type'

$extra

$code_before

db_old = db
db_new = db = database = DummyDAL(None, migrate=False)

$extra

$code_after

if not tables:
    tables = _uniq(db_old._tables + db_new._tables)
    tables = _excl(tables, _special_tables)

if not tables:
    raise ValueError('no-tables-found')


for table in tables:
    print('-- start ', table, '--', file=_file)
    if table in db_old and table in db_new:
        print(generate_sql(db_old[table], db_new[table], db_type=db_type), file=_file)
    elif table in db_old:
        print(f'DROP TABLE {table};', file=_file)
    else:
        print(generate_sql(db_new[table], db_type=db_type), file=_file)

    print('-- END OF MIGRATION --', file=_file)
    """


def sql_to_function_name(sql_statement: str) -> str:
    """
    Extract action (CREATE, ALTER, DROP) and table name from the SQL statement.
    """
    match = re.findall(r"(CREATE|ALTER|DROP)\s+TABLE\s+['\"]?(\w+)['\"]?", sql_statement.lower(), re.IGNORECASE)

    if not match:
        # raise ValueError("Invalid SQL statement. Unable to extract action and table name.")
        return "unknown_migration"

    action, table_name = match[0]

    # Generate a function name with the specified format
    return f"{action}_{table_name}"


def _setup_generic_edwh_migrate(file: Path, is_typedal: bool) -> None:
    contents = (
        "from edwh_migrate import migration\n"
        + ("from typedal import TypeDAL" if is_typedal else "from pydal import DAL")
        + "\n"
    )

    with file.open("w") as f:
        f.write(textwrap.dedent(contents))

    rich.print(f"[green] New migrate file {file} created [/green]")


START_RE = re.compile(r"-- start\s+\w+\s--\n")


def _build_edwh_migration(contents: str, cls: str, date: str, existing: Optional[str] = None) -> str:
    sql_func_name = sql_to_function_name(contents)
    func_name = "_placeholder_"
    contents = START_RE.sub("", contents)

    for n in range(1, 1000):
        func_name = f"{sql_func_name}_{date}_{str(n).zfill(3)}"

        if existing and f"def {func_name}" in existing:
            if contents.replace(" ", "").replace("\n", "") in existing.replace(" ", "").replace("\n", ""):
                rich.print(f"[yellow] migration {func_name} already exists, skipping! [/yellow]")
                return ""
            elif func_name.startswith("alter"):
                # bump number because alter migrations are different
                continue
            else:
                rich.print(
                    f"[red] migration {func_name} already exists [bold]with different contents[/bold], skipping! [/red]"
                )
                return ""
        else:
            # okay function name, stop incrementing
            break

    contents = textwrap.indent(contents.strip(), " " * 16)

    if not contents.strip():
        # no real migration!
        return ""

    return textwrap.dedent(
        f'''

        @migration
        def {func_name}(db: {cls}):
            db.executesql("""
{contents}
            """)
            db.commit()

            return True
        '''
    )


def _build_edwh_migrations(contents: str, is_typedal: bool, output: Optional[Path] = None) -> str:
    cls = "TypeDAL" if is_typedal else "DAL"
    date = datetime.now().strftime("%Y%m%d")  # yyyymmdd

    existing = output.read_text() if output and output.exists() else None

    return "".join(
        _build_edwh_migration(migration, cls, date, existing)
        for migration in contents.split("-- END OF MIGRATION --")
        if migration.strip()
    )


def _handle_output(
    file: io.StringIO,
    output_file: Path | str | io.StringIO | None,
    output_format: SUPPORTED_OUTPUT_FORMATS = DEFAULT_OUTPUT_FORMAT,
    is_typedal: bool = False,
) -> None:
    file.seek(0)
    contents = file.read()

    if isinstance(output_file, str):
        # `--output-file -` will print to stdout
        output_file = None if output_file == "-" else Path(output_file)

    if output_format == "edwh-migrate":
        contents = _build_edwh_migrations(contents, is_typedal, output_file if isinstance(output_file, Path) else None)
    elif output_format in {"default", "sql"} or not output_format:
        contents = "\n".join(contents.split("-- END OF MIGRATION --"))
    else:
        raise ValueError(
            f"Unknown format {output_format}. " f"Please choose one of {typing.get_args(_SUPPORTED_OUTPUT_FORMATS)}"
        )

    if isinstance(output_file, Path):
        if output_format == "edwh-migrate" and (not output_file.exists() or output_file.stat().st_size == 0):
            _setup_generic_edwh_migrate(output_file, is_typedal)

        if contents.strip():
            with output_file.open("a") as f:
                f.write(contents)

            rich.print(f"[green] Written migration(s) to {output_file} [/green]")
        else:
            rich.print(f"[yellow] Nothing to write to {output_file} [/yellow]")

    elif isinstance(output_file, io.StringIO):
        output_file.write(contents)
    else:
        # no file, just print to stdout:
        print(contents.strip())


IMPORT_IN_STR = re.compile(r'File "<string>", line (\d+), in <module>')


def _handle_import_error(code: str, error: ImportError) -> str:
    # error is deeper in a package, find the related import in the code:
    tb_lines = traceback.format_exc().splitlines()

    for line in tb_lines:
        if matches := IMPORT_IN_STR.findall(line):
            # 'File "<string>", line 15, in <module>'
            line_no = int(matches[0]) - 1
            lines = code.split("\n")
            return lines[line_no]

    # I don't know how to trigger this case:
    raise ValueError("Faulty import could not be automatically deleted") from error  # pragma: no cover


MISSING_RELATIONSHIP = re.compile(r"Cannot resolve reference (\w+) in \w+ definition")


def _handle_relation_error(error: KeyError) -> tuple[str, str]:
    if not (table := MISSING_RELATIONSHIP.findall(str(error))):
        # other error, raise again
        raise error

    t = table[0]

    return (
        t,
        """
    db.define_table('%s', redefine=True)
    """
        % t,
    )


def handle_cli(
    code_before: str,
    code_after: str,
    db_type: Optional[str] = None,
    tables: Optional[list[str] | list[list[str]]] = None,
    verbose: Optional[bool] = False,
    noop: Optional[bool] = False,
    magic: Optional[bool] = False,
    function_name: Optional[str | tuple[str, ...]] = "define_tables",
    use_typedal: bool | typing.Literal["auto"] = "auto",
    output_format: SUPPORTED_OUTPUT_FORMATS = DEFAULT_OUTPUT_FORMAT,
    output_file: Optional[str | Path | io.StringIO] = None,
) -> bool:
    """
    Handle user input for generating SQL migration statements based on before and after code.

    Args:
        code_before (str): The code representing the state of the database before the change.
        code_after (str, optional): The code representing the state of the database after the change.
        db_type (str, optional): The type of the database (e.g., "postgres", "mysql", etc.). Defaults to None.
        tables (list[str] or list[list[str]], optional): The list of tables to generate SQL for. Defaults to None.
        verbose (bool, optional): If True, print the generated code. Defaults to False.
        noop (bool, optional): If True, only print the generated code but do not execute it. Defaults to False.
        magic (bool, optional): If True, automatically add missing variables for execution. Defaults to False.
        function_name (str, optional): The name of the function where the tables are defined. Defaults: "define_tables".
        use_typedal: replace pydal imports with TypeDAL?
        output_format: defaults to just SQL, edwh-migrate migration syntax also supported
        output_file: append the output to a file instead of printing it?

    # todo: prefix (e.g. public.)

    Returns:
        bool: True if SQL migration statements are generated and executed successfully, False otherwise.
    """
    # todo: better typedal checking
    if use_typedal == "auto":
        use_typedal = "typedal" in code_before.lower() or "typedal" in code_after.lower()

    if function_name:
        define_table_functions: set[str] = set(function_name) if isinstance(function_name, tuple) else {function_name}
    else:
        define_table_functions = set()

    template = TEMPLATE_TYPEDAL if use_typedal else TEMPLATE_PYDAL

    to_execute = string.Template(textwrap.dedent(template))

    code_before = ensure_no_migrate_on_real_db(code_before, fix=magic)
    code_after = ensure_no_migrate_on_real_db(code_after, fix=magic)
    extra_code = ""

    generated_code = to_execute.substitute(
        {
            "tables": flatten(tables or []),
            "db_type": db_type or "",
            "code_before": textwrap.dedent(code_before),
            "code_after": textwrap.dedent(code_after),
            "extra": extra_code,
        }
    )
    if verbose or noop:
        rich.print(generated_code, file=sys.stderr)

    if noop:
        # done
        return True

    err: typing.Optional[Exception] = None
    catch: dict[str, Any] = {}
    retry_counter = MAX_RETRIES

    magic_vars = {"_file", "DummyDAL", "_special_tables", "_uniq", "_excl"}
    special_tables: set[str] = {"typedal_cache", "typedal_cache_dependency"} if use_typedal else set()

    while retry_counter:
        retry_counter -= 1
        try:
            if verbose:
                rich.print(generated_code, file=sys.stderr)

            # 'catch' is used to add and receive globals from the exec scope.
            # another argument could be added for locals, but adding simply {} changes the behavior negatively.
            # so for now, only globals is passed.
            catch["_file"] = io.StringIO()  # <- every print should go to this file, so we can handle it afterwards
            catch["DummyDAL"] = (
                DummyTypeDAL if use_typedal else DummyDAL
            )  # <- use a fake DAL that doesn't actually run queries
            catch["_special_tables"] = special_tables  # <- e.g. typedal_cache, auth_user
            # note: when adding something to 'catch', also add it to magic_vars!!!

            catch["_uniq"] = uniq  # function to make a list unique without changing order
            catch["_excl"] = excl  # function to exclude items from a list

            exec(generated_code, catch)  # nosec: B102
            _handle_output(catch["_file"], output_file, output_format, is_typedal=use_typedal)
            return True  # success!
        except ValueError as e:
            if str(e) != "no-tables-found":  # pragma: no cover
                rich.print(f"[yellow]{e}[/yellow]", file=sys.stderr)
                return False

            if define_table_functions:
                any_found = False
                for function_name in define_table_functions:
                    define_tables = find_function_to_call(generated_code, function_name)

                    # if define_tables function is found, add call to it at end of code
                    if define_tables is not None:
                        generated_code = add_function_call(generated_code, function_name, multiple=True)
                        any_found = True

                if any_found:
                    # hurray!
                    continue

            # else: no define_tables or other method to use found.

            print(f"No tables found in the top-level or {function_name} function!", file=sys.stderr)
            if use_typedal:
                print(
                    "Please use `db.define` or `database.define`, "
                    "or if you really need to use an alias like my_db.define, "
                    "add `my_db = db` at the top of the file or pass `--db-name mydb`.",
                    file=sys.stderr,
                )
            else:
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
            missing_vars = find_missing_variables(generated_code) - magic_vars
            if not magic:
                rich.print(
                    f"Your code is missing some variables: {missing_vars}. Add these or try --magic",
                    file=sys.stderr,
                )
                return False

            # postponed: this can possibly also be achieved by updating the 'catch' dict
            #   instead of injecting in the string.
            extra_code = extra_code + "\n" + textwrap.dedent(generate_magic_code(missing_vars))

            code_before = remove_if_falsey_blocks(code_before)
            code_after = remove_if_falsey_blocks(code_after)

            generated_code = to_execute.substitute(
                {
                    "tables": flatten(tables or []),
                    "db_type": db_type or "",
                    "extra": textwrap.dedent(extra_code),
                    "code_before": textwrap.dedent(code_before),
                    "code_after": textwrap.dedent(code_after),
                }
            )
        except ImportError as e:
            # should include ModuleNotFoundError
            err = e
            # if we catch an ImportError, we try to remove the import and retry
            if not e.path:
                # code exists in code itself
                code_before = remove_import(code_before, e.name or "")
                code_after = remove_import(code_after, e.name or "")
            else:
                to_remove = _handle_import_error(generated_code, e)
                code_before = code_before.replace(to_remove, "\n")
                code_after = code_after.replace(to_remove, "\n")

            generated_code = to_execute.substitute(
                {
                    "tables": flatten(tables or []),
                    "db_type": db_type or "",
                    "extra": textwrap.dedent(extra_code),
                    "code_before": textwrap.dedent(code_before),
                    "code_after": textwrap.dedent(code_after),
                }
            )

        except KeyError as e:
            err = e
            table_name, table_definition = _handle_relation_error(e)
            special_tables.add(table_name)
            extra_code = extra_code + "\n" + textwrap.dedent(table_definition)

            generated_code = to_execute.substitute(
                {
                    "tables": flatten(tables or []),
                    "db_type": db_type or "",
                    "extra": textwrap.dedent(extra_code),
                    "code_before": textwrap.dedent(code_before),
                    "code_after": textwrap.dedent(code_after),
                }
            )
        except Exception as e:
            err = e
            # otherwise: give up
            retry_counter = 0
        finally:
            # reset:
            typing.TYPE_CHECKING = False

        if retry_counter < 1:  # pragma: no cover
            rich.print(f"[red]Code could not be fixed automagically![/red]. Error: {err or '?'}", file=sys.stderr)
            return False

    # idk when this would happen, but something definitely went wrong here:
    return False  # pragma: no cover


def core_create(
    filename: Optional[str] = None,
    tables: Optional[list[str]] = None,
    db_type: Optional[SUPPORTED_DATABASE_TYPES_WITH_ALIASES] = None,
    magic: bool = False,
    noop: bool = False,
    verbose: bool = False,
    function: Optional[str | tuple[str, ...]] = None,
    output_format: Optional[SUPPORTED_OUTPUT_FORMATS] = DEFAULT_OUTPUT_FORMAT,
    output_file: Optional[str | Path] = None,
) -> bool:
    """
    Generates SQL migration statements for creating one or more tables, based on the code in a given source file.

    Args:
        filename: The filename of the source file to parse. This code represents the final state of the database.
        tables: A list of table names to generate SQL for.
            If None, the function will attempt to process all tables found in the code.
        db_type: The type of the database. If None, the function will attempt to infer it from the code.
        magic: If True, automatically add missing variables for execution.
        noop: If True, only print the generated code but do not execute it.
        verbose: If True, print the generated code and additional debug information.
        function: The name of the function where the tables are defined.
            If None, the function will use 'define_tables'.
        output_format: defaults to just SQL, edwh-migrate migration syntax also supported
        output_file: append the output to a file instead of printing it?

    Returns:
        bool: True if SQL migration statements are generated and (if not in noop mode) executed successfully,
            False otherwise.

    Raises:
        ValueError: If the source file cannot be found or if no tables could be found in the code.
    """
    git_root = find_git_root() or Path(os.getcwd())

    functions: set[str] = set()
    if function:  # pragma: no cover
        if isinstance(function, tuple):
            functions.update(function)
        else:
            functions.add(function)

    if filename and ":" in filename:
        # e.g. models.py:define_tables
        filename, _function = filename.split(":", 1)
        functions.add(_function)

    file_version, file_path = extract_file_version_and_path(
        filename, default_version="current" if filename else "stdin"
    )
    file_exists, file_absolute_path = get_absolute_path_info(file_path, file_version, git_root)

    if not file_exists:
        raise FileNotFoundError(f"Source file {filename} could not be found.")

    text = get_file_for_version(file_absolute_path, file_version, prompt_description="table definition")

    return handle_cli(
        "",
        text,
        db_type=db_type,
        tables=tables,
        verbose=verbose,
        noop=noop,
        magic=magic,
        function_name=tuple(functions),
        output_format=output_format,
        output_file=output_file,
    )


def core_alter(
    filename_before: Optional[str] = None,
    filename_after: Optional[str] = None,
    tables: Optional[list[str]] = None,
    db_type: Optional[SUPPORTED_DATABASE_TYPES_WITH_ALIASES] = None,
    magic: bool = False,
    noop: bool = False,
    verbose: bool = False,
    function: Optional[str] = None,
    output_format: Optional[SUPPORTED_OUTPUT_FORMATS] = DEFAULT_OUTPUT_FORMAT,
    output_file: Optional[str | Path] = None,
) -> bool:
    """
    Generates SQL migration statements for altering the database, based on the code in two given source files.

    Args:
        filename_before: The filename of the source file before changes.
             This code represents the initial state of the database.
        filename_after: The filename of the source file after changes.
             This code represents the final state of the database.
        tables: A list of table names to generate SQL for.
             If None, the function will attempt to process all tables found in the code.
        db_type: The type of the database. If None, the function will attempt to infer it from the code.
        magic: If True, automatically add missing variables for execution.
        noop: If True, only print the generated code but do not execute it.
        verbose: If True, print the generated code and additional debug information.
        function: The name of the function where the tables are defined.
             If None, the function will use 'define_tables'.
        output_format: defaults to just SQL, edwh-migrate migration syntax also supported
        output_file: append the output to a file instead of printing it?

    Returns:
        bool: True if SQL migration statements are generated and (if not in noop mode) executed successfully,
             False otherwise.

    Raises:
        ValueError: If either of the source files cannot be found, if no tables could be found in the code,
             or if the codes before and after are identical.
    """
    git_root = find_git_root(filename_before) or find_git_root(filename_after)

    functions: set[str] = set()
    if function:  # pragma: no cover
        functions.add(function)

    if filename_before and ":" in filename_before:
        # e.g. models.py:define_tables
        filename_before, _function = filename_before.split(":", 1)
        functions.add(_function)

    if filename_after and ":" in filename_after:
        # e.g. models.py:define_tables
        filename_after, _function = filename_after.split(":", 1)
        functions.add(_function)

    before, after = extract_file_versions_and_paths(filename_before, filename_after)

    version_before, filename_before = before
    version_after, filename_after = after

    # either ./file exists or /file exists (seen from git root):

    before_exists, before_absolute_path = get_absolute_path_info(filename_before, version_before, git_root)
    after_exists, after_absolute_path = get_absolute_path_info(filename_after, version_after, git_root)

    if not (before_exists and after_exists):
        message = ""
        message += "" if before_exists else f"Path {filename_before} does not exist! "
        if filename_before != filename_after:
            message += "" if after_exists else f"Path {filename_after} does not exist!"
        raise FileNotFoundError(message)

    try:
        code_before = get_file_for_version(
            before_absolute_path,
            version_before,
            prompt_description="current table definition",
            with_git=git_root is not None,
        )
        code_after = get_file_for_version(
            after_absolute_path,
            version_after,
            prompt_description="desired table definition",
            with_git=git_root is not None,
        )

        if not (code_before and code_after):
            message = ""
            message += "" if code_before else "Before code is empty (Maybe try `pydal2sql create`)! "
            message += "" if code_after else "After code is empty! "
            raise ValueError(message)

        if code_before == code_after:
            raise ValueError("Both contain the same code - nothing to alter!")

    except ValueError as e:
        rich.print(f"[yellow] {e} [/yellow]", file=sys.stderr)
        return False

    return handle_cli(
        code_before,
        code_after,
        db_type=db_type,
        tables=tables,
        verbose=verbose,
        noop=noop,
        magic=magic,
        function_name=tuple(functions),
        output_format=output_format,
        output_file=output_file,
    )
