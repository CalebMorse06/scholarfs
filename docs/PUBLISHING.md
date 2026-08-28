# Publish the ScholarFS repository

These steps describe how the initial public repository was prepared and how to cut future releases.

## 1. Review the name and ownership

The working project, package, repository, and CLI name is `ScholarFS` / `scholarfs`. Recheck GitHub and package indexes immediately before publishing, then make the final legal and branding decision. A practical availability screen is not trademark clearance.

The initial repository owner is `CalebMorse06`, and the canonical URL is <https://github.com/CalebMorse06/scholarfs>. Confirm the license holder in `LICENSE` and recheck the conduct/security contact language before each release.

## 2. Confirm release-specific values

Before tagging, confirm that no publishing placeholders were reintroduced:

```bash
rg -n 'YOUR[_]USERNAME|\[REPO[_]URL\]|\[CONDUCT[_]CONTACT\]' .
```

The search must return no matches. Repository and launch URLs should use the canonical URL above. Confidential conduct and security reports use GitHub private vulnerability reporting, which must remain enabled.

## 3. Verify from a clean environment

```bash
python -m venv .venv
```

Activate it, then:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
scholarfs validate examples/fall-2026 --strict
python -m build
```

Install the wheel in a second clean environment and run `scholarfs --help`. Do not publish a source tree that works only through `PYTHONPATH`.

## 4. Create Git history

From this directory:

```bash
git init
git branch -M main
git add --all
git commit -m "feat: launch ScholarFS v0.1"
```

Review the staged file list before committing. It should not contain virtual environments, build output, generated context, real semester files, or credentials.

## 5. Create GitHub repository

Create an empty public repository named `scholarfs`; do not add a generated README, license, or `.gitignore`. Then connect and push using the exact URL GitHub provides:

```bash
git remote add origin https://github.com/CalebMorse06/scholarfs.git
git push -u origin main
```

If GitHub CLI is authenticated, the equivalent is:

```bash
gh repo create scholarfs --public --source=. --remote=origin --push
```

## 6. Configure trust settings

- Enable private vulnerability reporting.
- Confirm the confidential reporting instructions in `CODE_OF_CONDUCT.md` still match the enabled GitHub feature.
- Protect `main` and require the CI checks after the first workflow run.
- Disable unused GitHub features rather than leaving empty surfaces.
- Confirm Actions permissions are read-only by default.

## 7. Tag v0.1.0

After CI passes and the quick start succeeds from the public URL:

```bash
git tag -a v0.1.0 -m "ScholarFS v0.1.0"
git push origin v0.1.0
```

Create a GitHub release from `CHANGELOG.md`. Attach the wheel and source distribution produced by `python -m build` if desired.

## 8. Recommended PyPI publication

For a broad student-facing launch, publish the package first so setup does not require Git. Register the exact `scholarfs` project only when ready to maintain releases. Prefer PyPI trusted publishing from a protected GitHub environment; do not store a long-lived API token in repository secrets or add an unreviewed publish workflow.

After publication, update the README quick start to `pipx install scholarfs` while keeping the source installation path for contributors.

## 9. Launch

Follow [`launch/README.md`](../launch/README.md) and post one channel at a time. Keep the connector status and privacy claims precise.
