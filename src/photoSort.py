#!/usr/bin/env python3
"""
photoSort.py - A utility to sort media files based on EXIF date taken.

This script recursively scans a source directory for media files (images, videos),
extracts the date taken from EXIF data, and organizes them into a destination
directory structure of YYYY/MM - Month (e.g., 2025/01 - Jan).
"""

import os
import sys
import shutil
import argparse
import logging
from datetime import datetime
from pathlib import Path
import mimetypes

# For EXIF data extraction
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import exifread
    HAS_EXIFREAD = True
except ImportError:
    HAS_EXIFREAD = False

try:
    import ffmpeg
    HAS_FFMPEG = True
except ImportError:
    HAS_FFMPEG = False

try:
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File types to process
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.heic', '.heif', '.dng'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.3gp', '.flv'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)

def check_dependencies():
    """Check if required dependencies are installed."""
    if not HAS_PIL and not HAS_EXIFREAD:
        logger.error("Neither PIL nor exifread is installed. At least one is required for image processing.")
        logger.error("Install with: pip install Pillow exifread")
        return False
    
    if not HAS_FFMPEG and any(VIDEO_EXTENSIONS):
        logger.warning("ffmpeg-python is not installed. Video date extraction may be limited.")
        logger.warning("Install with: pip install ffmpeg-python")
    
    if not HAS_PIEXIF:
        logger.warning("piexif is not installed. Cannot add EXIF data to images without it.")
        logger.warning("Install with: pip install piexif")
    
    return True

def get_date_taken_from_image(file_path):
    """Extract the date taken from image EXIF data."""
    # Try with PIL first
    if HAS_PIL:
        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == 'DateTimeOriginal':
                            return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            logger.error(f"PIL EXIF extraction failed for {file_path}: {e}")
    
    # Try with exifread as fallback
    if HAS_EXIFREAD:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                if 'EXIF DateTimeOriginal' in tags:
                    date_str = str(tags['EXIF DateTimeOriginal'])
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            logger.error(f"exifread extraction failed for {file_path}: {e}")
    
    return None

def get_date_taken_from_video(file_path):
    """Extract the creation date from video metadata."""
    if HAS_FFMPEG:
        try:
            probe = ffmpeg.probe(file_path)
            creation_time = None
            
            # Try to find creation_time in metadata
            if 'format' in probe and 'tags' in probe['format']:
                tags = probe['format']['tags']
                if 'creation_time' in tags:
                    creation_time = tags['creation_time']
            
            # Check streams if not found in format
            if not creation_time and 'streams' in probe:
                for stream in probe['streams']:
                    if 'tags' in stream and 'creation_time' in stream['tags']:
                        creation_time = stream['tags']['creation_time']
                        break
            
            if creation_time:
                # Handle different date formats
                try:
                    # ISO format: 2020-05-20T15:30:10.000000Z
                    return datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Try other common formats
                        return datetime.strptime(creation_time, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        logger.error(f"Could not parse creation time: {creation_time}")
        except Exception as e:
            logger.error(f"ffmpeg extraction failed for {file_path}: {e}")
    
    return None

def get_file_date(file_path):
    """Get the date taken from a media file, falling back to file modification time."""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Try to get date from metadata
    date_taken = None
    
    if file_ext in IMAGE_EXTENSIONS:
        date_taken = get_date_taken_from_image(file_path)
    elif file_ext in VIDEO_EXTENSIONS:
        date_taken = get_date_taken_from_video(file_path)
    
    # Fall back to file modification time if no EXIF data
    if not date_taken:
        mtime = os.path.getmtime(file_path)
        date_taken = datetime.fromtimestamp(mtime)
        logger.info(f"No metadata date found for {file_path}, using modification time: {date_taken}")
        
        # Try to add modification time to EXIF data for images
        if file_ext in IMAGE_EXTENSIONS and HAS_PIL and HAS_PIEXIF:
            try:
                add_date_to_exif(file_path, date_taken)
                logger.info(f"Added modification time to EXIF data for {file_path}")
            except Exception as e:
                logger.error(f"Failed to add modification time to EXIF data for {file_path}: {e}")
    
    return date_taken

def add_date_to_exif(file_path, date_taken):
    """Add date taken to EXIF data of an image file."""
    if not HAS_PIL or not HAS_PIEXIF:
        return False
    
    try:
        # Only works with JPEG files
        if not file_path.lower().endswith(('.jpg', '.jpeg')):
            return False
        
        # Format date string in EXIF format
        date_str = date_taken.strftime("%Y:%m:%d %H:%M:%S")
        
        # Get existing EXIF data or create new
        try:
            exif_dict = piexif.load(file_path)
        except:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        
        # Add DateTimeOriginal to EXIF data
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
        exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
        
        # Save the EXIF data back to the file
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, file_path)
        
        return True
    except Exception as e:
        logger.error(f"Error adding EXIF data: {e}")
        return False

def create_destination_path(dest_root, date_taken, file_path):
    """Create the destination path based on date taken."""
    # Get month name
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_name = month_names[date_taken.month - 1]
    
    # Create directory in format "YYYY/MM - Month"
    year_month_dir = os.path.join(dest_root, f"{date_taken.year:04d}", 
                                 f"{date_taken.month:02d} - {month_name}")
    os.makedirs(year_month_dir, exist_ok=True)
    
    # Use original filename
    filename = os.path.basename(file_path)
    return os.path.join(year_month_dir, filename)

def process_file(file_path, dest_root, dry_run=False, copy_instead_of_move=False):
    """Process a single media file."""
    try:
        date_taken = get_file_date(file_path)
        dest_path = create_destination_path(dest_root, date_taken, file_path)
        
        # Handle filename conflicts
        if os.path.exists(dest_path) and os.path.getsize(file_path) != os.path.getsize(dest_path):
            base, ext = os.path.splitext(dest_path)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = f"{base}_{counter}{ext}"
                counter += 1
        
        # Skip if destination exists and has same size
        if os.path.exists(dest_path) and os.path.getsize(file_path) == os.path.getsize(dest_path):
            logger.info(f"Skipping {file_path} (already exists at destination with same size)")
            return
        
        if dry_run:
            logger.info(f"Would {'copy' if copy_instead_of_move else 'move'} {file_path} to {dest_path}")
        else:
            if copy_instead_of_move:
                logger.debug(f"Copying {file_path} to {dest_path}")
                shutil.copy2(file_path, dest_path)
            else:
                logger.debug(f"Moving {file_path} to {dest_path}")
                shutil.move(file_path, dest_path)
        
        return True
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False

def process_directory(source_dir, dest_root, dry_run=False, copy_instead_of_move=False):
    """Recursively process all media files in the source directory."""
    source_dir = os.path.abspath(source_dir)
    dest_root = os.path.abspath(dest_root)
    
    if source_dir == dest_root:
        logger.error("Source and destination directories cannot be the same.")
        return False
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for root, _, files in os.walk(source_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in MEDIA_EXTENSIONS:
                result = process_file(file_path, dest_root, dry_run, copy_instead_of_move)
                if result:
                    success_count += 1
                else:
                    error_count += 1
            else:
                skipped_count += 1
                logger.info(f"Skipping non-media file: {file_path}")
    
    logger.info(f"Processing complete: {success_count} files processed, {error_count} errors, {skipped_count} skipped")
    return success_count > 0 and error_count == 0

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Sort media files based on EXIF date taken.')
    parser.add_argument('source', help='Source directory containing media files')
    parser.add_argument('destination', help='Destination directory for sorted files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--copy', action='store_true', help='Copy files instead of moving them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if not check_dependencies():
        sys.exit(1)
    
    if not os.path.isdir(args.source):
        logger.error(f"Source directory does not exist: {args.source}")
        sys.exit(1)
    
    os.makedirs(args.destination, exist_ok=True)
    
    logger.info(f"Starting media sort from {args.source} to {args.destination}")
    logger.info(f"Mode: {'Dry run' if args.dry_run else 'Copy' if args.copy else 'Move'}")
    
    success = process_directory(args.source, args.destination, args.dry_run, args.copy)
    
    if success:
        logger.info("Media sorting completed successfully")
        sys.exit(0)
    else:
        logger.error("Media sorting completed with errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
