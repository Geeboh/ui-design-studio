# PRISM Studio 2.0.8

PRISM Studio 2.0.8 replaces dashboard snapshot polling with authenticated SSE push.

The dashboard receives initial and changed snapshots through an authenticated stream, reconnects with bounded backoff, and keeps manual Refresh as a one-shot fallback. Browser polling is removed. OMP observer task snapshots now remain separate from director ownership, and the dashboard projects observable OMP task activity into the Workers panel when explicit worker records are absent.
