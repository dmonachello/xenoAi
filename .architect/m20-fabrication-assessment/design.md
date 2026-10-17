# M20 fabrication assessment

## Problem

The workspace stores fabrication constraints and native validation retains an
exact STL, but the constraints are not evaluated. The current mesh predicate
does not detect self-intersections, measure minimum feature size, or apply
process rules. M20 must make the build-volume evidence useful without turning
missing checks into approval. It must also preserve native validation as an
observation of XenoDream, not reinterpret old validation rows under a new
fabrication policy.

## Usage

After native validation, assess the latest successful mesh for `HEAD`:

```powershell
xenosculpt project assess sculpture.xsp
```

Select an earlier revision or an exact validation when needed:

```powershell
xenosculpt project assess sculpture.xsp `
  --ref front-bevel `
  --validation 9ad033cc093e62917b011c7dba9a603b2f11532e57374955f2468cae86d47146
```

The result names the evidence and every required check:

```json
{
  "schema": "xenosculpt-fabrication-assessment/v1",
  "policy": {
    "name": "workspace-constraints",
    "version": "1"
  },
  "revision_id": "...",
  "validation_id": "...",
  "mesh_sha256": "...",
  "verdict": "incomplete",
  "fabrication_suitable": false,
  "checks": [
    {
      "code": "basic-mesh",
      "status": "pass",
      "summary": "mesh passes the current basic topology predicate"
    },
    {
      "code": "build-volume",
      "status": "pass",
      "summary": "measured dimensions fit the configured axes in the current orientation",
      "measured_mm": [113.79, 113.79, 57.31],
      "limit_mm": [220.0, 220.0, 250.0]
    },
    {
      "code": "self-intersections",
      "status": "not_evaluated",
      "summary": "no exact self-intersection analyzer is implemented"
    },
    {
      "code": "minimum-feature",
      "status": "not_evaluated",
      "summary": "the recorded minimum feature has no verified measurement semantics"
    },
    {
      "code": "process",
      "status": "not_evaluated",
      "summary": "FDM is a recorded label, not a versioned process profile"
    }
  ]
}
```

Missing optional workspace constraints produce `not_applicable`, not `pass`.
A failed evaluated check makes the verdict `fail`. Any required unevaluated
check makes it `incomplete`. Only a complete set of passing required checks can
produce `pass` and `fabrication_suitable: true`. M20 cannot produce that result
because exact self-intersection evidence is not available yet.

Python callers use one workspace operation:

```python
assessment = workspace.assess_fabrication(ref="HEAD")

assert assessment.validation_id == validation.id
assert assessment.mesh_sha256 == validation.mesh_sha256
assert workspace.status().head.id == original_head_id
```

## Shape

### Domain model

Add `src/xenodream_xxp/fabrication.py`. Move `FabricationConstraints` from
`workspace.py` into this module and re-export it from `workspace.py` for source
compatibility. The policy and the values it consumes then have one owner.

```python
ASSESSMENT_SCHEMA = "xenosculpt-fabrication-assessment/v1"
WORKSPACE_POLICY = PolicyIdentity("workspace-constraints", "1")


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"
    NOT_APPLICABLE = "not_applicable"


class FabricationVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"


class CheckCode(StrEnum):
    BASIC_MESH = "basic-mesh"
    BUILD_VOLUME = "build-volume"
    SELF_INTERSECTIONS = "self-intersections"
    MINIMUM_FEATURE = "minimum-feature"
    PROCESS = "process"


@dataclass(frozen=True, slots=True)
class FabricationCheck:
    code: CheckCode
    status: CheckStatus
    summary: str
    measured_mm: tuple[float, float, float] | None = None
    limit_mm: tuple[Decimal, Decimal, Decimal] | None = None


@dataclass(frozen=True, slots=True)
class FabricationAssessment:
    id: str
    created_at: str
    revision_id: str
    artifact_sha256: str
    validation_id: str
    mesh_sha256: str
    policy: PolicyIdentity
    constraints: FabricationConstraints
    verdict: FabricationVerdict
    checks: tuple[FabricationCheck, ...]
    schema: str = ASSESSMENT_SCHEMA

    @property
    def fabrication_suitable(self) -> bool:
        return self.verdict is FabricationVerdict.PASS


def evaluate_fabrication(
    mesh: StlReport,
    *,
    constraints: FabricationConstraints,
) -> tuple[FabricationCheck, ...]:
    """Evaluate or account for every workspace-policy check."""
    raise NotImplementedError


def derive_fabrication_verdict(
    checks: tuple[FabricationCheck, ...],
) -> FabricationVerdict:
    raise NotImplementedError
```

Constructors validate stable identifiers, nonempty summaries, the allowed
measurement fields for each check, and exactly one result for every check code.
The verdict is derived from checks and verified when stored JSON is parsed.
This follows `model-the-domain` and `type-system-discipline`: missing evidence
has a value and cannot be confused with success.

The build-volume rule compares `StlReport.dimensions` axis by axis with the
recorded volume. It describes only the exported orientation and allows
translation. It does not rotate, pack, or rescale the mesh. It uses measured
dimensions rather than the exporter maximum because the exporter setting is an
envelope, not the mesh span.

`fabrication.py` also owns canonical JSON conversion. Database dictionaries do
not enter the public API. No numerical fabrication dependency is required in
M20. Later intersection and thickness implementations replace their
`not_evaluated` results behind the same evaluation call.

The version 1 policy freezes both its required check set and the statuses that
each check can produce. In particular, `self-intersections` cannot claim
`pass`, and version 1 cannot produce an overall `pass`. A future analyzer must
use a new policy version. That version becomes part of the cache identity and
defines its own required checks.

### Workspace operation and persistence

`ProjectWorkspace` adds one operation:

```python
def assess_fabrication(
    self,
    *,
    ref: str = "HEAD",
    validation_id: str | None = None,
) -> FabricationAssessment:
    """Assess an exact stored validation mesh without changing HEAD."""
    raise NotImplementedError
```

The method resolves `ref` once. When `validation_id` is absent, it selects the
latest successful mesh-bearing validation for that revision. When an ID is
provided, it must name a validation for the same revision. The method then:

1. Loads the canonical `meshes/<sha256>.stl`.
2. Verifies its SHA-256 before cache lookup.
3. Inspects the mesh again from canonical bytes.
4. Snapshots normalized workspace constraints.
5. Evaluates all checks and derives the verdict.
6. Inserts or returns one immutable assessment.

The cache request contains the assessment schema, policy identity, revision
ID, artifact hash, validation ID, mesh hash, and normalized constraints. Paths,
timestamps, `HEAD`, and CLI spelling are excluded. A unique request key plus
`INSERT OR IGNORE` makes repeated or concurrent identical requests converge.
On every read, the workspace recomputes the request key and assessment ID from
the stored result. It also compares the result with the table's validation,
policy, and constraints fields. Inconsistent cached provenance is an error.

Workspace schema version 3 adds an independent table:

```sql
CREATE TABLE fabrication_assessments (
    id TEXT PRIMARY KEY,
    request_key TEXT NOT NULL UNIQUE,
    validation_id TEXT NOT NULL REFERENCES validations(id),
    created_at TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    constraints_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE INDEX fabrication_assessments_validation_created
ON fabrication_assessments(validation_id, created_at DESC, id DESC);
```

The validation row remains unchanged. Existing version 1 and version 2
workspaces migrate through ordered additive steps. Old revisions, validations,
and mesh files keep their identities. Assessment never calls
`_record_revision()` and never changes a branch or detached `HEAD`.

`WorkspaceStatus` adds the latest fabrication assessment for the current
revision. The status lookup joins through validation so an assessment cannot
silently follow a branch to another revision.

### CLI

Add `project assess WORKSPACE [--ref REF] [--validation ID]`. The command
prints the complete assessment. Exit code `0` means `pass`; exit code `1`
means `fail` or `incomplete`; malformed input or missing evidence retains the
existing error exit path. This makes the command safe as a fabrication gate
without changing `project validate`, whose exit code still means basic mesh
validity.

### Module map

- `fabrication.py` owns constraints, the versioned policy, check results,
  verdict derivation, build-volume semantics, and JSON conversion.
- `mesh.py` remains the standard-library source of mesh facts.
- `native_export.py` remains responsible only for supervised XenoDream export.
- `workspace.py` binds assessment to immutable revision-validation-mesh
  evidence and owns caching and schema migration.
- `cli.py` parses selection arguments and prints the domain result. It contains
  no fabrication policy.

The call chain is `CLI -> ProjectWorkspace.assess_fabrication() ->
evaluate_fabrication()`. One public operation hides evidence selection, hash
verification, policy completeness, caching, and persistence. This is the deep
module boundary selected per `boundary-discipline` and
`minimize-reader-load`.

## Synthesis decision

The immutable-evidence candidate is the base because a separate assessment
record preserves the meaning and cache identity of native validation. The
future-policy candidate supplied the fixed check vocabulary and the rule that
missing required evidence must make the report incomplete. The simple
candidate supplied the compact three-state user model and confirmed that M20
needs no new numerical dependency.

The simple candidate's embedded assessment was rejected because native
validation should not change when a fabrication policy changes. The
evidence-first candidate's required `--profile` flag was removed because only
one policy exists. The future candidate's public policy registry and separate
evidence variants were rejected for M20 because no second implementation or
process profile exists. The optional validation ID preserves exact automation
without making the common user copy an ID between commands.

## Tradeoffs accepted

- We accept an `incomplete` first milestone in exchange for never presenting
  partial evidence as fabrication approval.
- We accept current-orientation axis comparison in exchange for one measured,
  deterministic build-volume rule.
- We accept a separate table and schema migration in exchange for preserving
  native validation identity and supporting later policy versions.
- We accept rehashing and reinspecting the retained mesh in exchange for
  detecting missing or corrupted evidence before returning a cached result.
- We accept a fixed built-in check list in exchange for a complete report with
  no public plug-in protocol before a second analyzer exists.

## Alternatives considered

Embedding the assessment in `validations` lost because a policy change would
change the meaning of old native evidence and prevent multiple assessments of
one mesh.

Adding fields to `StlReport` lost because mesh observations do not depend on a
printer profile, while fabrication decisions do.

A public analyzer registry lost because it exposes internal dispatch and
completeness rules without hiding any M20 complexity.

Automatic repair lost because it changes the subject under evaluation. Repair
must create a separate derived mesh and measure deviation from the native
export before that mesh can be assessed.

## Open questions and risks

- What exact property will replace the ambiguous `min_feature_mm`: wall
  thickness, clearance, neck diameter, retained detail, or a typed set?
- Which triangle-intersection algorithm and tolerance can scale to the retained
  442,364-triangle meshes?
- Will a future profile allow orthogonal rotation, arbitrary orientation, or
  only the exported orientation for build-volume fit?
- Must every future passing profile require a typed process, or may a
  process-independent geometry profile pass?
- Which distance metric and tolerance will define repair deviation?

## Implementation verification

The implementation added failing-first tests for verdict derivation,
axis-specific build-volume outcomes, missing constraints, schema migration,
deterministic reuse, mesh corruption, cached-provenance corruption, policy
versioning, decimal precision, unchanged workspace `HEAD`, and the CLI exit
contract. The full suite passes 219 tests. The packaged executable also
assessed a copied external workspace against its retained mesh and preserved
`HEAD`.
