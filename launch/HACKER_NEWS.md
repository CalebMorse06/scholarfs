# Hacker News draft

## Title

Show HN: ScholarFS - A local-first semester workspace for humans and AI

## Post

Hi HN - I built ScholarFS after noticing that the difficult part of using AI for school was often not the model, but giving it reliable context. Course information ends up scattered across an LMS, syllabus PDFs, folders, calendars, notes, and temporary chat history.

ScholarFS is an open-source workspace standard plus a small Python CLI. It organizes courses, deadlines, notes, and reusable context as ordinary Markdown and JSON files on your machine.

The CLI scaffolds and validates the workspace, but the files are the durable interface. They remain readable without the tool and can be used with a filesystem-aware coding agent, another assistant through a generated Markdown bundle, or no assistant at all.

v0.1 deliberately focuses on the foundations: the file convention, published schemas, deadline and reminder model, explicit memory scopes, a realistic fake semester, ICS export, and a file boundary for future connectors. Core has no telemetry, network access, credential handling, hosted service, or frontend. Its only conditional runtime package is Python's timezone data on Windows.

Connector hooks are not being presented as working LMS sync. The repository includes one offline converter to demonstrate preview-first, idempotent imports and the trust boundary.

I would especially value feedback on whether the workspace and deadline models are simple enough to become a useful shared convention, and where setup still feels too technical.

https://github.com/CalebMorse06/scholarfs

## First comment notes

Be ready to explain:

- why JSON rather than YAML or SQLite;
- why `AGENTS.md` is guidance, not a provider dependency;
- how private context is excluded;
- why there is no live Canvas integration yet;
- which schema changes are still expected before 1.0.
