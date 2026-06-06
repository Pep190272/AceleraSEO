import { useState, useCallback } from "react";

/**
 * Manages the async state machine shared across Tool components:
 * loading flag, error string, typed data, and a stable `execute` callback.
 *
 * `execute` is wrapped in `useCallback` with no external dependencies so its
 * identity is stable across renders — safe to list in `useEffect` dependency
 * arrays without triggering infinite loops.
 *
 * Usage:
 *   const { data, loading, error, execute, reset } = useApiCall<Plan>();
 *   // trigger the call
 *   execute(() => apiFetch("/api/strategy", { method: "POST", body: … }));
 */

export type ApiCallState<T> = {
  data: T | null;
  loading: boolean;
  error: string;
};

export type UseApiCallReturn<T> = ApiCallState<T> & {
  /** Run `op` and populate data/loading/error. Returns true on success. */
  execute: (op: () => Promise<T>) => Promise<boolean>;
  /** Clear data, error, and loading back to the initial state. */
  reset: () => void;
};

export function useApiCall<T>(): UseApiCallReturn<T> {
  const [state, setState] = useState<ApiCallState<T>>({
    data: null,
    loading: false,
    error: "",
  });

  // Stable identity — no captured state means no stale-closure risk and no
  // infinite loops when used as a useEffect dependency.
  const execute = useCallback(async (op: () => Promise<T>): Promise<boolean> => {
    setState({ data: null, loading: true, error: "" });
    try {
      const result = await op();
      setState({ data: result, loading: false, error: "" });
      return true;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Request failed";
      setState({ data: null, loading: false, error: message });
      return false;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: "" });
  }, []);

  return { ...state, execute, reset };
}
