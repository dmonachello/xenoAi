# M21: separate project history from XenoDream document behavior

## Problem

`ProjectWorkspace` currently owns two distinct concerns. Content-addressed artifacts, deterministic revisions, branches, and atomic `HEAD` updates are useful for any application. XDX parsing, verified XenoDream mutations, structural XDX comparison, native export, and STL validation are XenoDream behavior.

This milestone separates those concerns without changing the CLI, Python imports, schema version, artifact layout, revision IDs, or existing workspace behavior. It does not add speculative ComfyUI or MoI implementations.

## Usage

Existing callers keep the same API:

```python
from xenodream_xxp import ProjectWorkspace

workspace = ProjectWorkspace.open("sculpture.xsp")
workspace.apply(operation, message="change the form")
workspace.create_branch("alternate", checkout=True)
workspace.export("alternate.xxp")
```

The XenoDream workspace now specializes the reusable revision engine:

```python
class ProjectWorkspace(RevisionWorkspace):
    adapter = XenoDreamArtifactAdapter()
```

A future application can reuse `RevisionWorkspace` with its own document adapter. The core never imports XDX records, XenoDream operations, native UI automation, STL reports, or fabrication policy.

## Types and ownership

`xenosculpt.core.model` owns the application-neutral values:

```python
@dataclass(frozen=True, slots=True)
class ApplicationIdentity:
    name: str
    document_kind: str
    artifact_suffix: str

@dataclass(frozen=True, slots=True)
class Revision: ...

@dataclass(frozen=True, slots=True)
class ArtifactInfo: ...

@dataclass(frozen=True, slots=True)
class ApplyResult(Generic[MutationT]): ...

```

`RevisionWorkspace.initialize_history()` creates the shared metadata, revision,
branch, and state tables. It also records the first artifact and binds the
history to one `ApplicationIdentity`. Application workspaces add their own
tables in the same temporary database transaction.

`xenosculpt.core.workspace.RevisionWorkspace` owns artifact storage, hash verification, revision identity, application binding, ref resolution, branches, checkout, history, export, and atomic revision commits.

`xenodream_xxp.adapter.XenoDreamArtifactAdapter` owns XDX admission, exact parser round trips, XenoDream mutation, operation details, and XDX structural comparison.

`xenodream_xxp.workspace.ProjectWorkspace` owns schema-v3 creation and migration, controlled-language plan checks, native XenoDream execution, retained STL evidence, and fabrication assessment. Those records remain application-specific until a second application supplies a real contrasting execution model.

## Module map

```text
src/xenosculpt/core/
  errors.py      application-neutral workspace error
  model.py       revision and artifact transition values
  workspace.py   content-addressed revision engine

src/xenodream_xxp/
  adapter.py     XDX validation, mutation, and comparison
  workspace.py   XenoDream schema, plans, execution, and assessments
```

The old `xenodream_xxp` public imports remain aliases of the moved core values. There is one class definition for each moved type.

## Invariants

- Existing `.xsp` workspaces stay at schema version 3.
- Existing artifact paths remain `artifacts/<sha256>.xxp`.
- Canonical revision JSON and revision IDs do not change.
- A mutation and its revision commit remain one operation from the caller's view.
- The core accepts no XenoDream types and imports no `xenodream_xxp` modules.
- Stored history names its application, document kind, and safe artifact suffix.
- Native validation and fabrication remain outside the reusable core.

## Migration

1. Add architecture tests that require the core package, the concrete adapter, and compatibility type identities.
2. Add the core values, application identity, error, and revision engine.
3. Route source admission, mutation, manual import validation, and comparison through `XenoDreamArtifactAdapter`.
4. Make `ProjectWorkspace` inherit the revision engine and delete the duplicated storage and branch methods.
5. Run the full test suite and packaged CLI smoke tests. Compare a known revision ID before and after the extraction.

## Deliberate limits

This milestone does not add an application registry, a universal scene model, generic execution records, or placeholder ComfyUI and MoI packages. Those abstractions need a second vertical slice. It also does not rename the distribution or the current public package.

## Red-flag review

`RevisionWorkspace` is a deep module: it hides shared schema creation, hashing, verified reads, SQLite transactions, deterministic identities, stale-`HEAD` protection, and atomic writes. XenoDream document types do not leak into its API. The concrete adapter is exercised by current production paths, and the compatibility surface does not duplicate implementations.
