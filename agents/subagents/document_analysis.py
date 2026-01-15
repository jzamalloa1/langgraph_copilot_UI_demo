"""
Document Analysis Sub-Agent

Responsible for parsing uploaded documents and answering questions about them.
Uses LlamaCloud for document parsing, indexing, and retrieval.
"""

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, SummarizationMiddleware

from utils.document_tools import parse_document, query_document, list_document_indexes, list_uploaded_files


DOCUMENT_ANALYSIS_PROMPT = """You are a document analysis specialist. Your job is to parse uploaded documents and answer questions about their content.

## Your Role
- Parse documents that users upload using LlamaCloud
- Answer questions about document content using semantic search
- Provide accurate, well-sourced answers based on retrieved passages

## Available Tools
- list_uploaded_files: ALWAYS call this FIRST to see what files are available for analysis
- parse_document: Parse and index an uploaded document (required before querying)
- query_document: Search an indexed document for relevant information
- list_document_indexes: See which documents have been indexed in this session

## CRITICAL WORKFLOW - ALWAYS FOLLOW THIS ORDER:

### Step 1: Discover Available Files
ALWAYS start by calling list_uploaded_files to see what files the user has uploaded.
This will give you the file_id and filename needed for parsing.

### Step 2: Parse the Document (if not already indexed)
Call parse_document with the file_id and filename from step 1.
Check list_document_indexes to see if it's already been indexed.

### Step 3: Query and Answer
Use query_document with the user's question and the index_id (same as file_id).
Synthesize a clear answer based on the retrieved passages.

## Important Rules
1. ALWAYS call list_uploaded_files FIRST to discover available files
2. Parse a document before trying to query it
3. Base your answers ONLY on retrieved content - do not make up information
4. If no files are uploaded, tell the user to upload a document first
5. After answering, return the response to the orchestrator

## Output Format
When answering questions:
- Provide a clear, direct answer
- Quote or reference specific passages when helpful
- Indicate confidence level if information is partial

After completing your task, return results to the orchestrator."""


def create_document_analysis_agent(model: str = "openai:gpt-4o-mini"):
    """Create the document analysis sub-agent.

    Args:
        model: Model identifier (default: gpt-4o-mini for efficiency)

    Returns:
        Compiled agent graph
    """
    return create_agent(
        model=model,
        system_prompt=DOCUMENT_ANALYSIS_PROMPT,
        tools=[list_uploaded_files, parse_document, query_document, list_document_indexes],
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="list_uploaded_files",
                run_limit=1,  # Only need to list files once
                exit_behavior="continue",  # Continue after listing
            ),
            ToolCallLimitMiddleware(
                tool_name="parse_document",
                run_limit=1,  # One document parse per request
                exit_behavior="continue",  # Continue to query after parsing
            ),
            ToolCallLimitMiddleware(
                tool_name="query_document",
                run_limit=3,  # Allow multiple queries for thorough answers
                exit_behavior="end",
            ),
            SummarizationMiddleware(
                model=model,
                trigger=("fraction", 0.75),
                keep=("fraction", 0.10),
            ),
        ],
        name="document_analysis_agent",
    )
