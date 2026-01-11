"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useCoAgent, useCoAgentStateRender, useFrontendTool, useRenderToolCall, useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { ImageDisplay } from "./ImageDisplay";
import { TableDisplay } from "./TableDisplay";

interface ImageData {
  url: string;
  title?: string;
  timestamp: number;
}

export function GenerativeUIDemo() {
  const [images, setImages] = useState<ImageData[]>([]);
  const [agentStatus, setAgentStatus] = useState<string>("Ready");

  // Get loading state from CopilotKit
  const { isLoading } = useCopilotChat();

  // Configure the agent with recursion_limit to prevent infinite loops
  // Note: recursion_limit must be at the top level of config, not inside configurable
  useCoAgent({
    name: "my_agent",
    config: {
      recursion_limit: 100,
    },
  });

  // Update agent status based on loading state
  useEffect(() => {
    if (isLoading) {
      setAgentStatus("Processing...");
    } else {
      setAgentStatus("Ready");
    }
  }, [isLoading]);

  // Register a frontend tool for displaying images
  useFrontendTool({
    name: "display_image",
    description: "Display an image or plot in the UI. Use this when the agent generates a visualization. Pass the image_id from plot_historical_data.",
    parameters: [
      {
        name: "image_url",
        type: "string",
        description: "The image_id (e.g., 'plot_abc123'), URL, or base64 data URI of the image to display",
        required: true,
      },
      {
        name: "title",
        type: "string",
        description: "Optional title for the image",
        required: false,
      },
    ],
    handler: async ({ image_url, title }) => {
      console.log("[display_image] Called with:", { image_url, title });

      let displayUrl = image_url;

      // If it looks like an image_id (not a URL or data URI), fetch from API
      if (
        !image_url.startsWith("http") &&
        !image_url.startsWith("data:") &&
        !image_url.startsWith("/")
      ) {
        // It's an image_id - proxy through our API
        displayUrl = `/api/images/${image_url}`;
      }

      console.log("[display_image] Display URL:", displayUrl);

      setImages((prev) => {
        const newImages = [
          ...prev,
          {
            url: displayUrl,
            title: title || "Generated Visualization",
            timestamp: Date.now(),
          },
        ];
        console.log("[display_image] Updated images:", newImages);
        return newImages;
      });

      return {
        success: true,
        message: "Image displayed successfully",
      };
    },
  });

  // Register a tool for clearing displayed images
  useFrontendTool({
    name: "clear_images",
    description: "Clear all displayed images from the UI",
    parameters: [],
    handler: async () => {
      setImages([]);
      return {
        success: true,
        message: "All images cleared",
      };
    },
  });

  // Render tavily_search tool calls with custom UI
  useRenderToolCall({
    name: "tavily_search",
    render: ({ args, status }) => {
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-cyan-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">
                Searching: <span className="text-cyan-400">{args?.query || "..."}</span>
              </span>
            </div>
          </div>
        );
      }
      // Complete state
      return (
        <div className="p-2.5 bg-cyan-500/10 rounded-lg border border-cyan-500/30 my-2">
          <div className="flex items-center gap-1.5">
            <span className="text-cyan-400 text-sm">&#10003;</span>
            <span className="text-xs text-cyan-300">Search complete</span>
          </div>
        </div>
      );
    },
  });

  // Render load_skill tool calls with custom UI
  useRenderToolCall({
    name: "load_skill",
    render: ({ args, status }) => {
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-fuchsia-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">
                Loading skill: <span className="text-fuchsia-400">{args?.skill_name || "..."}</span>
              </span>
            </div>
          </div>
        );
      }
      // Complete state
      return (
        <div className="p-2.5 bg-fuchsia-500/10 rounded-lg border border-fuchsia-500/30 my-2">
          <div className="flex items-center gap-1.5">
            <span className="text-fuchsia-400 text-sm">&#10003;</span>
            <span className="text-xs text-fuchsia-300">Skill loaded: {args?.skill_name}</span>
          </div>
        </div>
      );
    },
  });

  // Track completed plot image IDs to add to gallery
  const [pendingImageId, setPendingImageId] = useState<{id: string, title: string} | null>(null);
  // Track which image IDs have already been scheduled to prevent duplicate setTimeout calls
  const scheduledImageIdsRef = useRef<Set<string>>(new Set());

  // Effect to add pending images to gallery (avoids setState during render)
  useEffect(() => {
    if (pendingImageId) {
      const displayUrl = `/api/images/${pendingImageId.id}`;
      setImages((prev) => {
        if (prev.some((img) => img.url === displayUrl)) {
          return prev;
        }
        return [...prev, { url: displayUrl, title: pendingImageId.title, timestamp: Date.now() }];
      });
      setPendingImageId(null);
    }
  }, [pendingImageId]);

  // Helper function to render plot tool results
  const renderPlotToolCall = (toolName: string, color: string) => ({
    name: toolName,
    render: ({ args, result, status }: { args: Record<string, unknown>; result: unknown; status: string }) => {
      // Parse result if it's a string
      let parsedResult = result as Record<string, unknown> | null;
      if (typeof result === "string") {
        try {
          parsedResult = JSON.parse(result);
        } catch {
          parsedResult = null;
        }
      }

      // Render inline preview (smaller size)
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className={`animate-spin h-3 w-3 border-2 border-${color}-400 border-t-transparent rounded-full`} />
              <span className="text-xs text-slate-300">Generating: {(args?.title as string) || "plot..."}</span>
            </div>
          </div>
        );
      }

      if (status === "complete" && parsedResult?.status === "success" && parsedResult?.image_id) {
        const imageId = parsedResult.image_id as string;
        const title = (parsedResult.title as string) || (args?.title as string) || "Generated Plot";
        const displayUrl = `/api/images/${imageId}`;

        // Schedule state update via effect (not during render)
        // Only schedule if this image hasn't been scheduled yet to prevent scroll jumps
        if (!scheduledImageIdsRef.current.has(imageId)) {
          scheduledImageIdsRef.current.add(imageId);
          setTimeout(() => setPendingImageId({ id: imageId, title }), 0);
        }

        return (
          <div className="p-2.5 bg-emerald-500/10 rounded-lg border border-emerald-500/30 my-2">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-emerald-400 text-sm">&#10003;</span>
              <span className="text-xs text-emerald-300 font-medium">{title}</span>
            </div>
            <img
              src={displayUrl}
              alt={title}
              className="max-w-[280px] rounded-lg border border-slate-700/50"
            />
          </div>
        );
      }

      if (parsedResult?.type === "error") {
        return (
          <div className="p-2.5 bg-rose-500/10 rounded-lg border border-rose-500/30 my-2">
            <span className="text-xs text-rose-400">Error: {parsedResult.message as string}</span>
          </div>
        );
      }

      // Default: show processing state
      return (
        <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
          <span className="text-xs text-slate-400">Processing...</span>
        </div>
      );
    },
  });

  // Render plot_historical_data tool calls with custom UI
  useRenderToolCall(renderPlotToolCall("plot_historical_data", "violet"));

  // Render plot_distribution_comparison tool calls with custom UI
  useRenderToolCall(renderPlotToolCall("plot_distribution_comparison", "teal"));

  // Render display_table tool calls with custom UI
  useRenderToolCall({
    name: "display_table",
    render: ({ args, result, status }: { args: Record<string, unknown>; result: unknown; status: string }) => {
      // Parse result if it's a string
      let parsedResult = result as Record<string, unknown> | null;
      if (typeof result === "string") {
        try {
          parsedResult = JSON.parse(result);
        } catch {
          parsedResult = null;
        }
      }

      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-cyan-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">Generating table: {(args?.title as string) || "..."}</span>
            </div>
          </div>
        );
      }

      if (status === "complete" && parsedResult?.status === "success" && parsedResult?.table_id) {
        const tableId = parsedResult.table_id as string;
        const title = (parsedResult.title as string) || (args?.title as string) || "Data Table";

        return <TableDisplay tableId={tableId} title={title} />;
      }

      if (parsedResult?.type === "error") {
        return (
          <div className="p-2.5 bg-rose-500/10 rounded-lg border border-rose-500/30 my-2">
            <span className="text-xs text-rose-400">Error: {parsedResult.message as string}</span>
          </div>
        );
      }

      // Default: show processing state
      return (
        <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
          <span className="text-xs text-slate-400">Processing table...</span>
        </div>
      );
    },
  });

  // Agent state render - returns null to avoid cluttering the chat
  // Activity indication is handled by the isLoading state in the main UI
  useCoAgentStateRender({
    name: "my_agent",
    render: () => null,
  });

  const clearAllImages = useCallback(() => {
    setImages([]);
  }, []);

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Main Content Area */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="max-w-4xl mx-auto">
          {/* Header - compact */}
          <header className="mb-6">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-400 via-fuchsia-400 to-cyan-400 bg-clip-text text-transparent">
              Data Analysis Agent
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Fetch data, analyze trends, and create visualizations
            </p>
          </header>

          {/* Status Bar - minimal */}
          <div className="mb-6 px-4 py-2.5 bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${agentStatus === "Ready" ? "bg-emerald-400 shadow-lg shadow-emerald-400/50" : "bg-amber-400 animate-pulse shadow-lg shadow-amber-400/50"}`} />
              <span className="text-xs text-slate-300">{agentStatus}</span>
            </div>
            {images.length > 0 && (
              <button
                onClick={clearAllImages}
                className="text-xs text-slate-400 hover:text-rose-400 transition-colors"
              >
                Clear plots
              </button>
            )}
          </div>

          {/* Activity Panel - shows when agent is working */}
          {isLoading && (
            <div className="mb-6 p-4 bg-slate-800/50 backdrop-blur rounded-xl border border-violet-500/30">
              <div className="flex items-center gap-3 mb-3">
                <div className="relative">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500/30 to-fuchsia-500/30 flex items-center justify-center">
                    <div className="animate-spin h-4 w-4 border-2 border-violet-400 border-t-transparent rounded-full" />
                  </div>
                  <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-amber-400 rounded-full animate-pulse" />
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-200">Agent Working</div>
                  <div className="text-xs text-slate-400">Processing your request...</div>
                </div>
              </div>

              {/* Progress bar animation */}
              <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-violet-500 via-fuchsia-500 to-cyan-500 rounded-full animate-progress" style={{ width: '100%' }} />
              </div>
            </div>
          )}

          {/* Images/Plots Display */}
          {images.length > 0 ? (
            <div>
              <div className="text-xs font-medium text-slate-400 mb-3">
                Visualizations ({images.length})
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {images.map((image, idx) => (
                  <ImageDisplay
                    key={`${image.timestamp}-${idx}`}
                    url={image.url}
                    title={image.title}
                    timestamp={image.timestamp}
                    onRemove={() => {
                      setImages((prev) => prev.filter((_, i) => i !== idx));
                    }}
                  />
                ))}
              </div>
            </div>
          ) : !isLoading && (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-12 h-12 mx-auto mb-4 rounded-xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 border border-violet-500/30 flex items-center justify-center">
                  <svg className="w-6 h-6 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                  </svg>
                </div>
                <p className="text-sm text-slate-300 mb-1">No visualizations yet</p>
                <p className="text-xs text-slate-500">Try: <span className="text-violet-400">"Plot AAPL stock price"</span></p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Chat Panel */}
      <div className="w-96 border-l border-slate-700/50 bg-slate-800/30 backdrop-blur flex flex-col h-screen">
        <CopilotChat
          className="flex-1 min-h-0"
          instructions="You are a helpful data analysis and visualization assistant. You have access to tools for generating plots and displaying images. When asked to create visualizations, use the 'display_image' tool to show them to the user."
        />
      </div>
    </div>
  );
}
