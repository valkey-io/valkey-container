#!/usr/bin/env python3
"""Promote verified candidate digests to production tags with rollback."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_REQUIRED_PLATFORMS = frozenset({
    "linux/amd64",
    "linux/arm64",
    "linux/arm/v7",
    "linux/ppc64le",
})


class PromotionError(Exception):
    """Raised when promotion cannot preserve the verified digest."""


@dataclass(frozen=True)
class Candidate:
    """One verified multi-platform candidate and its production aliases."""

    name: str
    repository: str
    digest: str
    tags: tuple[str, ...]
    platform_digests: tuple[tuple[str, str], ...] = ()

    @property
    def source(self) -> str:
        return f"{self.repository}@{self.digest}"


@dataclass(frozen=True)
class Promotion:
    """One production tag update derived from a candidate."""

    source: str
    destination: str
    digest: str
    staging: str


def load_candidates(metadata_dir: Path) -> list[Candidate]:
    """Load strict candidate metadata emitted by build jobs."""
    paths = sorted(metadata_dir.glob("*.json"))
    if not paths:
        raise PromotionError(f"no candidate metadata found in {metadata_dir}")

    candidates: list[Candidate] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise PromotionError(f"invalid candidate metadata {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise PromotionError(f"candidate metadata {path} must be an object")
        name = payload.get("name")
        repository = payload.get("repository")
        digest = payload.get("digest")
        tags = payload.get("tags")
        platform_digests = payload.get("platform_digests")
        if not isinstance(name, str) or not name:
            raise PromotionError(f"candidate metadata {path} has no name")
        if not isinstance(repository, str) or "/" not in repository:
            raise PromotionError(f"candidate metadata {path} has no repository")
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            raise PromotionError(f"candidate metadata {path} has an invalid digest")
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) for tag in tags):
            raise PromotionError(f"candidate metadata {path} has no string tags")
        if (
            not isinstance(platform_digests, dict)
            or set(platform_digests) != _REQUIRED_PLATFORMS
            or not all(
                isinstance(value, str) and _DIGEST_RE.fullmatch(value)
                for value in platform_digests.values()
            )
        ):
            raise PromotionError(
                f"candidate metadata {path} must record exactly the published platform digests"
            )
        candidates.append(Candidate(
            name,
            repository,
            digest,
            tuple(tags),
            tuple(sorted(platform_digests.items())),
        ))
    return candidates


def _tag_suffix(tag: str) -> str:
    prefix = "valkey-container:"
    if not tag.startswith(prefix) or len(tag) == len(prefix):
        raise PromotionError(f"unexpected generated tag {tag!r}")
    return tag[len(prefix):]


def build_promotions(
    candidates: Iterable[Candidate],
    *,
    correlation_id: str,
    repositories: Iterable[str],
) -> list[Promotion]:
    """Build a collision-free promotion plan for all registries and aliases."""
    if not _CORRELATION_RE.fullmatch(correlation_id):
        raise PromotionError("correlation ID contains unsafe characters")
    repositories = tuple(repository for repository in repositories if repository)
    if not repositories:
        raise PromotionError("no production repositories are configured")

    promotions: list[Promotion] = []
    destinations: dict[str, str] = {}
    for candidate in candidates:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "-", candidate.name)
        for repository in repositories:
            staging = f"{repository}:cve-staging-{correlation_id}-{safe_name}"
            for generated_tag in candidate.tags:
                destination = f"{repository}:{_tag_suffix(generated_tag)}"
                prior = destinations.get(destination)
                if prior is not None and prior != candidate.digest:
                    raise PromotionError(
                        f"production tag {destination} maps to multiple candidate digests"
                    )
                if prior == candidate.digest:
                    continue
                destinations[destination] = candidate.digest
                promotions.append(
                    Promotion(candidate.source, destination, candidate.digest, staging)
                )
    return promotions


class Skopeo:
    """Small fail-loud wrapper around skopeo."""

    def __init__(self, authfile: Path) -> None:
        self.authfile = authfile

    def _run(self, args: list[str]) -> str:
        if not args:
            raise PromotionError("skopeo command is empty")
        command = ["skopeo", args[0], "--authfile", str(self.authfile), *args[1:]]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PromotionError(f"failed to run {' '.join(command)}: {exc}") from exc
        if result.returncode != 0:
            raise PromotionError(
                f"{' '.join(command)} failed with exit {result.returncode}: "
                f"{result.stderr[-2000:]}"
            )
        return result.stdout.strip()

    def digest(self, reference: str) -> str:
        output = self._run(["inspect", "--format", "{{.Digest}}", f"docker://{reference}"])
        if not _DIGEST_RE.fullmatch(output):
            raise PromotionError(f"registry returned invalid digest {output!r} for {reference}")
        return output

    def copy(self, source: str, destination: str) -> None:
        self._run([
            "copy",
            "--all",
            "--preserve-digests",
            f"docker://{source}",
            f"docker://{destination}",
        ])


def promote(
    promotions: list[Promotion],
    *,
    skopeo: Skopeo,
) -> None:
    """Stage every digest, then update production tags with rollback on failure."""
    if not promotions:
        raise PromotionError("promotion plan is empty")

    old_digests: dict[str, str] = {}
    for promotion in promotions:
        if skopeo.digest(promotion.source) != promotion.digest:
            raise PromotionError(f"candidate digest changed for {promotion.source}")
        old_digests[promotion.destination] = skopeo.digest(promotion.destination)

    staged: set[tuple[str, str]] = set()
    for promotion in promotions:
        key = (promotion.staging, promotion.digest)
        if key in staged:
            continue
        skopeo.copy(promotion.source, promotion.staging)
        if skopeo.digest(promotion.staging) != promotion.digest:
            raise PromotionError(f"staging digest mismatch for {promotion.staging}")
        staged.add(key)

    attempted: list[Promotion] = []
    try:
        for promotion in promotions:
            staging_repository = promotion.staging.rsplit(":", 1)[0]
            # A registry may update the tag and still report a failed copy. Add
            # the destination before the operation so it participates in
            # rollback even when the failing copy was only partially applied.
            attempted.append(promotion)
            skopeo.copy(f"{staging_repository}@{promotion.digest}", promotion.destination)
            if skopeo.digest(promotion.destination) != promotion.digest:
                raise PromotionError(f"production digest mismatch for {promotion.destination}")
            print(f"Promoted {promotion.destination} -> {promotion.digest}")
    except PromotionError as exc:
        rollback_errors: list[str] = []
        for promotion in reversed(attempted):
            old_digest = old_digests[promotion.destination]
            repository = promotion.destination.rsplit(":", 1)[0]
            try:
                skopeo.copy(f"{repository}@{old_digest}", promotion.destination)
                if skopeo.digest(promotion.destination) != old_digest:
                    raise PromotionError("rollback digest verification failed")
            except PromotionError as rollback_exc:
                rollback_errors.append(f"{promotion.destination}: {rollback_exc}")
        suffix = ""
        if rollback_errors:
            suffix = "; rollback failures: " + "; ".join(rollback_errors)
        raise PromotionError(f"promotion failed and rollback was attempted: {exc}{suffix}") from exc


def configured_repositories() -> list[str]:
    """Return enabled production repositories from explicit environment variables."""
    return [
        value
        for value in (
            os.environ.get("GHCR_REPOSITORY", ""),
            os.environ.get("DOCKERHUB_REPOSITORY", ""),
            os.environ.get("ECR_REPOSITORY", ""),
        )
        if value
    ]


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-dir", type=Path, required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument(
        "--authfile",
        type=Path,
        default=Path.home() / ".docker" / "config.json",
    )
    args = parser.parse_args()

    try:
        candidates = load_candidates(args.metadata_dir)
        plan = build_promotions(
            candidates,
            correlation_id=args.correlation_id,
            repositories=configured_repositories(),
        )
        promote(plan, skopeo=Skopeo(args.authfile))
    except PromotionError as exc:
        print(f"candidate promotion failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
