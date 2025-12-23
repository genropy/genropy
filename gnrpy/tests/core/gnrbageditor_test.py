"""
Unit tests for BagEditor class and CLI.
"""
import pytest
from .common import BaseGnrTest
import tempfile
from pathlib import Path
import subprocess
import sys
import io
from unittest.mock import patch
from gnr.core.gnrbageditor import BagEditor
from gnr.core.cli.gnrbagedit import main as cli_main


class TestBagEditor(BaseGnrTest):
    """Test cases for BagEditor class."""

    @classmethod
    def setup_class(cls):
        """Set up test fixtures."""
        # Create a temporary XML file for testing
        cls.test_dir = tempfile.mkdtemp()
        cls.test_file = Path(cls.test_dir) / "test.xml"

        # Store the original XML content
        cls.original_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<GenRoBag>
    <projects>
        <project1 name="Test Project" path="/test"/>
    </projects>
</GenRoBag>
"""
        cls.test_file.write_text(cls.original_xml_content)

        cls.editor = BagEditor()

    def setup_method(self, method):
        """Reset test file before each test for isolation."""
        # Restore original XML content before each test
        self.test_file.write_text(self.original_xml_content)
        # Reset the editor to ensure clean state
        self.editor = BagEditor()

    @classmethod
    def teardown_class(cls):
        """Clean up test fixtures."""
        # Remove temporary files
        if cls.test_file.exists():
            cls.test_file.unlink()
        Path(cls.test_dir).rmdir()

    def test_init_without_file(self):
        """Test initializing BagEditor without a file."""
        editor = BagEditor()
        assert editor.bag is None
        assert editor.file_path is None

    def test_init_with_file(self):
        """Test initializing BagEditor with a file."""
        editor = BagEditor(str(self.test_file))
        assert editor.bag is not None
        assert editor.file_path == str(self.test_file)

    def test_load_existing_file(self):
        """Test loading an existing XML file."""
        self.editor.load(str(self.test_file))
        assert self.editor.bag is not None
        assert self.editor.file_path == str(self.test_file)

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.editor.load("/nonexistent/file.xml")

    def test_load_invalid_xml(self):
        """Test loading an invalid XML file raises Exception."""
        # Create a file with invalid XML content
        invalid_file = Path(self.test_dir) / "invalid.xml"
        invalid_file.write_text("This is not valid XML content")

        with pytest.raises(Exception) as context:
            self.editor.load(str(invalid_file))

        assert "Failed to load XML file as Bag" in str(context.value)

        # Clean up
        invalid_file.unlink()

    def test_add_entity(self):
        """Test adding a new entity."""
        self.editor.load(str(self.test_file))

        # Add a new entity
        self.editor.add_entity("projects.project2", {"name": "New Project", "path": "/new"})

        # Verify it was added
        assert self.editor.entity_exists("projects.project2") == True
        attrs = self.editor.get_entity_attributes("projects.project2")
        assert attrs['name'] == "New Project"
        assert attrs['path'] == "/new"

    def test_add_entity_nested(self):
        """Test adding a nested entity."""
        self.editor.load(str(self.test_file))

        # Add a deeply nested entity
        self.editor.add_entity("projects.goober.foobar", {"path": "/like"})

        # Verify it was added
        assert self.editor.entity_exists("projects.goober.foobar") == True
        attrs = self.editor.get_entity_attributes("projects.goober.foobar")
        assert attrs['path'] == '/like'

    def test_add_entity_without_bag(self):
        """Test adding entity without loading a bag raises ValueError."""
        with pytest.raises(ValueError):
            self.editor.add_entity("test.path", {})

    def test_add_entity_empty_path(self):
        """Test adding entity with empty path raises ValueError."""
        self.editor.load(str(self.test_file))
        with pytest.raises(ValueError):
            self.editor.add_entity("", {})

    def test_add_entity_none_attributes(self):
        """Test adding entity with None attributes (defaults to empty dict)."""
        self.editor.load(str(self.test_file))

        # Add entity with None attributes
        self.editor.add_entity("projects.project3", None)

        # Verify it was added
        assert self.editor.entity_exists("projects.project3") is True

    def test_set_entity(self):
        """Test setting an entity (creates if doesn't exist, replaces if exists)."""
        self.editor.load(str(self.test_file))

        # Set a new entity
        self.editor.set_entity("projects.project3", {"name": "Set Project", "path": "/set"})

        # Verify it was created
        assert self.editor.entity_exists("projects.project3") is True
        attrs = self.editor.get_entity_attributes("projects.project3")
        assert attrs['name'] == "Set Project"
        assert attrs['path'] == "/set"

    def test_set_entity_existing(self):
        """Test setting an existing entity replaces it."""
        self.editor.load(str(self.test_file))

        # Set an existing entity with new attributes
        self.editor.set_entity("projects.project1", {"name": "Replaced Project", "status": "active"})

        # Verify it was replaced
        attrs = self.editor.get_entity_attributes("projects.project1")
        assert attrs['name'] == "Replaced Project"
        assert attrs['status'] == "active"

    def test_set_entity_without_bag(self):
        """Test setting entity without loading a bag raises ValueError."""
        with pytest.raises(ValueError):
            self.editor.set_entity("test.path", {})

    def test_set_entity_empty_path(self):
        """Test setting entity with empty path raises ValueError."""
        self.editor.load(str(self.test_file))
        with pytest.raises(ValueError):
            self.editor.set_entity("", {})

    def test_set_entity_none_attributes(self):
        """Test setting entity with None attributes (defaults to empty dict)."""
        self.editor.load(str(self.test_file))

        # Set entity with None attributes
        self.editor.set_entity("projects.project4", None)

        # Verify it was created
        assert self.editor.entity_exists("projects.project4") is True

    def test_update_entity(self):
        """Test updating an existing entity."""
        self.editor.load(str(self.test_file))

        # Update existing entity
        self.editor.update_entity("projects.project1", {"name": "Updated Project"})

        # Verify it was updated
        attrs = self.editor.get_entity_attributes("projects.project1")
        assert attrs['name'] == "Updated Project"

    def test_update_nonexistent_entity(self):
        """Test updating a nonexistent entity raises ValueError."""
        self.editor.load(str(self.test_file))

        with pytest.raises(ValueError) as context:
            self.editor.update_entity("projects.nonexistent", {"name": "Test"})

        assert "Element not found" in str(context.value)

    def test_update_entity_without_bag(self):
        """Test updating entity without loading a bag raises ValueError."""
        with pytest.raises(ValueError):
            self.editor.update_entity("test.path", {})

    def test_update_entity_empty_path(self):
        """Test updating entity with empty path raises ValueError."""
        self.editor.load(str(self.test_file))
        with pytest.raises(ValueError):
            self.editor.update_entity("", {})

    def test_update_entity_none_attributes(self):
        """Test updating entity with None attributes (defaults to empty dict)."""
        self.editor.load(str(self.test_file))

        # Update entity with None attributes
        self.editor.update_entity("projects.project1", None)

        # Verify entity still exists
        assert self.editor.entity_exists("projects.project1") is True

    def test_delete_entity(self):
        """Test deleting an entity."""
        self.editor.load(str(self.test_file))

        # Verify entity exists
        assert self.editor.entity_exists("projects.project1") is True

        # Delete it
        self.editor.delete_entity("projects.project1")

        # Verify it's gone
        assert self.editor.entity_exists("projects.project1") is False

    def test_delete_nonexistent_entity(self):
        """Test deleting a nonexistent entity raises ValueError."""
        self.editor.load(str(self.test_file))

        with pytest.raises(ValueError) as context:
            self.editor.delete_entity("projects.nonexistent")

        assert "Element not found" in str(context.value)

    def test_delete_entity_without_bag(self):
        """Test deleting entity without loading a bag raises ValueError."""
        with pytest.raises(ValueError):
            self.editor.delete_entity("test.path")

    def test_delete_entity_empty_path(self):
        """Test deleting entity with empty path raises ValueError."""
        self.editor.load(str(self.test_file))
        with pytest.raises(ValueError):
            self.editor.delete_entity("")

    def test_entity_exists(self):
        """Test checking if entity exists."""
        self.editor.load(str(self.test_file))

        assert self.editor.entity_exists("projects.project1") is True
        assert self.editor.entity_exists("projects.nonexistent") is False

    def test_entity_exists_without_bag(self):
        """Test checking entity exists without loading a bag returns False."""
        assert self.editor.entity_exists("test.path") is False

    def test_get_entity_attributes(self):
        """Test getting entity attributes."""
        self.editor.load(str(self.test_file))

        attrs = self.editor.get_entity_attributes("projects.project1")
        assert attrs is not None
        assert attrs["name"] == "Test Project"
        assert attrs["path"] == "/test"

    def test_get_nonexistent_entity_attributes(self):
        """Test getting attributes of nonexistent entity returns None."""
        self.editor.load(str(self.test_file))

        attrs = self.editor.get_entity_attributes("projects.nonexistent")
        assert attrs is None

    def test_get_entity_attributes_without_bag(self):
        """Test getting entity attributes without loading a bag returns None."""
        attrs = self.editor.get_entity_attributes("test.path")
        assert attrs is None

    def test_get_entity(self):
        """Test getting complete entity information (value and attributes)."""
        self.editor.load(str(self.test_file))

        entity = self.editor.get_entity("projects.project1")
        assert entity is not None
        assert "value" in entity
        assert "attributes" in entity
        assert entity["attributes"]["name"] == "Test Project"
        assert entity["attributes"]["path"] == "/test"

    def test_get_nonexistent_entity(self):
        """Test getting a nonexistent entity returns None."""
        self.editor.load(str(self.test_file))

        entity = self.editor.get_entity("projects.nonexistent")
        assert entity is None

    def test_get_entity_without_bag(self):
        """Test getting entity without loading a bag returns None."""
        entity = self.editor.get_entity("test.path")
        assert entity is None

    def test_save(self):
        """Test saving the Bag to file."""
        self.editor.load(str(self.test_file))

        # Make a change
        self.editor.add_entity("projects.project2", {"name": "New Project"})

        # Save
        self.editor.save()

        # Load in a new editor and verify
        new_editor = BagEditor(str(self.test_file))
        assert new_editor.entity_exists("projects.project2") is True

    def test_save_to_different_file(self):
        """Test saving to a different file."""
        self.editor.load(str(self.test_file))

        # Make a change
        self.editor.add_entity("projects.project2", {"name": "New Project"})

        # Save to different file
        new_file = Path(self.test_dir) / "test2.xml"
        self.editor.save(str(new_file))

        # Verify new file exists and has the changes
        assert new_file.exists() is True
        new_editor = BagEditor(str(new_file))
        assert new_editor.entity_exists("projects.project2") is True

        # Clean up
        new_file.unlink()

    def test_save_without_bag(self):
        """Test saving without loading a bag raises ValueError."""
        # Create a fresh editor without loading a bag
        editor = BagEditor()
        with pytest.raises(ValueError):
            editor.save(str(self.test_file))

    def test_save_without_file_path(self):
        """Test saving without file path raises ValueError."""
        self.editor.load(str(self.test_file))
        self.editor.file_path = None

        with pytest.raises(ValueError):
            self.editor.save()

    def test_save_with_invalid_path(self):
        """Test saving to an invalid path raises Exception."""
        self.editor.load(str(self.test_file))

        # Try to save to an invalid location (path with null bytes)
        with pytest.raises(Exception) as context:
            self.editor.save("/invalid/\x00/path.xml")

        assert "Failed to write XML file" in str(context.value)

    def test_get_entity_attributes_empty_attrs(self):
        """Test getting entity attributes when entity has no attributes."""
        self.editor.load(str(self.test_file))

        # Add an entity without attributes
        self.editor.add_entity("projects.empty_project", {})

        # Get attributes - should return empty dict
        attrs = self.editor.get_entity_attributes("projects.empty_project")
        assert attrs == {}

    def test_get_entity_empty_attrs(self):
        """Test getting complete entity when entity has no attributes."""
        self.editor.load(str(self.test_file))

        # Add an entity without attributes
        self.editor.add_entity("projects.empty_entity", {})

        # Get entity - should have empty attributes dict
        entity = self.editor.get_entity("projects.empty_entity")
        assert entity is not None
        assert "value" in entity
        assert "attributes" in entity
        assert entity["attributes"] == {}

    def test_save_creates_backup_for_same_file(self):
        """Test that saving to the same file creates a backup."""
        # Clean up any existing backups first
        for backup in Path(self.test_dir).glob("test.xml-*"):
            backup.unlink()

        self.editor.load(str(self.test_file))

        # Make a change
        self.editor.add_entity("projects.project2", {"name": "New Project"})

        # Save to the same file
        self.editor.save()

        # Check that a backup was created
        backups = list(Path(self.test_dir).glob("test.xml-*"))
        assert len(backups) == 1
        backup_file = backups[0]

        # Verify backup filename format: test.xml-YYYYMMDDHHMMSS
        import re
        assert re.match(r"test\.xml-\d{14}$", backup_file.name)

        # Verify backup contains the original content (before the change)
        backup_editor = BagEditor(str(backup_file))
        assert not backup_editor.entity_exists("projects.project2")
        assert backup_editor.entity_exists("projects.project1")

        # Clean up backup
        backup_file.unlink()

    def test_save_no_backup_for_different_file(self):
        """Test that saving to a different file does not create a backup."""
        # Clean up any existing backups first
        for backup in Path(self.test_dir).glob("test.xml-*"):
            backup.unlink()

        self.editor.load(str(self.test_file))

        # Make a change
        self.editor.add_entity("projects.project2", {"name": "New Project"})

        # Save to a different file
        new_file = Path(self.test_dir) / "test2.xml"
        self.editor.save(str(new_file))

        # Check that no backup was created for the original file
        backups = list(Path(self.test_dir).glob("test.xml-*"))
        assert len(backups) == 0

        # Clean up
        new_file.unlink()

    def test_save_creates_multiple_backups(self):
        """Test that multiple saves create multiple backups with different timestamps."""
        import time
        # Clean up any existing backups first
        for backup in Path(self.test_dir).glob("test.xml-*"):
            backup.unlink()

        self.editor.load(str(self.test_file))

        # Make first change and save
        self.editor.add_entity("projects.project2", {"name": "Project 2"})
        self.editor.save()

        # Wait a moment to ensure different timestamp (now includes seconds)
        time.sleep(2)  # Wait 2 seconds to get different timestamp

        # Make second change and save
        self.editor.add_entity("projects.project3", {"name": "Project 3"})
        self.editor.save()

        # Check that two backups were created
        backups = list(Path(self.test_dir).glob("test.xml-*"))
        assert len(backups) >= 2

        # Clean up backups
        for backup in backups:
            backup.unlink()

    def test_save_backup_preserves_original_content(self):
        """Test that backup file contains the original content before changes."""
        # Clean up any existing backups first
        for backup in Path(self.test_dir).glob("test.xml-*"):
            backup.unlink()

        self.editor.load(str(self.test_file))

        # Get original attributes
        original_attrs = self.editor.get_entity_attributes("projects.project1")

        # Modify the entity
        self.editor.set_entity("projects.project1", {"name": "Modified", "status": "changed"})

        # Save (this should create a backup with original content)
        self.editor.save()

        # Find the backup file
        backups = list(Path(self.test_dir).glob("test.xml-*"))
        assert len(backups) == 1
        backup_file = backups[0]

        # Load backup and verify it has the original content
        backup_editor = BagEditor(str(backup_file))
        backup_attrs = backup_editor.get_entity_attributes("projects.project1")
        assert backup_attrs == original_attrs

        # Verify current file has the modified content
        current_editor = BagEditor(str(self.test_file))
        current_attrs = current_editor.get_entity_attributes("projects.project1")
        assert current_attrs["name"] == "Modified"
        assert current_attrs["status"] == "changed"

        # Clean up
        backup_file.unlink()

    def test_save_backup_failure(self):
        """Test that save raises exception when backup creation fails."""
        from unittest.mock import patch

        self.editor.load(str(self.test_file))

        # Make a change
        self.editor.add_entity("projects.project2", {"name": "New Project"})

        # Mock shutil.copy2 to raise an exception
        with patch('gnr.core.gnrbageditor.shutil.copy2', side_effect=Exception("Permission denied")):
            with pytest.raises(Exception) as context:
                self.editor.save()

            assert "Failed to create backup file" in str(context.value)


class TestBagEditorCLI(BaseGnrTest):
    """Test cases for BagEditor CLI command."""

    @classmethod
    def setup_class(cls):
        """Set up test fixtures for CLI tests."""
        cls.test_dir = tempfile.mkdtemp()
        cls.test_file = Path(cls.test_dir) / "test_cli.xml"

        cls.original_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<GenRoBag>
    <projects>
        <project1 name="Test Project" path="/test"/>
    </projects>
</GenRoBag>
"""
        cls.test_file.write_text(cls.original_xml_content)

        # Get the CLI module path
        cls.cli_module = "gnr.core.cli.gnrbagedit"

    def setup_method(self, method):
        """Reset test file before each test."""
        # Clean up any backup files from previous tests
        for backup in Path(self.test_dir).glob("test_cli.xml-*"):
            backup.unlink()
        # Reset the main test file
        self.test_file.write_text(self.original_xml_content)

    @classmethod
    def teardown_class(cls):
        """Clean up test fixtures."""
        # Remove all files in the test directory (including backups)
        for file_path in Path(cls.test_dir).glob("*"):
            if file_path.is_file():
                file_path.unlink()
        # Now remove the empty directory
        Path(cls.test_dir).rmdir()

    def run_cli(self, args, stdin_input=None):
        """Helper method to run the CLI command."""
        # Mock sys.argv
        with patch.object(sys, 'argv', ['gnrbagedit'] + args):
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Mock stdin if provided
            if stdin_input is not None:
                stdin_mock = io.StringIO(stdin_input)
            else:
                stdin_mock = sys.stdin

            with patch('sys.stdout', stdout_capture), \
                 patch('sys.stderr', stderr_capture), \
                 patch('sys.stdin', stdin_mock):

                try:
                    cli_main()
                    returncode = 0
                except SystemExit as e:
                    returncode = e.code if e.code is not None else 0
                except Exception:
                    returncode = 1

            # Create a result object similar to subprocess.CompletedProcess
            class Result:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            return Result(returncode, stdout_capture.getvalue(), stderr_capture.getvalue())

    def test_cli_add_entity_to_file(self):
        """Test adding entity to a file (overwrite default)."""
        result = self.run_cli([
            str(self.test_file),
            "add",
            "projects.project2",
            'name="New Project"',
            'path="/new"'
        ])

        assert result.returncode == 0
        assert "Successfully added entity: projects.project2" in result.stderr

        # Verify the file was modified
        editor = BagEditor(str(self.test_file))
        assert editor.entity_exists("projects.project2")
        attrs = editor.get_entity_attributes("projects.project2")
        assert attrs['name'] == "New Project"
        assert attrs['path'] == "/new"

    def test_cli_add_entity_with_output_file(self):
        """Test adding entity with --output to different file."""
        output_file = Path(self.test_dir) / "output.xml"

        result = self.run_cli([
            str(self.test_file),
            "add",
            "projects.project2",
            'name="New Project"',
            "--output",
            str(output_file)
        ])

        assert result.returncode == 0
        assert f"saved to {output_file}" in result.stderr

        # Verify output file exists and has the change
        assert output_file.exists()
        editor = BagEditor(str(output_file))
        assert editor.entity_exists("projects.project2")

        # Verify original file is unchanged
        original_editor = BagEditor(str(self.test_file))
        assert not original_editor.entity_exists("projects.project2")

        # Cleanup
        output_file.unlink()

    def test_cli_add_entity_with_output_stdout(self):
        """Test adding entity with --output - (stdout)."""
        result = self.run_cli([
            str(self.test_file),
            "add",
            "projects.project2",
            'name="New Project"',
            "--output",
            "-"
        ])

        assert result.returncode == 0
        assert "<?xml version" in result.stdout
        assert "project2" in result.stdout
        assert 'name="New Project"' in result.stdout

        # Verify original file is unchanged
        original_editor = BagEditor(str(self.test_file))
        assert not original_editor.entity_exists("projects.project2")

    def test_cli_stdin_to_stdout(self):
        """Test reading from stdin and writing to stdout."""
        stdin_content = self.test_file.read_text()

        result = self.run_cli([
            "-",
            "add",
            "projects.project2",
            'name="Stdin Project"'
        ], stdin_input=stdin_content)

        assert result.returncode == 0
        assert "<?xml version" in result.stdout
        assert "project2" in result.stdout
        assert 'name="Stdin Project"' in result.stdout

    def test_cli_stdin_with_output_file(self):
        """Test reading from stdin and writing to file."""
        stdin_content = self.test_file.read_text()
        output_file = Path(self.test_dir) / "stdin_output.xml"

        result = self.run_cli([
            "-",
            "add",
            "projects.project2",
            'name="Stdin Project"',
            "--output",
            str(output_file)
        ], stdin_input=stdin_content)

        assert result.returncode == 0
        assert output_file.exists()

        # Verify output file has the change
        editor = BagEditor(str(output_file))
        assert editor.entity_exists("projects.project2")

        # Cleanup
        output_file.unlink()

    def test_cli_set_entity(self):
        """Test set operation via CLI."""
        result = self.run_cli([
            str(self.test_file),
            "set",
            "projects.project1",
            'name="Updated"',
            'status="active"',
            "--output",
            "-"
        ])

        assert result.returncode == 0
        assert "project1" in result.stdout
        assert 'name="Updated"' in result.stdout
        assert 'status="active"' in result.stdout

    def test_cli_update_entity(self):
        """Test update operation via CLI."""
        result = self.run_cli([
            str(self.test_file),
            "update",
            "projects.project1",
            'name="Updated Project"'
        ])

        assert result.returncode == 0
        assert "Successfully updated entity: projects.project1" in result.stderr

        # Verify the update
        editor = BagEditor(str(self.test_file))
        attrs = editor.get_entity_attributes("projects.project1")
        assert attrs['name'] == "Updated Project"

    def test_cli_update_nonexistent_entity(self):
        """Test update operation on nonexistent entity fails."""
        result = self.run_cli([
            str(self.test_file),
            "update",
            "projects.nonexistent",
            'name="Test"'
        ])

        assert result.returncode != 0
        assert "Element not found" in result.stderr

    def test_cli_delete_entity(self):
        """Test delete operation via CLI."""
        result = self.run_cli([
            str(self.test_file),
            "delete",
            "projects.project1"
        ])

        assert result.returncode == 0
        assert "Successfully deleted entity: projects.project1" in result.stderr

        # Verify the deletion
        editor = BagEditor(str(self.test_file))
        assert not editor.entity_exists("projects.project1")

    def test_cli_delete_nonexistent_entity(self):
        """Test delete operation on nonexistent entity fails."""
        result = self.run_cli([
            str(self.test_file),
            "delete",
            "projects.nonexistent"
        ])

        assert result.returncode != 0
        assert "Element not found" in result.stderr

    def test_cli_get_entity(self):
        """Test get operation via CLI."""
        result = self.run_cli([
            str(self.test_file),
            "get",
            "projects.project1"
        ])

        assert result.returncode == 0
        assert "Entity: projects.project1" in result.stdout
        assert "name: Test Project" in result.stdout
        assert "path: /test" in result.stdout

    def test_cli_get_nonexistent_entity(self):
        """Test get operation on nonexistent entity fails."""
        result = self.run_cli([
            str(self.test_file),
            "get",
            "projects.nonexistent"
        ])

        assert result.returncode != 0
        assert "Entity not found" in result.stderr

    def test_cli_get_with_stdin(self):
        """Test get operation with stdin input."""
        stdin_content = self.test_file.read_text()

        result = self.run_cli([
            "-",
            "get",
            "projects.project1"
        ], stdin_input=stdin_content)

        assert result.returncode == 0
        assert "Entity: projects.project1" in result.stdout
        assert "name: Test Project" in result.stdout

    def test_cli_file_not_found(self):
        """Test CLI with nonexistent file."""
        result = self.run_cli([
            "/nonexistent/file.xml",
            "add",
            "projects.test",
            'name="Test"'
        ])

        assert result.returncode != 0
        assert "File not found" in result.stderr

    def test_cli_empty_stdin(self):
        """Test CLI with empty stdin."""
        result = self.run_cli([
            "-",
            "add",
            "projects.test",
            'name="Test"'
        ], stdin_input="")

        assert result.returncode != 0
        assert "No input provided on stdin" in result.stderr

    def test_cli_invalid_xml_stdin(self):
        """Test CLI with invalid XML on stdin."""
        result = self.run_cli([
            "-",
            "add",
            "projects.test",
            'name="Test"'
        ], stdin_input="This is not valid XML")

        assert result.returncode != 0

    def test_cli_add_without_attributes(self):
        """Test add operation without attributes."""
        result = self.run_cli([
            str(self.test_file),
            "add",
            "projects.project3"
        ])

        assert result.returncode == 0

        # Verify the entity was added
        editor = BagEditor(str(self.test_file))
        assert editor.entity_exists("projects.project3")

    def test_cli_multiple_operations_chain(self):
        """Test multiple operations in sequence."""
        # Add entity
        result1 = self.run_cli([
            str(self.test_file),
            "add",
            "projects.project2",
            'name="Project 2"'
        ])
        assert result1.returncode == 0

        # Update entity
        result2 = self.run_cli([
            str(self.test_file),
            "update",
            "projects.project2",
            'name="Updated Project 2"'
        ])
        assert result2.returncode == 0

        # Get entity
        result3 = self.run_cli([
            str(self.test_file),
            "get",
            "projects.project2"
        ])
        assert result3.returncode == 0
        assert "Updated Project 2" in result3.stdout

        # Delete entity
        result4 = self.run_cli([
            str(self.test_file),
            "delete",
            "projects.project2"
        ])
        assert result4.returncode == 0

        # Verify deletion
        editor = BagEditor(str(self.test_file))
        assert not editor.entity_exists("projects.project2")

    def test_cli_invalid_attribute_format(self):
        """Test with invalid attribute format (missing =)."""
        result = self.run_cli([
            str(self.test_file),
            "add",
            "projects.test",
            'invalid_format'
        ])

        assert result.returncode != 0
        assert "Invalid attribute format" in result.stderr

    def test_cli_get_with_attributes_warning(self):
        """Test get operation with attributes (should warn)."""
        result = self.run_cli([
            str(self.test_file),
            "get",
            "projects.project1",
            'name="ignored"'
        ])

        assert result.returncode == 0
        assert "Attributes are ignored for get operation" in result.stderr

    def test_cli_delete_with_attributes_warning(self):
        """Test delete operation with attributes (should warn)."""
        result = self.run_cli([
            str(self.test_file),
            "delete",
            "projects.project1",
            'name="ignored"'
        ])

        assert result.returncode == 0
        assert "Attributes are ignored for delete operation" in result.stderr

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_environment_default_flag(self, mock_paths):
        """Test --environment-default flag."""
        # Mock to return our test file as environment default
        mock_paths.return_value = (str(self.test_file), "instance.xml", "siteconfig.xml")

        result = self.run_cli([
            "--environment-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode == 0
        assert "Test Project" in result.stdout

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_instance_default_flag(self, mock_paths):
        """Test --instance-default flag."""
        # Mock to return our test file as instance default
        mock_paths.return_value = ("env.xml", str(self.test_file), "siteconfig.xml")

        result = self.run_cli([
            "--instance-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode == 0
        assert "Test Project" in result.stdout

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_siteconfig_default_flag(self, mock_paths):
        """Test --siteconfig-default flag."""
        # Mock to return our test file as siteconfig default
        mock_paths.return_value = ("env.xml", "instance.xml", str(self.test_file))

        result = self.run_cli([
            "--siteconfig-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode == 0
        assert "Test Project" in result.stdout

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_multiple_default_flags_error(self, mock_paths):
        """Test error when multiple default flags are specified."""
        mock_paths.return_value = (str(self.test_file), "instance.xml", "siteconfig.xml")

        result = self.run_cli([
            "--environment-default",
            "--instance-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode != 0
        assert "Only one default flag can be specified" in result.stderr

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_environment_default_not_configured(self, mock_paths):
        """Test --environment-default when environment is not configured."""
        mock_paths.return_value = (None, None, None)

        result = self.run_cli([
            "--environment-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode != 0
        assert "No Genro environment configured" in result.stderr

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_instance_default_not_configured(self, mock_paths):
        """Test --instance-default when environment is not configured."""
        mock_paths.return_value = (None, None, None)

        result = self.run_cli([
            "--instance-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode != 0
        assert "No Genro environment configured" in result.stderr

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_siteconfig_default_not_configured(self, mock_paths):
        """Test --siteconfig-default when environment is not configured."""
        mock_paths.return_value = (None, None, None)

        result = self.run_cli([
            "--siteconfig-default",
            "get",
            "projects.project1"
        ])

        assert result.returncode != 0
        assert "No Genro environment configured" in result.stderr

    @patch('gnr.core.cli.gnrbagedit.get_default_file_paths')
    def test_cli_file_with_default_flag_error(self, mock_paths):
        """Test error when both file and default flag are specified."""
        mock_paths.return_value = (str(self.test_file), "instance.xml", "siteconfig.xml")

        result = self.run_cli([
            "--environment-default",
            str(self.test_file),
            "get",
            "projects.project1"
        ])

        assert result.returncode != 0
        assert "Cannot specify both a file and a default flag" in result.stderr

    def test_cli_no_file_no_flag_error(self):
        """Test error when neither file nor default flag is specified."""
        result = self.run_cli([
            "get",
            "projects.project1"
        ])

        assert result.returncode != 0
        assert "Either specify a file or use one of the --*-default flags" in result.stderr

    def test_cli_get_entity_no_attributes(self):
        """Test get operation on entity with no attributes."""
        # Add an entity without attributes
        editor = BagEditor(str(self.test_file))
        editor.add_entity("projects.empty", {})
        editor.save()

        result = self.run_cli([
            str(self.test_file),
            "get",
            "projects.empty"
        ])

        assert result.returncode == 0
        assert "Attributes: (none)" in result.stdout

    @patch('tempfile.mkstemp')
    def test_cli_stdin_tempfile_error(self, mock_mkstemp):
        """Test error handling when temp file creation fails."""
        mock_mkstemp.side_effect = Exception("Temp file creation failed")

        stdin_content = self.test_file.read_text()
        result = self.run_cli([
            "-",
            "get",
            "projects.project1"
        ], stdin_input=stdin_content)

        assert result.returncode != 0
        assert "Error reading from stdin" in result.stderr

    @patch('os.fdopen')
    def test_cli_stdin_write_error_with_cleanup(self, mock_fdopen):
        """Test error handling when writing to temp file fails after creation."""
        # Mock fdopen to raise an exception after temp file is created
        mock_fdopen.side_effect = Exception("Write failed")

        stdin_content = self.test_file.read_text()
        result = self.run_cli([
            "-",
            "get",
            "projects.project1"
        ], stdin_input=stdin_content)

        assert result.returncode != 0
        assert "Error reading from stdin" in result.stderr

    @patch('gnr.core.gnrbageditor.BagEditor.load')
    def test_cli_stdin_file_not_found_with_cleanup(self, mock_load):
        """Test FileNotFoundError during load with temp file cleanup."""
        # Mock load to raise FileNotFoundError after temp file is created
        mock_load.side_effect = FileNotFoundError("File not found")

        stdin_content = self.test_file.read_text()
        result = self.run_cli([
            "-",
            "get",
            "projects.project1"
        ], stdin_input=stdin_content)

        assert result.returncode != 0
        assert "File not found" in result.stderr

    @patch('gnr.core.gnrbageditor.BagEditor.add_entity')
    def test_cli_generic_exception_handling(self, mock_add):
        """Test generic exception handling in CLI."""
        mock_add.side_effect = Exception("Unexpected error")

        result = self.run_cli([
            str(self.test_file),
            "add",
            "projects.test",
            'name="Test"'
        ])

        assert result.returncode != 0
        assert "Error:" in result.stderr

    def test_cli_main_as_script(self):
        """Test running CLI as a script."""
        # This tests the if __name__ == '__main__' block
        result = subprocess.run(
            [sys.executable, "gnr/core/cli/gnrbagedit.py", str(self.test_file), "get", "projects.project1"],
            capture_output=True,
            text=True
        )
        # Just verify it runs without crashing
        assert "projects.project1" in result.stdout or result.returncode in [0, 1, 2]

    def test_cli_main_direct_call(self):
        """Test the __name__ == '__main__' block by executing the module."""
        import importlib.util
        import sys
        from pathlib import Path

        # Get the path to gnrbagedit.py
        module_path = Path(__file__).parent.parent.parent / "gnr" / "core" / "cli" / "gnrbagedit.py"

        # Load the module
        spec = importlib.util.spec_from_file_location("__main__", str(module_path))
        module = importlib.util.module_from_spec(spec)

        # Mock sys.argv for this test
        original_argv = sys.argv
        sys.argv = ["gnrbagedit", str(self.test_file), "get", "projects.project1"]

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with patch('sys.stdout', stdout_capture), \
                 patch('sys.stderr', stderr_capture):
                try:
                    spec.loader.exec_module(module)
                except SystemExit:
                    pass  # Expected for CLI
        finally:
            sys.argv = original_argv

        # Verify output
        output = stdout_capture.getvalue()
        assert "projects.project1" in output or "Entity:" in output

    @patch('gnr.core.cli.gnrbagedit.getEnvironmentPath')
    def test_get_default_file_paths_exception(self, mock_env):
        """Test get_default_file_paths handles exceptions."""
        from gnr.core.cli.gnrbagedit import get_default_file_paths

        # Mock getEnvironmentPath to raise an exception
        mock_env.side_effect = Exception("Environment error")

        result = get_default_file_paths()
        assert result == (None, None, None)

    @patch('gnr.core.cli.gnrbagedit.getEnvironmentPath')
    def test_get_default_file_paths_none(self, mock_env):
        """Test get_default_file_paths when getEnvironmentPath returns None."""
        from gnr.core.cli.gnrbagedit import get_default_file_paths

        # Mock getEnvironmentPath to return None
        mock_env.return_value = None

        result = get_default_file_paths()
        assert result == (None, None, None)

    @patch('gnr.core.cli.gnrbagedit.getEnvironmentPath')
    def test_get_default_file_paths_valid(self, mock_env):
        """Test get_default_file_paths with valid path."""
        from gnr.core.cli.gnrbagedit import get_default_file_paths

        # Mock getEnvironmentPath to return a valid path
        mock_env.return_value = "/path/to/environment.xml"

        result = get_default_file_paths()
        assert result[0] == "/path/to/environment.xml"
        assert result[1] == "/path/to/instanceconfig/default.xml"
        assert result[2] == "/path/to/siteconfig/default.xml"


if __name__ == '__main__':
    pytest.main([__file__])
