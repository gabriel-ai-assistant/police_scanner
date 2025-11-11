import { useEffect, useState } from 'react';

const STORAGE_KEY = 'police-scanner-refresh-interval';

export function useRefreshInterval(defaultSeconds = 30) {
  const [interval, setInterval] = useState(defaultSeconds * 1000);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const fromStorage = window.localStorage.getItem(STORAGE_KEY);
    if (fromStorage) {
      const parsed = Number(fromStorage);
      if (!Number.isNaN(parsed) && parsed > 0) {
        setInterval(parsed * 1000);
      }
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY && event.newValue) {
        const value = Number(event.newValue);
        if (!Number.isNaN(value) && value > 0) {
          setInterval(value * 1000);
        }
      }
    };

    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  return interval;
}
