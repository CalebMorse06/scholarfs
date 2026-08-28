## Outcome

What changes for a student or connector author?

## Contract impact

- Canonical files changed:
- Schemas changed:
- Migration or rollback:

## Trust review

- [ ] Core remains offline and has no telemetry or credential handling.
- [ ] The default path is non-destructive.
- [ ] Context remains allowlisted and private-by-default.
- [ ] Fixtures contain no real student data or copyrighted course material.

## Verification

- [ ] `python -m unittest discover -s tests -v`
- [ ] `scholarfs validate examples/fall-2026 --strict`
- [ ] `python -m build`
- [ ] Clean wheel smoke-install

