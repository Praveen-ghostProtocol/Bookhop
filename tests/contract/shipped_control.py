"""Run the P14 control that the build actually enforces, as a black box.

**Why this file exists, and it is QA correcting itself.** QA-S0 v1.0's
`test_p14_is_not_guaranteed_by_naming` measured `tests/contract/denylist.py` —
QA's *own transcription* of ADR-003 §2.3 — and reported its escapes as the
shipped control's escapes. Backend is right that this is the same defect QA
found in `tests/unit/test_forbidden_schema.py`: a control judged against a
hand-copied rule rather than the real one. The irony is recorded in QA-S0.md §3
rather than quietly fixed.

This module removes the transcription from the measurement. It imports the
shipped guard and calls its live-schema assertions over whatever is in the
database at the time, so an attack is "caught" if and only if **the build would
go red**. Nothing here re-implements a rule.

It is deliberately *not* a judgement about how the guard is written. QA asserts
two separate things and keeps them apart:

* does the shipped control stop the attack (this module), and
* does the shipped control say what ADR-003 §2.3 says (`test_p14.py`'s
  conformance tests, which read the module's data and compare it with the ADR).
"""

import importlib
import inspect

import pytest

#: Assertions in the shipped guard that read the live schema. Discovered, not
#: listed, so a new one is picked up automatically.
_SKIP_NOT_SCHEMA_READING = {
    # These assert the predicates or the ADR's own data, not the live schema, so
    # running them tells us nothing about an attack we just inserted.
    "test_frozen_enum_value_set",
    "test_the_withdrawn_dob_exception_is_gone",
    "test_the_control_would_catch_each_known_attack",
    "test_the_contract_mandated_columns_are_not_false_positives",
}


def shipped():
    """The guard module the build runs. Skips, loudly, if it cannot be read."""
    try:
        return importlib.import_module("tests.unit.test_forbidden_schema")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"cannot load the shipped P14 control: {exc!r}")


def _skipped_by_its_own_marker(fn):
    """Honour the guard's own `@pytest.mark.skipif`.

    Calling a test function directly bypasses its markers, and one assertion in
    the guard (`test_the_money_column_is_an_integer_type`) is correctly
    skipped while `listings` does not exist. Running it anyway would report the
    guard as red on a clean schema and make every verdict here meaningless.
    """
    for mark in getattr(fn, "pytestmark", []):
        if mark.name == "skipif" and mark.args and bool(mark.args[0]):
            return True
    return False


def _callables(module):
    """Every live-schema assertion in the guard, with its arguments bound."""
    out = []
    for name, fn in vars(module).items():
        if not name.startswith("test_") or not callable(fn):
            continue
        if name in _SKIP_NOT_SCHEMA_READING:
            continue
        if _skipped_by_its_own_marker(fn):
            continue
        params = list(inspect.signature(fn).parameters)
        if not params:
            out.append((name, fn, ()))
        elif params == ["table"]:
            for table in sorted(getattr(module, "FROZEN_TABLES", {})):
                out.append((f"{name}[{table}]", fn, (table,)))
        # anything else takes fixtures this runner cannot supply; the names above
        # cover every schema-reading assertion in the file today, and
        # `test_the_runner_sees_every_schema_reading_assertion` fails if that
        # stops being true.
    return out


def run_shipped_control():
    """Run the guard over the current database.

    Returns `(failures, errors)`:
      * `failures` — assertions that fired: the build would be red, which is the
        guard doing its job;
      * `errors` — assertions that raised something other than an assertion: the
        build would also be red, but for the wrong reason, and that is reported
        separately because a guard that crashes is not a guard that caught
        something.
    """
    module = shipped()
    failures, errors = [], []
    for label, fn, args in _callables(module):
        try:
            fn(*args)
        except AssertionError as exc:
            failures.append((label, str(exc).splitlines()[0][:400]))
        except pytest.skip.Exception:
            continue
        except pytest.fail.Exception as exc:
            # `pytest.fail(...)` is the guard asserting, not the guard crashing.
            # Classifying it as an error was a bug in this runner's first draft
            # and it reported two shapes as escaped that the guard does catch.
            failures.append((label, str(exc).splitlines()[0][:400]))
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            errors.append((label, f"{type(exc).__name__}: {exc}"))
    return failures, errors


def control_catches():
    """True when the shipped guard would fail the build on the current schema."""
    failures, errors = run_shipped_control()
    return bool(failures or errors), failures, errors
