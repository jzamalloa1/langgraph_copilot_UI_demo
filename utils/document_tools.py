"""
Document processing tools using LlamaCloud.

Provides tools for parsing uploaded documents and querying their content
using LlamaCloud's managed vector store and retrieval services.
"""

import os
from pathlib import Path
from langchain_core.tools import tool


# Directory where uploaded files are stored
UPLOAD_DIR = Path("/tmp/uploads")

# In-memory index registry (maps file_id to LlamaCloudIndex instance)
_document_indexes: dict[str, any] = {}


def _get_llama_cloud_api_key() -> str:
    """Get the LlamaCloud API key from environment."""
    api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY environment variable not set")
    return api_key


@tool(parse_docstring=True)
def parse_document(file_id: str, filename: str) -> dict:
    """Parse and index an uploaded document using LlamaCloud.

    This tool parses the document using LlamaParse and creates a searchable
    vector index in LlamaCloud for later querying.

    Args:
        file_id: The unique identifier for the uploaded file (from upload API)
        filename: Original filename for display purposes

    Returns:
        Dictionary with index_id on success, or error message on failure
    """
    try:
        api_key = _get_llama_cloud_api_key()
    except ValueError as e:
        return {"type": "error", "message": str(e)}

    # Find the uploaded file
    matching_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matching_files:
        return {
            "type": "error",
            "message": f"File with id '{file_id}' not found in {UPLOAD_DIR}",
        }

    file_path = matching_files[0]

    try:
        from llama_cloud_services import LlamaParse, LlamaCloudIndex

        # Parse the document with LlamaParse
        parser = LlamaParse(api_key=api_key)
        documents = parser.load_data(str(file_path))

        if not documents:
            return {
                "type": "error",
                "message": f"No content extracted from document '{filename}'",
            }

        # Create a unique index name based on file_id
        index_name = f"doc_{file_id}"

        # Create LlamaCloudIndex which handles all the complexity
        # This creates the pipeline, embeds documents, and stores them
        index = LlamaCloudIndex.from_documents(
            documents,
            name=index_name,
            project_name="Default",  # Use existing Default project
            api_key=api_key,
        )

        # Store index instance for later querying
        _document_indexes[file_id] = {
            "index": index,
            "index_name": index_name,
            "filename": filename,
            "num_documents": len(documents),
            "document_text": documents[0].text if documents else "",
        }

        return {
            "type": "document_indexed",
            "status": "success",
            "index_id": file_id,
            "filename": filename,
            "chunks_created": len(documents),
            "message": f"Document '{filename}' has been parsed and indexed. You can now query it using query_document.",
        }

    except ImportError as e:
        return {
            "type": "error",
            "message": f"LlamaCloud libraries not installed: {e}. Run: pip install llama-cloud-services llama-cloud",
        }
    except Exception as e:
        return {"type": "error", "message": f"Failed to parse document: {str(e)}"}


@tool(parse_docstring=True)
def query_document(query: str, index_id: str) -> dict:
    """Search an indexed document for information relevant to the query.

    Args:
        query: The question or search query about the document content
        index_id: The index_id returned from parse_document (same as file_id)

    Returns:
        Dictionary with retrieved passages and their relevance scores
    """
    # Check if we have this index in memory
    index_info = _document_indexes.get(index_id)
    if not index_info:
        return {
            "type": "error",
            "message": f"No indexed document found with id '{index_id}'. Make sure to call parse_document first.",
        }

    try:
        # Get the stored index and create a retriever
        index = index_info["index"]
        retriever = index.as_retriever(similarity_top_k=5)

        # Retrieve relevant nodes
        nodes = retriever.retrieve(query)

        # Extract results
        results = []
        for node in nodes:
            results.append(
                {
                    "text": node.text,
                    "score": node.score if hasattr(node, "score") else 0.0,
                    "metadata": node.metadata if hasattr(node, "metadata") else {},
                }
            )

        return {
            "type": "query_results",
            "status": "success",
            "index_id": index_id,
            "filename": index_info["filename"],
            "query": query,
            "num_results": len(results),
            "results": results,
        }

    except Exception as e:
        return {"type": "error", "message": f"Failed to query document: {str(e)}"}


@tool(parse_docstring=True)
def list_document_indexes() -> dict:
    """List all documents that have been indexed in the current session.

    Returns:
        Dictionary with list of indexed documents and their metadata
    """
    indexes = []
    for file_id, info in _document_indexes.items():
        indexes.append(
            {
                "index_id": file_id,
                "filename": info["filename"],
                "num_chunks": info.get("num_documents", 0),
            }
        )

    return {
        "type": "index_list",
        "count": len(indexes),
        "indexes": indexes,
    }


@tool(parse_docstring=True)
def list_uploaded_files() -> dict:
    """List all files that have been uploaded and are available for analysis.

    Call this tool FIRST when the user asks about "the document", "this file",
    wants to "summarize it", or asks any question about an uploaded document.
    This will show you what files are available with their file_id and filename.

    Returns:
        Dictionary with list of uploaded files ready for parsing
    """
    if not UPLOAD_DIR.exists():
        return {
            "type": "upload_list",
            "count": 0,
            "files": [],
            "message": "No files have been uploaded yet.",
        }

    files = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            # Extract file_id from filename (format: {file_id}.{ext})
            filename = file_path.name
            file_id = file_path.stem  # filename without extension
            extension = file_path.suffix

            files.append({
                "file_id": file_id,
                "filename": filename,
                "extension": extension,
                "size": file_path.stat().st_size,
                "path": str(file_path),
            })

    if files:
        # Sort by modification time, newest first
        files.sort(key=lambda f: Path(f["path"]).stat().st_mtime, reverse=True)
        most_recent = files[0]
        message = f"Found {len(files)} uploaded file(s). Most recent: '{most_recent['filename']}' (file_id: {most_recent['file_id']}). Use parse_document with this file_id to analyze it."
    else:
        message = "No files have been uploaded yet."

    return {
        "type": "upload_list",
        "count": len(files),
        "files": files,
        "message": message,
    }
