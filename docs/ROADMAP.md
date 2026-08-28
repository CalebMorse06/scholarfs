# Roadmap

The workspace standard is the product in v0.1. The roadmap grows outward only when a boundary has proven useful and trustworthy.

## v0.1: the standard

Shipped in this repository:

- plain-file workspace contract;
- small, offline scaffold and validation CLI;
- canonical course, deadline, and notification models;
- explicit semester, course, and private memory scopes;
- deterministic context bundles;
- file capture with checksum audit log;
- ICS calendar export with alarms;
- preview-first connector interchange and an offline example;
- realistic fictional semester;
- privacy, security, contributor, and launch documentation.

Success means an unfamiliar student can create a semester, understand every stored field, and remove the CLI without losing their work.

## Candidate v0.2: imports

Candidates, not promises:

- read-only ICS import with conflict reporting;
- a syllabus-to-draft workflow that never treats extracted dates as confirmed;
- separately distributed Canvas, Moodle, or Blackboard deadline exporters;
- an explicit schema migration command with dry-run and rollback;
- better course-code mapping support for external connectors.

Before acceptance, a connector must document authentication, network destinations, stored state, pagination, revocation, failure behavior, and privacy.

## Candidate v0.3: routines

- deterministic daily and weekly briefing generation;
- local operating-system scheduler recipes;
- hook/event envelopes such as `deadline.approaching` and `course.material.added`;
- calendar subscription strategies with stable event identity;
- user-controlled archival of completed terms.

Routines should produce inspectable artifacts and require explicit permission before external actions.

## Explicit non-goals for v0.x

- hosted accounts or cloud sync;
- a full LMS replacement;
- a student social network;
- an autonomous submission or messaging agent;
- a homework-answer generator;
- a vector database or opaque RAG index as canonical state;
- a plugin marketplace or arbitrary connector execution;
- a gradebook, GPA calculator, or degree planner;
- multi-user collaboration and institutional administration;
- a large frontend before the file standard stabilizes.

These ideas are not inherently bad. They widen the privacy, security, maintenance, and product surface beyond what v0.1 needs to prove.

## Decision tests

A proposed feature belongs in core only if most answers are yes:

1. Does it strengthen the portable workspace standard?
2. Can a user inspect the input and output?
3. Does it work without a hosted ScholarFS service?
4. Can it avoid a runtime dependency or justify one clearly?
5. Is the canonical owner of each fact unambiguous?
6. Is the default non-destructive and private?
7. Can failure leave the original workspace intact?
8. Does it help a real semester task rather than a hypothetical platform?

## How to propose work

Open an issue using the feature template and include user outcome, data ownership, schema impact, privacy boundary, failure mode, rollback, and what remains outside scope. See [CONTRIBUTING.md](../CONTRIBUTING.md).
