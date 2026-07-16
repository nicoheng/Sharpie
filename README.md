# sharpie

A source-to-source transpiler that converts a subset of POSIX shell script into equivalent, executable Python. Given a `.sh` file, `sharpie` parses it line-by-line (with recursive handling for nested blocks) and prints the translated Python program to stdout.

## Supported shell constructs

- Variable assignment and expansion (`x=1`, `$x`)
- `echo` (including `echo -n`)
- Command substitution via backticks (`` `cmd` ``) → `subprocess.run(...)`
- `cd`, `read`, `exit`
- Glob patterns
- Control flow: `for`, `if`, `while` — including arbitrary nesting, with indentation tracked per level
- External command execution
- Inline comments (`# ...`), preserved in the generated output
- Cyclic/keyed logic for maintaining nested-block state via counters (no external parser dependency)

## How it works

`sharpie` is a single-pass, regex-driven translator:

1. Reads the input shell script line by line.
2. Each line is routed to a handler (`echo`, `assign`, `do_for`, `do_if`, `do_while`, `do_test`, etc.) based on pattern matching with Python's `re` module.
3. Control-flow handlers recurse into the line list, tracking a line counter and indentation string, and return the counter position once their block closes (`done`).
4. Handlers emit valid Python source directly to stdout, which can be piped to a file and executed with `python3`.

## Usage

```sh
python3 sharpie.py script.sh > script.py
python3 script.py
```

## Stack

Python, Regular Expressions (`re`), recursive-descent-style parsing.
