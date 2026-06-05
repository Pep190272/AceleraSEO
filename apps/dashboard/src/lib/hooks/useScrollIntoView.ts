import { useRef } from "react";

/**
 * Encapsulates the setTimeout → scrollIntoView({ behavior: "smooth" }) pattern
 * used across Tool components after a successful API response.
 *
 * Usage:
 *   const { ref, trigger } = useScrollIntoView();
 *   // attach `ref` to the result container
 *   // call `trigger()` after setting state
 */
export function useScrollIntoView<T extends HTMLElement = HTMLDivElement>(delay = 50) {
  const ref = useRef<T>(null);

  function trigger() {
    setTimeout(() => ref.current?.scrollIntoView({ behavior: "smooth" }), delay);
  }

  return { ref, trigger };
}
