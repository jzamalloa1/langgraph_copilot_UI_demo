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

# In-memory metadata store (no base64, just references)
_session_images: dict[str, dict] = {}


def _store_image_metadata(image_id: str, metadata: dict):
    """Store image metadata in session memory."""
    _session_images[image_id] = metadata


def _get_image_metadata(image_id: str) -> dict | None:
    """Retrieve image metadata from session memory."""
    return _session_images.get(image_id)


def _list_image_metadata() -> list[dict]:
    """List all stored image metadata."""
    return [{"image_id": k, **v} for k, v in _session_images.items()]


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
