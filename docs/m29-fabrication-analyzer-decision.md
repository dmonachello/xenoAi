# M29 fabrication analyzer decision

M29 does not promote `fabrication_suitable` to true.

The installed fabrication dependencies provide STL parsing, numerical arrays,
spatial indexing, and image/voxel algorithms. They do not provide a retained,
versioned triangle self-intersection validator with defined adjacency,
coplanar-contact, tolerance, and resource-limit semantics. Implementing an
ad-hoc floating-point triangle test would create an unsafe false-negative path:
an empty result could be mistaken for proof that the mesh is intersection-free.

The existing policy therefore remains the honest result:

- basic topology is evaluated;
- current-orientation axis-aligned build-volume fit is evaluated when configured;
- self-intersection remains `not_evaluated`;
- minimum feature remains `not_evaluated` when configured because no wall or
  local-thickness metric has been selected;
- process rules remain `not_evaluated` because `process` is a label, not a
  nozzle/material/layer/support/tolerance profile.

This is the milestone stop gate, not an implementation omission. A later policy
version must first check in generated oracle meshes covering transverse
crossings, coplanar overlaps, shared edges and vertices, near contacts, thin
closed walls, scale changes, and resource exhaustion. Its analyzer identity,
tolerance definition, limits, mesh hash, validation ID, revision ID, and policy
version must all participate in cache identity. Unknown, timeout, and unsupported
cases must remain incomplete.

Physical fabrication, repair, orientation choice, material selection, and
process acceptance belong to M30 and require human input.
