from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.cve.promote_candidates import (
    Candidate,
    Promotion,
    PromotionError,
    build_promotions,
    load_candidates,
    promote,
)
from scripts.cve.verify_candidate import (
    Target,
    VerificationError,
    decode_candidate_tags,
    decode_targets,
    parse_trivy_findings,
    target_matches_candidate,
    verify_candidate,
)


def _encoded_targets(values: list[dict[str, str]]) -> str:
    return base64.b64encode(json.dumps(values).encode()).decode()


def _target(**overrides: str) -> dict[str, str]:
    value = {
        "image": "valkey/valkey:9.0",
        "package": "libssl3t64",
        "cve_id": "CVE-2026-0001",
        "platform": "linux/amd64",
    }
    value.update(overrides)
    return value


def _platform_digests() -> dict[str, str]:
    return {
        "linux/amd64": "sha256:" + "1" * 64,
        "linux/arm64": "sha256:" + "2" * 64,
        "linux/arm/v7": "sha256:" + "3" * 64,
        "linux/ppc64le": "sha256:" + "4" * 64,
    }


class VerifyCandidateTests(unittest.TestCase):
    def test_target_matches_generated_aliases_including_release_candidates(self) -> None:
        rc_tags = ["valkey-container:9.1.0-rc1", "valkey-container:9.1"]
        rc_alpine_tags = [
            "valkey-container:9.1.0-rc1-alpine",
            "valkey-container:9.1-alpine",
        ]
        self.assertTrue(target_matches_candidate("9.1", rc_tags))
        self.assertTrue(target_matches_candidate("9.1-alpine", rc_alpine_tags))
        self.assertFalse(target_matches_candidate("9.1", rc_alpine_tags))
        self.assertFalse(target_matches_candidate("9.1-alpine", rc_tags))

    def test_decode_candidate_tags_is_strict(self) -> None:
        self.assertEqual(
            decode_candidate_tags('["valkey-container:9.1.0-rc1", "valkey-container:9.1"]'),
            ["valkey-container:9.1.0-rc1", "valkey-container:9.1"],
        )
        for raw in ("not json", "[]", '["other:9.1"]'):
            with self.subTest(raw=raw), self.assertRaises(VerificationError):
                decode_candidate_tags(raw)

    def test_decode_targets_round_trips_strict_contract(self) -> None:
        self.assertEqual(
            decode_targets(_encoded_targets([_target()])),
            [Target(
                image="valkey/valkey:9.0",
                package="libssl3t64",
                cve_id="CVE-2026-0001",
                platform="linux/amd64",
            )],
        )

    def test_decode_targets_rejects_malformed_payloads(self) -> None:
        values = [
            "not base64",
            base64.b64encode(b"not json").decode(),
            _encoded_targets([]),
            _encoded_targets([{"image": "valkey/valkey:9.0"}]),
        ]
        for encoded in values:
            with self.subTest(encoded=encoded):
                with self.assertRaises(VerificationError):
                    decode_targets(encoded)

    def test_parse_trivy_findings_is_strict(self) -> None:
        payload = {
            "SchemaVersion": 2,
            "Results": [{
                "Vulnerabilities": [{
                    "VulnerabilityID": "CVE-2026-0001",
                    "PkgName": "libssl3t64",
                }],
            }],
        }
        self.assertEqual(
            parse_trivy_findings(payload, context="test"),
            {("CVE-2026-0001", "libssl3t64")},
        )

    def test_verify_candidate_accepts_absent_target(self) -> None:
        target = Target(**_target())
        with patch(
            "scripts.cve.verify_candidate.run_trivy",
            return_value={"SchemaVersion": 2, "Results": []},
        ):
            verify_candidate(
                candidate="ghcr.io/valkey-io/valkey@sha256:" + "a" * 64,
                image_tag="9.0.5",
                candidate_tags=["valkey-container:9.0.5", "valkey-container:9.0"],
                targets=[target],
            )

    def test_verify_candidate_rejects_target_still_present(self) -> None:
        target = Target(**_target())
        payload = {
            "SchemaVersion": 2,
            "Results": [{
                "Vulnerabilities": [{
                    "VulnerabilityID": target.cve_id,
                    "PkgName": target.package,
                }],
            }],
        }
        with patch("scripts.cve.verify_candidate.run_trivy", return_value=payload):
            with self.assertRaisesRegex(VerificationError, "still contains"):
                verify_candidate(
                    candidate="ghcr.io/valkey-io/valkey@sha256:" + "a" * 64,
                    image_tag="9.0.5",
                    candidate_tags=["valkey-container:9.0.5", "valkey-container:9.0"],
                    targets=[target],
                )

    def test_verify_candidate_requires_target_for_matrix_image(self) -> None:
        with self.assertRaisesRegex(VerificationError, "no targeted findings"):
            verify_candidate(
                candidate="ghcr.io/valkey-io/valkey@sha256:" + "a" * 64,
                image_tag="8.1",
                candidate_tags=["valkey-container:8.1"],
                targets=[Target(**_target())],
            )


class PromoteCandidateTests(unittest.TestCase):
    def test_load_candidates_and_build_registry_plan(self) -> None:
        digest = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "9.0.json").write_text(json.dumps({
                "name": "9.0",
                "repository": "ghcr.io/valkey-io/valkey",
                "digest": digest,
                "tags": ["valkey-container:9.0.5", "valkey-container:9.0"],
                "platform_digests": _platform_digests(),
            }))
            candidates = load_candidates(path)
        plan = build_promotions(
            candidates,
            correlation_id="123-1",
            repositories=["ghcr.io/valkey-io/valkey", "docker.io/valkey/valkey"],
        )
        self.assertEqual(
            {item.destination for item in plan},
            {
                "ghcr.io/valkey-io/valkey:9.0.5",
                "ghcr.io/valkey-io/valkey:9.0",
                "docker.io/valkey/valkey:9.0.5",
                "docker.io/valkey/valkey:9.0",
            },
        )
        self.assertTrue(all(item.digest == digest for item in plan))

    def test_build_promotions_rejects_unsafe_correlation(self) -> None:
        candidate = Candidate(
            "9.0",
            "ghcr.io/valkey-io/valkey",
            "sha256:" + "a" * 64,
            ("valkey-container:9.0",),
        )
        with self.assertRaisesRegex(PromotionError, "unsafe"):
            build_promotions(
                [candidate],
                correlation_id="bad value",
                repositories=["ghcr.io/valkey-io/valkey"],
            )

    def test_build_promotions_rejects_destination_collision(self) -> None:
        candidates = [
            Candidate(
                "9.0",
                "ghcr.io/valkey-io/valkey",
                "sha256:" + "a" * 64,
                ("valkey-container:latest",),
            ),
            Candidate(
                "9.1",
                "ghcr.io/valkey-io/valkey",
                "sha256:" + "b" * 64,
                ("valkey-container:latest",),
            ),
        ]
        with self.assertRaisesRegex(PromotionError, "multiple candidate digests"):
            build_promotions(
                candidates,
                correlation_id="123-1",
                repositories=["ghcr.io/valkey-io/valkey"],
            )

    def test_promote_stages_then_updates_exact_digest(self) -> None:
        digest = "sha256:" + "a" * 64
        old_digest = "sha256:" + "b" * 64
        plan = [Promotion(
            source=f"ghcr.io/valkey-io/valkey@{digest}",
            destination="docker.io/valkey/valkey:9.0",
            digest=digest,
            staging="docker.io/valkey/valkey:cve-staging-1-9.0",
        )]
        skopeo = _FakeSkopeo({
            plan[0].source: digest,
            plan[0].destination: old_digest,
        })

        promote(plan, skopeo=skopeo)  # type: ignore[arg-type]

        self.assertEqual(skopeo.digests[plan[0].destination], digest)
        self.assertEqual(skopeo.digests[plan[0].staging], digest)

    def test_promote_rolls_back_prior_tag_when_later_tag_fails(self) -> None:
        digest = "sha256:" + "a" * 64
        old_one = "sha256:" + "b" * 64
        old_two = "sha256:" + "c" * 64
        source = f"ghcr.io/valkey-io/valkey@{digest}"
        staging = "docker.io/valkey/valkey:cve-staging-1-9.0"
        plan = [
            Promotion(source, "docker.io/valkey/valkey:9.0", digest, staging),
            Promotion(source, "docker.io/valkey/valkey:9", digest, staging),
        ]
        skopeo = _FakeSkopeo({
            source: digest,
            plan[0].destination: old_one,
            plan[1].destination: old_two,
        }, fail_once=plan[1].destination)

        with self.assertRaisesRegex(PromotionError, "rollback was attempted"):
            promote(plan, skopeo=skopeo)  # type: ignore[arg-type]

        self.assertEqual(skopeo.digests[plan[0].destination], old_one)
        self.assertEqual(skopeo.digests[plan[1].destination], old_two)


class _FakeSkopeo:
    def __init__(self, digests: dict[str, str], fail_once: str = "") -> None:
        self.digests = dict(digests)
        self.fail_once = fail_once

    def digest(self, reference: str) -> str:
        if reference in self.digests:
            return self.digests[reference]
        if "@sha256:" in reference:
            return "sha256:" + reference.rsplit("@sha256:", 1)[1]
        raise PromotionError(f"missing fake reference {reference}")

    def copy(self, source: str, destination: str) -> None:
        if destination == self.fail_once:
            self.fail_once = ""
            raise PromotionError("injected copy failure")
        self.digests[destination] = self.digest(source)


if __name__ == "__main__":
    unittest.main()
