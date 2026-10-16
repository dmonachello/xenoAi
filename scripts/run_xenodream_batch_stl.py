"""Run the packaged supervised XenoDream STL exporter."""

from xenodream_xxp.native_export import (
    MeshExportSettings,
    classify_timeout,
    inspect_binary_stl,
    main,
    run_export,
)


if __name__ == "__main__":
    raise SystemExit(main())
