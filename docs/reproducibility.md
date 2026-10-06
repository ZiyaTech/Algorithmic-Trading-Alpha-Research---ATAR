# Reproducibility and failure behavior

A candidate ID identifies a semantic parameterization, not a measurement. A result identity also includes the public code hash, data hash, dependency versions, window, backend and execution settings. Parameter dictionaries cannot override identity fields.

The demo records synthetic generation inputs and the resulting OHLC fingerprint. It records public source hashes without absolute filesystem paths. Different numeric implementations or dependency versions may produce different results, so those versions are included in cache identity.

Cache entries contain a complete context and a result digest. Corrupt records fail visibly. An incomplete or incompatible record is not silently accepted. Eager and progressive paths have separate caches so the second path does not benefit from the first path's evaluation cache.

Output is protected by a local exclusive writer lock. Files are atomically replaced individually. `run.json` changes to RUNNING before evaluation and COMPLETE at success. A matching `COMPLETE.json` is required to treat outputs as a finished run. This protocol is not a distributed transaction and does not claim universal power-loss recovery on every filesystem.

An interrupted process may leave a lock. Confirm that the writer is gone before manually removing it. Existing output with another signature is rejected. Use a fresh directory for changed code, parameters, data or dependencies.

The parameter sampling utility sorts by semantic IDs before tie-breaking. Its selected rows are reproducible under input permutation and a fixed seed. It is a coverage heuristic over supplied points, not an exact optimal design.
