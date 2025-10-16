"""
Output management system for organizing final and interim outputs.

Handles two types of outputs:
1. Final outputs - The primary deliverables (USFM, TEI, DOCX, etc.)
2. Interim outputs - Intermediate files for processing (extracted JSON, cache manifests, etc.)

Provides cleanup options while preserving cache and final outputs.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import shutil


class OutputType:
    """Output file type classifications."""
    FINAL = "final"      # Primary deliverables - never auto-deleted
    INTERIM = "interim"  # Intermediate files - can be cleaned
    CACHE = "cache"      # Downloaded content - never deleted


class OutputManager:
    """
    Manage output files with distinction between final and interim outputs.
    
    Output Structure:
        output/
        ├── final/          # Final deliverables (USFM, TEI, DOCX)
        │   ├── usfm/
        │   ├── tei/
        │   └── docx/
        ├── interim/        # Intermediate files (extracted JSON)
        │   └── json/
        └── .output_manifest.json  # Tracking file
    
    Cache remains separate: cache/ (never touched by output management)
    """
    
    FINAL_FORMATS = {
        'usfm': 'USFM Bible translation format',
        'tei': 'TEI XML scholarly format',
        'docx': 'Microsoft Word documents',
        'pdf': 'PDF documents'
    }
    
    INTERIM_FORMATS = {
        'json': 'Extracted JSON intermediate format',
        'temp': 'Temporary processing files',
        'logs': 'Processing logs'
    }
    
    def __init__(self, base_output_dir: str = "./output", keep_interim: bool = False):
        """
        Initialize output manager.
        
        Args:
            base_output_dir: Base directory for all outputs
            keep_interim: If True, don't auto-clean interim files
        """
        self.base_dir = Path(base_output_dir)
        self.final_dir = self.base_dir / "final"
        self.interim_dir = self.base_dir / "interim"
        self.manifest_path = self.base_dir / ".output_manifest.json"
        self.keep_interim = keep_interim
        
        # Create directory structure
        self._initialize_directories()
        
        # Load or create manifest
        self.manifest = self._load_manifest()
    
    def _initialize_directories(self):
        """Create output directory structure."""
        # Final output directories
        for format_name in self.FINAL_FORMATS:
            (self.final_dir / format_name).mkdir(parents=True, exist_ok=True)
        
        # Interim output directories
        for format_name in self.INTERIM_FORMATS:
            (self.interim_dir / format_name).mkdir(parents=True, exist_ok=True)
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load output manifest tracking file."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "created": datetime.now().isoformat(),
            "files": {},
            "statistics": {
                "total_final": 0,
                "total_interim": 0,
                "last_cleanup": None
            }
        }
    
    def _save_manifest(self):
        """Save output manifest."""
        self.manifest["updated"] = datetime.now().isoformat()
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def register_file(
        self,
        file_path: str,
        output_type: str,
        format_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Register an output file in the manifest.
        
        Args:
            file_path: Original file path (will be moved to appropriate location)
            output_type: "final" or "interim"
            format_name: Format type (usfm, json, etc.)
            metadata: Optional metadata about the file
        
        Returns:
            Final path where file is stored
        """
        file_path = Path(file_path)
        
        # Determine target directory
        if output_type == OutputType.FINAL:
            target_dir = self.final_dir / format_name
            self.manifest["statistics"]["total_final"] += 1
        elif output_type == OutputType.INTERIM:
            target_dir = self.interim_dir / format_name
            self.manifest["statistics"]["total_interim"] += 1
        else:
            raise ValueError(f"Invalid output type: {output_type}")
        
        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Target path
        target_path = target_dir / file_path.name
        
        # Move file if it's not already in the right place
        if file_path.absolute() != target_path.absolute():
            if file_path.exists():
                shutil.move(str(file_path), str(target_path))
        
        # Register in manifest
        file_id = str(target_path.relative_to(self.base_dir))
        self.manifest["files"][file_id] = {
            "output_type": output_type,
            "format": format_name,
            "created": datetime.now().isoformat(),
            "size_bytes": target_path.stat().st_size if target_path.exists() else 0,
            "metadata": metadata or {}
        }
        
        self._save_manifest()
        return target_path
    
    def get_final_path(self, format_name: str, filename: str) -> Path:
        """
        Get path for a final output file.
        
        Args:
            format_name: Format (usfm, tei, docx, etc.)
            filename: Output filename
        
        Returns:
            Path in final output directory
        """
        target_dir = self.final_dir / format_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename
    
    def get_interim_path(self, format_name: str, filename: str) -> Path:
        """
        Get path for an interim output file.
        
        Args:
            format_name: Format (json, temp, etc.)
            filename: Output filename
        
        Returns:
            Path in interim output directory
        """
        target_dir = self.interim_dir / format_name
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename
    
    def cleanup_interim(self, force: bool = False) -> Dict[str, Any]:
        """
        Clean up interim output files.
        
        Args:
            force: If True, clean even if keep_interim is True
        
        Returns:
            Statistics about cleanup operation
        """
        if self.keep_interim and not force:
            return {
                "cleaned": False,
                "reason": "keep_interim flag is set",
                "files_deleted": 0,
                "space_freed_bytes": 0
            }
        
        deleted_count = 0
        space_freed = 0
        deleted_files = []
        
        # Remove interim files
        for file_id, file_info in list(self.manifest["files"].items()):
            if file_info["output_type"] == OutputType.INTERIM:
                file_path = self.base_dir / file_id
                if file_path.exists():
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    space_freed += size
                    deleted_files.append(str(file_id))
                
                # Remove from manifest
                del self.manifest["files"][file_id]
        
        # Update statistics
        self.manifest["statistics"]["total_interim"] = 0
        self.manifest["statistics"]["last_cleanup"] = datetime.now().isoformat()
        self._save_manifest()
        
        return {
            "cleaned": True,
            "files_deleted": deleted_count,
            "space_freed_bytes": space_freed,
            "space_freed_mb": round(space_freed / 1024 / 1024, 2),
            "deleted_files": deleted_files
        }
    
    def list_files(
        self,
        output_type: Optional[str] = None,
        format_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List output files with optional filtering.
        
        Args:
            output_type: Filter by "final" or "interim"
            format_name: Filter by format
        
        Returns:
            List of file information dictionaries
        """
        files = []
        
        for file_id, file_info in self.manifest["files"].items():
            # Apply filters
            if output_type and file_info["output_type"] != output_type:
                continue
            if format_name and file_info["format"] != format_name:
                continue
            
            file_path = self.base_dir / file_id
            files.append({
                "path": str(file_path),
                "relative_path": file_id,
                "exists": file_path.exists(),
                **file_info
            })
        
        return files
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get output statistics."""
        stats = self.manifest["statistics"].copy()
        
        # Calculate sizes
        final_size = 0
        interim_size = 0
        
        for file_id, file_info in self.manifest["files"].items():
            file_path = self.base_dir / file_id
            if file_path.exists():
                size = file_path.stat().st_size
                if file_info["output_type"] == OutputType.FINAL:
                    final_size += size
                else:
                    interim_size += size
        
        stats["final_size_bytes"] = final_size
        stats["final_size_mb"] = round(final_size / 1024 / 1024, 2)
        stats["interim_size_bytes"] = interim_size
        stats["interim_size_mb"] = round(interim_size / 1024 / 1024, 2)
        
        return stats
    
    def clean_empty_directories(self):
        """Remove empty directories in output structure."""
        for directory in [self.final_dir, self.interim_dir]:
            for subdir in directory.rglob("*"):
                if subdir.is_dir() and not any(subdir.iterdir()):
                    subdir.rmdir()


def main():
    """CLI for output management."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m gundert_portal_scraper.storage.output_manager <command>")
        print("\nCommands:")
        print("  list [final|interim]  - List output files")
        print("  cleanup               - Clean interim files")
        print("  stats                 - Show statistics")
        sys.exit(1)
    
    manager = OutputManager()
    command = sys.argv[1]
    
    if command == "list":
        output_type = sys.argv[2] if len(sys.argv) > 2 else None
        files = manager.list_files(output_type=output_type)
        for file_info in files:
            print(f"{file_info['output_type']:8} {file_info['format']:8} {file_info['relative_path']}")
    
    elif command == "cleanup":
        result = manager.cleanup_interim(force=True)
        if result["cleaned"]:
            print(f"✅ Cleaned {result['files_deleted']} files")
            print(f"   Freed {result['space_freed_mb']} MB")
        else:
            print(f"ℹ️  {result['reason']}")
    
    elif command == "stats":
        stats = manager.get_statistics()
        print(f"Final outputs:   {stats['total_final']} files ({stats['final_size_mb']} MB)")
        print(f"Interim outputs: {stats['total_interim']} files ({stats['interim_size_mb']} MB)")
        if stats['last_cleanup']:
            print(f"Last cleanup:    {stats['last_cleanup']}")


if __name__ == "__main__":
    main()
