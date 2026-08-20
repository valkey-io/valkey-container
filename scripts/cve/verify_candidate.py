#!/usr/bin/env python3
"""Verify that targeted OS-package CVEs are absent from a candidate image."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

_DIGEST_REF_RE = re.compile(r"^\S+@sha256:[0-9a-f]{64}$")
_REQUIRED_TARGET_FIELDS = (
    "image",
    "package",
    "cve_id",
    "platform",
)


class VerificationError(Exception):
    """Raised when input or scanner output cannot be verified safely."""


@dataclass(frozen=True)
class Target:
    """A platform-specific vulnerability that a candidate must remove."""

    image: str
    package: str
    cve_id: str
    platform: str

    @property
    def image_tag(self) -> str:
        """Return the tag portion used by the container build matrix."""
        return self.image.rsplit(":", 1)[-1]


def decode_targets(encoded: str) -> list[Target]:
    """Decode and strictly validate the base64-encoded target list."""
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise VerificationError("targeted_findings is not valid base64") from exc

    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("targeted_findings does not contain valid UTF-8 JSON") from exc

    if not isinstance(payload, list) or not payload:
        raise VerificationError("targeted_findings must be a non-empty JSON list")

    targets: list[Target] = []
    for index, value in enumerate(payload):
        if not isinstance(value, dict):
            raise VerificationError(f"targeted_findings[{index}] must be an object")
        for field in _REQUIRED_TARGET_FIELDS:
            field_value = value.get(field)
            if not isinstance(field_value, str) or not field_value.strip():
                raise VerificationError(
                    f"targeted_findings[{index}].{field} must be a non-empty string"
                )
        target = Target(**{field: value[field] for field in _REQUIRED_TARGET_FIELDS})
        if not target.platform.startswith("linux/"):
            raise VerificationError(
                f"targeted_findings[{index}].platform must start with 'linux/'"
            )
        targets.append(target)
    return targets


def parse_trivy_findings(payload: Any, *, context: str) -> set[tuple[str, str]]:
    """Return vulnerable ``(CVE, package)`` pairs from strict Trivy JSON."""
    if not isinstance(payload, dict):
        raise VerificationError(f"{context}: Trivy output must be a JSON object")
    schema_version = payload.get("SchemaVersion")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise VerificationError(f"{context}: Trivy output has no integer SchemaVersion")

    results = payload.get("Results", [])
    if not isinstance(results, list):
        raise VerificationError(f"{context}: Trivy Results must be a list")

    findings: set[tuple[str, str]] = set()
    for result_index, result in enumerate(results):
        if not isinstance(result, dict):
            raise VerificationError(f"{context}: Results[{result_index}] must be an object")
        vulnerabilities = result.get("Vulnerabilities")
        if vulnerabilities is None:
            continue
        if not isinstance(vulnerabilities, list):
            raise VerificationError(
                f"{context}: Results[{result_index}].Vulnerabilities must be a list"
            )
        for vulnerability_index, vulnerability in enumerate(vulnerabilities):
            if not isinstance(vulnerability, dict):
                raise VerificationError(
                    f"{context}: vulnerability {vulnerability_index} must be an object"
                )
            cve_id = vulnerability.get("VulnerabilityID")
            package = vulnerability.get("PkgName")
            if not isinstance(cve_id, str) or not cve_id:
                raise VerificationError(f"{context}: vulnerability has no string VulnerabilityID")
            if not isinstance(package, str) or not package:
                raise VerificationError(f"{context}: vulnerability has no string PkgName")
            findings.add((cve_id, package))
    return findings


def run_trivy(candidate: str, platform: str, *, executable: str = "trivy") -> dict[str, Any]:
    """Scan one immutable candidate platform and return parsed Trivy JSON."""
    command = [
        executable,
        "image",
        "--format",
        "json",
        "--quiet",
        "--scanners",
        "vuln",
        "--pkg-types",
        "os",
        "--platform",
        platform,
        candidate,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError(f"Trivy failed for {candidate} ({platform}): {exc}") from exc
    if result.returncode != 0:
        raise VerificationError(
            f"Trivy failed for {candidate} ({platform}), exit {result.returncode}: "
            f"{result.stderr[-1000:]}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VerificationError(
            f"Trivy returned invalid JSON for {candidate} ({platform})"
        ) from exc
    if not isinstance(payload, dict):
        raise VerificationError(
            f"Trivy returned a non-object document for {candidate} ({platform})"
        )
    return payload


def decode_candidate_tags(raw: str) -> list[str]:
    """Parse the exact aliases generated for one build matrix entry."""
    try:
        tags = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VerificationError("candidate tags are not valid JSON") from exc
    if (
        not isinstance(tags, list)
        or not tags
        or not all(
            isinstance(tag, str) and tag.startswith("valkey-container:")
            for tag in tags
        )
    ):
        raise VerificationError(
            "candidate tags must be a non-empty list of valkey-container aliases"
        )
    return tags


def target_matches_candidate(target_tag: str, candidate_tags: list[str]) -> bool:
    """Match a scan target against the aliases generated for the candidate."""
    return f"valkey-container:{target_tag}" in candidate_tags


def verify_candidate(
    *,
    candidate: str,
    image_tag: str,
    candidate_tags: list[str],
    targets: list[Target],
    trivy_executable: str = "trivy",
) -> None:
    """Fail unless every target for ``image_tag`` is absent from the candidate."""
    if not _DIGEST_REF_RE.fullmatch(candidate):
        raise VerificationError("candidate must be an immutable @sha256 digest reference")

    selected = [
        target
        for target in targets
        if target_matches_candidate(target.image_tag, candidate_tags)
    ]
    if not selected:
        raise VerificationError(f"no targeted findings were supplied for image {image_tag!r}")

    by_platform: dict[str, list[Target]] = defaultdict(list)
    for target in selected:
        by_platform[target.platform].append(target)

    unresolved: list[Target] = []
    for platform, platform_targets in sorted(by_platform.items()):
        payload = run_trivy(candidate, platform, executable=trivy_executable)
        findings = parse_trivy_findings(
            payload,
            context=f"{candidate} ({platform})",
        )
        unresolved.extend(
            target
            for target in platform_targets
            if (target.cve_id, target.package) in findings
        )

    if unresolved:
        details = ", ".join(
            f"{target.cve_id}/{target.package}/{target.platform}"
            for target in unresolved
        )
        raise VerificationError(f"candidate still contains targeted findings: {details}")

    print(
        f"Verified {candidate}: {len(selected)} targeted finding(s) absent "
        f"across {len(by_platform)} platform(s)."
    )


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--image-tag", required=True)
    parser.add_argument("--candidate-tags-json", required=True)
    parser.add_argument("--targets-b64", required=True)
    parser.add_argument("--trivy", default="trivy")
    args = parser.parse_args()

    try:
        targets = decode_targets(args.targets_b64)
        candidate_tags = decode_candidate_tags(args.candidate_tags_json)
        verify_candidate(
            candidate=args.candidate,
            image_tag=args.image_tag,
            candidate_tags=candidate_tags,
            targets=targets,
            trivy_executable=args.trivy,
        )
    except VerificationError as exc:
        print(f"candidate verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
