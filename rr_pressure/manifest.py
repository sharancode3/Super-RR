"""Immutable input manifest generator and validator."""

import hashlib
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rr_pressure.config import PipelineConfig


def compute_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_environment_info() -> Dict[str, str]:
    info = {
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    for pkg in ["pandas", "numpy", "scipy", "sklearn", "xgboost", "matplotlib"]:
        try:
            mod = __import__(pkg)
            info[f"{pkg}_version"] = getattr(mod, "__version__", "installed")
        except ImportError:
            info[f"{pkg}_version"] = "missing"
    return info


def generate_input_manifest(config: PipelineConfig) -> Dict[str, Any]:
    file_map = config.validate_inputs()
    files_manifest = {}
    
    for fname, fpath in file_map.items():
        files_manifest[fname] = {
            "path": str(fpath),
            "size_bytes": fpath.stat().st_size,
            "sha256": compute_sha256(fpath),
        }
    
    stray_reg = config.raw_dir / "ipl_availability_registry.csv"
    audit_notes = {
        "missing_public_archives": "Public Cricsheet archives not pre-downloaded; raw pack is self-contained for audit and baseline modeling.",
        "unverified_dropdown_pool": "Live Unstop dropdown selection pool not yet frozen; full statistical candidate ranking proceeds first, dropdown eligibility filters applied at Stage 11.",
    }
    if stray_reg.is_file():
        audit_notes["stray_raw_registry_provenance"] = {
            "filename": "ipl_availability_registry.csv",
            "in_supplied_7file_manifest": False,
            "consumed_by_pipeline": False,
            "size_bytes": stray_reg.stat().st_size,
            "sha256": compute_sha256(stray_reg),
            "origin": "Generated accidentally by an earlier positional call build_ipl_availability_registry(raw_dir) where output_dir received raw_dir (fixed to output_dir=None, raw_dir=raw_dir). Never read as input.",
        }

    manifest_data = {
        "manifest_version": "1.0.0",
        "raw_dir": str(config.raw_dir),
        "seed": config.seed,
        "environment": get_environment_info(),
        "files": files_manifest,
        "audit_notes": audit_notes,
    }
    
    config.out_dir.mkdir(parents=True, exist_ok=True)
    out_file = config.out_dir / "input_manifest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        
    return manifest_data


def generate_market_evidence_manifest(
    out_dir: Path,
    raw_dir: Path,
    as_of_date: str = "2026-11-12",
) -> Tuple[Path, Dict[str, Any]]:
    """Fingerprint curated in-code market/strategy evidence separately from the 7-file raw pack."""
    from rr_pressure.availability import (
        PLAYER_STRATEGY_MAP,
        RAW_TRANSACTION_RECORDS,
        build_ipl_availability_registry,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    reg_path = out_dir / "ipl_availability_registry.csv"
    if not reg_path.exists():
        build_ipl_availability_registry(output_dir=out_dir, raw_dir=raw_dir)

    tx_payload = json.dumps([asdict(r) for r in RAW_TRANSACTION_RECORDS], sort_keys=True).encode("utf-8")
    strat_payload = json.dumps({str(k): v for k, v in sorted(PLAYER_STRATEGY_MAP.items())}, sort_keys=True).encode("utf-8")
    tx_sha = hashlib.sha256(tx_payload).hexdigest()
    strat_sha = hashlib.sha256(strat_payload).hexdigest()
    reg_sha = compute_sha256(reg_path)
    combined_sha = hashlib.sha256(f"{tx_sha}:{strat_sha}:{reg_sha}".encode("utf-8")).hexdigest()

    manifest = {
        "manifest_version": "1.0.0",
        "as_of_date": as_of_date,
        "separate_from_supplied_pack": True,
        "transaction_records_count": len(RAW_TRANSACTION_RECORDS),
        "transaction_records_sha256": tx_sha,
        "player_strategy_map_count": len(PLAYER_STRATEGY_MAP),
        "player_strategy_map_sha256": strat_sha,
        "generated_registry_file": str(reg_path),
        "generated_registry_sha256": reg_sha,
        "market_evidence_bundle_sha256": combined_sha,
    }
    manifest_path = out_dir / "market_evidence_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest_path, manifest
