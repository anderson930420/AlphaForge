# refactor-storage-artifact-ownership

Separate in-memory runtime result contracts from persisted artifact schemas and assign authoritative ownership for serialization, paths, and artifact layout.

Final migration state:

- `ExperimentResult` no longer carries persisted artifact paths.
- `ArtifactReceipt` is the storage-owned contract for persisted experiment artifact references.
- New callers must be receipt-first.
