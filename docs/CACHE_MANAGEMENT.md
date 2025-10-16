# Cache Management Guide

## Overview

The Gundert Portal Scraper uses a **two-phase architecture** with intelligent caching to avoid redundant downloads:

1. **Download Phase** - Fetch content once from OpenDigi portal (slow, requires browser)
2. **Processing Phase** - Extract pages from cached content (fast, no browser needed)

## Cache Directory Structure

```
cache/
├── GaXXXIV5a_content.json    # Malayalam Psalms (771KB, 201 pages)
├── GaXXXIV5b_content.json    # Another manuscript
└── ...
```

Each cache file contains:
- `book_id` - Manuscript identifier
- `content` - Complete HTML/XML content
- `metadata` - Book metadata
- `cached_at` - Timestamp
- `version` - Cache format version

## Important: Cache Safety

### ⚠️ Protected by .gitignore

The `cache/` directory is **gitignored** to:
- Prevent committing large binary content to git
- Avoid repository bloat
- Keep cached manuscripts local

### ✅ Cache Persistence

Cache files are **never deleted** automatically by:
- Extraction commands
- Transform commands
- Repository cleanup operations

### 🔒 Manual Cache Management Only

Cache is only cleared when you explicitly run:
```bash
# Clear specific book (NOT YET IMPLEMENTED)
uv run gundert-scraper cache clear GaXXXIV5a

# Clear all cache (NOT YET IMPLEMENTED)
uv run gundert-scraper cache clear --all
```

## Usage Patterns

### First Time Extraction
```bash
# Downloads content and saves to cache
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a
# Result: cache/GaXXXIV5a_content.json created (771KB)
```

### Subsequent Extractions
```bash
# Uses cached content - NO download!
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a

# Output:
# 📦 Loading from cache: GaXXXIV5a
# ✅ Cache loaded (cached at: 2025-10-16T07:04:52.123456)
```

### Force Re-download
```bash
# Force fresh download even if cached
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a --force-redownload
```

## Cache Benefits

### Performance
- **First download**: ~30-60 seconds (depends on network/portal speed)
- **Cached extraction**: ~2-5 seconds
- **Speedup**: 10-30x faster

### Reliability
- Avoid repeated portal requests
- Reduce risk of rate limiting
- Work offline after initial download

### Cost Savings
- Minimal network bandwidth
- Reduced server load on OpenDigi portal
- Faster development/testing cycles

## Backup Recommendations

### Local Backup
```bash
# Backup cache directory
tar -czf cache-backup-$(date +%Y%m%d).tar.gz cache/

# Or copy to external drive
cp -r cache/ /path/to/external/drive/gundert-cache/
```

### Cloud Backup
```bash
# Using rclone (example)
rclone sync cache/ remote:gundert-portal-cache/

# Using rsync (example)
rsync -avz cache/ user@server:/backups/gundert-cache/
```

## Cache Validation

### Check Cache Status
```bash
# List cached books (NOT YET IMPLEMENTED)
uv run gundert-scraper cache list

# Show cache info (NOT YET IMPLEMENTED)
uv run gundert-scraper cache info GaXXXIV5a
```

### Verify Cache Integrity
```bash
# Validate cache file (NOT YET IMPLEMENTED)
uv run gundert-scraper cache validate GaXXXIV5a
```

## Troubleshooting

### Cache Corruption
If cache is corrupted:
```bash
# Delete and re-download
rm cache/GaXXXIV5a_content.json
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a
```

### Disk Space Issues
Check cache size:
```bash
du -sh cache/
# Example: 771K    cache/

# If needed, clear old manuscripts
rm cache/OLD_BOOK_ID_content.json
```

### Permission Errors
Fix permissions:
```bash
chmod 755 cache/
chmod 644 cache/*.json
```

## Best Practices

### ✅ DO
- Keep cache directory backed up
- Use cache for multiple extractions
- Test transformations on cached data
- Document which manuscripts you have cached

### ❌ DON'T
- Don't commit cache/ to git (already gitignored)
- Don't manually edit cache JSON files
- Don't delete cache unless necessary
- Don't force re-download without reason

## Future Enhancements

Planned cache management features:
- [ ] `cache list` - List all cached books
- [ ] `cache info <book_id>` - Show cache details
- [ ] `cache validate <book_id>` - Verify integrity
- [ ] `cache clear <book_id>` - Remove specific cache
- [ ] `cache clear --all` - Remove all cache
- [ ] `cache stats` - Show cache statistics
- [ ] Cache compression for space savings
- [ ] Cache version migration tools
- [ ] Automatic cache expiry (optional)

## Technical Details

### Cache Format Version 1.0

```json
{
  "book_id": "GaXXXIV5a",
  "content": "<html>...</html>",
  "metadata": {
    "url": "https://...",
    "title": "...",
    "pages": 201
  },
  "cached_at": "2025-10-16T07:04:52.123456",
  "version": "1.0"
}
```

### Cache Location

Default: `./cache/` (relative to current directory)

Can be customized:
```python
from gundert_portal_scraper.core.cache import RawContentCache

cache = RawContentCache(cache_dir="/custom/path/to/cache")
```

---

**Remember**: Cache is your friend! It makes development faster and protects the OpenDigi portal from excessive requests. Always use cached content when possible. 🚀
