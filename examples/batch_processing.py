#!/usr/bin/env python3
"""
Batch Processing Examples for Gundert Portal Scraper

This file demonstrates processing multiple books concurrently with
proper error handling, progress tracking, and result aggregation.

Level: Intermediate
Use Case: Processing multiple manuscripts, production workflows
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from gundert_portal_scraper import (
    BookIdentifier,
    GundertPortalConnector,
    ContentScraper,
    create_transformation_engine,
    create_validation_engine
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingJob:
    """Represents a single book processing job."""
    url: str
    book_id: Optional[str] = None
    start_page: int = 1
    end_page: Optional[int] = None
    output_formats: List[str] = None
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ['usfm', 'json']


@dataclass
class ProcessingResult:
    """Result of processing a single book."""
    job: ProcessingJob
    success: bool
    output_files: List[Path]
    statistics: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    processing_time: float
    timestamp: datetime


class BatchProcessor:
    """Handles batch processing of multiple books."""
    
    def __init__(self, 
                 output_dir: Path,
                 max_workers: int = 3,
                 timeout_per_book: int = 600):  # 10 minutes per book
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.timeout_per_book = timeout_per_book
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize engines
        self.transformation_engine = create_transformation_engine()
        self.validation_engine = create_validation_engine()
        
        # Statistics
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.start_time = None
    
    def process_single_book(self, job: ProcessingJob) -> ProcessingResult:
        """Process a single book according to job specifications."""
        start_time = time.time()
        logger.info(f"Starting job: {job.url}")
        
        result = ProcessingResult(
            job=job,
            success=False,
            output_files=[],
            statistics={},
            errors=[],
            warnings=[],
            processing_time=0,
            timestamp=datetime.now()
        )
        
        try:
            # 1. Initialize book identifier
            book = BookIdentifier(job.url)
            job.book_id = book.book_id
            
            # 2. Extract content
            with GundertPortalConnector(book, use_selenium=True, headless=True) as connector:
                # Validate access
                if not connector.validate_book_access():
                    result.errors.append("Book not accessible")
                    return result
                
                # Get page count and adjust end_page if needed
                total_pages = connector.get_page_count()
                end_page = min(job.end_page or total_pages, total_pages)
                
                # Create scraper and extract
                scraper = ContentScraper(connector, preserve_formatting=True)
                
                def progress_callback(current, total):
                    logger.info(f"[{job.book_id}] Progress: {current}/{total} pages")
                
                book_data = scraper.scrape_full_book(
                    start_page=job.start_page,
                    end_page=end_page,
                    batch_size=5,
                    progress_callback=progress_callback
                )
                
                result.statistics = book_data.statistics.copy()
                
                # 3. Transform to requested formats
                for format_name in job.output_formats:
                    try:
                        output_file = self.output_dir / f"{job.book_id}.{format_name.replace('_', '.')}"
                        
                        transform_result = self.transformation_engine.transform(
                            book_storage=book_data,
                            target_format=format_name,
                            output_file=output_file
                        )
                        
                        if transform_result.success:
                            result.output_files.append(transform_result.output_file)
                            logger.info(f"[{job.book_id}] Generated {format_name}: {output_file}")
                        else:
                            result.warnings.append(f"Failed to generate {format_name}: {transform_result.errors}")
                            
                    except Exception as e:
                        result.warnings.append(f"Transformation error for {format_name}: {str(e)}")
                
                # 4. Validate outputs (optional)
                for output_file in result.output_files:
                    try:
                        format_type = self._detect_format_type(output_file)
                        if format_type:
                            validation_results = self.validation_engine.validate_file(
                                file_path=output_file,
                                format_type=format_type
                            )
                            
                            for val_result in validation_results:
                                if not val_result.is_valid:
                                    result.warnings.append(f"Validation issues in {output_file.name}: {val_result.issue_count} issues")
                                    
                    except Exception as e:
                        result.warnings.append(f"Validation error for {output_file}: {str(e)}")
                
                result.success = len(result.output_files) > 0
                
        except Exception as e:
            result.errors.append(f"Processing failed: {str(e)}")
            logger.error(f"[{job.book_id or 'Unknown'}] Error: {e}")
        
        finally:
            result.processing_time = time.time() - start_time
            
            if result.success:
                logger.info(f"[{job.book_id}] Completed successfully in {result.processing_time:.1f}s")
            else:
                logger.error(f"[{job.book_id or 'Unknown'}] Failed after {result.processing_time:.1f}s")
        
        return result
    
    def process_batch(self, jobs: List[ProcessingJob]) -> List[ProcessingResult]:
        """Process multiple books concurrently."""
        self.total_jobs = len(jobs)
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.start_time = time.time()
        
        logger.info(f"Starting batch processing of {self.total_jobs} books with {self.max_workers} workers")
        
        results = []
        
        # Sort jobs by priority
        sorted_jobs = sorted(jobs, key=lambda j: j.priority)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs
            future_to_job = {
                executor.submit(self.process_single_book, job): job
                for job in sorted_jobs
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_job, timeout=self.timeout_per_book * len(jobs)):
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.success:
                        self.completed_jobs += 1
                    else:
                        self.failed_jobs += 1
                    
                    # Log progress
                    processed = self.completed_jobs + self.failed_jobs
                    logger.info(f"Progress: {processed}/{self.total_jobs} books processed "
                              f"({self.completed_jobs} successful, {self.failed_jobs} failed)")
                    
                except Exception as e:
                    job = future_to_job[future]
                    logger.error(f"Job {job.url} generated an exception: {e}")
                    
                    # Create error result
                    error_result = ProcessingResult(
                        job=job,
                        success=False,
                        output_files=[],
                        statistics={},
                        errors=[str(e)],
                        warnings=[],
                        processing_time=0,
                        timestamp=datetime.now()
                    )
                    results.append(error_result)
                    self.failed_jobs += 1
        
        self._log_batch_summary(results)
        return results
    
    def _detect_format_type(self, file_path: Path) -> Optional[str]:
        """Detect format type from file extension."""
        extension = file_path.suffix.lower()
        format_mapping = {
            '.usfm': 'usfm',
            '.xml': 'tei_xml',
            '.json': 'parabible_json',
            '.docx': 'docx'
        }
        return format_mapping.get(extension)
    
    def _log_batch_summary(self, results: List[ProcessingResult]):
        """Log summary of batch processing results."""
        total_time = time.time() - self.start_time
        
        logger.info("\n" + "=" * 60)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total jobs: {self.total_jobs}")
        logger.info(f"Successful: {self.completed_jobs}")
        logger.info(f"Failed: {self.failed_jobs}")
        logger.info(f"Success rate: {self.completed_jobs/self.total_jobs*100:.1f}%")
        logger.info(f"Total time: {total_time:.1f} seconds")
        logger.info(f"Average time per job: {total_time/self.total_jobs:.1f} seconds")
        
        # Statistics
        total_pages = sum(r.statistics.get('pages_processed', 0) for r in results if r.success)
        total_files = sum(len(r.output_files) for r in results)
        
        logger.info(f"Total pages processed: {total_pages}")
        logger.info(f"Total output files: {total_files}")
        
        # Most common errors
        all_errors = []
        for result in results:
            all_errors.extend(result.errors)
        
        if all_errors:
            logger.info("\nMost common errors:")
            from collections import Counter
            error_counts = Counter(all_errors)
            for error, count in error_counts.most_common(3):
                logger.info(f"  - {error}: {count} occurrences")


def example_1_simple_batch():
    """Process a small batch of books with basic settings."""
    print("\n=== Example 1: Simple Batch Processing ===")
    
    # Define jobs
    jobs = [
        ProcessingJob(
            url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
            start_page=1,
            end_page=5,  # Small sample
            output_formats=['usfm', 'json'],
            priority=1
        )
        # Add more URLs here for real batch processing
        # ProcessingJob(url="https://...", ...)
    ]
    
    # Create processor
    processor = BatchProcessor(
        output_dir=Path("examples/output_samples/batch"),
        max_workers=2,
        timeout_per_book=300
    )
    
    # Process batch
    results = processor.process_batch(jobs)
    
    # Save detailed report
    save_batch_report(results, Path("examples/output_samples/batch/report.json"))
    
    return results


def example_2_priority_batch():
    """Process books with different priorities and formats."""
    print("\n=== Example 2: Priority-Based Batch Processing ===")
    
    jobs = [
        # High priority - important books first
        ProcessingJob(
            url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
            start_page=1,
            end_page=10,
            output_formats=['usfm', 'tei_xml', 'json'],
            priority=1  # High priority
        ),
        # Add more jobs with different priorities
        # ProcessingJob(url="https://...", priority=2),  # Medium
        # ProcessingJob(url="https://...", priority=3),  # Low
    ]
    
    processor = BatchProcessor(
        output_dir=Path("examples/output_samples/priority_batch"),
        max_workers=3
    )
    
    results = processor.process_batch(jobs)
    return results


def example_3_error_recovery():
    """Demonstrate error recovery and retry mechanisms."""
    print("\n=== Example 3: Error Recovery and Retries ===")
    
    class RetryProcessor(BatchProcessor):
        """Extended processor with retry capability."""
        
        def __init__(self, *args, max_retries: int = 2, **kwargs):
            super().__init__(*args, **kwargs)
            self.max_retries = max_retries
        
        def process_single_book_with_retry(self, job: ProcessingJob) -> ProcessingResult:
            """Process a book with retry logic."""
            last_result = None
            
            for attempt in range(self.max_retries + 1):
                if attempt > 0:
                    logger.info(f"[{job.book_id or 'Unknown'}] Retry attempt {attempt}/{self.max_retries}")
                    time.sleep(5 * attempt)  # Exponential backoff
                
                result = self.process_single_book(job)
                
                if result.success:
                    return result
                
                last_result = result
                logger.warning(f"[{job.book_id or 'Unknown'}] Attempt {attempt + 1} failed: {result.errors}")
            
            logger.error(f"[{job.book_id or 'Unknown'}] All retry attempts failed")
            return last_result
        
        def process_batch_with_retry(self, jobs: List[ProcessingJob]) -> List[ProcessingResult]:
            """Process batch with retry logic."""
            results = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_job = {
                    executor.submit(self.process_single_book_with_retry, job): job
                    for job in jobs
                }
                
                for future in as_completed(future_to_job):
                    result = future.result()
                    results.append(result)
            
            self._log_batch_summary(results)
            return results
    
    # Test with retry processor
    jobs = [
        ProcessingJob(
            url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
            end_page=3,
            output_formats=['usfm']
        ),
        # Add a potentially problematic URL for testing
        # ProcessingJob(url="https://opendigi.ub.uni-tuebingen.de/opendigi/MaybeProblematicBook")
    ]
    
    retry_processor = RetryProcessor(
        output_dir=Path("examples/output_samples/retry_batch"),
        max_workers=2,
        max_retries=2
    )
    
    results = retry_processor.process_batch_with_retry(jobs)
    return results


def example_4_progress_monitoring():
    """Monitor batch processing progress with detailed statistics."""
    print("\n=== Example 4: Progress Monitoring ===")
    
    class MonitoredProcessor(BatchProcessor):
        """Processor with enhanced progress monitoring."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.progress_file = self.output_dir / "progress.json"
            self.detailed_stats = {
                'jobs_completed': 0,
                'jobs_failed': 0,
                'total_pages_processed': 0,
                'total_processing_time': 0,
                'average_processing_time': 0,
                'start_time': None,
                'estimated_completion': None
            }
        
        def update_progress(self, result: ProcessingResult):
            """Update progress statistics."""
            if result.success:
                self.detailed_stats['jobs_completed'] += 1
                self.detailed_stats['total_pages_processed'] += result.statistics.get('pages_processed', 0)
            else:
                self.detailed_stats['jobs_failed'] += 1
            
            self.detailed_stats['total_processing_time'] += result.processing_time
            
            total_jobs_done = self.detailed_stats['jobs_completed'] + self.detailed_stats['jobs_failed']
            if total_jobs_done > 0:
                self.detailed_stats['average_processing_time'] = (
                    self.detailed_stats['total_processing_time'] / total_jobs_done
                )
                
                # Estimate completion time
                remaining_jobs = self.total_jobs - total_jobs_done
                estimated_remaining_time = remaining_jobs * self.detailed_stats['average_processing_time']
                self.detailed_stats['estimated_completion'] = (
                    datetime.now().timestamp() + estimated_remaining_time
                )
            
            # Save progress to file
            with open(self.progress_file, 'w') as f:
                json.dump({
                    **self.detailed_stats,
                    'timestamp': datetime.now().isoformat(),
                    'progress_percentage': (total_jobs_done / self.total_jobs) * 100
                }, f, indent=2)
        
        def process_batch_monitored(self, jobs: List[ProcessingJob]) -> List[ProcessingResult]:
            """Process batch with detailed monitoring."""
            self.detailed_stats['start_time'] = datetime.now().timestamp()
            
            results = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_job = {
                    executor.submit(self.process_single_book, job): job
                    for job in jobs
                }
                
                for future in as_completed(future_to_job):
                    result = future.result()
                    results.append(result)
                    self.update_progress(result)
                    
                    # Log detailed progress
                    total_done = self.detailed_stats['jobs_completed'] + self.detailed_stats['jobs_failed']
                    progress_pct = (total_done / self.total_jobs) * 100
                    
                    if self.detailed_stats['estimated_completion']:
                        est_completion = datetime.fromtimestamp(self.detailed_stats['estimated_completion'])
                        logger.info(f"Progress: {progress_pct:.1f}% - Estimated completion: {est_completion}")
                    else:
                        logger.info(f"Progress: {progress_pct:.1f}%")
            
            return results
    
    # Test monitored processing
    jobs = [
        ProcessingJob(
            url="https://opendigi.ub.uni-tuebingen.de/opendigi/GaXXXIV5_1",
            end_page=5,
            output_formats=['usfm', 'json']
        )
    ]
    
    monitored_processor = MonitoredProcessor(
        output_dir=Path("examples/output_samples/monitored_batch"),
        max_workers=2
    )
    
    results = monitored_processor.process_batch_monitored(jobs)
    
    # Show final progress file
    if monitored_processor.progress_file.exists():
        with open(monitored_processor.progress_file) as f:
            final_progress = json.load(f)
        logger.info(f"Final progress saved to: {monitored_processor.progress_file}")
        logger.info(f"Final statistics: {json.dumps(final_progress, indent=2)}")
    
    return results


def save_batch_report(results: List[ProcessingResult], report_file: Path):
    """Save detailed batch processing report."""
    report = {
        'summary': {
            'total_jobs': len(results),
            'successful_jobs': sum(1 for r in results if r.success),
            'failed_jobs': sum(1 for r in results if not r.success),
            'success_rate': sum(1 for r in results if r.success) / len(results) * 100 if results else 0,
            'total_output_files': sum(len(r.output_files) for r in results),
            'total_processing_time': sum(r.processing_time for r in results),
            'average_processing_time': sum(r.processing_time for r in results) / len(results) if results else 0,
            'timestamp': datetime.now().isoformat()
        },
        'jobs': []
    }
    
    for result in results:
        job_report = {
            'url': result.job.url,
            'book_id': result.job.book_id,
            'success': result.success,
            'output_files': [str(f) for f in result.output_files],
            'statistics': result.statistics,
            'errors': result.errors,
            'warnings': result.warnings,
            'processing_time': result.processing_time,
            'timestamp': result.timestamp.isoformat()
        }
        report['jobs'].append(job_report)
    
    # Ensure parent directory exists
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Batch report saved to: {report_file}")


def main():
    """Run all batch processing examples."""
    print("🚀 Starting Batch Processing Examples")
    print("=" * 50)
    
    # Example 1: Simple batch
    example_1_simple_batch()
    
    # Example 2: Priority-based batch
    example_2_priority_batch()
    
    # Example 3: Error recovery
    example_3_error_recovery()
    
    # Example 4: Progress monitoring
    example_4_progress_monitoring()
    
    print("\n" + "=" * 50)
    print("✅ Batch processing examples completed!")
    print("\nNext steps:")
    print("1. Check output_samples/ directories for batch results")
    print("2. Review progress.json files for processing statistics")
    print("3. Explore custom_transformation.py for format development")


if __name__ == "__main__":
    main()