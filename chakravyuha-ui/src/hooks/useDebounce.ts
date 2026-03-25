import { useEffect, useState } from "react";

/**
 * useDebounce – Delays updating the value until after wait milliseconds.
 */
export function useDebounce<T>(value: T, wait = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), wait);
    return () => clearTimeout(id);
  }, [value, wait]);

  return debounced;
}
