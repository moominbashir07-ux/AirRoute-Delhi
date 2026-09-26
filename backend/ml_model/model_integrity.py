"""Phase 5: Production Model & Artifact Integrity Verifier.

Computes and verifies SHA-256 hashes of production ML models and datasets
against the authoritative model_manifest.json without modifying any artifacts.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, List

logger = logging.getLogger("ModelIntegrity")

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "ml_model" / "model_manifest.json"


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA-256 hash of a file efficiently using 64KB chunks."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_artifact_integrity(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    """Verify all artifacts declared in the manifest.
    
    Returns structured verification report:
    {
        "status": "valid" | "corrupt" | "missing" | "no_manifest",
        "total_artifacts": int,
        "verified_artifacts": int,
        "errors": List[str],
        "details": Dict[str, Dict[str, Any]]
    }
    """
    if not manifest_path.exists():
        logger.warning(f"Model manifest not found at {manifest_path}")
        return {
            "status": "no_manifest",
            "total_artifacts": 0,
            "verified_artifacts": 0,
            "errors": [f"Manifest file not found: {manifest_path}"],
            "details": {}
        }

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read model manifest: {e}")
        return {
            "status": "corrupt",
            "total_artifacts": 0,
            "verified_artifacts": 0,
            "errors": [f"Malformed manifest JSON: {e}"],
            "details": {}
        }

    artifacts = manifest.get("artifacts", {})
    verified = 0
    errors = []
    details = {}

    for name, meta in artifacts.items():
        rel_path = meta.get("path")
        expected_hash = meta.get("sha256")
        expected_size = meta.get("size_bytes")

        target_file = BASE_DIR / rel_path
        if not target_file.exists():
            err = f"Artifact '{name}' missing at expected path: {rel_path}"
            errors.append(err)
            details[name] = {"status": "missing", "path": rel_path}
            continue

        try:
            actual_size = target_file.stat().st_size
            actual_hash = calculate_sha256(target_file)
            if actual_hash != expected_hash:
                err = f"Artifact '{name}' SHA-256 hash mismatch! Expected {expected_hash}, got {actual_hash}"
                errors.append(err)
                details[name] = {
                    "status": "hash_mismatch",
                    "path": rel_path,
                    "expected_sha256": expected_hash,
                    "actual_sha256": actual_hash
                }
            else:
                verified += 1
                details[name] = {
                    "status": "verified",
                    "path": rel_path,
                    "sha256": actual_hash,
                    "size_bytes": actual_size
                }
        except Exception as e:
            err = f"Error checking artifact '{name}': {e}"
            errors.append(err)
            details[name] = {"status": "read_error", "path": rel_path, "error": str(e)}

    status = "valid" if (verified == len(artifacts) and not errors) else ("missing" if any(d.get("status") == "missing" for d in details.values()) else "corrupt")

    return {
        "status": status,
        "total_artifacts": len(artifacts),
        "verified_artifacts": verified,
        "errors": errors,
        "details": details
    }
