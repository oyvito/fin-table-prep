"""
Tests for the CLI module.
"""

import tempfile
import os
from fin_table_prep.cli import main
import sys


class TestCLI:
    """Test cases for CLI functionality."""

    def test_main_with_missing_file(self, monkeypatch):
        """Test CLI with non-existent input file."""
        monkeypatch.setattr(sys, "argv", ["fin-table-prep", "nonexistent.csv"])

        result = main()
        assert result == 1

    def test_main_with_valid_csv(self, monkeypatch, capsys):
        """Test CLI with valid CSV file."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("col1,col2\n")
            f.write("1,2\n")
            temp_csv = f.name

        # Create a temporary output file path
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            temp_output = f.name

        try:
            monkeypatch.setattr(sys, "argv", ["fin-table-prep", temp_csv, "-o", temp_output])

            result = main()
            assert result == 0

            # Check that output file was created
            assert os.path.exists(temp_output)

            # Check output messages
            captured = capsys.readouterr()
            assert "Loading data" in captured.out
            assert "Successfully generated script" in captured.out
        finally:
            if os.path.exists(temp_csv):
                os.unlink(temp_csv)
            if os.path.exists(temp_output):
                os.unlink(temp_output)
