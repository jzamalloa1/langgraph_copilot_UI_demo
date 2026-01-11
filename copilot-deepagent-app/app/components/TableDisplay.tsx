"use client";

import { useState, useEffect } from "react";

interface TableData {
  title: string;
  caption?: string;
  columns: string[];
  rows: string[][];
  row_count: number;
  column_count: number;
}

interface TableDisplayProps {
  tableId: string;
  title?: string;
}

/**
 * TableDisplay component for rendering tabular data fetched from the backend.
 * Used by useRenderToolCall to display tables inline in the CopilotKit chat.
 */
export function TableDisplay({ tableId, title: propTitle }: TableDisplayProps) {
  const [tableData, setTableData] = useState<TableData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const fetchTableData = async () => {
      try {
        const response = await fetch(`/api/tables/${tableId}`);
        if (!response.ok) throw new Error("Failed to fetch");
        setTableData(await response.json());
      } catch {
        setHasError(true);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTableData();
  }, [tableId]);

  const displayTitle = propTitle || tableData?.title || "Data Table";

  if (isLoading) {
    return (
      <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 my-2">
        <div className="flex items-center gap-2">
          <div className="animate-spin h-3 w-3 border-2 border-cyan-400 border-t-transparent rounded-full" />
          <span className="text-xs text-slate-300">Loading table...</span>
        </div>
      </div>
    );
  }

  if (hasError || !tableData) {
    return (
      <div className="p-3 bg-rose-500/10 rounded-lg border border-rose-500/30 my-2">
        <span className="text-xs text-rose-400">Failed to load table</span>
      </div>
    );
  }

  return (
    <div className="my-2 rounded-lg border border-cyan-500/30 overflow-hidden">
      <div className="px-3 py-2 bg-cyan-500/10 border-b border-cyan-500/30">
        <span className="text-xs font-medium text-cyan-300">{displayTitle}</span>
        <span className="text-xs text-slate-400 ml-2">
          ({tableData.row_count} × {tableData.column_count})
        </span>
      </div>
      <div className="overflow-x-auto max-h-64">
        <table className="w-full text-xs">
          <thead className="bg-slate-700/50 sticky top-0">
            <tr>
              {tableData.columns.map((col, idx) => (
                <th key={idx} className="px-2 py-1.5 text-left font-medium text-slate-200 border-b border-slate-600/50 whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableData.rows.map((row, rowIdx) => (
              <tr key={rowIdx} className={rowIdx % 2 === 0 ? "bg-slate-800/30" : "bg-slate-800/50"}>
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} className="px-2 py-1.5 text-slate-300 border-b border-slate-700/30 whitespace-nowrap">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {tableData.caption && (
        <div className="px-3 py-1.5 bg-slate-800/50 border-t border-slate-700/50">
          <span className="text-xs text-slate-400">{tableData.caption}</span>
        </div>
      )}
    </div>
  );
}
