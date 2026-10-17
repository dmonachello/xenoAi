"""Command-line interface for `.xxp` inspection and preservation checks."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Sequence

from .diffing import diff_documents
from .document import parse_bytes
from .generator import (
    COMPILER_PROFILE,
    CUBE_SPHERE_COMPILER_PROFILE,
    CYLINDER_COMPILER_PROFILE,
    CubeProjectSpec,
    CubeSpec,
    CylinderSpec,
    GenerationError,
    ProjectSpec,
    SPHERE_COMPILER_PROFILE,
    SphereSpec,
    THREE_CUBE_COMPILER_PROFILE,
    TWO_CUBE_COMPILER_PROFILE,
    ThreeCubeProjectSpec,
    Vector3,
    compile_cube,
    compile_cube_project,
    compile_cylinder,
    compile_project,
    compile_sphere,
    compile_three_cubes,
)
from .report import inspect_document
from .metamorph import inspect_metamorphs
from .recipes import centered_x_row
from .mesh import inspect_binary_stl
from .native_export import DEFAULT_XENODREAM_EXECUTABLE, MeshExportSettings
from .solidify import SolidifySettings, solidify_binary_stl
from .mutation import (
    CenteredRowMutation,
    CylinderMetamorphMutation,
    ObjectMutation,
    SeededVariation,
    SphereMetamorphMutation,
    cylinder_metamorph_profiles,
    sphere_metamorph_profiles,
)
from .workspace import FabricationConstraints, ProjectWorkspace


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xenosculpt")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_command = commands.add_parser("inspect", help="print a JSON structure report")
    inspect_command.add_argument("input", type=Path)

    inspect_metamorph_command = commands.add_parser(
        "inspect-metamorphs",
        help="print persisted metamorph stacks with evidence-scoped meanings",
    )
    inspect_metamorph_command.add_argument("input", type=Path)

    roundtrip = commands.add_parser(
        "roundtrip", help="parse and write an unchanged byte-identical copy"
    )
    roundtrip.add_argument("input", type=Path)
    roundtrip.add_argument("output", type=Path)

    diff = commands.add_parser("diff", help="compare keys and value tokens")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)

    validate_stl = commands.add_parser(
        "validate-stl", help="inspect binary STL structure and basic topology"
    )
    validate_stl.add_argument("input", type=Path)

    solidify_stl = commands.add_parser(
        "solidify-stl",
        help="create a thicker derived STL while retaining the native source",
    )
    solidify_stl.add_argument("input", type=Path)
    solidify_stl.add_argument("output", type=Path)
    solidify_stl.add_argument("--amount-mm", type=Decimal, required=True)
    solidify_stl.add_argument(
        "--voxel-mm", type=Decimal, default=Decimal("0.5")
    )
    solidify_stl.add_argument("--max-voxels", type=int, default=30_000_000)

    generate = commands.add_parser(
        "generate-cube", help="create a deterministic XDX 1.220 cube project"
    )
    generate.add_argument("output", type=Path)
    generate.add_argument(
        "--scale",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("50"), Decimal("50"), Decimal("50")),
    )
    generate.add_argument(
        "--rotation",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )
    generate.add_argument(
        "--position",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )
    generate.add_argument("--color-density", type=Decimal, default=Decimal("1"))
    generate.add_argument("--face-warp", type=Decimal, default=Decimal("0"))

    generate_three = commands.add_parser(
        "generate-three-cubes",
        help="create the evidenced XDX 1.220 three-cube project",
    )
    generate_three.add_argument("output", type=Path)
    generate_three.add_argument(
        "--position",
        nargs=3,
        action="append",
        type=Decimal,
        metavar=("X", "Y", "Z"),
        help="cube position; if supplied, repeat exactly three times",
    )

    generate_two = commands.add_parser(
        "generate-two-cubes",
        help="create the evidenced XDX 1.220 two-cube project",
    )
    generate_two.add_argument("output", type=Path)
    generate_two.add_argument(
        "--position",
        nargs=3,
        action="append",
        type=Decimal,
        metavar=("X", "Y", "Z"),
        help="cube position; if supplied, repeat exactly two times",
    )

    generate_sphere = commands.add_parser(
        "generate-sphere",
        help="create the verified XDX 1.220 sphere project",
    )
    generate_sphere.add_argument("output", type=Path)

    generate_cylinder = commands.add_parser(
        "generate-cylinder",
        help="create the binary-recovered default XDX 1.220 Cylinder project",
    )
    generate_cylinder.add_argument("output", type=Path)
    generate_cylinder.add_argument(
        "--scale",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("50"), Decimal("50"), Decimal("50")),
    )
    generate_cylinder.add_argument(
        "--position",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )

    generate_cube_sphere = commands.add_parser(
        "generate-cube-sphere",
        help="create the verified Cube2 and Sphere3 project",
    )
    generate_cube_sphere.add_argument("output", type=Path)

    generate_row = commands.add_parser(
        "generate-row",
        help="place a supported object sequence in a centered X-axis row",
    )
    generate_row.add_argument("output", type=Path)
    generate_row.add_argument(
        "objects",
        nargs="+",
        choices=("cube", "sphere"),
        help="ordered object sequence",
    )
    generate_row.add_argument("--spacing", type=Decimal, required=True)
    generate_row.add_argument(
        "--center",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )

    project = commands.add_parser(
        "project", help="manage native artifacts, revisions, branches, and mutations"
    )
    project_commands = project.add_subparsers(dest="project_command", required=True)

    project_init = project_commands.add_parser(
        "init", help="create a revision workspace from an existing XDX project"
    )
    project_init.add_argument("workspace", type=Path)
    project_init.add_argument("source", type=Path)
    project_init.add_argument("--process")
    project_init.add_argument(
        "--build-volume", nargs=3, type=Decimal, metavar=("X", "Y", "Z")
    )
    project_init.add_argument("--min-feature-mm", type=Decimal)

    project_status = project_commands.add_parser(
        "status", help="show the current branch, revision, artifact, and constraints"
    )
    project_status.add_argument("workspace", type=Path)

    project_validate = project_commands.add_parser(
        "validate",
        help="evaluate a revision in isolated XenoDream and attach an STL report",
    )
    project_validate.add_argument("workspace", type=Path)
    project_validate.add_argument("--ref", default="HEAD")
    project_validate.add_argument(
        "--executable", type=Path, default=DEFAULT_XENODREAM_EXECUTABLE
    )
    project_validate.add_argument("--stl-max-dimension-mm", type=int, default=250)
    project_validate.add_argument("--mesh-size-percent", type=int, default=50)
    project_validate.add_argument("--timeout-seconds", type=float, default=600)
    project_validate.add_argument("--poll-seconds", type=float, default=1)

    project_mutate = project_commands.add_parser(
        "mutate", help="apply verified fields to one uniquely named object"
    )
    project_mutate.add_argument("workspace", type=Path)
    project_mutate.add_argument("--object", required=True)
    project_mutate.add_argument("--scale", nargs=3, type=Decimal, metavar=("X", "Y", "Z"))
    project_mutate.add_argument(
        "--rotation", nargs=3, type=Decimal, metavar=("X", "Y", "Z")
    )
    project_mutate.add_argument(
        "--position", nargs=3, type=Decimal, metavar=("X", "Y", "Z")
    )
    project_mutate.add_argument("--color-density", type=Decimal)
    project_mutate.add_argument("--face-warp", type=Decimal)
    project_mutate.add_argument("--message", required=True)
    project_mutate.add_argument("--prompt")

    project_metamorph = project_commands.add_parser(
        "metamorph", help="apply one measured metamorph profile"
    )
    project_metamorph.add_argument("workspace", type=Path)
    project_metamorph.add_argument(
        "--operation", choices=("Sphere", "Cylinder"), default="Sphere"
    )
    project_metamorph.add_argument("--object", required=True)
    project_metamorph.add_argument(
        "--profile",
        required=True,
        choices=sphere_metamorph_profiles() + cylinder_metamorph_profiles(),
    )
    project_metamorph.add_argument("--message", required=True)
    project_metamorph.add_argument("--prompt")

    project_row = project_commands.add_parser(
        "row", help="place the current supported objects in a centered X-axis row"
    )
    project_row.add_argument("workspace", type=Path)
    project_row.add_argument("--spacing", type=Decimal, required=True)
    project_row.add_argument(
        "--center",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )
    project_row.add_argument("--message", required=True)
    project_row.add_argument("--prompt")

    project_evolve = project_commands.add_parser(
        "evolve", help="derive a deterministic physical-form variation"
    )
    project_evolve.add_argument("workspace", type=Path)
    project_evolve.add_argument("--seed", type=int, required=True)
    project_evolve.add_argument(
        "--strength", type=Decimal, default=Decimal("0.35")
    )
    project_evolve.add_argument("--message", required=True)
    project_evolve.add_argument("--prompt")

    project_branch = project_commands.add_parser(
        "branch", help="create a branch at a revision or the current HEAD"
    )
    project_branch.add_argument("workspace", type=Path)
    project_branch.add_argument("name")
    project_branch.add_argument("--from", dest="from_ref", default="HEAD")
    project_branch.add_argument("--checkout", action="store_true")

    project_checkout = project_commands.add_parser(
        "checkout", help="restore HEAD to a branch or revision"
    )
    project_checkout.add_argument("workspace", type=Path)
    project_checkout.add_argument("ref")

    project_log = project_commands.add_parser(
        "log", help="show revision ancestry from a branch, revision, or HEAD"
    )
    project_log.add_argument("workspace", type=Path)
    project_log.add_argument("--ref", default="HEAD")

    project_compare = project_commands.add_parser(
        "compare", help="compare two branches or revisions"
    )
    project_compare.add_argument("workspace", type=Path)
    project_compare.add_argument("before")
    project_compare.add_argument("after")

    project_export = project_commands.add_parser(
        "export", help="write one revision as an editable native XDX project"
    )
    project_export.add_argument("workspace", type=Path)
    project_export.add_argument("output", type=Path)
    project_export.add_argument("--ref", default="HEAD")

    project_import = project_commands.add_parser(
        "import", help="record a manually edited XDX project as a revision"
    )
    project_import.add_argument("workspace", type=Path)
    project_import.add_argument("source", type=Path)
    project_import.add_argument("--message", required=True)
    project_import.add_argument("--prompt")
    return parser


def _print_json(value: object) -> None:
    def encode(item: object) -> str:
        if isinstance(item, (Decimal, Path)):
            return str(item)
        raise TypeError(f"cannot serialize {type(item).__name__} as JSON")

    print(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            default=encode,
        )
    )


def _vector(values: Sequence[Decimal] | None) -> Vector3 | None:
    return None if values is None else Vector3(*values)


def _handle_project(args: argparse.Namespace) -> int:
    if args.project_command == "init":
        constraints = FabricationConstraints(
            process=args.process,
            build_volume_mm=_vector(args.build_volume),
            min_feature_mm=args.min_feature_mm,
        )
        workspace = ProjectWorkspace.create(args.workspace, args.source, constraints)
        _print_json(asdict(workspace.status()))
        return 0

    workspace = ProjectWorkspace.open(args.workspace)
    if args.project_command == "status":
        _print_json(asdict(workspace.status()))
        return 0
    if args.project_command == "validate":
        validation = workspace.validate_native(
            ref=args.ref,
            executable=args.executable,
            settings=MeshExportSettings(
                stl_max_dimension_mm=args.stl_max_dimension_mm,
                mesh_size_percent=args.mesh_size_percent,
            ),
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
        _print_json(asdict(validation))
        return 0 if validation.basic_mesh_valid else 1
    if args.project_command == "mutate":
        result = workspace.apply(
            ObjectMutation(
                object_name=args.object,
                scale=_vector(args.scale),
                rotation=_vector(args.rotation),
                position=_vector(args.position),
                color_density=args.color_density,
                face_warp=args.face_warp,
            ),
            message=args.message,
            prompt=args.prompt,
        )
        _print_json(
            {
                "created": result.created,
                "revision": asdict(result.revision),
                "differences": []
                if result.mutation is None
                else result.mutation.differences,
            }
        )
        return 0
    if args.project_command == "metamorph":
        operation = (
            SphereMetamorphMutation(args.object, args.profile)
            if args.operation == "Sphere"
            else CylinderMetamorphMutation(args.object, args.profile)
        )
        result = workspace.apply(
            operation,
            message=args.message,
            prompt=args.prompt,
        )
        native_validation_required = (
            result.mutation.native_validation_required
            if result.mutation is not None
            else bool(result.revision.details.get("native_validation_required"))
        )
        fabrication_suitable = (
            result.mutation.fabrication_suitable
            if result.mutation is not None
            else bool(result.revision.details.get("fabrication_suitable"))
        )
        _print_json(
            {
                "created": result.created,
                "revision": asdict(result.revision),
                "differences": []
                if result.mutation is None
                else result.mutation.differences,
                "native_validation_required": native_validation_required,
                "fabrication_suitable": fabrication_suitable,
            }
        )
        return 0
    if args.project_command == "row":
        result = workspace.apply(
            CenteredRowMutation(args.spacing, Vector3(*args.center)),
            message=args.message,
            prompt=args.prompt,
        )
        _print_json(
            {
                "created": result.created,
                "revision": asdict(result.revision),
                "differences": []
                if result.mutation is None
                else result.mutation.differences,
            }
        )
        return 0
    if args.project_command == "evolve":
        result = workspace.apply(
            SeededVariation(args.seed, args.strength),
            message=args.message,
            prompt=args.prompt,
        )
        _print_json(
            {
                "created": result.created,
                "revision": asdict(result.revision),
                "differences": []
                if result.mutation is None
                else result.mutation.differences,
            }
        )
        return 0
    if args.project_command == "branch":
        revision = workspace.create_branch(
            args.name, from_ref=args.from_ref, checkout=args.checkout
        )
        _print_json(
            {
                "branch": args.name,
                "revision": asdict(revision),
                "checked_out": args.checkout,
            }
        )
        return 0
    if args.project_command == "checkout":
        _print_json(asdict(workspace.checkout(args.ref)))
        return 0
    if args.project_command == "log":
        _print_json([asdict(item) for item in workspace.history(args.ref)])
        return 0
    if args.project_command == "compare":
        differences = workspace.compare(args.before, args.after)
        _print_json(
            {
                "before": args.before,
                "after": args.after,
                "differences": differences,
            }
        )
        return 1 if differences else 0
    if args.project_command == "export":
        _print_json(asdict(workspace.export(args.output, args.ref)))
        return 0
    if args.project_command == "import":
        result = workspace.import_artifact(
            args.source, message=args.message, prompt=args.prompt
        )
        _print_json(
            {"created": result.created, "revision": asdict(result.revision)}
        )
        return 0
    raise ValueError(f"unsupported project command: {args.project_command}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "project":
            return _handle_project(args)

        if args.command == "inspect":
            document = parse_bytes(args.input.read_bytes())
            _print_json(inspect_document(document))
            return 0

        if args.command == "inspect-metamorphs":
            document = parse_bytes(args.input.read_bytes())
            _print_json(inspect_metamorphs(document))
            return 0

        if args.command == "roundtrip":
            if args.output.exists():
                print(f"refusing to overwrite: {args.output} already exists", file=sys.stderr)
                return 2
            source = args.input.read_bytes()
            output = parse_bytes(source).to_bytes()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "input": str(args.input),
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "byte_identical": source == output,
                }
            )
            return 0 if source == output else 1

        if args.command == "validate-stl":
            report = inspect_binary_stl(args.input)
            result = asdict(report)
            result["basic_mesh_valid"] = all(
                (
                    report.degenerate_triangles == 0,
                    report.boundary_edges == 0,
                    report.non_manifold_edges == 0,
                    report.inconsistent_winding_edges == 0,
                    report.connected_components == 1,
                    report.signed_volume != 0,
                )
            )
            result["printability_established"] = False
            _print_json(result)
            return 0 if result["basic_mesh_valid"] else 1

        if args.command == "solidify-stl":
            report = solidify_binary_stl(
                args.input,
                args.output,
                SolidifySettings(
                    amount_mm=args.amount_mm,
                    voxel_mm=args.voxel_mm,
                    max_voxels=args.max_voxels,
                ),
            )
            _print_json(asdict(report))
            return 0

        if args.command == "generate-cube":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            output = compile_cube(
                CubeSpec(
                    scale=Vector3(*args.scale),
                    rotation=Vector3(*args.rotation),
                    position=Vector3(*args.position),
                    color_density=args.color_density,
                    face_warp=args.face_warp,
                )
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": COMPILER_PROFILE,
                }
            )
            return 0

        if args.command == "generate-three-cubes":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            if args.position is None:
                spec = ThreeCubeProjectSpec()
            else:
                if len(args.position) != 3:
                    raise GenerationError(
                        "--position must be omitted or repeated exactly 3 times"
                    )
                spec = ThreeCubeProjectSpec(
                    cubes=tuple(
                        CubeSpec(position=Vector3(*position))
                        for position in args.position
                    )
                )
            output = compile_three_cubes(spec)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": THREE_CUBE_COMPILER_PROFILE,
                    "cube_count": 3,
                }
            )
            return 0

        if args.command == "generate-two-cubes":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            positions = args.position or [
                (Decimal("-50"), Decimal("0"), Decimal("0")),
                (Decimal("50"), Decimal("0"), Decimal("0")),
            ]
            if len(positions) != 2:
                raise GenerationError(
                    "--position must be omitted or repeated exactly 2 times"
                )
            output = compile_cube_project(
                CubeProjectSpec(
                    cubes=tuple(
                        CubeSpec(position=Vector3(*position))
                        for position in positions
                    )
                )
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": TWO_CUBE_COMPILER_PROFILE,
                    "cube_count": 2,
                }
            )
            return 0

        if args.command == "generate-sphere":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            output = compile_sphere()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": SPHERE_COMPILER_PROFILE,
                }
            )
            return 0

        if args.command == "generate-cylinder":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            output = compile_cylinder(
                CylinderSpec(
                    scale=Vector3(*args.scale),
                    position=Vector3(*args.position),
                )
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": CYLINDER_COMPILER_PROFILE,
                    "native_validation_required": True,
                    "fabrication_suitable": False,
                }
            )
            return 0

        if args.command == "generate-cube-sphere":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            output = compile_project(
                ProjectSpec(
                    objects=(
                        CubeSpec(
                            position=Vector3(
                                Decimal("-50"), Decimal("0"), Decimal("0")
                            )
                        ),
                        SphereSpec(
                            position=Vector3(
                                Decimal("50"), Decimal("0"), Decimal("0")
                            )
                        ),
                    )
                )
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": CUBE_SPHERE_COMPILER_PROFILE,
                }
            )
            return 0

        if args.command == "generate-row":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            object_types = {"cube": CubeSpec, "sphere": SphereSpec}
            objects = tuple(object_types[name]() for name in args.objects)
            project = centered_x_row(
                objects,
                spacing=args.spacing,
                center=Vector3(*args.center),
            )
            output = compile_project(project)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "recipe": "centered-x-row",
                    "objects": args.objects,
                    "spacing": str(args.spacing),
                    "center": [str(value) for value in args.center],
                }
            )
            return 0

        before = parse_bytes(args.before.read_bytes())
        after = parse_bytes(args.after.read_bytes())
        differences = diff_documents(before, after)
        _print_json(
            {
                "before": str(args.before),
                "after": str(args.after),
                "byte_identical": before.to_bytes() == after.to_bytes(),
                "differences": differences,
            }
        )
        return 1 if differences else 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
