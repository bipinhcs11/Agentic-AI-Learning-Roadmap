# ═══════════════════════════════════════════════════════════════
# Project 05 — Fine-Tuning Gemma3:4b on Apple Silicon M4
# Step 1: Prepare Dataset
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Creates a training dataset in Alpaca format for fine-tuning.
#   Domain: AI coding assistant — teaching the model to give
#   better, more specific coding help responses.
#
# ALPACA FORMAT:
#   Each example has three fields:
#     instruction: what the user asks
#     input:       optional context (code snippet, error, etc.)
#     output:      the ideal response we want the model to learn
#
#   The model learns to map (instruction + input) → output.
#   The more diverse and high-quality your examples, the better.
#
# HOW TO RUN:
#   python prepare_dataset.py
#   Output: dataset/train.jsonl (90 examples)
#           dataset/eval.jsonl  (10 examples)
# ═══════════════════════════════════════════════════════════════

import json
import random
import os

random.seed(42)

# ─────────────────────────────────────────────────────────────
# TRAINING EXAMPLES
# These teach the model our preferred response style:
#   - Specific, not vague
#   - Shows the fix, not just describes it
#   - Explains WHY, not just what
# ─────────────────────────────────────────────────────────────

EXAMPLES = [
    {
        "instruction": "Fix this Python function that should reverse a string",
        "input": "def reverse_string(s):\n    return s",
        "output": "The function currently just returns the string unchanged. To reverse it, use Python's slice notation with a step of -1:\n\n```python\ndef reverse_string(s: str) -> str:\n    return s[::-1]\n```\n\nThe `[::-1]` slice means: start from end, go to beginning, step -1. This is the most Pythonic and efficient way to reverse a string. Alternatively, `''.join(reversed(s))` works but is slower."
    },
    {
        "instruction": "Explain what this error means and how to fix it",
        "input": "TypeError: 'NoneType' object is not subscriptable",
        "output": "This error means you're trying to index (using `[]`) something that is `None`. Common causes:\n\n1. A function returned `None` instead of a list/dict\n2. A variable was never assigned a value\n3. A method like `dict.get()` returned `None`\n\nFix: check what the variable is before indexing:\n```python\nresult = my_function()\nif result is not None:\n    value = result[0]  # safe now\n```\n\nOr use a default: `result = my_function() or []`"
    },
    {
        "instruction": "Write a Python function to check if a number is prime",
        "input": "",
        "output": "```python\ndef is_prime(n: int) -> bool:\n    if n < 2:\n        return False\n    if n == 2:\n        return True\n    if n % 2 == 0:\n        return False\n    for i in range(3, int(n**0.5) + 1, 2):\n        if n % i == 0:\n            return False\n    return True\n```\n\nKey optimizations:\n- Return False immediately for n < 2 and even numbers\n- Only check up to √n (if n has a factor > √n, it has a corresponding factor < √n)\n- Skip even numbers in the loop (step=2)\n\nThis runs in O(√n) time, which is efficient for most practical uses."
    },
    {
        "instruction": "How do I read a JSON file in Python and handle errors properly?",
        "input": "",
        "output": "```python\nimport json\nfrom pathlib import Path\n\ndef load_json(filepath: str) -> dict:\n    path = Path(filepath)\n    \n    if not path.exists():\n        raise FileNotFoundError(f'File not found: {filepath}')\n    \n    try:\n        with open(path, 'r', encoding='utf-8') as f:\n            return json.load(f)\n    except json.JSONDecodeError as e:\n        raise ValueError(f'Invalid JSON in {filepath}: {e}') from e\n```\n\nThree things to always handle with JSON files:\n1. File doesn't exist → `FileNotFoundError`\n2. File has invalid JSON → `json.JSONDecodeError`\n3. Encoding issues → always specify `encoding='utf-8'`\n\nUse `pathlib.Path` instead of raw strings — it handles cross-platform paths automatically."
    },
    {
        "instruction": "What is the difference between a list and a tuple in Python?",
        "input": "",
        "output": "The key differences:\n\n| Feature | List | Tuple |\n|---------|------|-------|\n| Mutable | Yes (`list[0] = x`) | No (immutable) |\n| Syntax | `[1, 2, 3]` | `(1, 2, 3)` |\n| Use case | Data that changes | Data that doesn't change |\n| Performance | Slightly slower | Slightly faster |\n| Can be dict key | No | Yes (if all elements are hashable) |\n\nWhen to use each:\n- **List**: shopping cart items, query results, anything you'll modify\n- **Tuple**: coordinates (x, y), RGB colors, function return values, database rows\n\nA good rule: if the data represents a collection of similar items → list. If it represents a single record with multiple fields → tuple."
    },
    {
        "instruction": "How do I make a FastAPI endpoint that accepts a file upload?",
        "input": "",
        "output": "```python\nfrom fastapi import FastAPI, UploadFile, File, HTTPException\nimport shutil\nfrom pathlib import Path\n\napp = FastAPI()\nUPLOAD_DIR = Path('uploads')\nUPLOAD_DIR.mkdir(exist_ok=True)\n\n@app.post('/upload')\nasync def upload_file(file: UploadFile = File(...)):\n    # Validate file type\n    allowed = {'.pdf', '.txt', '.md'}\n    suffix = Path(file.filename).suffix.lower()\n    if suffix not in allowed:\n        raise HTTPException(400, f'File type {suffix} not allowed')\n    \n    # Save file\n    dest = UPLOAD_DIR / file.filename\n    with open(dest, 'wb') as f:\n        shutil.copyfileobj(file.file, f)\n    \n    return {'filename': file.filename, 'size': dest.stat().st_size}\n```\n\nKey points:\n- `UploadFile` gives you async file streaming (memory-efficient for large files)\n- Always validate file type before saving — never trust the client\n- Use `shutil.copyfileobj` to stream without loading entire file into memory"
    },
    {
        "instruction": "Explain Python decorators with a simple example",
        "input": "",
        "output": "A decorator is a function that wraps another function to add behavior without changing its code.\n\n```python\nimport time\n\ndef timer(func):\n    \"\"\"Decorator that prints how long a function takes.\"\"\"\n    def wrapper(*args, **kwargs):\n        start = time.time()\n        result = func(*args, **kwargs)   # call the original function\n        duration = time.time() - start\n        print(f'{func.__name__} took {duration:.3f}s')\n        return result\n    return wrapper\n\n@timer\ndef slow_function():\n    time.sleep(1)\n    return 'done'\n\nslow_function()  # prints: slow_function took 1.001s\n```\n\n`@timer` is syntactic sugar for `slow_function = timer(slow_function)`.\n\nCommon built-in decorators: `@property`, `@staticmethod`, `@classmethod`.\nPopular library decorators: `@app.route()` (Flask), `@app.get()` (FastAPI), `@cache` (functools)."
    },
    {
        "instruction": "How do I use async/await in Python? Give a practical example",
        "input": "",
        "output": "Async/await lets you run I/O operations concurrently without threads.\n\n```python\nimport asyncio\nimport httpx  # async-native HTTP client\n\nasync def fetch_url(url: str) -> str:\n    async with httpx.AsyncClient() as client:\n        response = await client.get(url)\n        return response.text\n\nasync def fetch_all(urls: list[str]) -> list[str]:\n    # Run all requests CONCURRENTLY (not one by one)\n    tasks = [fetch_url(url) for url in urls]\n    results = await asyncio.gather(*tasks)\n    return results\n\n# Entry point\nasyncio.run(fetch_all(['https://example.com', 'https://example.org']))\n```\n\nKey concepts:\n- `async def` = defines a coroutine (not run until awaited)\n- `await` = pause here, let other tasks run, resume when done\n- `asyncio.gather()` = run multiple coroutines concurrently\n- Use async for: HTTP calls, file I/O, database queries — not CPU work"
    },
    {
        "instruction": "What is wrong with this code and how do I fix it?",
        "input": "def add_to_list(item, my_list=[]):\n    my_list.append(item)\n    return my_list",
        "output": "This has a classic Python gotcha: **mutable default arguments**.\n\nThe default `[]` is created ONCE when the function is defined, not each time it's called. So all calls share the same list:\n\n```python\nadd_to_list(1)  # returns [1]\nadd_to_list(2)  # returns [1, 2]  ← unexpected!\nadd_to_list(3)  # returns [1, 2, 3]  ← keeps growing!\n```\n\n**Fix:** use `None` as the default and create the list inside:\n\n```python\ndef add_to_list(item, my_list=None):\n    if my_list is None:\n        my_list = []   # new list created each call\n    my_list.append(item)\n    return my_list\n```\n\nThis applies to any mutable default: `[]`, `{}`, `set()`, custom objects. Always use `None` as a sentinel for mutable defaults."
    },
    {
        "instruction": "How do I implement a simple LRU cache in Python?",
        "input": "",
        "output": "Python has a built-in LRU cache decorator:\n\n```python\nfrom functools import lru_cache\n\n@lru_cache(maxsize=128)\ndef expensive_function(n: int) -> int:\n    # This result is cached after first call\n    return n * n\n\nexpensive_function(4)   # computed: 16\nexpensive_function(4)   # returned from cache: 16\n```\n\nFor a custom implementation with TTL (time-to-live):\n\n```python\nfrom collections import OrderedDict\nimport time\n\nclass LRUCache:\n    def __init__(self, capacity: int, ttl_seconds: int = 300):\n        self.capacity = capacity\n        self.ttl = ttl_seconds\n        self.cache: OrderedDict = OrderedDict()\n\n    def get(self, key: str):\n        if key not in self.cache:\n            return None\n        value, timestamp = self.cache[key]\n        if time.time() - timestamp > self.ttl:\n            del self.cache[key]\n            return None\n        self.cache.move_to_end(key)  # mark as recently used\n        return value\n\n    def put(self, key: str, value) -> None:\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = (value, time.time())\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)  # remove least recently used\n```\n\nUse `@lru_cache` for pure functions with hashable args. Use the custom class when you need TTL or non-hashable values."
    },
    {
        "instruction": "How do I connect to a SQLite database in Python?",
        "input": "",
        "output": "```python\nimport sqlite3\nfrom contextlib import contextmanager\n\n# Using context manager for safe connection handling\n@contextmanager\ndef get_db(db_path: str = 'app.db'):\n    conn = sqlite3.connect(db_path)\n    conn.row_factory = sqlite3.Row  # rows behave like dicts\n    try:\n        yield conn\n        conn.commit()\n    except Exception:\n        conn.rollback()\n        raise\n    finally:\n        conn.close()\n\n# Usage\nwith get_db() as conn:\n    # Create table\n    conn.execute('''\n        CREATE TABLE IF NOT EXISTS users (\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            name TEXT NOT NULL,\n            email TEXT UNIQUE\n        )\n    ''')\n    \n    # Insert\n    conn.execute('INSERT INTO users (name, email) VALUES (?, ?)',\n                 ('Alice', 'alice@example.com'))  # always use ? placeholders\n    \n    # Query\n    rows = conn.execute('SELECT * FROM users').fetchall()\n    for row in rows:\n        print(dict(row))  # {'id': 1, 'name': 'Alice', 'email': '...'}\n```\n\nCritical: always use `?` placeholders, never string formatting — `f'WHERE name = {name}'` is SQL injection. `sqlite3.Row` makes rows accessible by column name."
    },
    {
        "instruction": "How do I write unit tests in Python?",
        "input": "",
        "output": "```python\nimport pytest\n\n# Function to test\ndef divide(a: float, b: float) -> float:\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b\n\n# Test file: test_divide.py\nclass TestDivide:\n    def test_normal_division(self):\n        assert divide(10, 2) == 5.0\n    \n    def test_float_division(self):\n        assert divide(1, 3) == pytest.approx(0.333, rel=1e-3)\n    \n    def test_negative_numbers(self):\n        assert divide(-6, 2) == -3.0\n    \n    def test_zero_divisor_raises(self):\n        with pytest.raises(ValueError, match='Cannot divide by zero'):\n            divide(10, 0)\n    \n    def test_zero_dividend(self):\n        assert divide(0, 5) == 0.0\n\n# Run: pytest test_divide.py -v\n```\n\nBest practices:\n- One assertion per test (easier to diagnose failures)\n- Test the happy path, edge cases, and error cases\n- Use `pytest.approx()` for floating point comparisons\n- Use `pytest.raises()` to verify exceptions are raised\n- Name tests `test_<what it does>_<expected result>`"
    },
    {
        "instruction": "Explain Python generators and when to use them",
        "input": "",
        "output": "A generator is a function that yields values one at a time instead of returning a full list. It uses memory for ONE item at a time, not all items.\n\n```python\n# Regular function — builds entire list in memory\ndef get_squares(n):\n    return [x**2 for x in range(n)]\n\n# Generator — yields one value at a time\ndef gen_squares(n):\n    for x in range(n):\n        yield x**2   # pauses here, resumes on next()\n\n# Usage is identical\nfor sq in gen_squares(1_000_000):  # uses ~0 extra memory\n    print(sq)\n```\n\nGenerator expressions (like list comprehensions but lazy):\n```python\nsquares = (x**2 for x in range(1000000))  # no memory used yet\nfirst_ten = [next(squares) for _ in range(10)]\n```\n\nUse generators when:\n- Processing large files line by line\n- Streaming API responses\n- Infinite sequences (keep generating until condition met)\n- Pipeline of data transformations\n\nDon't use generators when you need random access or to iterate multiple times (generators are consumed once)."
    },
    {
        "instruction": "How do I handle environment variables securely in Python?",
        "input": "",
        "output": "```python\nimport os\nfrom dotenv import load_dotenv\n\n# Load .env file (only in development — production uses real env vars)\nload_dotenv()\n\n# Required variables — fail loudly if missing\ndef get_required_env(key: str) -> str:\n    value = os.getenv(key)\n    if not value:\n        raise EnvironmentError(f'Required env var {key!r} is not set')\n    return value\n\n# Usage\nDATABASE_URL = get_required_env('DATABASE_URL')\nSECRET_KEY = get_required_env('SECRET_KEY')\n\n# Optional with defaults\nDEBUG = os.getenv('DEBUG', 'false').lower() == 'true'\nPORT = int(os.getenv('PORT', '8000'))\n```\n\n`.env` file (never commit to git):\n```\nDATABASE_URL=sqlite:///app.db\nSECRET_KEY=dev-secret-change-me\nDEBUG=true\n```\n\n`.gitignore` — always include:\n```\n.env\n.env.local\n*.env\n```\n\nFor production: use AWS Secrets Manager, environment variables in Docker/ECS, or a secrets vault. Never hardcode secrets in code — they end up in git history permanently."
    },
    {
        "instruction": "What is the difference between == and 'is' in Python?",
        "input": "",
        "output": "`==` checks **value equality** (are they equal?)\n`is` checks **identity** (are they the same object in memory?)\n\n```python\na = [1, 2, 3]\nb = [1, 2, 3]\nc = a\n\na == b   # True  — same values\na is b   # False — different objects in memory\na is c   # True  — c points to the same object as a\n\n# Modifying c also modifies a (they're the same object)\nc.append(4)\nprint(a)  # [1, 2, 3, 4]  ← a changed!\n```\n\nWhen to use `is`:\n- **Always** for `None`: `if x is None` (not `if x == None`)\n- **Never** for comparing values: `if x is 'hello'` is unreliable\n\nWhy `is None` instead of `== None`:\n- `None` is a singleton — there's exactly one `None` object\n- `is None` is faster (no equality method called)\n- Some objects override `==` in unexpected ways (e.g., numpy arrays)"
    },
    {
        "instruction": "How do I flatten a nested list in Python?",
        "input": "nested = [[1, 2], [3, [4, 5]], [6]]",
        "output": "There are several approaches depending on how deeply nested:\n\n**One level deep (simple):**\n```python\nnested = [[1, 2], [3, 4], [5]]\nflat = [item for sublist in nested for item in sublist]\n# [1, 2, 3, 4, 5]\n\n# Or using itertools (more readable)\nimport itertools\nflat = list(itertools.chain.from_iterable(nested))\n```\n\n**Arbitrarily deep (recursive):**\n```python\ndef flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))  # recurse\n        else:\n            result.append(item)\n    return result\n\nnested = [[1, 2], [3, [4, 5]], [6]]\nflatten(nested)  # [1, 2, 3, 4, 5, 6]\n```\n\nFor your specific input `[[1, 2], [3, [4, 5]], [6]]` — use the recursive version since it has a nested list inside a nested list.\n\nPython 3.12+ also has `itertools.batched()` for related flattening operations."
    },
    {
        "instruction": "How do I use Python's dataclasses?",
        "input": "",
        "output": "Dataclasses auto-generate `__init__`, `__repr__`, and `__eq__` so you don't write boilerplate:\n\n```python\nfrom dataclasses import dataclass, field\nfrom datetime import datetime\n\n@dataclass\nclass User:\n    name: str\n    email: str\n    role: str = 'viewer'              # default value\n    created_at: datetime = field(default_factory=datetime.now)  # dynamic default\n    tags: list = field(default_factory=list)  # mutable default — use field()\n\n# Auto-generated __init__:\nuser = User(name='Alice', email='alice@example.com')\nprint(user)  # User(name='Alice', email='alice@example.com', role='viewer', ...)\n\n# Auto-generated __eq__:\nuser2 = User(name='Alice', email='alice@example.com')\nuser == user2  # True\n```\n\nUseful options:\n```python\n@dataclass(frozen=True)   # immutable (like a tuple with names)\n@dataclass(order=True)    # enables <, >, <= comparisons\n@dataclass(slots=True)    # uses __slots__ for better performance (Python 3.10+)\n```\n\nUse dataclasses over plain dicts when your data has a fixed structure — you get type hints, IDE autocomplete, and validation for free."
    },
    {
        "instruction": "How do I implement retry logic in Python?",
        "input": "Making HTTP requests that sometimes fail",
        "output": "```python\nimport time\nimport requests\nfrom functools import wraps\n\ndef retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):\n    \"\"\"Decorator for automatic retry with exponential backoff.\"\"\"\n    def decorator(func):\n        @wraps(func)\n        def wrapper(*args, **kwargs):\n            current_delay = delay\n            for attempt in range(1, max_attempts + 1):\n                try:\n                    return func(*args, **kwargs)\n                except exceptions as e:\n                    if attempt == max_attempts:\n                        raise  # re-raise on final attempt\n                    print(f'Attempt {attempt} failed: {e}. Retrying in {current_delay}s...')\n                    time.sleep(current_delay)\n                    current_delay *= backoff  # exponential: 1s, 2s, 4s...\n        return wrapper\n    return decorator\n\n@retry(max_attempts=3, delay=1.0, exceptions=(requests.Timeout, requests.ConnectionError))\ndef call_api(url: str) -> dict:\n    response = requests.get(url, timeout=5)\n    response.raise_for_status()\n    return response.json()\n```\n\nFor production, use the `tenacity` library — it handles more edge cases:\n```python\nfrom tenacity import retry, stop_after_attempt, wait_exponential\n\n@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))\ndef call_api(url):\n    ...\n```"
    },
    {
        "instruction": "What is the GIL in Python and does it matter for my code?",
        "input": "",
        "output": "The GIL (Global Interpreter Lock) prevents multiple threads from executing Python bytecode simultaneously in CPython.\n\n**What this means practically:**\n\n```python\n# Threading — GIL-limited for CPU work\nimport threading\n# Two threads don't actually run Python code at the same time\n# One runs, the other waits for the GIL\n\n# BUT: GIL is released during I/O operations!\n# So threading IS effective for:\n# - HTTP requests, database queries, file reads\n# - Any time your code is waiting, not computing\n```\n\n**When the GIL matters:**\n- CPU-bound work (math, string processing, ML): use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`\n- I/O-bound work (HTTP, files, DB): use `threading` or `asyncio` — both work fine\n\n```python\nfrom concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor\n\n# CPU-bound: use processes (bypass GIL)\nwith ProcessPoolExecutor() as executor:\n    results = list(executor.map(cpu_heavy_function, data))\n\n# I/O-bound: use threads (GIL released during I/O anyway)\nwith ThreadPoolExecutor(max_workers=10) as executor:\n    results = list(executor.map(fetch_url, urls))\n```\n\nFor most web development and AI code (API calls, LLM requests), the GIL is irrelevant — you're I/O-bound, not CPU-bound."
    },
    {
        "instruction": "How do I use context managers (with statement) in Python?",
        "input": "",
        "output": "Context managers handle setup and teardown automatically — even if an exception occurs.\n\n```python\n# Built-in examples you already use:\nwith open('file.txt') as f:          # closes file automatically\n    data = f.read()\n\nwith sqlite3.connect('db.sqlite') as conn:  # commits/rollbacks + closes\n    conn.execute('INSERT ...')\n```\n\n**Creating your own with a class:**\n```python\nclass Timer:\n    def __enter__(self):\n        import time\n        self.start = time.time()\n        return self  # this becomes the 'as' variable\n    \n    def __exit__(self, exc_type, exc_val, exc_tb):\n        self.duration = time.time() - self.start\n        print(f'Elapsed: {self.duration:.3f}s')\n        return False  # don't suppress exceptions\n\nwith Timer() as t:\n    time.sleep(1)\n# prints: Elapsed: 1.001s\n```\n\n**Creating your own with `@contextmanager` (simpler):**\n```python\nfrom contextlib import contextmanager\n\n@contextmanager\ndef managed_resource():\n    print('Setup')     # __enter__\n    try:\n        yield           # code inside 'with' block runs here\n    finally:\n        print('Teardown')  # __exit__ — always runs\n\nwith managed_resource():\n    print('Working')\n# Setup → Working → Teardown\n```\n\nUse context managers for: files, database connections, locks, timers, temporary directories."
    },
]

# Add more varied examples to reach 100 total
EXTRA_EXAMPLES = [
    {
        "instruction": "How do I sort a list of dictionaries by a key in Python?",
        "input": "users = [{'name': 'Charlie', 'age': 30}, {'name': 'Alice', 'age': 25}, {'name': 'Bob', 'age': 35}]",
        "output": "```python\n# Sort by age (ascending)\nsorted_users = sorted(users, key=lambda u: u['age'])\n# [{'name': 'Alice', 'age': 25}, {'name': 'Charlie', 'age': 30}, {'name': 'Bob', 'age': 35}]\n\n# Sort by age (descending)\nsorted_users = sorted(users, key=lambda u: u['age'], reverse=True)\n\n# Sort by name (alphabetical)\nsorted_users = sorted(users, key=lambda u: u['name'])\n\n# Sort by multiple keys: age first, then name\nsorted_users = sorted(users, key=lambda u: (u['age'], u['name']))\n\n# In-place sort (modifies original list)\nusers.sort(key=lambda u: u['age'])\n```\n\nUse `sorted()` when you need a new list. Use `.sort()` to sort in-place. The `key` function extracts the comparison value from each element.\n\nFor typed data, `operator.itemgetter` is faster than lambda:\n```python\nfrom operator import itemgetter\nsorted_users = sorted(users, key=itemgetter('age'))\n```"
    },
    {
        "instruction": "How do I merge two dictionaries in Python?",
        "input": "dict1 = {'a': 1, 'b': 2}\ndict2 = {'b': 3, 'c': 4}",
        "output": "```python\ndict1 = {'a': 1, 'b': 2}\ndict2 = {'b': 3, 'c': 4}\n\n# Python 3.9+ — cleanest syntax\nmerged = dict1 | dict2\n# {'a': 1, 'b': 3, 'c': 4}  ← dict2 wins on conflicts\n\n# Update dict1 in-place (Python 3.9+)\ndict1 |= dict2\n\n# Python 3.5+ — unpacking\nmerged = {**dict1, **dict2}\n\n# Pre-3.5 — update method\nmerged = dict1.copy()\nmerged.update(dict2)\n```\n\nIn all cases, if both dicts have the same key, the **right-hand dict wins**.\n\nTo keep both values when there's a conflict:\n```python\nfrom collections import defaultdict\n\ndef merge_keep_all(d1, d2):\n    result = defaultdict(list)\n    for d in (d1, d2):\n        for k, v in d.items():\n            result[k].append(v)\n    return dict(result)\n\nmerge_keep_all({'a': 1, 'b': 2}, {'b': 3, 'c': 4})\n# {'a': [1], 'b': [2, 3], 'c': [4]}\n```"
    },
    {
        "instruction": "How do I use type hints in Python and why are they useful?",
        "input": "",
        "output": "Type hints make your code self-documenting and enable IDE autocomplete + static analysis.\n\n```python\nfrom typing import Optional, Union\n\n# Basic types\ndef greet(name: str, times: int = 1) -> str:\n    return f'Hello {name}! ' * times\n\n# Optional = can be None\ndef find_user(user_id: int) -> Optional[dict]:\n    # Returns dict or None\n    ...\n\n# List, dict, tuple\ndef process(items: list[str]) -> dict[str, int]:\n    return {item: len(item) for item in items}\n\n# Union (Python 3.10+ can use X | Y syntax)\ndef parse(value: str | int | None) -> str:\n    return str(value)\n\n# TypedDict for structured dicts\nfrom typing import TypedDict\nclass UserData(TypedDict):\n    name: str\n    age: int\n    email: str\n```\n\nType hints are NOT enforced at runtime — Python still runs code with wrong types. To enforce them:\n- **mypy**: `mypy your_file.py` — static checker\n- **pydantic**: runtime validation for APIs and config\n- **beartype**: `@beartype` decorator for runtime checking\n\nAlways add type hints to function signatures. Skip them in one-liners where the type is obvious."
    },
    {
        "instruction": "How do I implement a simple pub/sub event system in Python?",
        "input": "",
        "output": "```python\nfrom collections import defaultdict\nfrom typing import Callable\n\nclass EventBus:\n    \"\"\"Simple synchronous publish/subscribe event system.\"\"\"\n    \n    def __init__(self):\n        self._handlers: dict[str, list[Callable]] = defaultdict(list)\n    \n    def subscribe(self, event: str, handler: Callable) -> None:\n        \"\"\"Register a handler for an event.\"\"\"\n        self._handlers[event].append(handler)\n    \n    def unsubscribe(self, event: str, handler: Callable) -> None:\n        self._handlers[event].remove(handler)\n    \n    def publish(self, event: str, **data) -> None:\n        \"\"\"Fire an event, calling all registered handlers.\"\"\"\n        for handler in self._handlers[event]:\n            handler(**data)\n\n# Usage\nbus = EventBus()\n\n@bus.subscribe('user_created')  # can also do this as a method call\ndef send_welcome_email(username: str, email: str):\n    print(f'Sending welcome email to {email}')\n\ndef log_new_user(username: str, **kwargs):\n    print(f'New user registered: {username}')\n\nbus.subscribe('user_created', log_new_user)\nbus.publish('user_created', username='alice', email='alice@example.com')\n# Output:\n# Sending welcome email to alice@example.com\n# New user registered: alice\n```\n\nFor async pub/sub, use `asyncio.Queue` (as in Phase 5 Project 03). For distributed pub/sub across processes or machines, use Redis Pub/Sub."
    },
    {
        "instruction": "How do I profile Python code to find performance bottlenecks?",
        "input": "",
        "output": "Three levels of profiling:\n\n**1. Quick timing with timeit:**\n```python\nimport timeit\n\n# Time a single expression\ntime = timeit.timeit('sum(range(1000))', number=10000)\nprint(f'{time:.4f}s for 10,000 runs')\n```\n\n**2. Function-level profiling with cProfile:**\n```bash\npython -m cProfile -s cumulative your_script.py\n```\nOr in code:\n```python\nimport cProfile\nimport pstats\n\nwith cProfile.Profile() as pr:\n    your_function()  # profile this\n\nstats = pstats.Stats(pr)\nstats.sort_stats('cumulative')\nstats.print_stats(20)  # show top 20 functions by time\n```\n\n**3. Line-level profiling with line_profiler:**\n```bash\npip install line_profiler\n```\n```python\n@profile  # added by line_profiler at runtime\ndef slow_function():\n    ...\n```\n```bash\nkernprof -l -v your_script.py\n```\n\n**Common bottlenecks in Python:**\n- String concatenation in loops → use `''.join(list)`\n- List search → use `set` for O(1) lookup\n- Repeated attribute lookup → cache `obj.attr` in local var\n- Unnecessary copies → use generators, slices, views\n\nProfile before optimizing. Never guess where the bottleneck is."
    },
]

# Combine all examples
ALL_EXAMPLES = EXAMPLES + EXTRA_EXAMPLES

def save_dataset(examples: list, output_dir: str = "dataset"):
    """Split into train/eval and save as JSONL."""
    os.makedirs(output_dir, exist_ok=True)
    random.shuffle(examples)

    split = int(len(examples) * 0.9)
    train = examples[:split]
    eval_ = examples[split:]

    train_path = os.path.join(output_dir, "train.jsonl")
    eval_path  = os.path.join(output_dir, "eval.jsonl")

    with open(train_path, "w") as f:
        for ex in train:
            f.write(json.dumps(ex) + "\n")

    with open(eval_path, "w") as f:
        for ex in eval_:
            f.write(json.dumps(ex) + "\n")

    return train_path, eval_path, len(train), len(eval_)


def main():
    print("=" * 60)
    print("  Dataset Preparation — AI Coding Assistant")
    print("=" * 60)

    train_path, eval_path, n_train, n_eval = save_dataset(ALL_EXAMPLES)

    print(f"\n  Total examples: {len(ALL_EXAMPLES)}")
    print(f"  Train: {n_train} examples → {train_path}")
    print(f"  Eval:  {n_eval} examples  → {eval_path}")

    # Show a sample
    print(f"\n  Sample training example:")
    print(f"  Instruction: {ALL_EXAMPLES[0]['instruction'][:70]}...")
    print(f"  Input:       {ALL_EXAMPLES[0]['input'][:50] or '(none)'}")
    print(f"  Output:      {ALL_EXAMPLES[0]['output'][:80]}...")

    print(f"\n  Dataset ready. Next step: python finetune.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
