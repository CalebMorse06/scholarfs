# Security policy

## Supported versions

Until a newer release exists, security fixes target the latest `0.1.x` release and the `main` branch.

## Report a vulnerability privately

Use GitHub **Private vulnerability reporting** under the repository's Security tab. Maintainers must enable it before launch. If the private channel is unavailable, open a public issue asking for it to be enabled without including vulnerability details. Do not disclose credential exposure, path traversal, unsafe overwrite, connector-import corruption, or unintended context exposure publicly.

Include:

- affected ScholarFS version and commit;
- operating system and Python version;
- a minimal reproduction using invented data;
- expected and observed file access or mutation;
- whether exploitation requires a malicious workspace, import file, or local user action.

Never send a real student workspace, token, syllabus, grade, or private context file.

## Security boundaries

ScholarFS core is offline and does not execute connector code. Its trusted boundary includes the installed Python package and the selected workspace. It does not sandbox external AI tools, editors, shells, sync clients, or connectors.

Relevant defenses include:

- course-code validation against traversal and reserved Windows names;
- atomic structured writes;
- non-overwriting initialization and file capture;
- preview-first imports with backups and no implicit deletion;
- strict connector-envelope fields;
- allowlisted context generation that rejects symlinks and Windows directory junctions;
- explicit overwrite for calendar export;
- privacy warnings in workspace validation.

## Response expectations

Maintainers should acknowledge a report within seven days, confirm impact before public discussion, prepare a regression test with synthetic data, and coordinate disclosure after a fix or mitigation exists. This is a community project, not a guarantee of a service-level response.
