import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

/**
 * API route to serve images from /tmp/plots.
 *
 * The LangGraph agent saves plot images to /tmp/plots with unique IDs.
 * This route reads and serves those images to the frontend.
 */

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ filename: string }> }
) {
  const { filename } = await params;

  // Sanitize filename to prevent path traversal
  const sanitizedFilename = filename.replace(/[^a-zA-Z0-9._-]/g, "");
  if (sanitizedFilename !== filename) {
    return NextResponse.json(
      { error: "Invalid filename" },
      { status: 400 }
    );
  }

  // Add .png extension if not present (image_id doesn't include extension)
  const imageFilename = sanitizedFilename.endsWith(".png")
    ? sanitizedFilename
    : `${sanitizedFilename}.png`;

  const imagePath = join("/tmp/plots", imageFilename);

  try {
    const imageBuffer = await readFile(imagePath);

    return new NextResponse(imageBuffer, {
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (error) {
    console.error("Error reading image:", error);
    return NextResponse.json(
      { error: "Image not found" },
      { status: 404 }
    );
  }
}
