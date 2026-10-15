# Cube and sphere project

## Controlled result

The XDX 1.220 project contains Group1 with Cube2 at X -50 followed by Sphere3
at X 50. XenoDream displayed both objects in the tree and rendered both in the
preview shown in the user's screenshot.

```text
bytes: 4126
sha256: bf4c03b607ed8b27af0840e0dade492f1706bdfad3f31f451df640c65e76bc85
line endings: 233 CRLF records; no bare CR or LF
```

Against the clean two-cube reference, exactly four values differ. All four
belong to the second child:

- `Holon\2.Name` changes from `Cube3` to `Sphere3`.
- `Holon\2\MM\0.Style` changes from 5 to 1.
- `Holon\2\MM\0.NumPars` changes from 9 to 12.
- `Holon\2\MM\0.Pars` changes from the nine-token cube payload to the
  twelve-token sphere payload.

The bytes through Cube2 and all bytes from `[Gradients]` to the end match the
two-cube reference. After normalizing section number, ID, name, and X position,
the Sphere3 holon and metamorph block match the earlier Sphere2 baseline byte
for byte.

## Scope

This proves one application-created order: Cube2 followed by Sphere3. It does
not prove that Style 1 alone selects sphere geometry, that names are freely
editable, or that sphere-first, repeated-sphere, and longer mixed sequences
work. The Style 1 parameter meanings remain unknown.

The compiler now reproduces this reference statically. Generated-file
acceptance still requires XenoDream to open, render, and resave
`output/m4_generated_cube_sphere.xxp`.
