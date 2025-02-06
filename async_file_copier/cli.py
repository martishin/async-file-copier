#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))

from async_file_copier.processing import (
    collect_dirs_structure,
    copy_code_and_task_files,
    create_main_file,
    create_mod_files,
    mkdir_async,
)


async def run(origin: str, destination: str, dry_run: bool = False):
    """
    Main function:
      - origin: source directory.
      - destination: target directory (typically the src folder).
      - dry_run: if True, no file system changes occur.
    """
    origin_dir = Path(origin)
    dest_dir = Path(destination)
    dirs_structure = await collect_dirs_structure(origin_dir, dest_dir)
    if dry_run:
        logging.info(f"[DRY RUN] Would create destination directory {dest_dir}")
    else:
        await mkdir_async(dest_dir, parents=True, exist_ok=True)

    await copy_code_and_task_files(dirs_structure, dry_run)
    await create_mod_files(dirs_structure, dry_run)
    # await create_main_file(dest_dir, dirs_structure, dry_run)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    asyncio.run(run(args.origin, args.destination, args.dry_run))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Organize Rust project files into a destination with snake_case names and mod.rs structure."
    )
    parser.add_argument(
        "--origin",
        type=str,
        required=True,
        help="Path to the source (origin) directory",
    )
    parser.add_argument(
        "--destination",
        type=str,
        required=True,
        help="Path to the target (destination) directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run (only log actions, do not copy files)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
