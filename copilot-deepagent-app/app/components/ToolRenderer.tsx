"use client";

import { useMemo } from "react";

interface PlotData {
  type: "plot" | "chart" | "image";
  format?: "png" | "svg" | "base64" | "url";
  data?: string;
  image_id?: string;
  title?: string;
  description?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

interface ToolRendererProps {
  toolCall: unknown;
  toolMessage: {
    result?: unknown;
  };
}

export function ToolRenderer({ toolMessage }: ToolRendererProps) {
  const customRender = useMemo(() => {
    if (!toolMessage?.result) {
      return null;
    }

    let result = toolMessage.result;

    // Parse if it's a string
    if (typeof result === "string") {
      try {
        result = JSON.parse(result);
      } catch {
        // Not JSON, might be a URL or base64
        if (result.startsWith("http") || result.startsWith("data:image")) {
          return (
            <div className="tool-result-image">
              <img src={result} alt="Generated visualization" className="max-w-full rounded" />
            </div>
          );
        }
        return null;
      }
    }

    // Type guard for result object
    if (typeof result !== "object" || result === null) {
      return null;
    }

    const resultObj = result as Record<string, unknown>;

    // Handle structured plot data
    if (resultObj.type === "plot" || resultObj.type === "image" || resultObj.type === "chart") {
      const plotData = resultObj as unknown as PlotData;

      // Don't render if status is error
      if (plotData.status === "error" || (typeof resultObj.message === "string" && resultObj.message.includes("error"))) {
        return null;
      }

      // If we have an image_id, fetch from API
      const imageUrl = plotData.image_id
        ? `/api/images/${plotData.image_id}`
        : plotData.data?.startsWith("data:")
        ? plotData.data
        : plotData.data
        ? `data:image/png;base64,${plotData.data}`
        : null;

      return (
        <div className="tool-result-container p-4 border rounded-lg bg-white shadow-sm">
          {plotData.title && (
            <h3 className="text-lg font-semibold mb-2">{plotData.title}</h3>
          )}

          <div className="visualization-content">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={plotData.description || "Generated visualization"}
                className="max-w-full h-auto rounded"
              />
            ) : (
              <div className="text-gray-500 text-sm">
                Image generated: {plotData.image_id || "unknown"}
              </div>
            )}
          </div>

          {plotData.description && (
            <p className="text-sm text-gray-600 mt-2">{plotData.description}</p>
          )}

          {plotData.metadata && (
            <details className="mt-2">
              <summary className="text-sm text-gray-500 cursor-pointer">
                Metadata
              </summary>
              <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto">
                {JSON.stringify(plotData.metadata, null, 2)}
              </pre>
            </details>
          )}
        </div>
      );
    }

    // Default: no custom rendering
    return null;
  }, [toolMessage]);

  // Return custom render if available
  return customRender;
}
