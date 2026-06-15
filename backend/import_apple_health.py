"""Import an Apple Health export from the command line (handles large files).

iPhone Health app -> your profile -> "Export All Health Data" -> export.zip.
Copy it to your computer, then:

    python import_apple_health.py path/to/export.zip
    python import_apple_health.py path/to/export.xml

Maps resting HR, HRV, VO2max, steps, weight, SpO2, blood pressure, and sleep
to your biomarker timelines (Health Score + Action Plan update automatically).
"""
from __future__ import annotations

import sys

from sqlmodel import Session

from app.connectors.apple_health import import_apple_health
from app.db import engine, init_db


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python import_apple_health.py <export.zip|export.xml>")
        return 2
    init_db()
    with Session(engine) as session:
        result = import_apple_health(session, sys.argv[1])
    print(f"Imported {result['added']} readings. Metrics: {', '.join(result['metrics']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
