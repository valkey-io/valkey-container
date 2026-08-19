# Valkey-specific replacement for bashbrew's stock "sbom" template helper.
#
# The stock helper (auto-downloaded, gitignored .template-helper-functions.jq)
# omits fields that SPDX 2.3 marks mandatory, so strict scanners reject the
# resulting document (https://github.com/valkey-io/valkey-container/issues/114).
# This tracked module produces a minimal but spec-compliant SPDX 2.3 document.
#
# input:
# {
#     name: "packageName",
#     version: "packageVersion",
#     downloadLocation: "https://.../source.tar.gz",
#     params: {
#         "foo": "bar"
#     },
#     licenses: ["packageLicense" ... ]
# }
# output: object
#
# The "@SPDX_CREATED@" and "@SPDX_UUID@" tokens are substituted with the real
# build-time timestamp and a fresh UUID in Dockerfile.template.

# Split a Valkey version into the CPE 2.3 "version" and "update" components.
# NVD records release candidates with the rcN in the update field, not in the
# version field (e.g. cpe:2.3:a:lfprojects:valkey:7.2.4:rc1:*:*:*:*:*:* rather
# than ...:valkey:7.2.4-rc1:*:...), so "9.1.0-rc2" has to become
# version "9.1.0" + update "rc2" to correlate with NVD advisories.
# GA releases use "*" for update: NVD is inconsistent between "-" and "*" there,
# and advisory match criteria use "*" with version ranges.
def _cpe_version_update:
	if test("-rc[0-9]+$") then
		{ version: sub("-rc[0-9]+$"; ""), update: ("rc" + capture("-rc(?<n>[0-9]+)$").n) }
	else
		{ version: ., update: "*" }
	end
;

def valkey_sbom:
	# "unstable" is a moving target with no corresponding NVD release, so a CPE
	# built from it would be a fabricated identifier that matches nothing.
	(if .version == "unstable" then null else (.version | _cpe_version_update) end) as $cpe
	| {
		spdxVersion: "SPDX-2.3",
		dataLicense: "CC0-1.0",
		SPDXID: "SPDXRef-DOCUMENT",
		name: (.name + "-sbom"),
		# The namespace must identify exactly one document globally. Name and
		# version alone are not enough: the debian and alpine variants of one
		# version are different documents, so the variant and a fresh UUID are
		# included. The UUID (not the timestamp) is what guarantees uniqueness;
		# creationInfo.created remains the human-readable creation time.
		documentNamespace: (
			"https://valkey.io/spdxdocs/" + .name + "-sbom-" + .version
			+ "-" + (.params.os_name // "unknown") + "-" + (.params.os_version // "unknown")
			+ "-@SPDX_UUID@"
		),
		creationInfo: {
			created: "@SPDX_CREATED@",
			creators: [
				"Organization: The Valkey Project",
				"Tool: valkey-container"
			]
		},
		packages: [
			{
				name: .name,
				versionInfo: .version,
				SPDXID: ("SPDXRef-Package--" + .name),
				supplier: "Organization: The Valkey Project",
				downloadLocation: (.downloadLocation // "NOASSERTION"),
				filesAnalyzed: false,
				externalRefs: ([
					{
						referenceCategory: "PACKAGE-MANAGER",
						referenceType: "purl",
						referenceLocator: ("pkg:generic/" + .name + "@" + .version + "?" + (.params | [to_entries[] | .key + "=" + .value] | join("\u0026")))
					}
				] + (
					# "lfprojects:valkey" is the vendor:product pair NVD registers
					# for Valkey, so scanners can correlate this package with
					# advisories. The generic purl above is not matchable on its
					# own: it has no authoritative namespace and its name
					# ("valkey-server") differs from the NVD product ("valkey").
					if $cpe then [
						{
							referenceCategory: "SECURITY",
							referenceType: "cpe23Type",
							referenceLocator: ("cpe:2.3:a:lfprojects:valkey:" + $cpe.version + ":" + $cpe.update + ":*:*:*:*:*:*")
						}
					] else [] end
				)),
				licenseDeclared: (if .licenses | length > 0 then
					(.licenses | join(" AND "))
				else
					"NOASSERTION"
				end)
			}
		],
		# State explicitly what this document describes, rather than leaving
		# consumers to infer it from there being a single package.
		relationships: [
			{
				spdxElementId: "SPDXRef-DOCUMENT",
				relationshipType: "DESCRIBES",
				relatedSpdxElement: ("SPDXRef-Package--" + .name)
			}
		]
	}
;
