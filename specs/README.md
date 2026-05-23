# Internal Specifications

Development tracking and historical documentation.

> **Note**: This directory contains internal project files. For user-facing documentation, see [docs/](../docs/).

---

## Archive

Historical records of completed work (Phase 0-5):

```
archive/
├── phases/              # Phase 0-5 implementation tracking
│   ├── PHASE0_TODO.md
│   ├── PHASE1_TODO.md
│   ├── PHASE2_TODO.md
│   ├── PHASE2.5_TODO.md
│   ├── PHASE3_TODO.md
│   └── PHASE4_TODO.md
│
├── fixes/               # Historical bug fixes
│   ├── close-orphaned-positions-on-load.md
│   ├── disable-dry-run-database-save.md
│   ├── disable-dry-run-notifications.md
│   ├── orphaned-position-ticket-fix.md
│   └── ticket-bigint-fix.md
│
├── implementation-logs/ # Implementation notes
│   ├── week16.1-trading-accounts-implementation.md
│   ├── week16.2-account-sync-service-implementation.md
│   └── week16.3-account-selector-implementation.md
│
├── dashboard/           # Phase 6 planning
│   ├── DASHBOARD_BRAINSTORM.md
│   └── DASHBOARD_REQUIREMENTS_ANALYSIS.md
│
└── database/            # Database analysis (completed)
    ├── DATABASE_ANALYSIS_GAPS.md
    └── DATABASE_SCHEMA_REALITY_CHECK.md
```

---

## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| 0-5 | ✅ Complete | See archive/ |
| 5.5 | ⏳ In Progress | Database enhancement |
| 6 | 📋 Planned | Web dashboard |

For current roadmap, see [docs/planning/roadmap.md](../docs/planning/roadmap.md).

---

## Purpose

These files serve as:
- **Historical record** - What was implemented and when
- **Decision trail** - Why certain approaches were taken
- **Reference** - Bug fixes and their solutions

All content here is **archival** and not actively maintained.
