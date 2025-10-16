# Output Management System

## Overview

The Gundert Portal Scraper implements a sophisticated output management system that distinguishes between **final outputs** (primary deliverables) and **interim outputs** (intermediate processing files).

## Output Types

### 1. Final Outputs 🎯
**Purpose**: Primary deliverables - the very goal of the process

- **USFM** - Bible translation format
- **TEI XML** - Scholarly digital edition
- **DOCX** - Publication-ready Word documents  
- **PDF** - Final publication format

**Storage**: `output/final/<format>/`

**Lifetime**: **NEVER auto-deleted** - These are your primary work products

### 2. Interim Outputs 📝
**Purpose**: Intermediate files that facilitate production of final outputs

- **JSON** - Extracted manuscript data (when transforming to other formats)
- **Temp files** - Temporary processing data
- **Logs** - Processing logs

**Storage**: `output/interim/<format>/`

**Lifetime**: Can be cleaned up after transformation complete

### 3. Cache 💾
**Purpose**: Downloaded manuscript content

**Storage**: `cache/`

**Lifetime**: **NEVER auto-deleted** - See [CACHE_MANAGEMENT.md](CACHE_MANAGEMENT.md)

## Directory Structure

```
project/
├── cache/                          # Downloaded content (never deleted)
│   └── GaXXXIV5a_content.json
├── output/
│   ├── final/                      # Final deliverables (never auto-deleted)
│   │   ├── usfm/
│   │   │   └── GaXXXIV5a.usfm
│   │   ├── tei/
│   │   │   └── GaXXXIV5a.xml
│   │   └── docx/
│   │       └── GaXXXIV5a.docx
│   ├── interim/                    # Intermediate files (can be cleaned)
│   │   ├── json/
│   │   │   └── GaXXXIV5a.json
│   │   └── temp/
│   │       └── processing.tmp
│   └── .output_manifest.json      # Tracking file
```

## Usage

### Basic Extraction

#### Keep Interim Files (Default for Debugging)
```bash
# Extract to JSON only - JSON is final output
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a

# Extract and transform - keep interim JSON for debugging
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a \
  --formats json,usfm --keep-interim
```

#### Auto-cleanup Interim Files
```bash
# Extract and transform - auto-clean interim JSON after USFM created
uv run gundert-scraper extract https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5a \
  --formats usfm --clean-interim

# Result: Only final USFM file retained
```

### Transform Command

```bash
# Transform JSON to USFM - JSON treated as interim, can be cleaned
uv run gundert-scraper transform output/interim/json/GaXXXIV5a.json \
  --format usfm --clean-interim
```

### Manual Cleanup

```bash
# Show current output status
uv run gundert-scraper cleanup --dry-run

# Clean interim files interactively
uv run gundert-scraper cleanup

# Force cleanup without confirmation
uv run gundert-scraper cleanup --force
```

## Workflow Examples

### Scenario 1: Development/Debugging
Keep all interim files for inspection:

```bash
# Extract with interim files kept
uv run gundert-scraper extract URL --formats usfm --keep-interim

# Inspect interim JSON if needed
cat output/interim/json/GaXXXIV5a.json

# Clean up manually later
uv run gundert-scraper cleanup
```

### Scenario 2: Production
Auto-clean interim files to save space:

```bash
# Extract and transform - auto-cleanup
uv run gundert-scraper extract URL --formats usfm,tei,docx --clean-interim

# Result: Only final/ directory contains files
```

### Scenario 3: Batch Processing
Process multiple books with cleanup:

```bash
for url in $(cat book_urls.txt); do
    uv run gundert-scraper extract $url --formats usfm --clean-interim
done

# All final USFM files saved, no interim clutter
```

## Safety Guarantees

### ✅ Protected from Deletion

**Never Auto-Deleted:**
1. `cache/` - Downloaded manuscript content
2. `output/final/` - All final deliverables
3. `.output_manifest.json` - Tracking metadata

**Only User Commands Can Delete:**
- `cleanup` command for interim files
- Manual `rm` commands

### ⚠️ Cleanup Behavior

**What Gets Cleaned:**
- `output/interim/` - Intermediate processing files
- Only when explicitly requested

**What Survives:**
- All files in `output/final/`
- All files in `cache/`
- Manifest and metadata

## Output Manifest

The `.output_manifest.json` file tracks all outputs:

```json
{
  "created": "2025-10-16T10:30:00",
  "files": {
    "final/usfm/GaXXXIV5a.usfm": {
      "output_type": "final",
      "format": "usfm",
      "created": "2025-10-16T10:35:00",
      "size_bytes": 16507,
      "metadata": {
        "book_id": "GaXXXIV5a",
        "chapters": 10,
        "verses": 156
      }
    }
  },
  "statistics": {
    "total_final": 1,
    "total_interim": 0,
    "last_cleanup": "2025-10-16T10:36:00"
  }
}
```

## Best Practices

### ✅ DO
- Use `--keep-interim` during development/debugging
- Use `--clean-interim` for production workflows
- Review outputs before cleanup with `cleanup --dry-run`
- Keep final outputs backed up
- Check manifest file for output tracking

### ❌ DON'T
- Don't manually delete `output/final/` directory
- Don't delete cache/ (see CACHE_MANAGEMENT.md)
- Don't rely on interim files being available later
- Don't commit `output/` to git (add to .gitignore)

## CLI Reference

### Extract Command
```bash
uv run gundert-scraper extract URL [OPTIONS]

Options:
  --formats TEXT           Comma-separated formats (json,usfm,tei,docx)
  --keep-interim          Keep interim JSON files [default: False]
  --clean-interim         Auto-clean interim files after transformation
  --output PATH           Output directory [default: ./output]
```

### Transform Command
```bash
uv run gundert-scraper transform JSON_FILE [OPTIONS]

Options:
  --format [usfm|tei|docx]  Output format [default: usfm]
  --keep-interim            Keep interim files [default: False]
  --clean-interim           Clean interim files after transform
  --output PATH             Output file path
```

### Cleanup Command
```bash
uv run gundert-scraper cleanup [OPTIONS]

Options:
  --output-dir PATH   Output directory to manage [default: ./output]
  --force             Force cleanup without confirmation
  --dry-run           Show what would be deleted (not yet implemented)
```

## Troubleshooting

### "No interim files to clean"
All interim files already cleaned. This is normal after `--clean-interim`.

### "keep_interim flag is set"
You ran cleanup but extraction was done with `--keep-interim`. Use `--force` to override.

### Files in wrong directory
Check `.output_manifest.json` to see where files were registered. Use output manager API to move files.

## Python API

```python
from gundert_portal_scraper.storage.output_manager import OutputManager, OutputType

# Initialize
manager = OutputManager(base_output_dir="./output", keep_interim=False)

# Register final output
final_path = manager.get_final_path('usfm', 'book.usfm')
manager.register_file(
    str(final_path),
    output_type=OutputType.FINAL,
    format_name='usfm',
    metadata={'chapters': 10}
)

# Register interim output
interim_path = manager.get_interim_path('json', 'book.json')
manager.register_file(
    str(interim_path),
    output_type=OutputType.INTERIM,
    format_name='json'
)

# Cleanup interim files
result = manager.cleanup_interim(force=False)
print(f"Cleaned {result['files_deleted']} files")

# Get statistics
stats = manager.get_statistics()
print(f"Final: {stats['total_final']} files ({stats['final_size_mb']} MB)")
```

## Future Enhancements

Planned features:
- [ ] `--dry-run` flag for cleanup preview
- [ ] Compression of interim files before cleanup
- [ ] Automatic backup before cleanup
- [ ] Output file deduplication
- [ ] Size-based cleanup policies
- [ ] Age-based cleanup policies
- [ ] Integration with version control

---

**Remember**: Final outputs are sacred 🎯, interim files are disposable 📝, and cache is eternal 💾!
