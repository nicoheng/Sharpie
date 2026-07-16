#!/usr/bin/env python3

import sys
import re
import os

# function to check condition 
def check_condition(line):
    # strip the newline
    line = line.strip()
    
    # obtain the line and comment
    line, comment = split_comment(line)
    
    if not line:
        return None, comment
    if line.startswith("echo "):
        output = echo(line)    
    elif re.match(r'[a-zA-Z_][a-zA-Z0-9_]*=', line):
        output = assign(line)
    elif line.startswith("exit "):
        output = do_exit(line)
    elif line.startswith("cd "):
        output = do_cd(line)
    elif line.startswith("read "):
        output = do_read(line)
    else:
        output = external_command(line)
        
    return output, comment
    
# function to handle echo in shell
def echo(line):
    # grab the content of echo ...
    parts = line.split(maxsplit=1)
    
    # if it is an empty line
    if len(parts) == 1:
        return 'print()'
    
    # parts to handle echo -n where it does not care with any newline
    newline = True
    content = parts[1]
    if content.startswith("-n "):
        newline = False
        content = content[3:].strip()
     
    # to check if it contains backtick    
    content = do_backtick(content)
    
    # if it contains only single quote
    if content.startswith("'") and content.endswith("'"):
        content = content[1:-1]
        if newline:
            return f'print({repr(content)})'
        else:
            return f'print({repr(content)}, end="")'
    
    # if it contains double quotes
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]

        # expand variables
        content = variable(content)
        if newline:
            return f'print(f"{content}")'
        else:
            return f'print(f"{content}", end="")'
        
    # remove all excessive white spaces
    content = re.sub(r' +', ' ', content)
    
    # globs only if no backticks
    if globs(content) and 'subprocess.run' not in content:
        if newline:
            return f'print(" ".join(sorted(glob.glob("{content}"))), end="")'
        else:
            return f'print(" ".join(sorted(glob.glob("{content}"))), end="")'
    
    # else without globs
    content = variable(content)
    if '{' in content:
        # print with variables
        if newline:
            return f'print(f"{content}")'
        else:
            return f'print(f"{content}", end="")'
            
    else:        
        # basic print
        if newline:
            return f'print({repr(content)})'
        else:
            return f'print({repr(content)}, end="")'          
    
# function to handle all '=' logics
def assign(line):
    var, value = line.split('=', 1)
    var = var.strip()
    value = value.strip()
    value = do_backtick(value)
    
    # if it is with single quote
    if value.startswith("'") and value.endswith("'"):
        content = value[1:-1]
        return f'{var} = {repr(content)}'
    
    # if it is double quotes
    if value.startswith('"') and value.endswith('"'):
        content = value[1:-1]
        content = variable(content)
        return f'{var} = f"{content}"'
    
    # glob only if no backticks
    if globs(value) and "subprocess.run" not in value:
        return f'{var} = " ".join(sorted(glob.glob("{value}")))'
    
    value = variable(value)
    
    if '{' in value:
        # assign with variables
        return f'{var} = f"{value}"'
    else:
        # basic assign
        return f'{var} = {repr(value)}'

# function to handle all the variables output   
def variable(line):
    # interpret the $# command in shell
    line = line.replace("$#", "{len(sys.argv) - 1}")
    
    # interpret the $# command in shell
    line = line.replace("$@", "{' '.join(sys.argv[1:])}")
    
    # return all the captured variable in '${..}'
    line = re.sub(r'\${([a-zA-Z_][a-zA-Z0-9_]*)}', r'{\1}', line)
    
    # capture the $1, $2, etc variables
    line = re.sub(r'\$([0-9])', r'{sys.argv[\1]}', line)
    
    # return all the captured variable after '$'
    line = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', r'{\1}', line)
    
    return line

# function to split comment
def split_comment(line):
    if '#' in line:
        parts = line.split('#', 1)
        
        # code contains all that comes before #
        code = parts[0].rstrip()
        
        # comment contains the comment messages
        comment = '#' + parts[1]
        return code, comment
    return line, '' 

# function to check if it contains any globbing characters
def globs(line):
    return any(c in line for c in ['*', '?', '[', ']'])

# function to handle for condition
def do_for(lines, counter, indent=""):
    line = lines[counter].strip()
    
    # split var and items
    match = re.match(r'for (\w+) in (.+)', line)
    var = match.group(1)
    items = match.group(2).strip()
    
    # if it is a double quotes case
    if items.startswith('"') and items.endswith('"'):
        items = items[1:-1]
        iterable = f'[{repr(items)}]'
    # if it is a globbing then
    elif globs(items):
        iterable = f'sorted(glob.glob("{items}"))'
    else:
        # split into list otherwise
        parts = items.split()
        items_str = ", ".join(f'"{p}"' for p in parts)
        iterable = f'[{items_str}]'

    print(indent + f'for {var} in {iterable}:')

    counter += 1

    # skip do
    if lines[counter].strip() == "do":
        counter += 1
        
    # process body
    while counter < len(lines):
        line = lines[counter].strip()
        
        # skip done
        if line == "done":
            return counter + 1
        
        # does the same thing as check condition function to handle recursive case
        if line.startswith("for "):
            counter = do_for(lines, counter, indent + "    ")
        elif line.startswith("if "):
            counter = do_if(lines, counter, indent + "    ")
        elif line.startswith("while "):
            counter = do_while(lines, counter, indent + "    ")
        else:
            output, comment = check_condition(line)
            if output:
                print(indent + "    " + output + (" " + comment if comment else ""))
            elif comment:
                print(indent + "    " + comment)
            counter += 1
    
    return counter

# function to handle exit
def do_exit(line):
    code = line.split()
    if len(code) == 1:
        return "sys.exit()"
    else:
        return f'sys.exit({code[1]})'
    
# function to handle cd
def do_cd(line):
    dir = line[3:].strip()
    return f'os.chdir({repr(dir)})'
    
# function to handle read
def do_read(line):
    var = line[5:].strip()
    return f'{var} = input()'
    
# function for external command
def external_command(line):
    line = do_backtick(line)
    words = re.findall(r'"[^"]*"|\S+', line)
    
    sols = []
    for w in words:
        # Remove quotes if present
        if w.startswith('"') and w.endswith('"'):
            w = w[1:-1]
            
        w = variable(w)
        if '{' in w:
            # if it is a variable then don't include the double quotes
            sols.append(f'f"{w}"')
        else:
            # include double quotes otherwise
            sols.append(repr(w))
    return f'subprocess.run([{", ".join(sols)}])'

# function to handle test
def do_test(line):
    line = line.strip()
    
    # remove "test"
    if line.startswith("test "):
        line = line[5:].strip()
        
    # use regex to properly split or keep quoted strings together
    code = re.findall(r'"[^"]*"|\S+', line)
    
    if code[0] == "-z":
        val = code[1]
        # Remove quotes if present
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        val = variable(val)
        if '{' in val:
            return f'len(f"{val}") == 0'
        else:
            return f'len({repr(val)}) == 0'
    
    # handles for -r, -x, -w, -d and -f
    if code[0] in ["-r", "-x", "-w", "-d", "-f"]:
        val = code[1]
        # Remove quotes if present
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        val = variable(val)
        
        # if it is variable then use f-string
        if '{' in val:
            next_val = f'f"{val}"'
        else:
            next_val = repr(val)
            
        if code[0] == "-r":
            return f'os.access({next_val}, os.R_OK)'
        
        if code[0] == "-x":
            return f'os.access({next_val}, os.X_OK)'
        
        if code[0] == "-w":
            return f'os.access({next_val}, os.W_OK)'
        
        if code[0] == "-d":
            return f'os.path.isdir({next_val})'
        
        if code[0] == "-f":
            return f'os.path.isfile({next_val})'
            
    # cases for binary operators
    left = code[0]
    op = code[1]
    right = code[2]

    # Remove quotes if present
    if left.startswith('"') and left.endswith('"'):
        left = left[1:-1]
    if right.startswith('"') and right.endswith('"'):
        right = right[1:-1]
        
    left = variable(left)
    right = variable(right)
    
    ops = {
        "=": "==",
        "!=": "!=",
        "-eq": "==",
        "-ne": "!=",
        "-lt": "<",
        "-le": "<=",
        "-gt": ">",
        "-ge": ">="
    }

    if '{' in left:
        next_left = f'f"{left}"'
    else:
        next_left = repr(left)
        
    if '{' in right:
        next_right = f'f"{right}"'
    else:
        next_right = repr(right)
    
    # if the operator is binary then convert to int   
    if op in ["-lt", "-le", "-gt", "-ge"]:
        return f'int({next_left}) {ops[op]} int({next_right})'
        
    # make it as string otherwise
    if op in ops:
        return f'{next_left} {ops[op]} {next_right}'

    # if no test condition satisfy
    return "False"

# function to handle if    
def do_if(lines, counter, indent=""):
    line = lines[counter].strip()
    
    # grab the condition of the if statement
    condition = do_test(line[3:].strip())
    print(indent + f"if {condition}:")
    
    counter += 1
    
    # skip then
    if lines[counter].strip() == "then":
        counter += 1
    
    # handle the body
    while counter < len(lines):
        line = lines[counter].strip()
        
        # terminates if it reaches fi
        if line == "fi":
            return counter + 1
        
        # if it is elif condition
        if line.startswith("elif "):
            condition = do_test(line[5:].strip())
            print(indent + f"elif {condition}:")
            counter += 1
            
            # skip then
            if counter < len(lines) and lines[counter].strip() == "then":
                counter += 1
            continue
        
        # if it is else condition
        if line == "else":
            print(indent + "else:")
            counter += 1
            
            if counter < len(lines) and lines[counter].strip() == "then":
                counter += 1
            continue
        
        # handles nested conditions cases
        if line.startswith("for "):
            counter = do_for(lines, counter, indent + "    ")
        elif line.startswith("if "):
            counter = do_if(lines, counter, indent + "    ")
        elif line.startswith("while "):
            counter = do_while(lines, counter, indent + "    ")
        else:
            output, comment = check_condition(line)
            if output:
                print(indent + "    " + output + (" " + comment if comment else ""))
            elif comment:
                print(indent + "    " + comment)
            counter += 1
    
    return counter

# function to handle while condition    
def do_while(lines, counter, indent=""):
    line = lines[counter].strip()
    
    condition = do_test(line[6:].strip())
    
    print(indent + f"while {condition}:")
    
    counter += 1

    # skip do
    if lines[counter].strip() == "do":
        counter += 1

    # do the entire loop body
    while counter < len(lines):
        line = lines[counter].strip()
            
        # terminates if it reaches done
        if line == "done":
            return counter + 1
        # handles recursive cases
        elif line.startswith("for "):
            counter = do_for(lines, counter, indent + "    ")
        elif line.startswith("if "):
            counter = do_if(lines, counter, indent + "    ")
        elif line.startswith("while "):
            counter = do_while(lines, counter, indent + "    ")
        else:
            output, comment = check_condition(line)
            # print output + comment if exist
            if output:
                print(indent + "    " + output + (" " + comment if comment else ""))
            # print comment only otherwise
            elif comment:
                print(indent + "    " + comment)
            counter += 1
    return counter
    
# function to handle backticks
def do_backtick(line):
    # regex pattern to match and take the backtick content if available
    pattern = r'`([^`]*)`'
    
    # function to see if it matches the bactick
    def repl(match):
        # list of bactick words
        cmd = match.group(1).strip().split()
        
        # make a list of all the backtick words and make sure no quotes
        parts = [repr(w) for w in cmd]

        return f'{{subprocess.run([{", ".join(parts)}], capture_output=True, text=True).stdout.strip()}}'
    
    return re.sub(pattern, repl, line)

# main function of everything
print("#!/usr/bin/env python3")
print("import sys, glob, os, subprocess")
# grab the input
file = sys.argv[1]
with open(file, 'r') as f:
    lines = f.readlines()
    counter = 0
    # reads the whole lines of the shell input
    while counter < len(lines):
        line = lines[counter].strip()
        
        if line.startswith("for "):
            counter = do_for(lines, counter)
        elif line.startswith("if "):
            counter = do_if(lines, counter)
        elif line.startswith("while "):
            counter = do_while(lines, counter)
        else:
            output, comment = check_condition(line)
            # print output + comment if exist
            if output:
                print(output + (" " + comment if comment else ""))
            # print comment only otherwise
            elif comment:
                print(comment)
            counter += 1