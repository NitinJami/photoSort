# PhotoSort

A utility to sort media files (images and videos) based on EXIF date taken.
Code Generated in Cursor AI using Claude-3.7-sonnet!

## Features

- Recursively scans a source directory for media files
- Extracts date taken from EXIF data for images and videos
- Organizes files into a destination directory structure of `YYYY/MM - Month` (e.g., `2025/01 - Jan`)
- Handles filename conflicts by appending a counter
- Supports both copying and moving files
- Provides a dry-run mode to preview changes
- Adds file modification time to EXIF data when original EXIF data is not available

## Supported File Types

- Images: .jpg, .jpeg, .png, .gif, .tiff, .bmp, .heic, .heif
- Videos: .mp4, .mov, .avi, .mkv, .wmv, .m4v, .3gp, .flv

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Basic usage:

```bash
python src/photoSort.py /path/to/source /path/to/destination
```

Options:

- `--dry-run`: Show what would be done without making changes
- `--copy`: Copy files instead of moving them
- `--verbose` or `-v`: Enable verbose logging

Examples:

```bash
# Move files from source to destination
python src/photoSort.py ~/Pictures/Unsorted ~/Pictures/Sorted

# Copy files instead of moving them
python src/photoSort.py ~/Pictures/Unsorted ~/Pictures/Sorted --copy

# Preview what would be done without making changes
python src/photoSort.py ~/Pictures/Unsorted ~/Pictures/Sorted --dry-run

# Enable verbose logging
python src/photoSort.py ~/Pictures/Unsorted ~/Pictures/Sorted --verbose
```

## Fallback Behavior

If EXIF data cannot be extracted from a file, the script will:
1. Fall back to using the file's modification time
2. For JPEG images, add the modification time to the file's EXIF data to preserve the date information

## Dependencies

- Pillow: For extracting EXIF data from images
- exifread: Alternative library for extracting EXIF data
- ffmpeg-python: For extracting creation date from video files
- piexif: For adding EXIF data to images

## License

This project is open source and available under the MIT License.
