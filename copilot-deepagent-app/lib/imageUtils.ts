/**
 * Utility functions for handling images from LangGraph agents
 */

/**
 * Check if a string is a valid image URL or data URI
 */
export function isValidImageUrl(url: string): boolean {
  if (!url) return false;

  // Check for data URI
  if (url.startsWith("data:image/")) {
    return true;
  }

  // Check for HTTP/HTTPS URL
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return true;
  }

  // Check for relative URL (proxy through our API)
  if (url.startsWith("/api/images/")) {
    return true;
  }

  return false;
}

/**
 * Convert a filename to a proxied image URL
 * Use this when your LangGraph agent returns just a filename
 */
export function getProxiedImageUrl(filename: string): string {
  // If it's already a full URL or data URI, return as-is
  if (isValidImageUrl(filename)) {
    return filename;
  }

  // Otherwise, proxy through our API route
  return `/api/images/${filename}`;
}

/**
 * Convert base64 string to data URI
 */
export function base64ToDataUri(
  base64: string,
  mimeType: string = "image/png"
): string {
  // If it's already a data URI, return as-is
  if (base64.startsWith("data:")) {
    return base64;
  }

  return `data:${mimeType};base64,${base64}`;
}

/**
 * Parse image metadata from agent state
 */
export interface ImageMetadata {
  url: string;
  title?: string;
  description?: string;
  format?: "png" | "svg" | "jpg" | "jpeg";
  timestamp?: number;
}

export function parseImageFromState(state: any): ImageMetadata | null {
  if (!state) return null;

  // Check for image_url field
  if (state.image_url) {
    return {
      url: getProxiedImageUrl(state.image_url),
      title: state.image_title,
      description: state.image_description,
      format: state.image_format || "png",
      timestamp: Date.now(),
    };
  }

  // Check for nested image data
  if (state.visualization?.url) {
    return {
      url: getProxiedImageUrl(state.visualization.url),
      title: state.visualization.title,
      description: state.visualization.description,
      format: state.visualization.format || "png",
      timestamp: Date.now(),
    };
  }

  return null;
}

/**
 * Download image data as a file
 */
export async function downloadImage(
  imageUrl: string,
  filename: string = "image.png"
): Promise<void> {
  try {
    const response = await fetch(imageUrl);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Failed to download image:", error);
    throw new Error("Failed to download image");
  }
}

/**
 * Get image dimensions from URL
 */
export function getImageDimensions(
  url: string
): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.width, height: img.height });
    };
    img.onerror = reject;
    img.src = url;
  });
}
