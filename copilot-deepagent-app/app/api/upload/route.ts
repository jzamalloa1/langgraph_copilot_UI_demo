import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { randomUUID } from "crypto";

/**
 * API route to handle document uploads.
 *
 * Receives files via FormData, saves them to /tmp/uploads with a unique ID,
 * and returns metadata for the LangGraph agent to process.
 */

const UPLOAD_DIR = "/tmp/uploads";

// Allowed file extensions for document processing
const ALLOWED_EXTENSIONS = new Set([
  ".pdf",
  ".docx",
  ".doc",
  ".txt",
  ".csv",
  ".xlsx",
  ".xls",
  ".pptx",
  ".ppt",
  ".html",
  ".htm",
  ".md",
]);

// Max file size: 50MB
const MAX_FILE_SIZE = 50 * 1024 * 1024;

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json(
        { error: "No file provided" },
        { status: 400 }
      );
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: `File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB` },
        { status: 400 }
      );
    }

    // Get file extension
    const originalName = file.name;
    const lastDot = originalName.lastIndexOf(".");
    const extension = lastDot !== -1 ? originalName.slice(lastDot).toLowerCase() : "";

    // Validate extension
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return NextResponse.json(
        {
          error: `Invalid file type. Allowed: ${Array.from(ALLOWED_EXTENSIONS).join(", ")}`,
        },
        { status: 400 }
      );
    }

    // Generate unique file ID
    const fileId = randomUUID().split("-")[0]; // Short UUID
    const savedFilename = `${fileId}${extension}`;

    // Ensure upload directory exists
    await mkdir(UPLOAD_DIR, { recursive: true });

    // Save file
    const filePath = join(UPLOAD_DIR, savedFilename);
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    await writeFile(filePath, buffer);

    // Return metadata for the agent
    return NextResponse.json({
      success: true,
      file_id: fileId,
      filename: originalName,
      saved_path: filePath,
      size: file.size,
      extension: extension,
      message: `File "${originalName}" uploaded successfully. Use file_id "${fileId}" for document analysis.`,
    });
  } catch (error) {
    console.error("Upload error:", error);
    return NextResponse.json(
      { error: "Failed to upload file" },
      { status: 500 }
    );
  }
}
