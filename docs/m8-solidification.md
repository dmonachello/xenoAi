# M8 geometric solidification

Date: 2026-10-16

## Result

`xenosculpt solidify-stl` now adds material to an exported closed STL by a
caller-selected distance in millimetres. It writes a new mesh and leaves the
native `.xxp` and source STL untouched.

```powershell
xenosculpt solidify-stl input.stl output-solid.stl `
  --amount-mm 1.0 --voxel-mm 0.5
```

The command voxelizes the closed source, applies a Euclidean outward offset,
reconstructs an isosurface, writes binary STL, and reruns the independent mesh
checks. It refuses open or non-manifold input, an existing output path, an
offset smaller than one voxel, and a grid above the configured memory limit.

This is geometric thickening. It is not slicer infill or wall count. It may
merge gaps narrower than about twice the offset. The report keeps
`printability_established=false` because the current checker still lacks
self-intersection, local thickness, overhang, and process-specific tests.

## Native-control investigation

XenoDream has two controls whose names looked relevant at first.

The Active Holon `Relative Density` control writes a double-valued field through
handler `0x77f488` and callback `0x5e36d0`. A controlled probe changed only
`Holon\1.Density` to -0.5000 and +0.5000. All three native files evaluated and
exported. Bounds, triangle count, topology, and volume did not change beyond
the application's measured run-to-run mesh variation. We therefore do not map
Relative Density to solidification.

Mesh Export `Shell size` is part of simplification. Its embedded help says that
simplification removes excluded pieces starting with the smallest. It can
discard small components, but it does not thicken walls.

See `evidence/runtime/solidify-density-probe-summary.json` for the measurements.

## Real-mesh checkpoint

The source was XenoDream's 100 mm, 25 percent Mesh Size export of the accepted
Cube/Sphere scene.

| Measurement | Source | 1 mm solidified result |
| --- | ---: | ---: |
| Triangles | 27,108 | 53,584 |
| Maximum dimension | 95.839 mm | 98.000 mm |
| Absolute volume | 196,456.905 mm3 | 218,906.579 mm3 |
| Connected components | 1 | 1 |
| Boundary edges | 0 | 0 |
| Non-manifold edges | 0 | 0 |
| Winding conflicts | 0 | 0 |
| Degenerate triangles | 0 | 0 |

The final output hash was
`b5b86c55c88f264dd4d6fb9b84755badb7f6eaca7bca6749979eadea874f00ad`.
Its signed volume was positive 218,906.579 mm3.

The trimmed standalone executable is 60,667,853 bytes with SHA-256
`106d74027d58f82d5ee0b3eb0a32e526b124aa425db73f845a17bae0518e4a86`.
It reproduced the same solidified STL hash as the Python command.

## Limits

- `voxel-mm` controls fidelity. Features near that size may move or disappear.
- The operation increases overall dimensions and may close intended holes.
- The thickened STL is a fabrication derivative. It is not imported into the
  editable XenoDream project.
- A closed edge-manifold STL is not automatically printable.
