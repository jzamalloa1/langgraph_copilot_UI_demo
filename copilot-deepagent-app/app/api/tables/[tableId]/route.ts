import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

/**
 * API route to serve table data from /tmp/tables.
 *
 * The LangGraph agent saves table JSON to /tmp/tables with unique IDs.
 * This route reads and serves that data to the frontend.
 */

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ tableId: string }> }
) {
  const { tableId } = await params;

  // Sanitize tableId to prevent path traversal
  const sanitizedTableId = tableId.replace(/[^a-zA-Z0-9._-]/g, "");
  if (sanitizedTableId !== tableId) {
    return NextResponse.json(
      { error: "Invalid table ID" },
      { status: 400 }
    );
  }

  // Add .json extension if not present (table_id doesn't include extension)
  const tableFilename = sanitizedTableId.endsWith(".json")
    ? sanitizedTableId
    : `${sanitizedTableId}.json`;

  const tablePath = join("/tmp/tables", tableFilename);

  try {
    const tableContent = await readFile(tablePath, "utf-8");
    const tableData = JSON.parse(tableContent);

    return NextResponse.json(tableData, {
      headers: {
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (error) {
    console.error("Error reading table:", error);
    return NextResponse.json(
      { error: "Table not found" },
      { status: 404 }
    );
  }
}
