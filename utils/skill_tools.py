"""
Skill tools that encapsulate complete workflows.

Each skill tool handles its workflow internally (script execution, file handling).
The agent only needs to pass structured parameters.
Scripts are executed externally - their code is NOT loaded into context.
Images are stored on disk at /tmp/plots for frontend access, with metadata in memory.
"""

import json
import subprocess
import uuid
from pathlib import Path
from langchain_core.tools import tool


SCRIPTS_DIR = Path(__file__).parent / "scripts"
OUTPUT_DIR = Path("/tmp/plots")
TABLES_DIR = Path("/tmp/tables")

# In-memory metadata store (no base64, just references)
_session_images: dict[str, dict] = {}
_session_tables: dict[str, dict] = {}


def _store_image_metadata(image_id: str, metadata: dict):
    """Store image metadata in session memory."""
    _session_images[image_id] = metadata


def _get_image_metadata(image_id: str) -> dict | None:
    """Retrieve image metadata from session memory."""
    return _session_images.get(image_id)


def _list_image_metadata() -> list[dict]:
    """List all stored image metadata."""
    return [{"image_id": k, **v} for k, v in _session_images.items()]


def _store_table_metadata(table_id: str, metadata: dict):
    """Store table metadata in session memory."""
    _session_tables[table_id] = metadata


def _get_table_metadata(table_id: str) -> dict | None:
    """Retrieve table metadata from session memory."""
    return _session_tables.get(table_id)


@tool(parse_docstring=True)
def plot_historical_data(
    dates: list[str],
    values: list[float],
    title: str,
    ylabel: str = "Value",
) -> dict:
    """Create a plot from dates and values. Load skill 'historical-plotter' for usage details.

    Args:
        dates: Date strings
        values: Numeric values
        title: Plot title
        ylabel: Y-axis label

    Returns:
        Dictionary with image_id for retrieval and display
    """
    if not dates or not values:
        return {"type": "error", "message": "dates and values cannot be empty"}
    if len(dates) != len(values):
        return {"type": "error", "message": f"STOP: dates ({len(dates)}) and values ({len(values)}) length mismatch. Do NOT retry. Tell user the data could not be extracted correctly."}

    # Generate unique image ID (also used as filename)
    image_id = f"plot_{uuid.uuid4().hex[:8]}"
    filename = f"{image_id}.png"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename

    config = {
        "dates": dates,
        "values": values,
        "output_file": str(output_path),
        "title": title,
        "ylabel": ylabel,
    }

    script_path = SCRIPTS_DIR / "plot_historical_data.py"

    try:
        # Execute external script (script code NOT in context)
        result = subprocess.run(
            ["python3", str(script_path), json.dumps(config)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"type": "error", "message": result.stderr.strip()}

        # Verify the file was created
        if not output_path.exists():
            return {"type": "error", "message": f"Plot file was not created at {output_path}"}

        # Store metadata in session memory (NOT the image data)
        metadata = {
            "type": "image",
            "filename": filename,
            "path": str(output_path),
            "title": title,
            "description": f"Line plot with {len(dates)} data points",
        }
        _store_image_metadata(image_id, metadata)

        # Return response with instruction to display in UI
        return {
            "type": "image",
            "status": "success",
            "image_id": image_id,
            "title": title,
            "data_points": len(dates),
            "next_action": f"Call display_image(image_url='{image_id}', title='{title}') to show the plot in the UI."
        }

    except subprocess.TimeoutExpired:
        return {"type": "error", "message": "Plot generation timed out"}
    except FileNotFoundError as e:
        return {"type": "error", "message": f"Script or file not found: {e}"}
    except Exception as e:
        return {"type": "error", "message": str(e)}


@tool(parse_docstring=True)
def get_stored_image(image_id: str) -> dict:
    """Retrieve information about a stored image by its ID.

    Args:
        image_id: The ID of the image to retrieve (e.g., 'plot_abc123')

    Returns:
        Dictionary with image metadata or error
    """
    metadata = _get_image_metadata(image_id)
    if metadata:
        # Check if file still exists
        path = Path(metadata.get("path", ""))
        if path.exists():
            return {
                "type": "image",
                "status": "success",
                "image_id": image_id,
                **metadata
            }
        else:
            return {
                "type": "error",
                "message": f"Image file for '{image_id}' no longer exists on disk"
            }
    else:
        return {
            "type": "error",
            "message": f"Image '{image_id}' not found in session storage"
        }


@tool(parse_docstring=True)
def list_stored_images() -> dict:
    """List all images stored in the current session.

    Returns:
        Dictionary with list of stored images (id, title, description)
    """
    images = _list_image_metadata()

    # Return metadata only
    image_list = [
        {
            "image_id": img.get("image_id"),
            "title": img.get("title"),
            "description": img.get("description"),
        }
        for img in images
    ]

    return {
        "type": "image_list",
        "count": len(image_list),
        "images": image_list
    }


@tool(parse_docstring=True)
def plot_distribution_comparison(
    groups: list[dict],
    plot_type: str = "kde",
    title: str = "Distribution Comparison",
    xlabel: str = "Value",
    ylabel: str = "",
) -> dict:
    """Compare distributions of one or more data groups. Load skill 'distribution-comparison' for usage details.

    Args:
        groups: List of groups to compare. Each group is a dict with 'name' (str) and 'values' (list of floats).
        plot_type: Type of plot - 'histogram', 'kde', 'ecdf', 'violin', 'box', 'strip', 'swarm', or 'ridge'.
        title: Plot title
        xlabel: X-axis label (or value label for violin/box/strip/swarm)
        ylabel: Y-axis label (auto-generated if empty)

    Returns:
        Dictionary with image_id for retrieval and display
    """
    # Validate inputs
    if not groups:
        return {"type": "error", "message": "groups cannot be empty"}

    for i, group in enumerate(groups):
        if "name" not in group or "values" not in group:
            return {"type": "error", "message": f"Group {i} must have 'name' and 'values' keys"}
        if not group["values"]:
            return {"type": "error", "message": f"Group '{group['name']}' has empty values"}

    valid_plot_types = ["histogram", "kde", "ecdf", "violin", "box", "strip", "swarm", "ridge"]
    if plot_type not in valid_plot_types:
        return {"type": "error", "message": f"Invalid plot_type '{plot_type}'. Must be one of: {valid_plot_types}"}

    # Generate unique image ID
    image_id = f"dist_{uuid.uuid4().hex[:8]}"
    filename = f"{image_id}.png"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename

    config = {
        "groups": groups,
        "output_file": str(output_path),
        "plot_type": plot_type,
        "title": title,
        "xlabel": xlabel,
        "ylabel": ylabel if ylabel else None,
    }

    script_path = SCRIPTS_DIR / "plot_distribution_comparison.py"

    try:
        # Execute external script (script code NOT in context)
        result = subprocess.run(
            ["python3", str(script_path), json.dumps(config)],
            capture_output=True,
            text=True,
            timeout=60,  # Longer timeout for potentially large datasets
        )

        if result.returncode != 0:
            return {"type": "error", "message": result.stderr.strip()}

        # Verify the file was created
        if not output_path.exists():
            return {"type": "error", "message": f"Plot file was not created at {output_path}"}

        # Build description
        group_names = [g["name"] for g in groups]
        total_points = sum(len(g["values"]) for g in groups)

        # Store metadata in session memory
        metadata = {
            "type": "image",
            "filename": filename,
            "path": str(output_path),
            "title": title,
            "description": f"{plot_type.upper()} plot comparing {len(groups)} group(s): {', '.join(group_names)} ({total_points} total data points)",
        }
        _store_image_metadata(image_id, metadata)

        return {
            "type": "image",
            "status": "success",
            "image_id": image_id,
            "title": title,
            "plot_type": plot_type,
            "groups": len(groups),
            "total_data_points": total_points,
        }

    except subprocess.TimeoutExpired:
        return {"type": "error", "message": "Plot generation timed out (60s limit)"}
    except FileNotFoundError as e:
        return {"type": "error", "message": f"Script or file not found: {e}"}
    except Exception as e:
        return {"type": "error", "message": str(e)}


@tool(parse_docstring=True)
def display_table(
    columns: list[str],
    rows: list[list],
    title: str = "Data Table",
    caption: str = "",
) -> dict:
    """Display tabular data as a formatted table. Load skill 'table-display' for usage details.

    Args:
        columns: List of column header names
        rows: List of rows, where each row is a list of values (strings, numbers, etc.)
        title: Table title displayed above the table
        caption: Optional description or caption below the table

    Returns:
        Dictionary with table_id for retrieval and display
    """
    # Validate inputs
    if not columns:
        return {"type": "error", "message": "columns cannot be empty"}
    if not rows:
        return {"type": "error", "message": "rows cannot be empty"}

    num_cols = len(columns)
    for i, row in enumerate(rows):
        if len(row) != num_cols:
            return {
                "type": "error",
                "message": f"Row {i} has {len(row)} values but expected {num_cols} columns. Ensure all rows have the same number of values as columns.",
            }

    # Generate unique table ID
    table_id = f"table_{uuid.uuid4().hex[:8]}"
    filename = f"{table_id}.json"

    # Ensure output directory exists
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TABLES_DIR / filename

    config = {
        "columns": columns,
        "rows": rows,
        "output_file": str(output_path),
        "title": title,
        "caption": caption if caption else None,
    }

    script_path = SCRIPTS_DIR / "render_table.py"

    try:
        # Execute external script
        result = subprocess.run(
            ["python3", str(script_path), json.dumps(config)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {"type": "error", "message": result.stderr.strip()}

        # Verify the file was created
        if not output_path.exists():
            return {"type": "error", "message": f"Table file was not created at {output_path}"}

        # Store metadata in session memory
        metadata = {
            "type": "table",
            "filename": filename,
            "path": str(output_path),
            "title": title,
            "caption": caption,
            "description": f"Table with {len(columns)} columns and {len(rows)} rows",
        }
        _store_table_metadata(table_id, metadata)

        return {
            "type": "table",
            "status": "success",
            "table_id": table_id,
            "title": title,
            "columns": len(columns),
            "rows": len(rows),
        }

    except subprocess.TimeoutExpired:
        return {"type": "error", "message": "Table generation timed out"}
    except FileNotFoundError as e:
        return {"type": "error", "message": f"Script or file not found: {e}"}
    except Exception as e:
        return {"type": "error", "message": str(e)}
