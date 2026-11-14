from dualview.deadcode import dead_code_counts, find_dead_code
from dualview.formatters import render_code

CLEAN = '''import sys
def solve(n):
    total = 0
    for _ in range(n):
        total += 1
    return total
a, b = map(int, sys.stdin.readline().split())
while True:
    print(solve(a))
    break
'''

DEAD = '''import os
import sys
def helper(x):
    return x + 1
def solve(n):
    return n
    print("nunca")
unused = 42
if False:
    print("nunca")
print(solve(int(sys.stdin.readline())))
'''


def test_clean_code_has_no_dead_code():
    assert find_dead_code(CLEAN) == []


def test_each_kind_is_found():
    c = dead_code_counts(DEAD)
    assert c == {"unused_function": 1, "unused_import": 1, "unused_variable": 1, "unreachable": 1,
                 "constant_condition": 1, "total": 5}
    names = {name for _, _, name in find_dead_code(DEAD)}
    assert {"helper", "os", "unused"} <= names


def test_invalid_python_does_not_raise():
    assert find_dead_code("print 'py2'") == [] and dead_code_counts("def (:")["total"] == 0


def test_battery_dead_code_channel_is_detected_as_dead():
    base = "n = int(input())\nprint(n * 2)\n"
    assert dead_code_counts(base)["total"] == 0
    padded = render_code(base, view="raw", injection="dead_code", is_attack=True, key="k")
    assert dead_code_counts(padded)["unused_function"] == 3
