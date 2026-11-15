"""Checkpoint and progress ledger tracking for rr_pressure."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def get_default_progress_path(out_dir: Path) -> Path:
    return out_dir / "round1_progress.json"


def load_progress(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "release_status": "IN_PROGRESS",
            "next_prompt": "round1_prompts/00_project_contract.md",
            "resume_prompt": None,
            "repair_origin": None,
            "stages": {},
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp_path.replace(path)


def record_stage(
    progress_path: Path,
    stage_id: str,
    status: str,
    command: str,
    next_prompt: Optional[str] = None,
    resume_prompt: Optional[str] = None,
    input_fingerprints: Optional[Dict[str, str]] = None,
    output_fingerprints: Optional[Dict[str, str]] = None,
    output_paths: Optional[list] = None,
    evidence: Optional[Dict[str, Any]] = None,
    open_issues: Optional[list] = None,
    release_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Atomically record stage execution into the checkpoint ledger."""
    prog = load_progress(progress_path)
    
    stage_record = {
        "status": status,
        "command": command,
        "input_fingerprints": input_fingerprints or {},
        "output_fingerprints": output_fingerprints or {},
        "output_paths": output_paths or [],
        "evidence": evidence or {},
        "open_issues": open_issues or [],
        "retry_count": prog.get("stages", {}).get(stage_id, {}).get("retry_count", 0) + (1 if status == "FAIL" else 0),
    }
    
    prog.setdefault("stages", {})[stage_id] = stage_record
    if next_prompt:
        prog["next_prompt"] = next_prompt
    if resume_prompt is not None:
        prog["resume_prompt"] = resume_prompt
    if release_status:
        prog["release_status"] = release_status
        
    save_progress(progress_path, prog)
    return prog
