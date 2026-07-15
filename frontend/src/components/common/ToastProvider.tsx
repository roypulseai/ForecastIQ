import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react';
import { Snackbar, Alert, type AlertColor } from '@mui/material';

interface Toast {
  id: number;
  message: string;
  severity: AlertColor;
}

interface ToastContextValue {
  showToast: (message: string, severity?: AlertColor) => void;
}

const ToastContext = createContext<ToastContextValue>({ showToast: () => {} });

const MAX_TOASTS = 4;
const TOAST_DURATION = 4000;

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }): ReactNode {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, severity: AlertColor = 'success') => {
    const id = nextId.current++;
    setToasts((prev) => {
      const next = [...prev, { id, message, severity }];
      return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
    });
    setTimeout(() => removeToast(id), TOAST_DURATION);
  }, [removeToast]);

  const handleClose = (_: unknown, reason?: string) => {
    if (reason === 'clickaway') return;
    setToasts((prev) => (prev.length > 0 ? prev.slice(1) : prev));
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toasts.map((toast, index) => (
        <Snackbar
          key={toast.id}
          open
          autoHideDuration={TOAST_DURATION}
          onClose={handleClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
          sx={{ bottom: `${(toasts.length - 1 - index) * 64}px !important` }}
        >
          <Alert severity={toast.severity} variant="filled" sx={{ width: '100%' }}>
            {toast.message}
          </Alert>
        </Snackbar>
      ))}
    </ToastContext.Provider>
  );
}
