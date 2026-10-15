# M4 sphere and mixed-project acceptance

## Static result

The compiler generated two XDX 1.220 projects:

```text
output/m4_generated_sphere.xxp
bytes: 3400
sha256: 19bdf9608585ea50de30490d08ac0ae80aa96803d6de6028191559ba314f9013

output/m4_generated_cube_sphere.xxp
bytes: 4126
sha256: bf4c03b607ed8b27af0840e0dade492f1706bdfad3f31f451df640c65e76bc85
```

Each output matches its current application-created reference. The full test
suite verifies profile hashes, object identities, allowed transform fields,
unsupported sequences, deterministic output, CLI overwrite refusal, and exact
parser round trips.

## Application result

XenoDream opened and rendered both generated projects.

The mixed generated and resaved files are byte-identical. Both have 4,126
bytes and SHA-256
`bf4c03b607ed8b27af0840e0dade492f1706bdfad3f31f451df640c65e76bc85`.

The initial sphere file opened and rendered, but XenoDream changed
`SelectionSpots.0` from the old 27-token value to `3 1 1` when it saved the
file. No other value changed. The compiler now uses that 3,400-byte resaved
file as the sphere template.

Application status: accepted for the default sphere and the tested Cube2 plus
Sphere3 profile. The `SelectionSpots` meaning remains unknown.
