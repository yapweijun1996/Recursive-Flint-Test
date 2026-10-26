"""Execute trusted behavioral checks against a restricted candidate in a child process."""

import ast
import builtins
import json
import pathlib
import runpy
import sys

ALLOWED_IMPORTS = {'collections': {'OrderedDict'}, 'math': {'ceil', 'floor'},
                   'typing': {'Any', 'List', 'Tuple', 'Dict', 'Optional', 'Iterable'}}


def validate(code):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in ALLOWED_IMPORTS for alias in node.names):
                raise ValueError('Import is outside the verification allowlist')
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS or any(alias.name not in ALLOWED_IMPORTS[node.module] for alias in node.names):
                raise ValueError('Import is outside the verification allowlist')
        if isinstance(node, ast.Name) and node.id.startswith('__'):
            raise ValueError('Dunder variable access is not allowed')
        if isinstance(node, ast.Attribute) and node.attr.startswith('__'):
            raise ValueError('Dunder attribute access is not allowed')
    return tree


def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in ALLOWED_IMPORTS:
        raise ImportError('Import is outside the verification allowlist')
    return builtins.__import__(name, globals, locals, fromlist, level)


def run(task, path):
    code = pathlib.Path(path).read_text(encoding='utf-8')
    tree = validate(code)
    names = ['abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter', 'float',
             'frozenset', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
             'map', 'max', 'min', 'next', 'object', 'property', 'range', 'reversed',
             'round', 'set', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'tuple',
             'type', 'zip', 'Exception', 'ValueError', 'TypeError', 'KeyError',
             'IndexError', 'RuntimeError', 'AssertionError', 'StopIteration', '__build_class__']
    safe_builtins = {name: getattr(builtins, name) for name in names}
    safe_builtins['__import__'] = restricted_import
    namespace = {'__builtins__': safe_builtins, '__name__': 'candidate'}
    exec(compile(tree, str(path), 'exec'), namespace)
    suite = runpy.run_path(str(pathlib.Path(__file__).with_name('suite.py')))
    return suite['check_candidate'](task, namespace)


if __name__ == '__main__':
    try:
        print(json.dumps(run(sys.argv[1], sys.argv[2])))
    except Exception as error:
        print(json.dumps({'passed': False, 'error': type(error).__name__ + ': ' + str(error)[:300]}))
