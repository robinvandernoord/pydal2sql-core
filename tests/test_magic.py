import textwrap

from src.pydal2sql_core.magic import (
    find_missing_variables,
    generate_magic_code,
    remove_specific_variables,
)


def test_find_missing():
    # Example usage:
    code_string = """
       from math import floor # ast.ImportFrom
       import datetime # ast.Import
       from pydal import * # ast.ImportFrom with *
       a = 1
       b = 2
       print(a, b + c)
       d = e + b
       f = d
       del f  # ast.Del
       print(f)
       xyz
       floor(d)
       ceil(d)
       ceil(e)

       datetime.utcnow()

       db = DAL()

       db.define_table('...')

       for table in []:
           print(table)

       if toble := True:
           print(toble)
       """

    missing_variables = find_missing_variables(code_string)
    assert missing_variables == {"c", "xyz", "ceil", "e", "f"}, missing_variables


def test_fix_missing():
    code = generate_magic_code({"bla"})

    assert "empty = Empty()" in code
    assert "bla = empty" in code


def test_remove_specific_variables():
    code = textwrap.dedent(
        """
    db = 1
    def database():
        return True
    
    my_database = 'exists'
    print('hi')
    """
    )
    new_code = remove_specific_variables(code)
    assert "print('hi')" in new_code
    assert "db" not in new_code
    assert "def database" not in new_code
    assert "my_database" in new_code
