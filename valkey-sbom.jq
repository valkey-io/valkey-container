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
# The "@SPDX_CREATED@" token is substituted with the real build-time timestamp
# in Dockerfile.template.
def valkey_sbom:
    {
		spdxVersion: "SPDX-2.3",
		dataLicense: "CC0-1.0",
		SPDXID: "SPDXRef-DOCUMENT",
		name: (.name + "-sbom"),
		documentNamespace: ("https://valkey.io/spdxdocs/" + .name + "-sbom-" + .version + "-@SPDX_CREATED@"),
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
				downloadLocation: (.downloadLocation // "NOASSERTION"),
				filesAnalyzed: false,
				externalRefs: [
					{
						referenceCategory: "PACKAGE-MANAGER",
						referenceType: "purl",
						referenceLocator: ("pkg:generic/" + .name + "@" + .version + "?" + (.params | [to_entries[] | .key + "=" + .value] | join("\u0026")))
					}
				],
				licenseDeclared: (if .licenses | length > 0 then
					(.licenses | join(" AND "))
				else
					"NOASSERTION"
				end)
			}
		]
	}
;
