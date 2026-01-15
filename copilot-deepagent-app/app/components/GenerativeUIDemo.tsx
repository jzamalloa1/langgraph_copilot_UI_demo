"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useCoAgent, useCoAgentStateRender, useFrontendTool, useRenderToolCall, useCopilotChat, useCopilotReadable } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { ImageDisplay } from "./ImageDisplay";
import { TableDisplay } from "./TableDisplay";
import { DocumentUpload } from "./DocumentUpload";

interface ImageData {
  url: string;
  title?: string;
  timestamp: number;
}

interface UploadedDocument {
  file_id: string;
  filename: string;
  size: number;
  extension: string;
}

// Safe image component that only renders when src is valid
function SafeImage({ src, alt, className }: { src: string | null | undefined; alt: string; className?: string }) {
  if (!src || src.trim() === "") {
    return null;
  }
  return <img src={src} alt={alt} className={className} />;
}

// Custom markdown image renderer that guards against empty URLs
// This prevents the "empty src" error from CopilotKit's markdown rendering
const safeMarkdownComponents = {
  img: ({ src, alt, ...props }: { src?: string; alt?: string; [key: string]: unknown }) => {
    if (!src || typeof src !== "string" || src.trim() === "") {
      return null;
    }
    return (
      <img
        src={src}
        alt={alt || "Image"}
        className="max-w-full h-auto rounded-lg border border-slate-700/50 my-2"
        {...props}
      />
    );
  },
};

// Helper to safely convert result to string for parsing
function resultToString(result: unknown): string {
  if (result === null || result === undefined) {
    return "";
  }
  if (typeof result === "string") {
    return result;
  }
  try {
    return JSON.stringify(result);
  } catch {
    return "";
  }
}

export function GenerativeUIDemo() {
  const [images, setImages] = useState<ImageData[]>([]);
  const [agentStatus, setAgentStatus] = useState<string>("Ready");
  const [uploadedDoc, setUploadedDoc] = useState<UploadedDocument | null>(null);

  // Get loading state from CopilotKit
  const { isLoading } = useCopilotChat();

  // Configure the agent with recursion_limit to prevent infinite loops
  // Note: recursion_limit must be at the top level of config, not inside configurable
  // Also pass uploaded document info through initialState so the agent can access it
  useCoAgent({
    name: "my_agent",
    initialState: {
      uploaded_document: uploadedDoc
        ? {
            file_id: uploadedDoc.file_id,
            filename: uploadedDoc.filename,
            extension: uploadedDoc.extension,
            size: uploadedDoc.size,
          }
        : null,
    },
    config: {
      recursion_limit: 100,
    },
  });

  // Make uploaded document info available as readable context for the agent
  // This ensures the agent always knows about uploaded documents
  useCopilotReadable({
    description: "Currently uploaded document information",
    value: uploadedDoc
      ? `UPLOADED DOCUMENT AVAILABLE:
- Filename: ${uploadedDoc.filename}
- File ID: ${uploadedDoc.file_id}
- Extension: ${uploadedDoc.extension}
- Size: ${uploadedDoc.size} bytes

IMPORTANT: When the user asks about "the document", "this file", wants to "summarize it", or asks any question about the uploaded document, you MUST call the document_analysis sub-agent with this task: "Parse and analyze document with file_id='${uploadedDoc.file_id}' and filename='${uploadedDoc.filename}'. User question: [their question]"`
      : "No document has been uploaded yet.",
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

  // Register a tool to get uploaded document info
  // This allows the agent to retrieve the file_id when user asks about "the document"
  useFrontendTool({
    name: "get_uploaded_document",
    description: "Get information about the currently uploaded document. Call this when the user asks about a document they uploaded, wants to summarize it, or asks questions about it. Returns file_id and filename needed for document_analysis.",
    parameters: [],
    handler: async () => {
      if (uploadedDoc) {
        return {
          success: true,
          has_document: true,
          file_id: uploadedDoc.file_id,
          filename: uploadedDoc.filename,
          size: uploadedDoc.size,
          extension: uploadedDoc.extension,
          message: `Document "${uploadedDoc.filename}" is uploaded. Use file_id "${uploadedDoc.file_id}" with document_analysis to answer questions about it.`,
        };
      } else {
        return {
          success: true,
          has_document: false,
          message: "No document has been uploaded yet. Ask the user to upload a document first.",
        };
      }
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

  // Helper to extract image_id from sub-agent text response
  const extractImageId = (text: string | undefined | null): string | null => {
    if (!text) return null;
    // Look for patterns like "image_id: plot_abc123" or "plot_abc123" or "dist_abc123"
    const patterns = [
      /image_id[:\s]+["']?([a-zA-Z]+_[a-f0-9]+)["']?/i,
      /\b(plot_[a-f0-9]+)\b/i,
      /\b(dist_[a-f0-9]+)\b/i,
    ];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) return match[1];
    }
    return null;
  };

  // Helper to extract table_id from sub-agent text response
  const extractTableId = (text: string | undefined | null): string | null => {
    if (!text) return null;
    // Look for patterns like "table_id: table_abc123" or "table_abc123"
    const patterns = [
      /table_id[:\s]+["']?([a-zA-Z]+_[a-f0-9]+)["']?/i,
      /\b(table_[a-f0-9]+)\b/i,
    ];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) return match[1];
    }
    return null;
  };

  // Render web_research sub-agent tool calls (orchestrator level)
  useRenderToolCall({
    name: "web_research",
    render: ({ args, status }) => {
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-cyan-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">
                Researching: <span className="text-cyan-400">{(args?.query as string)?.slice(0, 50) || "..."}</span>
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
            <span className="text-xs text-cyan-300">Research complete</span>
          </div>
        </div>
      );
    },
  });

  // Render plot_analytics sub-agent tool calls (orchestrator level)
  useRenderToolCall({
    name: "plot_analytics",
    render: ({ result, status }) => {
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-violet-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">Creating visualization...</span>
            </div>
          </div>
        );
      }

      // Sub-agent returns text content, try to extract image_id
      const resultText = resultToString(result);
      const imageId = extractImageId(resultText);

      if (status === "complete" && imageId) {
        const displayUrl = `/api/images/${imageId}`;

        // Schedule state update via effect (not during render)
        if (!scheduledImageIdsRef.current.has(imageId)) {
          scheduledImageIdsRef.current.add(imageId);
          setTimeout(() => setPendingImageId({ id: imageId, title: "Generated Plot" }), 0);
        }

        return (
          <div className="p-2.5 bg-emerald-500/10 rounded-lg border border-emerald-500/30 my-2">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-emerald-400 text-sm">&#10003;</span>
              <span className="text-xs text-emerald-300 font-medium">Plot created</span>
            </div>
            <SafeImage
              src={displayUrl}
              alt="Generated Plot"
              className="max-w-[280px] rounded-lg border border-slate-700/50"
            />
          </div>
        );
      }

      // Complete but no image found - show text result
      if (status === "complete") {
        return (
          <div className="p-2.5 bg-amber-500/10 rounded-lg border border-amber-500/30 my-2">
            <span className="text-xs text-amber-300">Plot analytics completed</span>
          </div>
        );
      }

      return (
        <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
          <span className="text-xs text-slate-400">Processing...</span>
        </div>
      );
    },
  });

  // Render display_data sub-agent tool calls (orchestrator level)
  useRenderToolCall({
    name: "display_data",
    render: ({ result, status }) => {
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-cyan-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">Creating table...</span>
            </div>
          </div>
        );
      }

      // Sub-agent returns text content, try to extract table_id
      const resultText = resultToString(result);
      const tableId = extractTableId(resultText);

      if (status === "complete" && tableId) {
        return <TableDisplay tableId={tableId} title="Data Table" />;
      }

      // Complete but no table found
      if (status === "complete") {
        return (
          <div className="p-2.5 bg-amber-500/10 rounded-lg border border-amber-500/30 my-2">
            <span className="text-xs text-amber-300">Display data completed</span>
          </div>
        );
      }

      return (
        <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
          <span className="text-xs text-slate-400">Processing table...</span>
        </div>
      );
    },
  });

  // Render document_analysis sub-agent tool calls (orchestrator level)
  useRenderToolCall({
    name: "document_analysis",
    render: ({ result, status }) => {
      if (status === "executing") {
        return (
          <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin h-3 w-3 border-2 border-amber-400 border-t-transparent rounded-full" />
              <span className="text-xs text-slate-300">
                Analyzing document...
              </span>
            </div>
          </div>
        );
      }

      // Check if the result indicates document indexing or query results
      const resultText = resultToString(result);
      const isIndexed = resultText.includes("indexed") || resultText.includes("parsed");
      const hasResults = resultText.includes("results") || resultText.includes("found");

      if (status === "complete") {
        return (
          <div className="p-2.5 bg-amber-500/10 rounded-lg border border-amber-500/30 my-2">
            <div className="flex items-center gap-1.5">
              <span className="text-amber-400 text-sm">&#10003;</span>
              <span className="text-xs text-amber-300">
                {isIndexed ? "Document indexed" : hasResults ? "Document queried" : "Document analysis complete"}
              </span>
            </div>
          </div>
        );
      }

      return (
        <div className="p-2.5 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
          <span className="text-xs text-slate-400">Processing document...</span>
        </div>
      );
    },
  });

  // Agent state render - returns null to avoid cluttering the chat
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
                <p className="text-xs text-slate-500">Try: <span className="text-violet-400">&quot;Plot AAPL stock price&quot;</span></p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Chat Panel */}
      <div className="w-96 border-l border-slate-700/50 bg-slate-800/30 backdrop-blur flex flex-col h-screen">
        {/* Document Upload Section */}
        <div className="p-3 border-b border-slate-700/50">
          <div className="text-xs font-medium text-slate-400 mb-2">Upload Document</div>
          <DocumentUpload
            onUploadComplete={(file) => {
              setUploadedDoc(file);
            }}
            disabled={isLoading}
          />
          {uploadedDoc && (
            <div className="mt-2 text-xs text-slate-400">
              Ask questions about: <span className="text-violet-400">{uploadedDoc.filename}</span>
            </div>
          )}
        </div>
        <CopilotChat
          className="flex-1 min-h-0"
          instructions={`You are a helpful data analysis and visualization assistant. You have access to sub-agents for web research, plotting, displaying tables, and document analysis.${
            uploadedDoc
              ? `

CRITICAL DOCUMENT CONTEXT:
The user has uploaded a document that is ready for analysis:
- Filename: "${uploadedDoc.filename}"
- File ID: "${uploadedDoc.file_id}"

When the user asks ANYTHING about "the document", "this file", "it", wants to "summarize", "analyze", or asks ANY question that could relate to the uploaded document, you MUST:
1. Call the document_analysis sub-agent with EXACTLY this task string:
   "Analyze the document with file_id='${uploadedDoc.file_id}' and filename='${uploadedDoc.filename}'. User question: [insert user's question here]"
2. The sub-agent will handle parsing and querying the document.
3. Return the results to the user.

DO NOT say "no document uploaded" - a document IS uploaded with file_id="${uploadedDoc.file_id}".`
              : ""
          }`}
          markdownTagRenderers={safeMarkdownComponents}
        />
      </div>
    </div>
  );
}
