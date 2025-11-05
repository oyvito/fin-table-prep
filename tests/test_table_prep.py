"""
Tests for the table_prep module.
"""

import pytest
import pandas as pd
import tempfile
import os
from fin_table_prep.table_prep import TablePrep


class TestTablePrep:
    """Test cases for TablePrep class."""

    def test_init(self):
        """Test TablePrep initialization."""
        prep = TablePrep()
        assert prep.config == {}

    def test_load_csv_data(self):
        """Test loading CSV data."""
        prep = TablePrep()

        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("col1,col2,col3\n")
            f.write("1,2,3\n")
            f.write("4,5,6\n")
            temp_path = f.name

        try:
            df = prep.load_data(temp_path)
            assert len(df) == 2
            assert list(df.columns) == ["col1", "col2", "col3"]
            assert df.iloc[0]["col1"] == 1
        finally:
            os.unlink(temp_path)

    def test_load_unsupported_format(self):
        """Test that unsupported formats raise an error."""
        prep = TablePrep()

        with pytest.raises(ValueError, match="Unsupported file format"):
            prep.load_data("test.txt")

    def test_prepare_table_basic(self):
        """Test basic table preparation."""
        prep = TablePrep()

        # Create test data
        data = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6], "col3": [7, 8, 9]})

        config = {"columns": ["col1", "col2"]}
        result = prep.prepare_table(data, config)

        assert list(result.columns) == ["col1", "col2"]
        assert len(result) == 3

    def test_generate_script(self):
        """Test script generation."""
        prep = TablePrep()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            temp_path = f.name

        try:
            config = {"input_file": "test_data.csv"}
            script = prep.generate_script(config, temp_path)

            assert "import pandas as pd" in script
            assert "test_data.csv" in script
            assert os.path.exists(temp_path)

            with open(temp_path, "r") as f:
                content = f.read()
                assert content == script
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
