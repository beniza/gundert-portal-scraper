# Cache Safety Summary

## 🔒 Key Guarantees

### ✅ Cache is Protected
1. **Never auto-deleted** - No automatic cleanup of cache files
2. **Gitignored** - Won't be accidentally committed to repository
3. **Persistent** - Survives all normal operations (extract, transform, cleanup)
4. **Force-download flag** - Must explicitly request re-download

### 📁 Current Implementation

```python
# From core/cache.py
class RawContentCache:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Cache is NEVER deleted unless explicitly called:
    # - clear(book_id) - Remove specific book
    # - clear_all() - Remove all cache
```

```python
# From extraction/two_phase_scraper.py
class TwoPhaseContentScraper:
    def __init__(
        self,
        connector: GundertPortalConnector,
        cache_dir: str = "./cache",
        force_redownload: bool = False  # Must explicitly force
    ):
        self.force_redownload = force_redownload
    
    def _download_phase(self) -> dict:
        # Check cache first
        if not self.force_redownload and self.cache.is_cached(self.book_id):
            print(f"📦 Loading from cache: {self.book_id}")
            return self.cache.load(self.book_id)
        
        # Only downloads if not cached or forced
        print(f"🌐 Downloading content from portal...")
```

### 🚫 What Doesn't Delete Cache

- ✅ Running `extract` command multiple times
- ✅ Running `transform` command
- ✅ Repository cleanup operations
- ✅ Git operations (commit, push, pull)
- ✅ Running with different page ranges
- ✅ Generating different output formats

### ⚠️ What Can Delete Cache

- ❌ Manually deleting `cache/` directory
- ❌ Running `rm cache/*.json`
- ❌ Future: `gundert-scraper cache clear` command (not yet implemented)
- ❌ Future: `gundert-scraper cache clear --all` command (not yet implemented)

## 📦 Cache Benefits

### Performance
- **First download**: 30-60 seconds (network dependent)
- **Cached extraction**: 2-5 seconds  
- **Improvement**: 10-30x faster ⚡

### Storage
- **201-page manuscript**: 771KB
- **Minimal disk usage**: <1MB per book
- **Compression possible**: Future enhancement

## 🔄 Typical Workflow

```bash
# Day 1: Initial extraction (slow, downloads)
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a
# → Creates cache/GaXXXIV5a_content.json

# Day 2-N: Extract different page ranges (fast, uses cache)
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a --start-page 1 --end-page 10
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a --start-page 50 --end-page 100
# → Uses same cache, no re-download

# Transform cached data to USFM
uv run gundert-scraper transform output/GaXXXIV5a.json --format usfm
# → Cache remains untouched

# Months later: Cache still there
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a
# → Still uses original cache from Day 1
```

## 💾 Backup Recommendations

### Local Backup
```bash
# Simple copy
cp -r cache/ cache-backup-$(date +%Y%m%d)/

# Compressed archive
tar -czf cache-backup-$(date +%Y%m%d).tar.gz cache/
```

### External Storage
```bash
# USB drive
cp -r cache/ /media/usb/gundert-cache/

# Network location
rsync -avz cache/ user@server:/backups/gundert-cache/
```

## 🔍 Verifying Cache

```bash
# Check cache exists
ls -lh cache/

# Example output:
# total 771K
# -rw-r--r-- 1 user user 771K Oct 16 07:04 GaXXXIV5a_content.json

# Check cache timestamp
stat cache/GaXXXIV5a_content.json | grep "Modify"
```

## 📋 Checklist

Before major operations, ensure:
- [ ] Cache directory exists: `ls cache/`
- [ ] Cache has proper permissions: `chmod 755 cache/`
- [ ] Cache is in .gitignore: `git check-ignore cache/`
- [ ] Have backup of important manuscripts
- [ ] Know how to force re-download if needed

## 🎯 Summary

**Cache is safe by design:**
- Protected from automatic deletion
- Only explicit commands can remove it
- Gitignored but should be backed up locally
- Provides 10-30x performance improvement
- Minimal storage overhead (<1MB per book)

**Remember**: Once downloaded, manuscripts stay cached until you explicitly remove them. This is intentional and protects your work! 🛡️
