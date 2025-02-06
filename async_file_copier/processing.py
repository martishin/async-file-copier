import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import aiofiles

EXCLUDED_FOLDERS = [".cargo", ".idea", "target"]


@dataclass(frozen=True)
class PathMapping:
    source: Path
    dest: Path

    def __lt__(self, other: "PathMapping") -> bool:
        """Sort based on the last part of the destination path."""
        return self.dest.name < other.dest.name


@dataclass
class DirectoriesStructure:
    dirs: Dict[PathMapping, Dict[PathMapping, List[PathMapping]]] = field(
        default_factory=dict
    )


async def collect_dirs_structure(
    origin_dir: Path,
    dest_dir: Path,
) -> DirectoriesStructure:
    """
    Collect all modules in a structured dict.
    - Keeps `source` path as is.
    - Applies `to_snake_case` to `dest` paths only.
    """
    result = {}
    first_level_dirs = [
        d for d in origin_dir.iterdir() if d.is_dir() and d.name not in EXCLUDED_FOLDERS
    ]
    for first_level_dir in first_level_dirs:
        first_level_mapping = PathMapping(
            source=first_level_dir,
            dest=dest_dir / to_snake_case(first_level_dir.name),
        )
        result[first_level_mapping] = {}
        second_level_dirs = [d for d in first_level_dir.iterdir() if d.is_dir()]
        for second_level_dir in second_level_dirs:
            second_level_mapping = PathMapping(
                source=second_level_dir,
                dest=first_level_mapping.dest / to_snake_case(second_level_dir.name),
            )
            result[first_level_mapping][second_level_mapping] = [
                PathMapping(
                    source=d,
                    dest=second_level_mapping.dest / to_snake_case(d.name),
                )
                for d in second_level_dir.iterdir()
                if d.is_dir()
            ]

    return DirectoriesStructure(result)


async def copy_code_and_task_files(
    dirs_struct: DirectoriesStructure, dry_run: bool = False
):
    """
    Copy `src/main.rs` and `task.md` files to the appropriate destination
    """
    tasks = []

    for second_level_to_third_level_dir in dirs_struct.dirs.values():
        for (
            second_level_dir,
            third_level_dirs,
        ) in second_level_to_third_level_dir.items():
            for third_level_dir in third_level_dirs:
                source_main_file = third_level_dir.source / "src" / "main.rs"
                dest_main_file = third_level_dir.dest.with_suffix(".rs")
                if not await file_exists(dest_main_file):
                    tasks.append(copy_file(source_main_file, dest_main_file, dry_run))

                source_task_file = third_level_dir.source / "task.md"
                dest_task_file = third_level_dir.dest.with_suffix(".md")
                if not await file_exists(dest_main_file):
                    tasks.append(copy_file(source_task_file, dest_task_file, dry_run))

    await asyncio.gather(*tasks)


async def create_mod_files(dirs_struct: DirectoriesStructure, dry_run: bool = False):
    tasks = []

    for first_level_dir, second_level_to_third_level_dir in dirs_struct.dirs.items():
        content = "\n\n".join(
            f"pub mod {second_level_dir.dest.name} {{\n"
            + "\n".join(
                f"    pub mod {third_level_dir.dest.name};"
                for third_level_dir in sorted(third_level_dirs)
            )
            + "\n}"
            for second_level_dir, third_level_dirs in sorted(
                second_level_to_third_level_dir.items()
            )
        )
        dest_mod_file = first_level_dir.dest / "mod.rs"
        tasks.append(write_to_file(dest_mod_file, content, dry_run))

    await asyncio.gather(*tasks)


async def create_main_file(
    dest_dir: Path, dirs_struct: DirectoriesStructure, dry_run: bool = False
):
    content = ["#![allow(dead_code)]"]

    content.extend(
        f"mod {first_level_dir.dest.name};"
        for first_level_dir in dirs_struct.dirs.keys()
    )

    content.append("\nfn main() {")

    for first_level_dir, second_level_to_third_level_dir in dirs_struct.dirs.items():
        content.append(f"    // {first_level_dir.source.name.upper()}")
        for (
            second_level_dir,
            third_level_dirs,
        ) in second_level_to_third_level_dir.items():
            content.append(f"    // {second_level_dir.source.name.upper()}")
            for third_level_dir in third_level_dirs:
                content.append(
                    f"    // {first_level_dir.dest.name}::{second_level_dir.dest.name}::{third_level_dir.dest.name}::main();"
                )
    content.append("}")
    main_file = dest_dir / "main.rs"
    await write_to_file(main_file, "\n".join(content), dry_run)


def to_snake_case(name):
    """Convert a string to snake_case"""
    s = name.replace(",", "")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"-+", "_", s)
    s = re.sub(r"[^\w_]", "", s)
    s = s.lower()
    return s


async def file_exists(path: Path) -> bool:
    """Check if a file exists (run in a thread to avoid blocking)."""
    return await asyncio.to_thread(lambda: path.exists())


async def mkdir_async(path: Path, parents=True, exist_ok=True):
    """Asynchronously create directories (wraps Path.mkdir)."""
    await asyncio.to_thread(path.mkdir, parents=parents, exist_ok=exist_ok)


async def copy_file(source_file: Path, dest_file: Path, dry_run: bool = False):
    if await file_exists(source_file):
        if dry_run:
            logging.info(f"[DRY RUN] Would copy {source_file} to {dest_file}")
        else:
            await mkdir_async(dest_file.parent, parents=True, exist_ok=True)

            async with aiofiles.open(source_file, mode="r") as f:
                content = await f.read()

            async with aiofiles.open(dest_file, mode="w") as f:
                await f.write(content)
                logging.info(f"Copied {source_file} to {dest_file}")
    else:
        logging.warning(f"File not found: {source_file}")


async def write_to_file(dest_file: Path, content: str, dry_run: bool = False):
    if dry_run:
        logging.info(f"[DRY RUN] Would write to {dest_file} file, content:\n{content}")
    else:
        await mkdir_async(dest_file.parent, parents=True, exist_ok=True)

        async with aiofiles.open(dest_file, mode="w") as f:
            await f.write(content)
