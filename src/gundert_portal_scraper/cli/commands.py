"""Additional CLI commands for transformation, validation, and management."""

import click
from pathlib import Path
from typing import List, Optional
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import (
    console, print_error, print_success, print_warning, print_info,
    validate_formats, validate_output_dir
)
from ..storage.manager import BookStorageManager
from ..transformations import create_transformation_engine
from ..validation import create_validation_engine
from ..storage.schemas import BookStorage

# Import the main CLI group
from . import cli


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--formats', '-f', required=True, callback=validate_formats,
              help='Comma-separated list of output formats')
@click.option('--output', '-o', type=click.Path(), callback=validate_output_dir,
              help='Output directory for transformed files')
@click.option('--validate/--no-validate', default=True, help='Validate generated content')
@click.pass_context
def transform(ctx, input_file, formats, output, validate):
    """
    Transform saved book content to different formats.
    
    INPUT_FILE: Path to saved book content (.json file)
    
    Example:
        gundert-scraper transform book.json --formats usfm,docx --output ./output
    """
    try:
        # Load book content
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
            load_task = progress.add_task("📖 Loading book content...")
            
            with open(input_file, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
            
            # Filter out unsupported fields and fix field name compatibility
            filtered_data = {k: v for k, v in book_data.items() 
                           if k not in ['download_statistics']}
            
            # Fix field name compatibility for book_metadata
            if 'book_metadata' in filtered_data:
                book_meta = filtered_data['book_metadata']
                # Rename url to base_url
                if 'url' in book_meta:
                    book_meta['base_url'] = book_meta.pop('url')
                # Remove extra fields not in BookMetadata schema
                extra_fields = ['extraction_timestamp']
                for field in extra_fields:
                    book_meta.pop(field, None)
                # Fix content_type for USFM compatibility  
                if book_meta.get('content_type') == 'unknown':
                    book_meta['content_type'] = 'all'  # Force compatibility by using "all"
            
            # Fix field compatibility for extraction_parameters
            if 'extraction_parameters' in filtered_data:
                extract_params = filtered_data['extraction_parameters']
                # Remove extra fields not in ExtractionParameters schema
                expected_fields = ['start_page', 'end_page', 'batch_size', 'preserve_formatting', 
                                 'transcript_extraction', 'portal_type']
                filtered_params = {k: v for k, v in extract_params.items() if k in expected_fields}
                # Add missing required fields with defaults
                filtered_params.setdefault('start_page', 1)
                filtered_params.setdefault('end_page', 10)
                filtered_params.setdefault('batch_size', 10)
                filtered_params.setdefault('preserve_formatting', True)
                filtered_params.setdefault('transcript_extraction', True)
                filtered_params.setdefault('portal_type', 'opendigi')
                filtered_data['extraction_parameters'] = filtered_params
            
            # Fix field compatibility for statistics
            if 'statistics' in filtered_data:
                stats = filtered_data['statistics']
                expected_fields = ['pages_processed', 'pages_with_transcripts', 'pages_with_images',
                                 'total_lines_extracted', 'extraction_start_time', 'extraction_end_time',
                                 'extraction_duration_seconds', 'pages_per_minute', 'success_rate', 'errors']
                filtered_stats = {k: v for k, v in stats.items() if k in expected_fields}
                # Rename processing_duration_seconds to extraction_duration_seconds if present
                if 'processing_duration_seconds' in stats:
                    filtered_stats['extraction_duration_seconds'] = stats['processing_duration_seconds']
                # Add missing required fields with defaults
                filtered_stats.setdefault('pages_processed', 0)
                filtered_stats.setdefault('pages_with_transcripts', 0)
                filtered_stats.setdefault('pages_with_images', 0)
                filtered_stats.setdefault('total_lines_extracted', 0)
                filtered_stats.setdefault('extraction_start_time', None)
                filtered_stats.setdefault('extraction_end_time', None)
                filtered_stats.setdefault('extraction_duration_seconds', 0.0)
                filtered_stats.setdefault('pages_per_minute', 0.0)
                filtered_stats.setdefault('success_rate', 0.0)
                filtered_stats.setdefault('errors', [])
                filtered_data['statistics'] = filtered_stats
            
            # Fix page structure for USFM transformer compatibility
            if 'pages' in filtered_data:
                for page in filtered_data['pages']:
                    if 'transcript_info' in page and 'lines' in page['transcript_info']:
                        # Add transcript_text field expected by USFM transformer
                        lines = page['transcript_info']['lines']
                        transcript_text = '\n'.join(line.get('text', '') for line in lines)
                        page['transcript_info']['transcript_text'] = transcript_text
            
            book_storage = BookStorage.from_dict(filtered_data)
            progress.update(load_task, completed=100)
            
            if not ctx.obj.get('quiet'):
                console.print(f"\n[bold green]📚 Book Loaded:[/bold green]")
                console.print(f"   Book ID: [cyan]{book_storage.book_metadata.book_id}[/cyan]")
                console.print(f"   Pages: [cyan]{len(book_storage.pages)}[/cyan]")
                console.print(f"   Lines: [cyan]{book_storage.statistics.total_lines_extracted}[/cyan]")
        
        # Transform to requested formats
        transformation_engine = create_transformation_engine()
        
        if not output:
            output = input_file.parent / 'transformed'
            output.mkdir(exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console
        ) as progress:
            
            transform_task = progress.add_task(f"🔄 Transforming to {len(formats)} formats...", total=len(formats))
            
            results = {}
            
            for format_name in formats:
                try:
                    # Determine output filename
                    extension = _get_format_extension(format_name)
                    output_file = output / f"{book_storage.book_metadata.book_id}.{extension}"
                    
                    # Transform
                    result = transformation_engine.transform(book_storage, format_name, output_file)
                    
                    if result.success:
                        results[format_name] = {'success': True, 'file': output_file}
                        print_success(f"{format_name.upper()}: {output_file}")
                        
                        # Validate if requested
                        if validate:
                            validation_engine = create_validation_engine()
                            validation_results = validation_engine.validate_file(output_file, format_name)
                            
                            for validation_result in validation_results:
                                if validation_result.is_valid:
                                    print_success(f"  ✓ Validation passed")
                                else:
                                    error_count = validation_result.error_count
                                    warning_count = validation_result.warning_count
                                    print_warning(f"  ⚠️  Validation: {error_count} errors, {warning_count} warnings")
                                    
                                    # Show critical issues
                                    critical_issues = [i for i in validation_result.issues 
                                                     if i.severity.value in ['error', 'critical']]
                                    if critical_issues and ctx.obj.get('verbose'):
                                        for issue in critical_issues[:3]:
                                            console.print(f"    [red]• {issue.message}[/red]")
                    else:
                        results[format_name] = {'success': False, 'errors': result.errors}
                        print_error(f"{format_name.upper()}: {', '.join(result.errors)}")
                
                except Exception as e:
                    results[format_name] = {'success': False, 'error': str(e)}
                    print_error(f"{format_name.upper()}: {e}")
                
                progress.advance(transform_task)
        
        # Summary
        successful = len([r for r in results.values() if r.get('success')])
        console.print(f"\n[bold green]🎉 Transformation complete: {successful}/{len(formats)} successful[/bold green]")
        
    except Exception as e:
        print_error(f"Transformation failed: {e}")
        if ctx.obj.get('verbose'):
            import traceback
            console.print(traceback.format_exc())


@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--format', '-f', 'format_type', 
              type=click.Choice(['usfm', 'tei_xml', 'parabible_json', 'bibleml', 'docx']),
              help='File format (auto-detected if not specified)')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed validation report')
@click.pass_context
def validate(ctx, files, format_type, detailed):
    """
    Validate content files for format compliance and quality.
    
    FILES: One or more files to validate
    
    Example:
        gundert-scraper validate *.usfm --detailed
        gundert-scraper validate book.json --format parabible_json
    """
    try:
        validation_engine = create_validation_engine()
        
        all_results = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task(f"🔍 Validating {len(files)} files...", total=len(files))
            
            for file_path in files:
                # Auto-detect format if not specified
                if not format_type:
                    detected_format = _detect_format(file_path)
                    if not detected_format:
                        print_warning(f"Cannot detect format for {file_path}, skipping")
                        progress.advance(task)
                        continue
                else:
                    detected_format = format_type
                
                # Validate
                validation_results = validation_engine.validate_file(file_path, detected_format)
                all_results[str(file_path)] = {
                    'format': detected_format,
                    'results': validation_results
                }
                
                progress.advance(task)
        
        # Display results
        console.print(f"\n[bold blue]📋 Validation Results[/bold blue]")
        
        total_files = len(all_results)
        valid_files = 0
        total_errors = 0
        total_warnings = 0
        
        for file_path, file_results in all_results.items():
            format_name = file_results['format']
            results = file_results['results']
            
            console.print(f"\n[bold cyan]📄 {Path(file_path).name}[/bold cyan] ([dim]{format_name}[/dim])")
            
            for result in results:
                validator_name = result.metadata.get('validator', 'Unknown')
                
                if result.is_valid:
                    valid_files += 1
                    console.print(f"  ✅ [green]{validator_name}: VALID[/green]")
                else:
                    console.print(f"  ❌ [red]{validator_name}: ISSUES FOUND[/red]")
                
                total_errors += result.error_count
                total_warnings += result.warning_count
                
                if result.issues:
                    console.print(f"     📊 {result.error_count} errors, {result.warning_count} warnings, {result.info_count} info")
                    
                    if detailed:
                        for issue in result.issues:
                            severity_color = {
                                'critical': 'bold red',
                                'error': 'red',
                                'warning': 'yellow',
                                'info': 'blue'
                            }.get(issue.severity.value, 'white')
                            
                            location = f" [{issue.location}]" if issue.location else ""
                            line = f" (line {issue.line_number})" if issue.line_number else ""
                            
                            console.print(f"       [{severity_color}]• {issue.code}: {issue.message}{location}{line}[/{severity_color}]")
                            
                            if issue.suggestion:
                                console.print(f"         [dim]💡 {issue.suggestion}[/dim]")
        
        # Summary
        console.print(f"\n[bold blue]📊 Summary[/bold blue]")
        summary_table = Table()
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="magenta")
        
        summary_table.add_row("Total Files", str(total_files))
        summary_table.add_row("Valid Files", str(valid_files))
        summary_table.add_row("Invalid Files", str(total_files - valid_files))
        summary_table.add_row("Total Errors", str(total_errors))
        summary_table.add_row("Total Warnings", str(total_warnings))
        
        console.print(summary_table)
        
        # Exit code based on validation results
        if total_errors > 0:
            console.print(f"\n[bold red]❌ Validation failed with {total_errors} errors[/bold red]")
            return 1
        elif total_warnings > 0:
            console.print(f"\n[bold yellow]⚠️  Validation completed with {total_warnings} warnings[/bold yellow]")
        else:
            console.print(f"\n[bold green]✅ All files validated successfully[/bold green]")
        
        return 0
        
    except Exception as e:
        print_error(f"Validation failed: {e}")
        if ctx.obj.get('verbose'):
            import traceback
            console.print(traceback.format_exc())
        return 1


@cli.command()
@click.argument('book_files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option('--formats', '-f', callback=validate_formats,
              help='Comma-separated list of output formats')
@click.option('--output', '-o', type=click.Path(), callback=validate_output_dir,
              help='Output directory for batch processing')
@click.option('--validate/--no-validate', default=True, help='Validate generated content')
@click.option('--parallel', '-p', type=int, default=1, help='Number of parallel processes')
@click.pass_context
def batch(ctx, book_files, formats, output, validate, parallel):
    """
    Batch process multiple book files.
    
    BOOK_FILES: Multiple book content files (.json) to process
    
    Example:
        gundert-scraper batch *.json --formats usfm,docx --output ./batch_output
    """
    try:
        if not formats:
            formats = ['usfm', 'plain_text']  # Default formats
            print_info(f"No formats specified, using defaults: {', '.join(formats)}")
        
        if not output:
            output = Path.cwd() / 'batch_output'
            output.mkdir(exist_ok=True)
            print_info(f"No output directory specified, using: {output}")
        
        console.print(f"\n[bold blue]🔄 Batch Processing[/bold blue]")
        console.print(f"Files: {len(book_files)}")
        console.print(f"Formats: {', '.join(formats)}")
        console.print(f"Output: {output}")
        
        transformation_engine = create_transformation_engine()
        validation_engine = create_validation_engine() if validate else None
        
        total_operations = len(book_files) * len(formats)
        successful_operations = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console
        ) as progress:
            
            main_task = progress.add_task(f"📦 Processing {len(book_files)} books...", total=total_operations)
            
            for book_file in book_files:
                try:
                    # Load book
                    with open(book_file, 'r', encoding='utf-8') as f:
                        book_data = json.load(f)
                    
                    book_storage = BookStorage(**book_data)
                    book_id = book_storage.book_metadata.book_id
                    
                    console.print(f"\n[cyan]📚 Processing: {book_id}[/cyan]")
                    
                    # Create book-specific output directory
                    book_output = output / book_id
                    book_output.mkdir(exist_ok=True)
                    
                    # Transform to each format
                    for format_name in formats:
                        try:
                            extension = _get_format_extension(format_name)
                            output_file = book_output / f"{book_id}.{extension}"
                            
                            result = transformation_engine.transform(book_storage, format_name, output_file)
                            
                            if result.success:
                                console.print(f"  ✅ {format_name.upper()}: {output_file.name}")
                                successful_operations += 1
                                
                                # Validate if requested
                                if validation_engine:
                                    validation_results = validation_engine.validate_file(output_file, format_name)
                                    
                                    for validation_result in validation_results:
                                        if not validation_result.is_valid:
                                            error_count = validation_result.error_count
                                            warning_count = validation_result.warning_count
                                            console.print(f"    [yellow]⚠️  {error_count} errors, {warning_count} warnings[/yellow]")
                            else:
                                console.print(f"  ❌ {format_name.upper()}: {', '.join(result.errors)}")
                        
                        except Exception as e:
                            console.print(f"  ❌ {format_name.upper()}: {e}")
                        
                        progress.advance(main_task)
                
                except Exception as e:
                    console.print(f"❌ Failed to process {book_file}: {e}")
                    progress.advance(main_task, advance=len(formats))
        
        # Final summary
        success_rate = (successful_operations / total_operations) * 100
        console.print(f"\n[bold green]🎉 Batch processing complete[/bold green]")
        console.print(f"Success rate: {successful_operations}/{total_operations} ({success_rate:.1f}%)")
        
    except Exception as e:
        print_error(f"Batch processing failed: {e}")
        if ctx.obj.get('verbose'):
            import traceback
            console.print(traceback.format_exc())


@cli.command()
@click.option('--show-formats', is_flag=True, help='Show supported transformation formats')
@click.option('--show-validators', is_flag=True, help='Show available validators')
@click.option('--system-info', is_flag=True, help='Show system information')
def info(show_formats, show_validators, system_info):
    """
    Display information about the scraper capabilities and system.
    
    Example:
        gundert-scraper info --show-formats --show-validators
    """
    try:
        if show_formats:
            console.print("\n[bold blue]🔄 Supported Transformation Formats[/bold blue]")
            
            formats_table = Table()
            formats_table.add_column("Format", style="cyan")
            formats_table.add_column("Extension", style="magenta")
            formats_table.add_column("Description", style="green")
            
            format_info = [
                ("USFM", ".usfm", "Unified Standard Format Marker - Bible translation standard"),
                ("TEI XML", ".xml", "Text Encoding Initiative - Academic text markup"),
                ("ParaBible JSON", ".json", "Structured JSON format for verse data"),
                ("BibleML", ".xml", "OSIS-based Biblical markup language"),
                ("DOCX", ".docx", "Microsoft Word document format"),
                ("Markdown", ".md", "Markdown formatted text"),
                ("Plain Text", ".txt", "Simple plain text format")
            ]
            
            for name, ext, desc in format_info:
                formats_table.add_row(name, ext, desc)
            
            console.print(formats_table)
        
        if show_validators:
            console.print("\n[bold blue]🔍 Available Validators[/bold blue]")
            
            validation_engine = create_validation_engine()
            supported_formats = validation_engine.get_supported_formats()
            
            validators_table = Table()
            validators_table.add_column("Format", style="cyan")
            validators_table.add_column("Validators", style="magenta")
            
            for format_name in supported_formats:
                validators = validation_engine.get_validators_for_format(format_name)
                validators_table.add_row(format_name.upper(), ", ".join(validators))
            
            console.print(validators_table)
        
        if system_info:
            console.print("\n[bold blue]🖥️  System Information[/bold blue]")
            
            import sys
            import platform
            from pathlib import Path
            
            info_table = Table()
            info_table.add_column("Component", style="cyan")
            info_table.add_column("Version/Info", style="magenta")
            
            info_table.add_row("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
            info_table.add_row("Platform", platform.platform())
            info_table.add_row("Working Directory", str(Path.cwd()))
            
            # Check optional dependencies
            optional_deps = {
                'usfm-grammar': 'USFM validation',
                'jsonschema': 'JSON validation',
                'python-docx': 'DOCX support',
                'lxml': 'XML processing'
            }
            
            for dep, desc in optional_deps.items():
                try:
                    __import__(dep.replace('-', '_'))
                    status = "[green]✅ Available[/green]"
                except ImportError:
                    status = "[red]❌ Not available[/red]"
                
                info_table.add_row(f"{dep} ({desc})", status)
            
            console.print(info_table)
        
        if not any([show_formats, show_validators, system_info]):
            # Show general info
            console.print("\n[bold blue]ℹ️  Gundert Portal Scraper Information[/bold blue]")
            console.print("Use --help with any command for detailed usage information.")
            console.print("Available options:")
            console.print("  --show-formats    Show supported transformation formats")
            console.print("  --show-validators Show available content validators")
            console.print("  --system-info     Show system and dependency information")
        
    except Exception as e:
        print_error(f"Failed to display information: {e}")


def _detect_format(file_path: Path) -> Optional[str]:
    """Auto-detect file format based on extension."""
    extension = file_path.suffix.lower()
    
    format_map = {
        '.usfm': 'usfm',
        '.xml': 'tei_xml',  # Default XML to TEI, could be BibleML
        '.json': 'parabible_json',
        '.docx': 'docx'
    }
    
    return format_map.get(extension)


def _get_format_extension(format_name: str) -> str:
    """Get file extension for format."""
    extensions = {
        'usfm': 'usfm',
        'tei_xml': 'xml',
        'parabible_json': 'json',
        'bibleml': 'xml',
        'docx': 'docx',
        'markdown': 'md',
        'plain_text': 'txt'
    }
    return extensions.get(format_name, format_name)