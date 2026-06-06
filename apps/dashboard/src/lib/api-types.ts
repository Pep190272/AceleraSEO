// Normalized error envelope for all API routes.
// The `detail` field is kept for backward compatibility: existing client error
// displays read `data?.detail || data?.error`, so removing it would blank them out.

export interface ApiError {
  error: string;
  detail?: unknown;
}
