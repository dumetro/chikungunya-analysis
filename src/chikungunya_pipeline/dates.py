"""The single dedicated date normalisation function for the whole pipeline.

Every date column in the source Excel is routed through :func:`to_iso8601`,
which accepts the messy variety of real-world inputs and returns a
``datetime.date`` (which serialises to an ISO-8601 ``YYYY-MM-DD`` string) or
``None`` for blanks / unparseable values.

Handled inputs:
    * already-parsed ``date`` / ``datetime`` / pandas ``Timestamp``
    * Excel serial numbers (e.g. ``45292`` -> 2024-01-01), incl. numeric strings
    * ISO strings ``YYYY-MM-DD`` (and with time component)
    * day-first strings ``DD/MM/YYYY``, ``DD-MM-YYYY``, ``DD.MM.YYYY``
    * textual months ``12 Jan 2024`` / ``Jan 12, 2024``
    * blanks, ``"NA"``, ``"-"``, ``NaN`` -> ``None``

Ambiguous numeric dates (e.g. ``03/04/2024``) are interpreted day-first by
default, matching WHO / international convention; set ``dayfirst=False`` to
override.
"""

from __future__ import annotations

import datetime as _dt
import math
import re
from typing import Optional, Union

import pandas as pd

# Matches an ISO-8601 date prefix (YYYY-MM-DD), optionally with a time part.
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T].*)?$")

DateLike = Union[str, int, float, _dt.date, _dt.datetime, pd.Timestamp, None]

# Strings that should be treated as "no value".
_NULL_TOKENS = {"", "na", "n/a", "nan", "none", "null", "-", "--", "?", "unknown"}

# Excel's 1900 date system epoch. Excel serial 1 == 1900-01-01, but Excel
# wrongly treats 1900 as a leap year, so serials are offset by 2 days from the
# 1899-12-30 anchor used here (the standard correction).
_EXCEL_EPOCH = _dt.datetime(1899, 12, 30)

# Plausible range for an Excel serial number (≈ 1990-01-01 to 2069). Guards
# against treating a 4-digit year or an age from being read as a serial.
_EXCEL_SERIAL_MIN = 30000  # 1982-02-19
_EXCEL_SERIAL_MAX = 60000  # 2064-04-08


def _is_null(value: DateLike) -> bool:
    if value is None or value is pd.NaT:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        return value.strip().lower() in _NULL_TOKENS
    # Catches pandas NaT / NA scalars without raising on lists/arrays.
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _from_excel_serial(serial: float) -> Optional[_dt.date]:
    if not (_EXCEL_SERIAL_MIN <= serial <= _EXCEL_SERIAL_MAX):
        return None
    return (_EXCEL_EPOCH + _dt.timedelta(days=float(serial))).date()


def to_iso8601(value: DateLike, *, dayfirst: bool = True) -> Optional[_dt.date]:
    """Normalise an arbitrary date-like value to a ``datetime.date``.

    Returns ``None`` for blanks / unparseable values. Raising is avoided on
    purpose: invalid dates surface later as nulls and are caught by validation.
    """
    if _is_null(value):
        return None

    # Already a date/datetime/Timestamp.
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date()
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value

    # Numeric -> candidate Excel serial.
    if isinstance(value, (int, float)):
        return _from_excel_serial(float(value))

    text = str(value).strip()
    if text.lower() in _NULL_TOKENS:
        return None

    # A bare number passed as a string is an Excel serial.
    try:
        as_float = float(text)
    except ValueError:
        pass
    else:
        if as_float.is_integer():
            return _from_excel_serial(as_float)

    # Fall back to pandas' flexible parser (handles ISO, slashes, textual
    # months). errors="coerce" -> NaT for anything unparseable. ISO strings are
    # unambiguous, so don't apply dayfirst to them (avoids a pandas warning).
    iso_like = bool(_ISO_RE.match(text))
    parsed = pd.to_datetime(text, dayfirst=dayfirst and not iso_like, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def to_iso_string(value: DateLike, *, dayfirst: bool = True) -> Optional[str]:
    """Convenience wrapper returning the ISO string form (or ``None``)."""
    parsed = to_iso8601(value, dayfirst=dayfirst)
    return parsed.isoformat() if parsed is not None else None
