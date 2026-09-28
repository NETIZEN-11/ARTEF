'use client';
import { useEffect } from 'react';
import { initWebVitals } from './web-vitals';
export function WebVitalsWrapper() {
  useEffect(() => {
    const timer = setTimeout(() => {
      initWebVitals();
    }, 100);
    return () => clearTimeout(timer);
  }, []);
  return null;
}
