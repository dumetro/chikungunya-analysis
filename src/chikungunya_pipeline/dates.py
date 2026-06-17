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


def _full_year(year: int) -> int:
    """Expand a 2-digit year to 20xx (data is current-century)."""
    return year + 2000 if year < 100 else year


def _force_year(d: Optional[_dt.date], assume_year: Optional[int]) -> Optional[_dt.date]:
    """Override the year of a parsed date (used when all data is one year)."""
    if assume_year and d is not None:
        try:
            return d.replace(year=assume_year)
        except ValueError:  # e.g. 29 Feb in a non-leap target year
            return d
    return d


def _parse_dotted(
    text: str, assume_year: Optional[int], dayfirst: bool = True
) -> Optional[_dt.date]:
    """Parse dot-separated dates that pandas mishandles:

        DD.MM.YYYY / DD.MM.YY   -> day, month, year
        M.YYYY / M.YY           -> month, year (day = 1)        e.g. "3.26"
        DD.MM (no year)         -> day, month, DATA_YEAR        e.g. "27.05"

    Two-digit years expand to 20xx; ``assume_year`` overrides the year (and is
    required to resolve a year-less DD.MM). Ambiguous decimals like "3.5" return
    None so they are not mistaken for dates.
    """
    parts = [p.strip() for p in text.split(".")]
    if not (2 <= len(parts) <= 3) or not all(p.isdigit() for p in parts):
        return None
    nums = [int(p) for p in parts]
    try:
        if len(parts) == 3:  # DD.MM.YY(YY)
            day, month, yr = nums
            return _dt.date(assume_year or _full_year(yr), month, day)

        a, b = nums
        if len(parts[1]) == 4:            # M.YYYY
            return _dt.date(assume_year or b, a, 1)
        if b > 12:                        # M.YY  (b is a 2-digit year)
            return _dt.date(assume_year or _full_year(b), a, 1)
        # b is a plausible month (1..12) -> DD.MM with the year missing.
        # 'a' is a day if it can't be a month, or if both parts are zero-padded.
        if 1 <= b <= 12 and (a > 12 or (len(parts[0]) == 2 and len(parts[1]) == 2)):
            if not assume_year:
                return None  # no year available to complete the date
            day, month = (a, b) if (dayfirst or a > 12) else (b, a)
            return _dt.date(assume_year, month, day)
        return None  # ambiguous / decimal (e.g. "3.5")
    except ValueError:
        return None


def to_iso8601(
    value: DateLike, *, dayfirst: bool = True, assume_year: Optional[int] = None
) -> Optional[_dt.date]:
    """Normalise an arbitrary date-like value to a ``datetime.date``.

    ``assume_year`` forces the year of every parsed date (set it when the dataset
    is known to be a single year). Returns ``None`` for blanks / unparseable
    values — invalid dates surface later as nulls and are caught by validation.
    """
    if _is_null(value):
        return None

    # Already a date/datetime/Timestamp.
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else _force_year(value.date(), assume_year)
    if isinstance(value, _dt.datetime):
        return _force_year(value.date(), assume_year)
    if isinstance(value, _dt.date):
        return _force_year(value, assume_year)

    # Numeric -> Excel serial; a non-integer float may be a dotted date (3.26).
    if isinstance(value, (int, float)):
        serial = _from_excel_serial(float(value))
        if serial is not None:
            return _force_year(serial, assume_year)
        if not (isinstance(value, float) and not float(value).is_integer()):
            return None
        text = str(value).strip()
    else:
        text = str(value).strip()
        if text.lower() in _NULL_TOKENS:
            return None
        # A bare integer string is an Excel serial.
        try:
            as_float = float(text)
        except ValueError:
            as_float = None
        if as_float is not None and as_float.is_integer():
            serial = _from_excel_serial(as_float)
            if serial is not None:
                return _force_year(serial, assume_year)

    # Dot-separated numeric dates (DD.MM.YY(YY), M.YY(YY), or year-less DD.MM).
    dotted = _parse_dotted(text, assume_year, dayfirst)
    if dotted is not None:
        return dotted

    # Fall back to pandas' flexible parser (ISO, slashes, textual months).
    # ISO strings are unambiguous, so don't apply dayfirst (avoids a warning).
    iso_like = bool(_ISO_RE.match(text))
    parsed = pd.to_datetime(text, dayfirst=dayfirst and not iso_like, errors="coerce")
    if pd.isna(parsed):
        return None
    return _force_year(parsed.date(), assume_year)


def to_iso_string(
    value: DateLike, *, dayfirst: bool = True, assume_year: Optional[int] = None
) -> Optional[str]:
    """Convenience wrapper returning the ISO string form (or ``None``)."""
    parsed = to_iso8601(value, dayfirst=dayfirst, assume_year=assume_year)
    return parsed.isoformat() if parsed is not None else None
