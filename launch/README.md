# Launch kit

These drafts tell one honest story: course context is fragmented, and students should own a readable copy. Repository links point to <https://github.com/CalebMorse06/scholarfs>.

## Message

Primary description:

> ScholarFS is a local-first workspace standard and CLI for course files, deadlines, notes, and durable AI context.

Short tagline:

> Your semester, organized for humans and AI.

Do not lead with “AI student planner.” ScholarFS is not a hosted planner or autonomous agent. The useful idea is the inspectable, provider-neutral context layer.

## Assets to prepare

- [ ] Public repository at the final URL.
- [ ] Clean README quick start tested from a fresh clone.
- [ ] 30-45 second terminal recording using only `examples/fall-2026`.
- [ ] Screenshot or recording alt text.
- [ ] GitHub private vulnerability reporting enabled.
- [ ] Confidential conduct-reporting channel verified.
- [ ] Package and repository URLs verified.
- [ ] License holder and repository owner confirmed.
- [ ] Name reviewed by the owner; collision screen is not legal clearance.

Recommended demo sequence:

```bash
scholarfs validate examples/fall-2026
cd examples/fall-2026
scholarfs status --as-of 2026-08-28T12:00:00-05:00
scholarfs context CS-241
```

Show the file tree and deadline output before showing an AI prompt. The workspace is the product.

## Sequence

1. Ask 3-5 students to complete the quick start without help.
2. Fix naming and setup friction they actually encounter.
3. Publish a tagged GitHub release and package, if desired.
4. Post the Reddit draft where self-promotion rules allow and ask about real workflow fit.
5. Post Show HN when the maintainer can answer architecture and trust questions for several hours.
6. Share the X and LinkedIn versions independently rather than copying one launch blast.
7. Record concrete failures and completed setups, not only stars and impressions.

## Drafts

- [Hacker News](./HACKER_NEWS.md)
- [Reddit](./REDDIT.md)
- [X](./X.md)
- [LinkedIn](./LINKEDIN.md)

## Claims gate

Before publishing, verify from the release artifact:

- no runtime dependencies except the documented Windows-only timezone-data package;
- no telemetry or core network access;
- clean installation on the operating systems claimed;
- example passes core and JSON Schema validation;
- connector is described as an offline example, not working LMS sync;
- context excludes private files by default;
- calendar behavior is described as export, not live synchronization.
