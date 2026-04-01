# Python 3.13 PR Review Checklist

> **Target Python Version:** 3.13+  
> All new code must use modern Python patterns available in 3.13.

---

## Modern Python (3.13+)

- [ ] **No `typing.Optional` imports** — use `T | None` syntax instead  
      @detect: from\s+typing\s+import\s+.*Optional|:\s*Optional\[|->\s*Optional\[|tuple\[.*Optional\[|list\[.*Optional\[|dict\[.*Optional\[  
      @msg: Legacy Optional[T] syntax — use T | None instead  
      @fix: Remove 'from typing import Optional' and change 'Optional[T]' to 'T | None'

- [ ] **No `typing.Union` imports** — use `X | Y` syntax (PEP 604)  
      @detect: from\s+typing\s+import\s+.*\bUnion\b|Union\[  
      @msg: Legacy Union[X, Y] syntax — use X | Y instead  
      @fix: Remove 'from typing import Union' and change 'Union[X, Y]' to 'X | Y'

- [ ] **No `typing.List/Dict/Tuple/Set` imports** — use built-in generics `list`, `dict`, `tuple`, `set`  
      @detect: from\s+typing\s+import\s+.*\bList\b|from\s+typing\s+import\s+.*\bDict\b|from\s+typing\s+import\s+.*\bTuple\b|from\s+typing\s+import\s+.*\bSet\b|:\s*List\[|:\s*Dict\[|:\s*Tuple\[|:\s*Set\[|->\s*List\[|->\s*Dict\[|->\s*Tuple\[|->\s*Set\[  
      @msg: Legacy typing.List/Dict/Tuple/Set — use built-in list/dict/tuple/set  
      @fix: Remove 'from typing import List/Dict/Tuple/Set' and use built-in generics

- [ ] **No `typing.TypeVar` for simple generics** — use `def func[T]()` syntax (PEP 695)  
      @detect: from\s+typing\s+import\s+.*\bTypeVar\b|\w+\s*=\s*TypeVar\(  
      @anti: def\s+\w+\[\w+\s*:\s*\w+\]  
      @msg: Legacy TypeVar syntax — use modern def func[T]() syntax (PEP 695)  
      @fix: Use 'def func[T](x: T) -> T:' instead of TypeVar

- [ ] **No `typing.Generic` with explicit inheritance** — use `class MyClass[T]:` syntax (PEP 695)  
      @detect: class\s+\w+\(.*Generic\[|from\s+typing\s+import\s+.*\bGeneric\b  
      @anti: class\s+\w+\[\w+\s*:\s*\w+\]  
      @msg: Legacy Generic[T] inheritance — use modern class syntax (PEP 695)  
      @fix: Use 'class MyClass[T]:' instead of 'class MyClass(Generic[T])'

- [ ] **No `typing.NamedTuple` with class body** — use `typing.NamedTuple` with field assignment or dataclasses  
      @detect: class\s+\w+\(.*NamedTuple\):\s*\n\s+\w+\s*:\s*\w+  
      @msg: Legacy NamedTuple class body syntax — use field assignment syntax  
      @fix: Use 'class Person(NamedTuple): name: str' as one-liners or switch to @dataclass

- [ ] **No `setup_method` in pytest tests** — use `@pytest.fixture(autouse=True)` instead  
      @detect: def\s+setup_method\s*\(\s*self  
      @msg: Legacy pytest setup_method — use @pytest.fixture(autouse=True)  
      @fix: Replace setup_method with a pytest fixture decorated with @pytest.fixture(autouse=True)

- [ ] **No manual `sys.modules` manipulation for mocking** — use `pytest-mock`, `@patch`, or `monkeypatch`  
      @detect: sys\.modules\[.*\]\s*=  
      @msg: Manual sys.modules stubbing — use pytest-mock or @patch instead  
      @fix: Use @patch decorator or pytest-mock fixtures instead of manipulating sys.modules

- [ ] **Use `typing.Self` for self-referential types** (Python 3.11+)  
      @detect: ->\s*["']?\w+["']?\s*:\s*\n\s*return\s+self  
      @anti: ->\s*Self\s*:\s*\n\s*return\s+self  
      @msg: Method returns self but doesn't use typing.Self  
      @fix: Use 'from typing import Self' and '-> Self' for fluent interface methods

- [ ] **Use `typing.Required/NotRequired` for TypedDict** (Python 3.11+) instead of total=False workarounds  
      @detect: class\s+\w+\(.*TypedDict.*\):\s*\n\s+total\s*=\s*False  
      @msg: Legacy TypedDict total=False pattern — use Required/NotRequired  
      @fix: Use 'field: Required[str]' or 'field: NotRequired[str]' instead of total=False

- [ ] **Use `typing.TypedDict` with `__required_keys__`/`__optional_keys__` properly typed**  
      @detect: class\s+\w+\(.*TypedDict\):\s*\n\s+\w+\s*=\s*\w+\s*:\s*\w+\s*=  
      @msg: TypedDict with default values — use dataclass or NamedTuple instead  
      @fix: TypedDict doesn't support defaults; use @dataclass(frozen=True) or NamedTuple

- [ ] **Use `typing.Never` instead of `NoReturn` for unreachable code** (Python 3.11+)  
      @detect: from\s+typing\s+import\s+.*\bNoReturn\b|:\s*NoReturn  
      @msg: Legacy NoReturn — use Never (Python 3.11+)  
      @fix: Use 'from typing import Never' instead of NoReturn

---

## Code Quality

- [ ] **Functions have complete type hints** — all parameters and return values typed  
      @detect: ^def\s+\w+\([^)]*\)(?!\s*->)\s*:\s*$  
      @anti: ->\s*\w+|->\s*None|^def\s+\w+\s*\(\s*self\s*\)\s*->|#\s*type:\s*ignore  
      @msg: Missing return type annotation  
      @fix: Add '-> ReturnType' to function signature

- [ ] **No bare `except:` clauses** — always catch specific exceptions  
      @detect: except\s*:  
      @anti: except\s+\w+Error|except\s+Exception|except\s+\w+  
      @msg: Bare except clause — catch specific exceptions  
      @fix: Use 'except SpecificError:' instead of bare 'except:'

- [ ] **Use `exceptiongroups` or `*` syntax for exception groups** (Python 3.11+)  
      @detect: except\s*\(\s*Exception\s*,\s*\w+Error  
      @msg: Legacy multi-exception syntax — use exception groups for Python 3.11+  
      @fix: Use 'except* ExceptionGroup:' or 'except* ValueError:' syntax

- [ ] **Use `tomllib` for TOML parsing** (Python 3.11+, replaces toml/tomli)  
      @detect: import\s+tomli|import\s+toml\b|from\s+tomli|from\s+toml  
      @msg: Legacy TOML library — use stdlib tomllib (Python 3.11+)  
      @fix: Use 'import tomllib' from stdlib instead of tomli/toml package

- [ ] **Use `datetime.UTC` instead of `timezone.utc`** (Python 3.11+)  
      @detect: timezone\.utc|datetime\.now\(timezone\.utc\)  
      @anti: datetime\.UTC|datetime\.now\(UTC\)  
      @msg: Legacy timezone.utc — use datetime.UTC (Python 3.11+)  
      @fix: Use 'from datetime import UTC' and 'datetime.now(UTC)'

- [ ] **Use `enum.StrEnum` for string enums** (Python 3.11+)  
      @detect: class\s+\w+\(.*Enum\):\s*\n\s+\w+\s*=\s*["']\w+["']  
      @anti: class\s+\w+\(.*StrEnum\)  
      @msg: Legacy Enum with string values — use StrEnum (Python 3.11+)  
      @fix: Use 'class Status(StrEnum):' instead of manual string Enum

---

## Documentation & Best Practices

- [ ] **No commented-out code** — remove before committing  
      @detect: ^\s*#\s*\w+\([^)]*\)|^\s*#\s*print\s*\(|^\s*#\s*return\s|^\s*#\s*if\s+|^\s*#\s*for\s+|^\s*#\s*while\s+  
      @msg: Commented-out code detected  
      @fix: Remove the commented code or convert to a proper TODO comment

- [ ] **Docstrings for public functions** — all public APIs documented with Google/NumPy style  
      @detect: ^def\s+\w+\([^)]*\)(\s*->\s*\w+)?\s*:\s*\n\s+(?!"""|#|pass|\.\.\.)  
      @anti: """|pass\s*\n|\.\.\.\s*\n  
      @msg: Missing docstring for public function  
      @fix: Add a docstring describing the function's purpose and parameters

- [ ] **Use `typing.overload` for function overloads** — document complex function signatures  
      @detect: @overload\s*\n\s*def\s+\w+  
      @msg: Function with @overload detected — ensure all variants are covered  
      @fix: Add @overload decorators for all function signature variants

---

## Performance & Security

- [ ] **Use `functools.lru_cache` or `functools.cache`** for expensive pure functions  
      @detect: ^\s+_cache\s*=\s*\{\}|if\s+\w+\s+not\s+in\s+_cache  
      @anti: @lru_cache|@cache  
      @msg: Manual caching pattern — use @lru_cache or @cache  
      @fix: Use 'from functools import cache' and '@cache' decorator

- [ ] **Use `pathlib.Path` instead of `os.path`** — modern path handling  
      @detect: os\.path\.join|os\.path\.exists|os\.path\.isfile|os\.path\.isdir  
      @anti: Path\(|from\s+pathlib\s+import  
      @msg: Legacy os.path usage — use pathlib.Path  
      @fix: Use 'from pathlib import Path' and Path objects

- [ ] **Use `hashlib.file_digest` for file hashing** (Python 3.11+)  
      @detect: hashlib\.\w+\([^)]*\.read\(\)  
      @msg: Manual file hashing — use hashlib.file_digest (Python 3.11+)  
      @fix: Use 'hashlib.file_digest(f, "sha256")' instead of manual read+update

- [ ] **Use `base64.b64encode` with `urlsafe=True` for URL-safe encoding**  
      @detect: base64\.b64encode.*replace\(['"][\+/]['"]  
      @msg: Manual base64 URL-safe conversion — use urlsafe_b64encode  
      @fix: Use 'base64.urlsafe_b64encode()' instead of manual replace

---

## Testing

- [ ] **Use `pytest.raises` with `match=` parameter** — precise exception testing  
      @detect: pytest\.raises\([^)]+\)(?!.*match)  
      @msg: pytest.raises without match parameter  
      @fix: Add 'match="expected pattern"' to pytest.raises() for precise matching

- [ ] **Use `tmp_path` fixture instead of `tmpdir`** — modern pathlib-based fixture  
      @detect: def\s+test_\w+\(.*tmpdir|request\.fixturenames.*tmpdir  
      @anti: tmp_path  
      @msg: Legacy tmpdir fixture — use tmp_path (pathlib.Path)  
      @fix: Use 'tmp_path: Path' fixture instead of 'tmpdir'

- [ ] **Use `caplog` fixture for logging assertions** — don't patch logging manually  
      @detect: patch\(['"]logging\.|with\s+patch.*logging  
      @msg: Manual logging patching — use caplog fixture  
      @fix: Use 'caplog: pytest.LogCaptureFixture' instead of patching logging

- [ ] **Use `monkeypatch` fixture instead of manual os.environ manipulation**  
      @detect: os\.environ\[.*\]\s*=|os\.environ\.setdefault|os\.environ\.update  
      @msg: Manual os.environ manipulation in tests — use monkeypatch  
      @fix: Use 'monkeypatch.setenv("KEY", "value")' with automatic cleanup

---

## Quick Reference: Python 3.13 Modernization

| Legacy Pattern | Modern Python 3.13 |
|----------------|-------------------|
| `Optional[T]` | `T \| None` |
| `Union[X, Y]` | `X \| Y` |
| `List[T]` | `list[T]` |
| `Dict[K, V]` | `dict[K, V]` |
| `Tuple[T, ...]` | `tuple[T, ...]` |
| `TypeVar("T")` | `def func[T]()` |
| `Generic[T]` | `class C[T]:` |
| `NoReturn` | `Never` |
| `timezone.utc` | `UTC` (from datetime) |
| `tomli/tom` | `tomllib` (stdlib) |
| `Enum` + strings | `StrEnum` |
| `tmpdir` | `tmp_path` |
| `NamedTuple` class body | `@dataclass` or one-liner |
| `TypedDict(total=False)` | `Required/NotRequired` |
| `setup_method` | `@pytest.fixture` |
| `os.path` | `pathlib.Path` |

---

## Auto-Detection Tags

Items with `@detect` tags are automatically scanned. Add new patterns following this format:

```markdown
- [ ] **Rule description** — explanation here
      @detect: pattern1|pattern2
      @anti: exclusion_pattern (optional)
      @msg: Short violation message
      @fix: How to fix it
```

> **Note:** Only one `@detect` line per rule — combine multiple patterns with `|`. Multiple `@detect` lines are silently ignored.
