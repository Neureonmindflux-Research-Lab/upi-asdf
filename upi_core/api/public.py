from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..telemetry.logger import get_logger
from ..utils.yaml_tools import load_yaml
from ..config_system.spec_schema import normalize_pipeline_spec
from ..config_system.interpolation import interpolate_config
from ..config_system.validation import validate_pipeline_config
from ..config_system.resolver import PipelineResolver
from ..plugin_system.discovery_fs import discover_plugins_fs
from ..plugin_system.discovery_entrypoints import discover_plugins_entrypoints
from ..plugin_system.validator import validate_manifests
from ..plugin_system.registry import PluginRegistry
from ..plugin_system.enablelist import load_enablelist
from ..runtime.context import RuntimeContext
from ..runtime.engine import Engine
from ..telemetry.audit import AuditLog
from ..runtime.exceptions import ConfigError
from .types import PipelineSpec
from ..plugin_system.plugin_paths import add_plugin_roots


log = get_logger("upi.api")


YamlLike = Union[str, Path, Dict[str, Any]]


def load_pipeline(source: YamlLike, *, repo_root: Optional[Union[str, Path]] = None) -> PipelineSpec:
    """
    Load and normalize a pipeline spec from YAML/path/dict.
    Also applies interpolation (${env}, ${path}, ${ref}).
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()

    raw = load_yaml(source)
    raw = normalize_pipeline_spec(raw)
    raw = interpolate_config(raw, base_path=root)

    return PipelineSpec.model_validate(raw)


def scan_plugins(
    *,
    repo_root: Optional[Union[str, Path]] = None,
    plugin_dirs: Optional[List[Union[str, Path]]] = None,
    fs: bool = True,
    entrypoints: bool = True,
) -> PluginRegistry:
    """
    Discover + validate + register plugins into a registry.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    add_plugin_roots(repo_root=root, extra_roots=plugin_dirs)
    enablelist = load_enablelist(root)

    manifests = []
    if fs:
        manifests.extend(discover_plugins_fs(root, plugin_dirs=plugin_dirs))
    if entrypoints:
        manifests.extend(discover_plugins_entrypoints())

    valid = validate_manifests(manifests, enablelist=enablelist)
    reg = PluginRegistry(enablelist=enablelist)
    reg.register_all(valid)
    return reg


def list_plugins(
    registry: PluginRegistry,
    *,
    plugin_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List registered plugins in the registry.
    """
    items = registry.list(plugin_type=plugin_type)
    return [m.model_dump() for m in items]


def validate(
    pipeline: Union[PipelineSpec, YamlLike],
    *,
    registry: Optional[PluginRegistry] = None,
    repo_root: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Validate pipeline against available plugins.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    spec = pipeline if isinstance(pipeline, PipelineSpec) else load_pipeline(pipeline, repo_root=root)
    reg = registry or scan_plugins(repo_root=root)
    return validate_pipeline_config(spec, reg, raise_on_error=False)


def explain(
    pipeline: Union[PipelineSpec, YamlLike],
    *,
    registry: Optional[PluginRegistry] = None,
    repo_root: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Explain plugin selection for each stage.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    spec = pipeline if isinstance(pipeline, PipelineSpec) else load_pipeline(pipeline, repo_root=root)
    reg = registry or scan_plugins(repo_root=root)

    out: Dict[str, Any] = {}
    for stage in spec.stages():
        out[stage.name] = reg.explain_selection(
            plugin_type=stage.uses.plugin_type,
            capability=stage.uses.capability,
            prefer=stage.uses.prefer,
            version_constraint=stage.uses.version,
        )
    return out


def run(
    pipeline: Union[PipelineSpec, YamlLike],
    *,
    registry: Optional[PluginRegistry] = None,
    repo_root: Optional[Union[str, Path]] = None,
    scheduler: str = "local",
    limits: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run a pipeline.
    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    add_plugin_roots(repo_root=root)
    spec = pipeline if isinstance(pipeline, PipelineSpec) else load_pipeline(pipeline, repo_root=root)
    reg = registry or scan_plugins(repo_root=root)

    # validate hard
    validate_pipeline_config(spec, reg, raise_on_error=True)

    # build context
    workdir = spec.case.workdir or root
    ctx = RuntimeContext(
        seed=spec.case.seed,
        device=spec.case.device,
        workdir=Path(workdir),
        rundir=Path(workdir) / "runs" / "latest",
        tags={k: str(v) for k, v in {"tags": ",".join(spec.case.tags)}.items()},
    )

    audit = AuditLog(ctx.rundir / "audit.jsonl")
    engine = Engine(
        registry=reg,
        context=ctx,
        audit=audit,
        scheduler_name=scheduler,
        limits=limits or {},
    )

    try:
        result = engine.run(spec)
    except Exception as e:
        audit.write({"event": "run.error", "error": repr(e)})
        audit.close()
        raise
    finally:
        audit.close()

    return result


def doctor(*, repo_root: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Environment diagnosis.
    """
    from ..utils.platform import inspect_platform
    root = Path(repo_root) if repo_root is not None else Path.cwd()

    info = inspect_platform()
    info["repo_root"] = str(root)
    info["enablelist_found"] = load_enablelist(root) is not None
    return info
