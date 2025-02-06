import pytest

from async_file_copier.processing import (
    DirectoriesStructure,
    PathMapping,
    collect_dirs_structure,
    copy_code_and_task_files,
    create_main_file,
    create_mod_files,
    file_exists,
    to_snake_case,
    write_to_file,
)


@pytest.mark.parametrize(
    "input_str, expected_output",
    [
        ("Accessing Values in a Hash Map", "accessing_values_in_a_hash_map"),
        ("Hello World", "hello_world"),
        ("Module-Test", "module_test"),
        ("Already_Snake", "already_snake"),
    ],
)
def test_to_snake_case(input_str, expected_output):
    """Test snake_case conversion."""
    assert to_snake_case(input_str) == expected_output


@pytest.mark.asyncio
async def test_collect_dirs_structure(tmp_path):
    """Test that collect_dirs_structure properly maps directories."""
    origin = tmp_path / "origin"
    dest = tmp_path / "dest"
    origin.mkdir()

    first = origin / "First Module"
    first.mkdir()
    second = first / "Second Module"
    second.mkdir()
    third = second / "Third Module"
    third.mkdir()

    dirs_struct = await collect_dirs_structure(origin, dest)

    assert len(dirs_struct.dirs) == 1
    first_level = next(iter(dirs_struct.dirs.keys()))
    assert first_level.source == first
    assert first_level.dest == dest / "first_module"

    second_level = next(iter(dirs_struct.dirs[first_level].keys()))
    assert second_level.source == second
    assert second_level.dest == first_level.dest / "second_module"

    third_level = dirs_struct.dirs[first_level][second_level][0]
    assert third_level.source == third
    assert third_level.dest == second_level.dest / "third_module"


@pytest.mark.asyncio
async def test_copy_code_and_task_files(tmp_path):
    """Test copying of main.rs and task.md."""
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()

    third = source_root / "Third Module"
    src_dir = third / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "main.rs").write_text("fn main() {}")
    (third / "task.md").write_text("Task content")

    third_mapping = PathMapping(source=third, dest=dest_root / "third_module")
    second_mapping = PathMapping(
        source=tmp_path / "Second", dest=dest_root / "second_module"
    )
    dirs_struct = DirectoriesStructure(
        {second_mapping: {second_mapping: [third_mapping]}}
    )

    await copy_code_and_task_files(dirs_struct, dry_run=False)

    assert (third_mapping.dest.with_suffix(".rs")).exists()
    assert (third_mapping.dest.with_suffix(".md")).exists()
    assert (third_mapping.dest.with_suffix(".rs")).read_text() == "fn main() {}"
    assert (third_mapping.dest.with_suffix(".md")).read_text() == "Task content"


@pytest.mark.asyncio
async def test_create_mod_files(tmp_path):
    """Test generation of mod.rs files."""
    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    first_mapping = PathMapping(
        source=tmp_path / "First", dest=dest_root / "first_module"
    )
    second_mapping = PathMapping(
        source=tmp_path / "Second", dest=first_mapping.dest / "second_module"
    )
    third_mapping = PathMapping(
        source=tmp_path / "Third", dest=second_mapping.dest / "third_module"
    )

    dirs_struct = DirectoriesStructure(
        {first_mapping: {second_mapping: [third_mapping]}}
    )
    await create_mod_files(dirs_struct, dry_run=False)

    mod_file = first_mapping.dest / "mod.rs"
    assert mod_file.exists()
    content = mod_file.read_text()
    assert f"pub mod {second_mapping.dest.name}" in content
    assert f"    pub mod {third_mapping.dest.name};" in content


@pytest.mark.asyncio
async def test_create_main_file(tmp_path):
    """Test main.rs file generation."""
    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    first_mapping = PathMapping(
        source=tmp_path / "First", dest=dest_root / "first_module"
    )
    second_mapping = PathMapping(
        source=tmp_path / "Second", dest=first_mapping.dest / "second_module"
    )
    third_mapping = PathMapping(
        source=tmp_path / "Third", dest=second_mapping.dest / "third_module"
    )

    dirs_struct = DirectoriesStructure(
        {first_mapping: {second_mapping: [third_mapping]}}
    )

    await create_main_file(dest_root, dirs_struct, dry_run=False)

    main_file = dest_root / "main.rs"
    assert main_file.exists()
    content = main_file.read_text()

    assert "#![allow(dead_code)]" in content
    assert f"mod {first_mapping.dest.name};" in content
    assert f"    // {first_mapping.source.name.upper()}" in content
    assert f"    // {second_mapping.source.name.upper()}" in content
    assert (
        f"    // {first_mapping.dest.name}::{second_mapping.dest.name}::{third_mapping.dest.name}::main();"
        in content
    )


@pytest.mark.asyncio
async def test_write_to_file(tmp_path):
    """Test async file writing."""
    test_file = tmp_path / "test_file.rs"
    content = "fn main() {}"

    await write_to_file(test_file, content, dry_run=False)

    assert test_file.exists()
    assert test_file.read_text() == content


@pytest.mark.asyncio
async def test_file_exists(tmp_path):
    """Test file existence check."""
    test_file = tmp_path / "test_file.rs"
    test_file.write_text("fn main() {}")

    assert await file_exists(test_file) is True
    assert await file_exists(tmp_path / "non_existent.rs") is False
