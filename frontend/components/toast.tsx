'use client';

import { useEffect, useState } from 'react';

export type ToastMessage = {
  id: number;
  type: 'success' | 'error' | 'info';
  message: string;
};

const listeners = new Set<(toast: ToastMessage) => void>();

function emit(toast: ToastMessage) {
  listeners.forEach((l) => l(toast));
}

export const toast = {
  success(message: string) {
    emit({ id: Date.now() + Math.random(), type: 'success', message });
  },
  error(message: string) {
    emit({ id: Date.now() + Math.random(), type: 'error', message });
  },
  info(message: string) {
    emit({ id: Date.now() + Math.random(), type: 'info', message });
  }
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const handler = (t: ToastMessage) => {
      setToasts((prev) => [...prev, t]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((p) => p.id !== t.id));
      }, 4000);
    };
    listeners.add(handler);
    return () => {
      listeners.delete(handler);
    };
  }, []);

  return (
    <>
      {children}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`px-4 py-2 rounded shadow text-sm border bg-white ${
              t.type === 'error'
                ? 'border-red-500 text-red-700'
                : t.type === 'success'
                ? 'border-green-500 text-green-700'
                : 'border-gray-300 text-gray-700'
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </>
  );
};
