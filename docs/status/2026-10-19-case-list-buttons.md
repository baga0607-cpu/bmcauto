# Larger case-list controls — 2026-10-19

Shared repository-hierarchy CSS scales Actions icon buttons by 1.2 and folder-collapse buttons by 1.4 without changing layout dimensions. Applies to Repository, Plan and import-source trees. Parameter controls are excluded.

Browser verification: Repository row widths/heights exactly matched before/after. Actions changed from 20x20 to 24x24 px; folder toggles from 16x18 to 22.4x25.2 px. Parameter remained 72.1875x28 px. No Actions overlap in Repository or Plan import mode. Collapse/expand works; import Close restores navigation. Plan and source trees use the enlarged dimensions too. CSS only; no restart or database change.

Backup: bmca-runtime/backups/case-list-buttons-before.css
Screenshot: bmca-runtime/verification/case-list-larger-buttons.png
