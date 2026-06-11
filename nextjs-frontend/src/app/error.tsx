"use client";
import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center space-y-4">
      <div className="w-14 h-14 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center">
        <AlertTriangle size={24} className="text-rose-500" />
      </div>
      <div>
        <h2 className="font-display text-lg font-semibold text-[var(--text)] mb-1">Something went wrong</h2>
        <p className="text-sm text-[var(--text-2)] max-w-sm leading-relaxed">
          {error.message || "An unexpected error occurred. The backend may be unavailable."}
        </p>
      </div>
      <button
        onClick={reset}
        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
      >
        <RotateCcw size={13} /> Try again
      </button>
    </div>
  );
}
