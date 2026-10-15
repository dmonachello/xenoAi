# M4 sphere and mixed-project acceptance

## Static result

The compiler generated two XDX 1.220 projects:

```text
output/m4_generated_sphere.xxp
bytes: 3465
sha256: b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32

output/m4_generated_cube_sphere.xxp
bytes: 4126
sha256: bf4c03b607ed8b27af0840e0dade492f1706bdfad3f31f451df640c65e76bc85
```

Each output is byte-identical to its application-created reference. The full
test suite verifies profile hashes, object identities, allowed transform
fields, unsupported sequences, deterministic output, CLI overwrite refusal,
and exact parser round trips.

This establishes static equivalence. It does not establish application
acceptance for generated paths.

## XenoDream checks

Open `output/m4_generated_sphere.xxp`, confirm that Group1 contains Sphere2
and the preview renders a sphere, then save a copy as
`output/m4_generated_sphere_resaved.xxp`.

Open `output/m4_generated_cube_sphere.xxp`, confirm that Group1 contains
Cube2 at X -50 and Sphere3 at X 50 and that both objects render, then save a
copy as `output/m4_generated_cube_sphere_resaved.xxp`.

Generated sphere and mixed-project support remains pending until those files
open and render and their resaved bytes are compared.
