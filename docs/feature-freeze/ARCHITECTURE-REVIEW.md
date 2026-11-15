# Architecture review

The authored `.omp` tree is the engine and asset source. Hatchling maps it into the Python wheel payload without a second maintained copy. `runtime.py` loads that payload for installed entry points. The stdio MCP adapter confines operations to an explicit repository. HTTP servers publish authenticated local dashboards and run evidence. The OMP extension owns a dashboard child and projects progress without replacing Pi Tasks ownership.

Runs are file-backed dossiers. Theme and approval identities use content hashes. Atomic writes protect individual records; advisory or exclusive locks protect selected multi-file operations. No application database or schema migration service exists. Compatibility covers legacy dossier versions through explicit read paths.

Confirmed design gap: scope enum validation did not enforce the documented full-release boundary. Fix at the shared validator rather than duplicating checks across CLI, MCP and registry callers. Existing structures are sufficient. No architecture rewrite is justified.

Remaining component review is in progress.
