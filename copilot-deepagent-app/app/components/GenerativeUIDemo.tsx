"use client";

import { useState, useCallback, useEffect } from "react";
import { useCoAgentStateRender, useFrontendTool, useRenderToolCall, useCopilotChat } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { ImageDisplay } from "./ImageDisplay";
import { parseImageFromState } from "@/lib/imageUtils";

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

  // Render plot_historical_data tool calls with custom UI
  useRenderToolCall({
    name: "plot_historical_data",
    render: ({ args, result, status }) => {
      console.log("[plot_historical_data] Rendering tool call:", { args, result, status });

      // Parse result if it's a string
      let parsedResult = result;
      if (typeof result === "string") {
        try {
          parsedResult = JSON.parse(result);
        } catch {
          // Not JSON
        }
      }

      // If successful, add image to display
      useEffect(() => {
        if (status === "complete" && parsedResult?.status === "success" && parsedResult?.image_id) {
          const displayUrl = `/api/images/${parsedResult.image_id}`;
          setImages((prev) => {
            // Avoid duplicates
            if (prev.some((img) => img.url === displayUrl)) {
              return prev;
            }
            return [
              ...prev,
              {
                url: displayUrl,
                title: parsedResult.title || args?.title || "Generated Plot",
                timestamp: Date.now(),
              },
            ];
          });
        }
      }, [status, parsedResult, args]);

      // Render inline preview (smaller size)
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-violet-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">Generating: {args?.title || "plot..."}</span>
            </div>
          </div>
        );
      }

      if (status === "complete" && parsedResult?.status === "success") {
        return (
          <div className="p-2.5 bg-emerald-500/10 rounded-lg border border-emerald-500/30 my-2">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-emerald-400 text-sm">&#10003;</span>
              <span className="text-xs text-emerald-300 font-medium">
                {parsedResult.title || args?.title}
              </span>
            </div>
            <img
              src={`/api/images/${parsedResult.image_id}`}
              alt={parsedResult.title || "Generated plot"}
              className="max-w-[280px] rounded-lg border border-slate-700/50"
            />
          </div>
        );
      }

      if (parsedResult?.type === "error") {
        return (
          <div className="p-2.5 bg-rose-500/10 rounded-lg border border-rose-500/30 my-2">
            <span className="text-xs text-rose-400">Error: {parsedResult.message}</span>
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

  // Render agent state
  useCoAgentStateRender({
    name: "sample_agent",
    render: ({ state }) => {
      // Update status based on agent state
      if (state?.status) {
        setAgentStatus(state.status);
      }

      // Parse and handle image data from state
      const imageData = parseImageFromState(state);
      if (imageData) {
        setImages((prev) => {
          // Avoid duplicates
          if (prev.some((img) => img.url === imageData.url)) {
            return prev;
          }
          return [
            ...prev,
            {
              url: imageData.url,
              title: imageData.title || "Agent Generated Plot",
              timestamp: imageData.timestamp || Date.now(),
            },
          ];
        });
      }

      // Render agent state UI
      if (!state || Object.keys(state).length === 0) {
        return null;
      }

      return (
        <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
          <div className="text-xs font-medium text-slate-400 mb-2">Agent State</div>

          {/* Current Step */}
          {state.current_step && (
            <div className="text-xs text-slate-300 mb-1">
              <span className="text-slate-500">Step:</span> {state.current_step}
            </div>
          )}

          {/* Progress Bar */}
          {state.progress !== undefined && (
            <div className="mb-2">
              <div className="flex justify-between text-xs mb-0.5">
                <span className="text-slate-500">Progress</span>
                <span className="text-slate-300">{Math.round(state.progress)}%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-1.5">
                <div
                  className="bg-gradient-to-r from-violet-500 to-fuchsia-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${state.progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Status Message */}
          {state.message && (
            <div className="text-xs text-slate-300 bg-slate-900/50 p-1.5 rounded border border-slate-700/50">
              {state.message}
            </div>
          )}
        </div>
      );
    },
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
              Data Visualization Agent
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Ask me to plot stock prices, trends, or any historical data
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

              {/* Animated progress steps */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="text-slate-400">Searching for data...</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                  <span className="text-slate-400">Loading skills...</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
                  <span className="text-slate-400">Generating visualization...</span>
                </div>
              </div>

              {/* Progress bar animation */}
              <div className="mt-3 h-1 bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-violet-500 via-fuchsia-500 to-cyan-500 rounded-full animate-pulse" style={{ width: '60%' }} />
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
