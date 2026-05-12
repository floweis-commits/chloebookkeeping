"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { AlertCircle, CheckCircle, X } from "lucide-react";

interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (type: "success" | "error" | "info", message: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (type: "success" | "error" | "info", message: string) => {
      const id = Date.now().toString();
      setToasts((prev) => [...prev, { id, type, message }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4000);
    },
    []
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}

function ToastContainer({
  toasts,
  removeToast,
}: {
  toasts: Toast[];
  removeToast: (id: string) => void;
}) {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm shadow-lg ${
            toast.type === "success"
              ? "bg-green-50 text-green-700"
              : toast.type === "error"
              ? "bg-red-50 text-red-700"
              : "bg-blue-50 text-blue-700"
          }`}
        >
          {toast.type === "success" ? (
            <CheckCircle size={18} className="flex-shrink-0" />
          ) : (
            <AlertCircle size={18} className="flex-shrink-0" />
          )}
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            className="flex-shrink-0 hover:opacity-75"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
