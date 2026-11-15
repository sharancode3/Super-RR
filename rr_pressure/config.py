"""Configuration and path definitions for rr_pressure."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

REQUIRED_RAW_FILES = [
    "ball_by_ball.csv",
    "competitions.csv",
    "competition_team_player_mapping.csv",
    "matches.csv",
    "playing_eleven.csv",
    "teams.csv",
    "Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf",
]


def default_raw_dir() -> Path:
    """Use the organizer's recorded-extras pack when it is present in the workspace."""
    recorded_extras = Path("6af458274c1e8_data_pack")
    return recorded_extras if recorded_extras.is_dir() else Path("6af3166e7b922_data_pack")


@dataclass
class PipelineConfig:
    raw_dir: Path = field(default_factory=default_raw_dir)
    out_dir: Path = Path("artifacts")
    public_dir: Optional[Path] = None
    seed: int = 2027
    required_files: List[str] = field(default_factory=lambda: list(REQUIRED_RAW_FILES))

    def validate_inputs(self) -> Dict[str, Path]:
        """Validate that all required input files exist and return mapping."""
        if not self.raw_dir.exists():
            raise FileNotFoundError(f"Raw data pack directory not found: {self.raw_dir}")
        
        found = {}
        missing = []
        for fname in self.required_files:
            fpath = self.raw_dir / fname
            if not fpath.is_file():
                missing.append(fname)
            else:
                found[fname] = fpath
        
        if missing:
            raise FileNotFoundError(
                f"Missing required raw data files in {self.raw_dir}: {missing}"
            )
        return found
