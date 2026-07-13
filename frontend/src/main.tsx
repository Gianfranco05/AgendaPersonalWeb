import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import * as Sentry from '@sentry/react';
import './index.css';
import App from './App';

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN as string,
    environment: import.meta.env.VITE_ENVIRONMENT || 'development',
    tracesSampleRate: Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE) || 0.1,
  });
}

createRoot(document.getElementById('app')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
