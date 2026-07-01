"""
Pipeline orchestrator
─────────────────────
Runs Bronze → Silver → Gold in sequence.
Each layer can also be run independently via its own __main__ block.

Usage
-----
  python pipeline.py            # full run
  python pipeline.py --bronze   # bronze only
  python pipeline.py --silver   # silver only (bronze must exist)
  python pipeline.py --gold     # gold only   (silver must exist)
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from src.extract.bronze import run as bronze_run
from src.load.gold import run as gold_run
from src.transform.silver import run as silver_run
from src.utils.logger import get_logger

log = get_logger("pipeline")


def run_full():
    """Execute the full Bronze → Silver → Gold pipeline."""
    start = time.perf_counter()
    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  Lending Club ETL — Medallion Pipeline       ║")
    log.info(f"║  Started at {datetime.now():%Y-%m-%d %H:%M:%S}              ║")
    log.info("╚══════════════════════════════════════════════╝")

    steps = [
        ("BRONZE", bronze_run),
        ("SILVER", silver_run),
        ("GOLD",   gold_run),
    ]

    for name, fn in steps:
        t0 = time.perf_counter()
        log.info(f"▶ Running {name}…")
        fn()
        elapsed = time.perf_counter() - t0
        log.info(f"✓ {name} completed in {elapsed:.1f}s")

    total = time.perf_counter() - start
    log.info(f"\n✅  Full pipeline completed in {total:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Lending Club Medallion ETL")
    group  = parser.add_mutually_exclusive_group()
    group.add_argument("--bronze", action="store_true", help="Run Bronze layer only")
    group.add_argument("--silver", action="store_true", help="Run Silver layer only")
    group.add_argument("--gold",   action="store_true", help="Run Gold layer only")
    args = parser.parse_args()

    if args.bronze:
        bronze_run()
    elif args.silver:
        silver_run()
    elif args.gold:
        gold_run()
    else:
        run_full()


if __name__ == "__main__":
    main()
