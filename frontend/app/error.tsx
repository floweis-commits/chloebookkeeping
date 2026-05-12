"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <p className="text-gray-500 mb-4">Something went wrong.</p>
        <button onClick={reset} className="text-sm text-blush-500 hover:underline">
          Try again
        </button>
      </div>
    </div>
  );
}
