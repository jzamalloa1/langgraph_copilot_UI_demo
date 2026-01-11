#!/usr/bin/env python3
"""
Render tabular data as a styled HTML table.
Saves the table to a specified output file as JSON (for frontend rendering).
"""

import sys
import json


def render_table(columns, rows, output_file, title="Data Table", caption=None):
    """
    Create a JSON representation of tabular data for frontend rendering.

    Args:
        columns: List of column header strings
        rows: List of row data (each row is a list of values)
        output_file: Path where the table JSON should be saved
        title: Table title
        caption: Optional table caption/description
    """
    # Validate data
    if not columns:
        raise ValueError("columns cannot be empty")
    if not rows:
        raise ValueError("rows cannot be empty")

    num_cols = len(columns)
    for i, row in enumerate(rows):
        if len(row) != num_cols:
            raise ValueError(f"Row {i} has {len(row)} values but expected {num_cols} columns")

    # Convert all values to strings for consistent rendering
    string_rows = [[str(val) if val is not None else "" for val in row] for row in rows]

    # Create the table data structure
    table_data = {
        "title": title,
        "caption": caption,
        "columns": columns,
        "rows": string_rows,
        "row_count": len(rows),
        "column_count": num_cols,
    }

    # Save as JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(table_data, f, indent=2, ensure_ascii=False)

    print(f"Table saved to: {output_file}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python render_table.py <config_json>")
        print("\nConfig JSON should contain:")
        print('  {"columns": [...], "rows": [[...], [...]], "output_file": "...", '
              '"title": "...", "caption": "..."}')
        sys.exit(1)

    # Load configuration from JSON argument
    config = json.loads(sys.argv[1])

    columns = config["columns"]
    rows = config["rows"]
    output_file = config.get("output_file", "/tmp/tables/table.json")
    title = config.get("title", "Data Table")
    caption = config.get("caption")

    render_table(columns, rows, output_file, title, caption)


if __name__ == "__main__":
    main()
