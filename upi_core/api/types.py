from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseSpec(BaseModel):
    """
    Global run/case configuration.
    """
    model_config = ConfigDict(extra="forbid")

    seed: int = 0
    device: str = "cpu"
    tags: List[str] = Field(default_factory=list)
    workdir: Optional[Path] = None


class UseSelector(BaseModel):
    """
    How to select a plugin from the registry.
    """
    model_config = ConfigDict(extra="forbid")

    plugin_type: str
    capability: Optional[str] = None
    prefer: Optional[str] = None            # id/name hint
    version: Optional[str] = None           # packaging specifier, e.g. ">=1.0,<2.0"


class StageSpec(BaseModel):
    """
    A pipeline stage.
    """
    model_config = ConfigDict(extra="forbid")

    name: str
    uses: UseSelector
    config: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)  # reserved for future


class PipelineSpec(BaseModel):
    """
    Root pipeline specification (matches YAML structure).
    """
    model_config = ConfigDict(extra="forbid")

    case: CaseSpec = Field(default_factory=CaseSpec)
    pipeline: Dict[str, Any]

    @field_validator("pipeline")
    @classmethod
    def _validate_pipeline(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        stages = v.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError("pipeline.stages must be a non-empty list")
        return v

    def stages(self) -> List[StageSpec]:
        return [StageSpec.model_validate(s) for s in self.pipeline["stages"]]
