# Public update records

Every publication must leave a readable update record without exposing private account, quota or credit data.

- New translation editions use `tools/adopt.py`; it automatically appends an immutable entry in `data/updates.json`, including added/revised verses, model labels and a timezone-aware adoption time.
- Before publishing site-only changes, run `python tools/record_update.py --id UNIQUE-ID --title "Korean change title" --detail "What readers can now do" --url /related/`. Use one stable ID per meaningful change. Append corrections instead of rewriting historical records.
- Build and check `/updates/`, its JSON/RSS feeds and the existing edition archives. Keep the translation edition number unchanged for UI-only work.
- An adoption or source-record time is not a deployment completion time. The updates page reads public Pages workflow status separately. Do not label unreviewed cloud drafts as published translations.
