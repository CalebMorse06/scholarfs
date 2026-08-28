# Personal context
.student/private/*
!.student/private/README.md
!.student/private/*.example.md

# Connector credentials and local state
.student/connector-state/*
!.student/connector-state/README.md
.student/cache/
.student/backups/
.student/generated/
.student/import-log.jsonl
.env
.env.*
!.env.example
*credentials*.json
*secret*.json
*.pem
*.key

# Raw inbox and course attachments are private by default
inbox/*
!inbox/README.md
courses/*/syllabus/files/
courses/*/assignments/*/files/
courses/*/lectures/files/
courses/*/resources/files/

# Local tools
.venv/
venv/
__pycache__/
.DS_Store
Thumbs.db
