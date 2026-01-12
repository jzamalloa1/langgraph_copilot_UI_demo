"use client";

import { useState } from "react";
import { downloadImage, getProxiedImageUrl } from "@/lib/imageUtils";

interface ImageDisplayProps {
  url: string;
  title?: string;
  description?: string;
  timestamp?: number;
  onRemove?: () => void;
}

export function ImageDisplay({
  url,
  title = "Generated Visualization",
  description,
  timestamp,
  onRemove,
}: ImageDisplayProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Guard against empty/invalid URLs - don't render anything
  if (!url || url.trim() === "") {
    return null;
  }

  const proxiedUrl = getProxiedImageUrl(url);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const filename = `${title.replace(/\s+/g, "_")}_${timestamp || Date.now()}.png`;
      await downloadImage(proxiedUrl, filename);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Failed to download image");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleImageLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleImageError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  return (
    <div className="image-display-container bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-4 hover:border-violet-500/30 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-medium text-slate-200 text-sm">{title}</h3>
          {timestamp && (
            <p className="text-xs text-slate-500 mt-1">
              {new Date(timestamp).toLocaleString()}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-1">
          <button
            onClick={handleDownload}
            disabled={isDownloading || hasError}
            className="p-1.5 text-slate-400 hover:text-violet-400 hover:bg-violet-500/10 rounded-lg transition-colors disabled:opacity-50"
            title="Download image"
          >
            {isDownloading ? (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            )}
          </button>

          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Remove image"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Image */}
      <div className="relative">
        {isLoading && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 rounded-lg">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-violet-400 border-t-transparent" />
          </div>
        )}

        {hasError ? (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-6 text-center">
            <svg
              className="mx-auto h-8 w-8 text-rose-400 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-rose-300 font-medium text-sm">Failed to load image</p>
            <p className="text-rose-400/70 text-xs mt-1">
              The image could not be displayed
            </p>
          </div>
        ) : (
          <img
            src={proxiedUrl}
            alt={description || title}
            className="w-full h-auto rounded-lg border border-slate-700/50"
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="text-xs text-slate-400 mt-3 border-t border-slate-700/50 pt-3">
          {description}
        </p>
      )}
    </div>
  );
}
