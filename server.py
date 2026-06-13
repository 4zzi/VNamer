from flask import Flask, request, jsonify
import requests
import time
import re

app = Flask(__name__)

LUA_KEYWORDS = {
    'local','function','end','if','then','else','elseif',
    'return','for','while','do','repeat','until','not','and',
    'or','in','true','false','nil','break','continue',
    'self','super','pcall','xpcall','error','assert',
    'pairs','ipairs','next','select','type','typeof',
    'tostring','tonumber','print','warn','rawget','rawset',
    'setmetatable','getmetatable','require','loadstring',
    'task','game','workspace','script','math','string',
    'table','os','bit32','utf8','coroutine','debug',
    'unpack','pcall','tonumber','tostring','rawequal',
}

# Well-known Roblox globals that should never be renamed
ROBLOX_GLOBALS = {
    'Players', 'RunService', 'TweenService', 'UserInputService',
    'TextService', 'StarterGui', 'CoreGui', 'HttpService',
    'LocalPlayer', 'Character', 'Humanoid', 'HumanoidRootPart',
    'ReplicatedStorage', 'ServerStorage', 'ServerScriptService',
    'Workspace', 'Lighting', 'SoundService', 'MarketplaceService',
    'game', 'workspace', 'script',
}

# Standard Lua/Roblox library method names
LUA_STDLIB_METHODS = {
    'match','find','gsub','sub','format','len','rep','reverse','lower','upper','byte','char','dump',
    'insert','remove','concat','sort','unpack','move','create','resume','yield','wrap','status',
    'floor','ceil','abs','max','min','sqrt','sin','cos','tan','exp','log','random','huge','pi',
    'clock','time','date','difftime',
    'GetService','FindFirstChild','FindFirstChildOfClass','WaitForChild','IsA','IsDescendantOf',
    'GetChildren','GetDescendants','Clone','Destroy','Connect','Disconnect','Fire','Invoke',
    'FireServer','InvokeServer','FireClient','InvokeClient','FireAllClients',
    'new','fromRGB','fromHSV','fromHex',
    'wait','spawn','defer','delay',
}

# Garbage identifier pattern: 1-2 uppercase letters followed by digits (A1, B2, I9, J10)
GARBAGE_ID_RE = re.compile(r'^[A-Z]{1,2}[0-9]+$')

PROMPT_TEMPLATE = """<s>[INST] You are a Luau code formatter. Your ONLY job is to rename user-defined identifiers to meaningful PascalCase names. Output ONLY raw Lua code, nothing else.

========================================
  LUAU ORIENTATION — READ THIS FIRST
========================================
LuaU is Roblox's typed dialect of Lua. Native Roblox/LuaU coders follow these conventions:

ROBLOX OBJECT NAMES — always use the exact Roblox term, nothing more:
  The player's avatar is called "Character", never "CharacterModel" or "PlayerModel"
  The physics body is "HumanoidRootPart", never "RootComponent" or "PhysicsRoot"
  The stat object is "Humanoid", never "HumanoidComponent" or "HumanoidObject"
  A part is a "Part", never a "PartObject" or "PartEntity"

INTERMEDIATE VARIABLES — name by their mathematical or logical role, not generic nouns:
  local tmp = a * b   (area calculation)  ->  local Area = Width * Height   (NOT "Product")
  local tmp = x + y   (sum)               ->  local Sum = Left + Right      (NOT "Result")
  "Product", "Component", "Model", "Manager", "Entity" — these are NOT LuaU vocabulary.

LOOP COUNTERS — name by what they count:
  local i = 0  (ticks up to 10)           ->  local TickCount = 0  (NOT "Tick" alone)
  Prefer the fuller "TickCount" over bare "Tick" when the variable increments numerically.

========================================
  ABSOLUTE OUTPUT RULES
========================================
- Raw Lua code ONLY. No markdown fences. No comments. No explanations. No preamble. No trailing text.
- Preserve ALL logic exactly as-is. Do not add, remove, reorder, or restructure any lines.
- Lua keywords stay exactly lowercase: local end if then else elseif return function for while do repeat until not and or in true false nil break

========================================
  WHAT YOU ARE NOT ALLOWED TO CHANGE
========================================
You ONLY rename identifiers. Everything else is completely FROZEN.

STRING LITERALS — never touch anything inside quotes:
  "%s+"  →  still "%s+"      NEVER "%Str+" or any variation
  "^TopbarPlus (.*)$"  →  unchanged
  "Product.4.0"  →  unchanged
  Any string pattern, URL, asset ID, format string — completely frozen.

STANDARD LIBRARY NAMES — these are NOT user-defined, do NOT rename them:
  string.match, string.find, string.gsub, string.sub, string.format,
  string.lower, string.upper, string.byte, string.len, string.rep,
  table.insert, table.remove, table.concat, table.sort, table.unpack,
  math.floor, math.ceil, math.abs, math.max, math.min, math.sqrt,
  math.random, math.huge, math.pi, math.sin, math.cos, math.tan,
  os.clock, os.time, os.date,
  pcall, xpcall, error, assert, pairs, ipairs, next, select,
  type, typeof, tostring, tonumber, rawget, rawset, rawequal,
  setmetatable, getmetatable, require, loadstring,
  task.wait, task.spawn, task.defer, task.delay,
  coroutine.create, coroutine.resume, coroutine.yield, coroutine.wrap

ROBLOX API METHODS — do NOT rename these:
  :GetService(), :FindFirstChild(), :WaitForChild(), :IsA(), :Clone(),
  :Destroy(), :Connect(), :Disconnect(), :Fire(), :Invoke(),
  :FireServer(), :InvokeServer(), :FireClient(), :FireAllClients(),
  :GetChildren(), :GetDescendants(), :GetProductInfo(), :GetAttribute()

CONTROL FLOW — preserve every loop, branch, and block exactly:
  while loops, for loops, repeat/until, if/elseif/else chains — line for line

LINE COUNT — the output must have EXACTLY the same number of lines as the input.
  If you collapse a loop or inline a condition, you have failed.

IF YOU RESTRUCTURE A LOOP, CHANGE A STRING PATTERN, OR RENAME A STDLIB FUNCTION — YOU HAVE FAILED.

========================================
  CORE PRINCIPLE — READ BEFORE NAMING
========================================
Before naming ANY identifier, ask: "What does this variable DO or REPRESENT in this specific code?"

Read how it is USED:
  - What is it assigned from?
  - What operations involve it?
  - What does it control, accumulate, or gate?
  - What does the function body do with its parameters?

NEVER assign a generic fallback name when usage gives ANY hint of purpose.
A name like "Flag", "Counter", "ValA", "I9", "Tmp" means you did NOT read the code.

============================
  ROLE-SPECIFIC CONVENTIONS
============================

FUNCTIONS — always Verb + Noun:
  function calc(a, b)   -- computes area         -> function CalculateArea(Width, Height)
  function send(p, msg) -- fires a remote        -> function SendNotification(Target, Message)
  function get(id)      -- fetches a player      -> function GetPlayerById(PlayerId)
  Single-verb names like "Area", "Calc", "Get" alone are NEVER acceptable.

FUNCTION PARAMETERS — derive from how they are USED in the body:
  function calc(a, b)  where body does: return a * b / 2  ->  CalculateArea(Width, Height)
  "ValA", "ValB", "ParamA", "Arg1" are NEVER acceptable.

BOOLEANS — always prefix with Is, Has, Can, Was, Should:
  local done = false   (loop exits when true)   -> local IsDone = false
  "Flag" is NEVER acceptable for a boolean.

LOOP COUNTERS — name by what they count:
  local i = 0  (ticks up, limit 10)             -> local TickCount = 0
  local n = 0  (counts players joined)          -> local JoinedCount = 0
  "Counter" alone is NEVER acceptable.

INTERMEDIATE VARIABLES — name by what they hold:
  local tmp = a * b     (area intermediate)     -> local Area = Width * Height
  local res = tmp / 2   (final result)          -> local HalfArea = Area / 2
  NEVER: I9, J10, A1, B2, Tmp1, Res2, Product, Component

SERVICES — exact Roblox service name:
  local ps = game:GetService("Players")         -> local Players = game:GetService("Players")

CONNECTIONS:
  local c = part.Touched:Connect(fn)            -> local TouchLink = part.Touched:Connect(fn)

============================
  BANNED — NEVER PRODUCE
============================
  Letter+digit names ........... A1, B2, C3, I9, J10  (NEVER)
  Generic booleans ............. Flag  (use IsX / HasX)
  Naked counters ............... Counter  (add context)
  Meaningless params ........... ValA, ValB, ParamA, ParamB, Arg1
  Redundant suffixes ........... PlayersService, RunServiceInstance
  Single-verb functions ........ Area, Calc, Send, Get, Run
  Modified stdlib .............. String.Match, Table.Insert, Math.Floor  (KEEP lowercase)
  Modified string patterns ..... "%Str+", "%D+" when original was "%s+", "%d+"
  Non LuaU names or slangs ..... Product, Component, Model, Manager, Controller, Handler, Wrapper, Entity, Node, System, Module (NEVER use these as suffixes or standalone names)

====================
  GOOD EXAMPLES
====================
  local v = game:GetService("Players")              -> local Players = game:GetService("Players")
  local flag = false  -- exits loop at limit        -> local IsDone = false
  local i = 0  -- increments to 10 then stops      -> local TickCount = 0
  function calc(a, b)  -- returns a*b/2
    local tmp = a * b                               ->   local Area = Width * Height
    local res = tmp / 2                             ->   local HalfArea = Area / 2
    return res                                      ->   return HalfArea
  local v4 = string.match(v1.Name, "^Top (.*)$")   -> local NameMatch = string.match(RawName, "^Top (.*)$")
  local v5 = v4 and v4:gsub("%s+", "")             -> local CleanName = NameMatch and NameMatch:gsub("%s+", "")

====================
  LAST-RESORT NAMES
====================
Only if usage gives zero semantic hint: Idx, Key, Src, Dst, Acc, Buf
NEVER: A1, B2, Tmp1, ValA, Param1

Code to rename:
__SCRIPT__ [/INST]"""

# Single-letter fallback map
SINGLE_LETTER_MAP = {
    'a': 'Src',    'b': 'Dst',    'c': 'Cap',    'd': 'Delta',
    'e': 'Elem',   'f': 'Fn',     'g': 'Group',  'h': 'Height',
    'i': 'Idx',    'j': 'Jdx',    'k': 'Key',    'l': 'Len',
    'm': 'Mid',    'n': 'Num',    'o': 'Out',    'p': 'Pos',
    'q': 'Query',  'r': 'Result', 's': 'Str',    't': 'Tbl',
    'u': 'Unit',   'v': 'Val',    'w': 'Width',  'x': 'PosX',
    'y': 'PosY',   'z': 'PosZ',
}

# Fallback pool for garbage identifiers (A1, I9, etc.)
GARBAGE_FALLBACKS = [
    'Result', 'Accum', 'Buf', 'Src', 'Dst',
    'Idx', 'Key', 'Val', 'Num', 'Out',
]

BANNED_SUFFIXES = [
    'Service', 'Instance', 'Object', 'Obj', 'Ref', 'Var',
    'Number', 'String', 'Table', 'Bool', 'Value', 'Param',
    'Callback', 'Function', 'Handler',
    # Non-LuaU slang — Qwen pulls these from Unity/React/generic OOP
    'Model', 'Component', 'Entity', 'Controller', 'Manager',
    'Wrapper', 'Module', 'System', 'Node',
]

MAX_RETRIES = 3
CHUNK_SIZE  = 80  

def sanitize_garbage_ids(code: str) -> str:
    seen: dict[str, str] = {}
    counter = [0]

    def fix(m: re.Match) -> str:
        word = m.group(0)
        if word in ROBLOX_GLOBALS:
            return word
        if not GARBAGE_ID_RE.match(word):
            return word
        if word not in seen:
            seen[word] = GARBAGE_FALLBACKS[counter[0] % len(GARBAGE_FALLBACKS)]
            counter[0] += 1
        return seen[word]

    return re.sub(r'\b[A-Z][a-zA-Z0-9_]*\b', fix, code)


def strip_verbose_suffixes(code: str) -> str:
    def fix(m: re.Match) -> str:
        word = m.group(0)
        if word in ROBLOX_GLOBALS:
            return word
        if word.lower() in LUA_KEYWORDS:
            return word.lower()
        for suffix in BANNED_SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                stripped = word[:-len(suffix)]
                if stripped and stripped[0].isupper():
                    return stripped
        return word
    return re.sub(r'\b[A-Z][a-zA-Z0-9_]*\b', fix, code)


# Standalone banned words that should never appear as a complete identifier
BANNED_STANDALONE = {
    'Model', 'Component', 'Entity', 'Controller', 'Manager',
    'Wrapper', 'Module', 'System', 'Node', 'Product', 'Handler',
}

def strip_standalone_banned(code: str) -> str:
    def fix(m: re.Match) -> str:
        word = m.group(0)
        if word in ROBLOX_GLOBALS:
            return word
        if word in BANNED_STANDALONE:
            return 'Target'
        return word
    return re.sub(r'\b[A-Z][a-zA-Z0-9_]*\b', fix, code)


def enforce_pascal_case(code: str) -> str:
    def fix(m: re.Match) -> str:
        word = m.group(0)
        if word in ROBLOX_GLOBALS:
            return word
        if word.lower() in LUA_KEYWORDS:
            return word.lower()
        if word in LUA_STDLIB_METHODS:
            return word                      # leave stdlib names exactly as-is
        if word in SINGLE_LETTER_MAP:
            return SINGLE_LETTER_MAP[word]
        if len(word) == 1 and word.isalpha():
            return SINGLE_LETTER_MAP.get(word, word.upper())
        if word[0].islower():
            return word[0].upper() + word[1:]
        return word
    return re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', fix, code)


def strip_comments(code: str) -> str:
    result = []
    i = 0
    n = len(code)
    in_string = False
    string_char = ''

    while i < n:
        ch = code[i]

        if not in_string and ch == '"':
            in_string = True
            string_char = '"'
            result.append(ch)
            i += 1
            continue
        if not in_string and ch == "'":
            in_string = True
            string_char = "'"
            result.append(ch)
            i += 1
            continue
        if in_string:
            if ch == '\\' and i + 1 < n:          # escape sequence
                result.append(ch)
                result.append(code[i + 1])
                i += 2
                continue
            if ch == string_char:
                in_string = False
            result.append(ch)
            i += 1
            continue

        if code[i:i+2] == '--' and i + 2 < n and code[i+2] == '[':
            # Count '=' signs
            j = i + 2
            eq = 0
            while j < n and code[j] == '=':
                eq += 1
                j += 1
            if j < n and code[j] == '[':
                # Valid long comment — find closing ]=*]
                close = ']' + '=' * eq + ']'
                end = code.find(close, j + 1)
                if end != -1:
                    i = end + len(close)
                    # Remove trailing whitespace left on this line if comment was inline
                    # (don't add anything — just skip the comment)
                    continue
            # Fall through to single-line comment handler below

        if code[i:i+2] == '--':
            # Skip to end of line but keep the newline itself
            while i < n and code[i] != '\n':
                i += 1
            continue

        result.append(ch)
        i += 1

    return ''.join(result)


def normalize_blank_lines(code: str) -> str:
    lines = code.split('\n')
    out = []
    blank_run = 0

    for idx, line in enumerate(lines):
        stripped = line.strip()
        is_blank = stripped == ''

        if is_blank:
            blank_run += 1
            # Allow at most one consecutive blank line
            if blank_run <= 1:
                out.append(line)
        else:
            blank_run = 0
            out.append(line)

    result = []
    for idx, line in enumerate(out):
        if line.strip() == '':
            lookahead = idx + 1
            while lookahead < len(out) and out[lookahead].strip() == '':
                lookahead += 1
            if lookahead < len(out):
                nxt = out[lookahead].strip().split()[0] if out[lookahead].strip() else ''
                if nxt in ('end', 'until'):
                    continue
        result.append(line)

    return '\n'.join(result)


def restore_string_literals(original: str, output: str) -> str:
    orig_strings = re.findall(r'"(?:[^"\\]|\\.)*"', original)
    out_strings  = re.findall(r'"(?:[^"\\]|\\.)*"', output)
    if orig_strings == out_strings:
        return output          # nothing changed, skip

    # Replace each output string with the corresponding original string
    result = output
    iter_orig = iter(orig_strings)
    def replacer(m: re.Match) -> str:
        try:
            return next(iter_orig)
        except StopIteration:
            return m.group(0)
    return re.sub(r'"(?:[^"\\]|\\.)*"', replacer, result)


def clean_output(code: str) -> str:
    code = re.sub(r'^```[\w]*\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'\n?```$',      '', code, flags=re.MULTILINE)
    code = re.sub(r'^```',         '', code, flags=re.MULTILINE)

    skip_prefixes = (
        'here', 'note', 'this', 'i ', 'the ', 'output',
        'refactored', 'renamed', 'changed', 'below', 'result',
        'sure', 'okay', 'of course', 'certainly', 'as requested',
        'in the ', 'please ', 'above',
    )
    cleaned = []
    for line in code.split('\n'):
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue
        if any(stripped.lower().startswith(p) for p in skip_prefixes):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip()

def has_lowercase_identifiers(code: str) -> bool:
    for m in re.finditer(r'\b[a-z][a-zA-Z0-9_]{2,}\b', code):
        word = m.group(0)
        if word.lower() not in LUA_KEYWORDS and word not in ROBLOX_GLOBALS and word not in LUA_STDLIB_METHODS:
            return True
    return False


def has_garbage_identifiers(code: str) -> bool:
    for m in re.finditer(r'\b[A-Z][a-zA-Z0-9_]*\b', code):
        word = m.group(0)
        if word not in ROBLOX_GLOBALS and GARBAGE_ID_RE.match(word):
            return True
    return False


def verify_structure(original: str, output: str) -> list[str]:
    issues = []

    orig_stripped = strip_comments(original)
    out_stripped  = strip_comments(output)

    orig_lines = [l for l in orig_stripped.splitlines() if l.strip()]
    out_lines  = [l for l in out_stripped.splitlines()  if l.strip()]
    if len(out_lines) != len(orig_lines):
        issues.append(
            f"line count mismatch (input={len(orig_lines)}, output={len(out_lines)})"
        )

    orig_strings = re.findall(r'"(?:[^"\\]|\\.)*"', original)
    out_strings  = re.findall(r'"(?:[^"\\]|\\.)*"', output)
    if sorted(orig_strings) != sorted(out_strings):
        issues.append("string literals were modified")

    return issues


def output_is_clean(original: str, code: str) -> bool:
    return (
        not has_lowercase_identifiers(code)
        and not has_garbage_identifiers(code)
        and not verify_structure(original, code)
    )


def build_prompt(script: str) -> str:
    return PROMPT_TEMPLATE.replace('__SCRIPT__', script)

def rename_chunk(chunk: str, temperature: float = 0.01) -> str | None:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5-coder:7b",
                "prompt": build_prompt(chunk),
                "stream": False,
                "temperature": temperature,
                "options": {
                    "num_predict": 16384,
                    "top_p": 0.5,
                    "repeat_penalty": 1.3,
                },
            },
            timeout=300,
        )
        raw = response.json().get("response", "").strip()
        return clean_output(raw)
    except Exception as e:
        print(f"  chunk error: {e}")
        return None


def split_into_chunks(script: str, chunk_size: int) -> list[str]:
    lines = script.split('\n')
    chunks, current = [], []
    for line in lines:
        current.append(line)
        if len(current) >= chunk_size and line.strip() in ('end', 'end,', 'end;', ''):
            chunks.append('\n'.join(current))
            current = []
    if current:
        chunks.append('\n'.join(current))
    return chunks


def post_process(code: str, original_chunk: str) -> str:
    code = enforce_pascal_case(code)
    code = strip_verbose_suffixes(code)
    code = strip_standalone_banned(code)
    code = sanitize_garbage_ids(code)
    code = restore_string_literals(original_chunk, code)
    code = strip_comments(code)
    code = normalize_blank_lines(code)
    return code

@app.route('/rewrite', methods=['POST'])
def fix_script():
    data = request.get_json(force=True)
    if not data or 'script' not in data or not data['script']:
        return jsonify({'fixed_script': '-- Error: No script received'})

    original   = data['script']
    start_time = time.time()
    line_count = original.count('\n') + 1

    if line_count <= CHUNK_SIZE:
        current = None
        for attempt in range(MAX_RETRIES):
            print(f"Single-pass attempt {attempt + 1}/{MAX_RETRIES}...")
            temperature = round(0.01 + attempt * 0.08, 2)
            raw = rename_chunk(original, temperature)
            if raw is None:
                return jsonify({'fixed_script': '-- Error: model returned nothing'})
            current = post_process(raw, original)
            if output_is_clean(original, current):
                print(f"  clean on attempt {attempt + 1}")
                break
            issues = []
            if has_lowercase_identifiers(current): issues.append("lowercase identifiers")
            if has_garbage_identifiers(current):   issues.append("garbage ids")
            issues.extend(verify_structure(original, current))
            print(f"  attempt {attempt + 1}: {', '.join(issues)} — retrying...")

        if current is None:
            return jsonify({'fixed_script': '-- Error: model returned nothing'})

        elapsed = time.time() - start_time
        print(f"Done (single-pass) in {elapsed:.2f}s")
        return jsonify({'fixed_script': f"-- Generated by VSpy\n\n{current}"})

    print(f"Script has {line_count} lines — chunking into ~{CHUNK_SIZE}-line pieces...")
    chunks   = split_into_chunks(original, CHUNK_SIZE)
    renamed  = []

    for chunk_idx, chunk in enumerate(chunks):
        print(f"  Chunk {chunk_idx + 1}/{len(chunks)} ({chunk.count(chr(10)) + 1} lines)...")
        result = None

        for attempt in range(MAX_RETRIES):
            temperature = round(0.01 + attempt * 0.08, 2)
            raw = rename_chunk(chunk, temperature)
            if raw is None:
                continue
            processed = post_process(raw, chunk)

            # Accept if structure is intact, otherwise retry
            issues = verify_structure(chunk, processed)
            if not issues:
                result = processed
                print(f"    clean on attempt {attempt + 1}")
                break
            print(f"    attempt {attempt + 1}: {', '.join(issues)} — retrying chunk...")

        if result is None:
            # Fallback: use post-processed raw output even if imperfect
            print(f"    chunk {chunk_idx + 1} could not be fully cleaned — using best effort")
            result = post_process(raw or chunk, chunk)

        renamed.append(result)

    current = '\n'.join(renamed)
    elapsed = time.time() - start_time
    print(f"Done (chunked, {len(chunks)} chunks) in {elapsed:.2f}s")
    return jsonify({'fixed_script': f"-- Generated by VSpy\n\n{current}"})


if __name__ == '__main__':
    print("Starting VNamer")
    print("Listening on http://127.0.0.1:5000")
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=5000)
    except ImportError:
        app.run(host='127.0.0.1', port=5000)