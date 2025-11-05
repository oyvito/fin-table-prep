"""
Command-line interface for fin-table-prep.
"""

import argparse
import json
import sys
from pathlib import Path
from fin_table_prep.table_prep import TablePrep


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Applikasjon for å generere python-script til statistikktabeller"
    )

    parser.add_argument("input", type=str, help="Input data file (CSV or Excel)")

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output_script.py",
        help="Output script file path (default: output_script.py)",
    )

    parser.add_argument(
        "-c", "--config", type=str, help="Configuration file for table preparation (JSON)"
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()

    # Validate input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    # Initialize TablePrep
    prep = TablePrep()

    # Load configuration if provided
    config = {}
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            print(f"Warning: Config file not found: {args.config}", file=sys.stderr)

    try:
        # Load data
        print(f"Loading data from {args.input}...")
        data = prep.load_data(args.input)
        print(f"Loaded {len(data)} rows")

        # Generate script
        print(f"Generating script to {args.output}...")
        config["input_file"] = args.input
        prep.generate_script(config, args.output)

        print(f"Successfully generated script: {args.output}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
