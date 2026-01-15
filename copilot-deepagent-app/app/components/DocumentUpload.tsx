"use client";

import { useState, useCallback, useRef } from "react";

interface UploadedFile {
  file_id: string;
  filename: string;
  size: number;
  extension: string;
}

interface DocumentUploadProps {
  onUploadComplete: (file: UploadedFile) => void;
  disabled?: boolean;
}

export function DocumentUpload({ onUploadComplete, disabled = false }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(async (file: File) => {
    setError(null);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Upload failed");
      }

      const uploadedFileData: UploadedFile = {
        file_id: data.file_id,
        filename: data.filename,
        size: data.size,
        extension: data.extension,
      };

      setUploadedFile(uploadedFileData);
      onUploadComplete(uploadedFileData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }, [onUploadComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleUpload(file);
    }
  }, [handleUpload]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  }, [handleUpload]);

  const handleClick = useCallback(() => {
    if (!disabled && !isUploading) {
      fileInputRef.current?.click();
    }
  }, [disabled, isUploading]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const clearUpload = useCallback(() => {
    setUploadedFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileSelect}
        accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.pptx,.ppt,.html,.htm,.md"
        className="hidden"
        disabled={disabled || isUploading}
      />

      {uploadedFile ? (
        // Show uploaded file
        <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <div className="text-sm text-emerald-300 font-medium truncate max-w-[200px]">
                  {uploadedFile.filename}
                </div>
                <div className="text-xs text-slate-400">
                  {formatFileSize(uploadedFile.size)} • Ready for analysis
                </div>
              </div>
            </div>
            <button
              onClick={clearUpload}
              className="p-1 text-slate-400 hover:text-rose-400 transition-colors"
              title="Remove file"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      ) : (
        // Show upload zone
        <div
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            p-4 rounded-lg border-2 border-dashed cursor-pointer transition-all
            ${isDragging
              ? "border-violet-400 bg-violet-500/10"
              : "border-slate-600 hover:border-slate-500 bg-slate-800/30"
            }
            ${disabled || isUploading ? "opacity-50 cursor-not-allowed" : ""}
          `}
        >
          <div className="flex flex-col items-center gap-2 text-center">
            {isUploading ? (
              <>
                <div className="animate-spin h-6 w-6 border-2 border-violet-400 border-t-transparent rounded-full" />
                <span className="text-sm text-slate-300">Uploading...</span>
              </>
            ) : (
              <>
                <div className="w-10 h-10 rounded-lg bg-slate-700/50 flex items-center justify-center">
                  <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <span className="text-sm text-slate-300">
                    Drop a document or <span className="text-violet-400">click to browse</span>
                  </span>
                  <p className="text-xs text-slate-500 mt-1">
                    PDF, DOCX, TXT, CSV, XLSX, PPTX, HTML, MD
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="mt-2 p-2 bg-rose-500/10 rounded-lg border border-rose-500/30">
          <span className="text-xs text-rose-400">{error}</span>
        </div>
      )}
    </div>
  );
}
