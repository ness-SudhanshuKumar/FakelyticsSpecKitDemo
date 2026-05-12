"""Media storage service for downloading and storing extracted media files."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp
from urllib.parse import urlparse

from src.core.config.settings import settings
from src.core.extraction.service import MediaItem

logger = logging.getLogger(__name__)


@dataclass
class MediaDownloadResult:
    """Result of media download operation."""
    success: bool
    local_path: Optional[str] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None
    downloaded_at: datetime = None

    def __post_init__(self):
        if self.downloaded_at is None:
            self.downloaded_at = datetime.utcnow()


class MediaStorageError(Exception):
    """Base exception for media storage errors."""
    pass


class MediaStorage:
    """Service for downloading and storing media files from extracted URLs."""

    # Maximum file sizes by type (in bytes)
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
    MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB

    # Allowed MIME types
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml', 'image/bmp'
    }
    ALLOWED_AUDIO_TYPES = {
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/flac', 'audio/aac'
    }
    ALLOWED_VIDEO_TYPES = {
        'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska',
        'video/x-flv', 'application/x-mpegURL'
    }

    def __init__(self):
        """Initialize media storage service."""
        self.storage_base = Path(settings.DOWNLOADED_MEDIA_DIR)
        self.storage_base.mkdir(parents=True, exist_ok=True)
        self.timeout = aiohttp.ClientTimeout(total=settings.CONTENT_EXTRACTION_TIMEOUT)

    def _get_max_size(self, media_type: str) -> int:
        """Get maximum file size for media type."""
        if media_type == 'image':
            return self.MAX_IMAGE_SIZE
        elif media_type == 'audio':
            return self.MAX_AUDIO_SIZE
        elif media_type == 'video':
            return self.MAX_VIDEO_SIZE
        return 10 * 1024 * 1024  # Default 10 MB

    def _is_allowed_type(self, media_type: str, content_type: str) -> bool:
        """Check if content type is allowed for media type."""
        content_type_lower = (content_type or '').lower()
        
        if media_type == 'image':
            return content_type_lower in self.ALLOWED_IMAGE_TYPES
        elif media_type == 'audio':
            return content_type_lower in self.ALLOWED_AUDIO_TYPES
        elif media_type == 'video':
            return content_type_lower in self.ALLOWED_VIDEO_TYPES
        
        return False

    def _generate_storage_path(self, request_id: str, media_type: str, url: str) -> Path:
        """Generate local storage path for media file."""
        # Parse URL to get filename
        parsed = urlparse(url)
        filename = parsed.path.split('/')[-1] or f"media_{hash(url) % 10000}"
        
        # Create subdirectory: media/<request_id>/<media_type>/
        subdir = self.storage_base / request_id / media_type
        subdir.mkdir(parents=True, exist_ok=True)
        
        # Return full path
        return subdir / filename

    async def download_media(
        self,
        media_item: MediaItem,
        request_id: str,
        max_retries: int = 3
    ) -> MediaDownloadResult:
        """
        Download and store a single media file.
        
        **Satisfies**: T-202 (Download and store extracted media files)
        
        Args:
            media_item: Media item to download
            request_id: Request ID for organization
            max_retries: Maximum retry attempts
            
        Returns:
            MediaDownloadResult: Result of download operation
        """
        local_path = self._generate_storage_path(request_id, media_item.media_type, media_item.url)
        max_size = self._get_max_size(media_item.media_type)

        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(media_item.url, ssl=False, allow_redirects=True) as response:
                        # Check response status
                        if response.status != 200:
                            logger.warning(
                                f"Media download returned status {response.status}",
                                extra={"url": media_item.url, "media_type": media_item.media_type, "attempt": attempt + 1}
                            )
                            continue

                        # Validate content type
                        content_type = response.headers.get('Content-Type', '')
                        if not self._is_allowed_type(media_item.media_type, content_type):
                            logger.warning(
                                f"Unexpected content type for media",
                                extra={"url": media_item.url, "media_type": media_item.media_type, "content_type": content_type}
                            )
                            continue

                        # Check content length
                        content_length = response.headers.get('Content-Length')
                        if content_length and int(content_length) > max_size:
                            logger.warning(
                                f"Media file exceeds size limit",
                                extra={"url": media_item.url, "size": content_length, "limit": max_size}
                            )
                            continue

                        # Download file
                        file_size = 0
                        with open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                file_size += len(chunk)
                                if file_size > max_size:
                                    logger.warning(
                                        f"Media file exceeds size limit during download",
                                        extra={"url": media_item.url, "size": file_size, "limit": max_size}
                                    )
                                    local_path.unlink(missing_ok=True)
                                    raise MediaStorageError("File size exceeds limit")
                                f.write(chunk)

                        logger.info(
                            f"Successfully downloaded media",
                            extra={"url": media_item.url, "size": file_size, "path": str(local_path)}
                        )

                        return MediaDownloadResult(
                            success=True,
                            local_path=str(local_path),
                            size_bytes=file_size,
                            downloaded_at=datetime.utcnow()
                        )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout downloading media (attempt {attempt + 1})",
                    extra={"url": media_item.url}
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
            except Exception as e:
                logger.warning(
                    f"Error downloading media (attempt {attempt + 1}): {str(e)}",
                    extra={"url": media_item.url, "error": str(e)}
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return MediaDownloadResult(
            success=False,
            error=f"Failed to download media after {max_retries} attempts"
        )

    async def download_all_media(
        self,
        media_items: list[MediaItem],
        request_id: str
    ) -> dict:
        """
        Download all media items concurrently.
        
        Args:
            media_items: List of media items to download
            request_id: Request ID for organization
            
        Returns:
            Dictionary with results per media type
        """
        if not media_items:
            return {"images": [], "audio": [], "video": []}

        # Download all media concurrently
        download_tasks = [
            self.download_media(item, request_id)
            for item in media_items
        ]

        results = await asyncio.gather(*download_tasks, return_exceptions=True)

        # Organize results by media type
        organized_results = {"images": [], "audio": [], "video": []}
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Media download task failed: {result}")
                continue
            
            media_item = media_items[i]
            if result.success:
                organized_results[f"{media_item.media_type}s"].append({
                    "url": media_item.url,
                    "local_path": result.local_path,
                    "size_bytes": result.size_bytes,
                    "title": media_item.title
                })
            else:
                logger.warning(
                    f"Failed to download media: {result.error}",
                    extra={"url": media_item.url}
                )

        return organized_results

    def cleanup_media(self, request_id: str) -> bool:
        """
        Clean up downloaded media files for a request.
        
        **Satisfies**: T-202 (Clean up files after processing)
        
        Args:
            request_id: Request ID to clean up
            
        Returns:
            True if cleanup successful
        """
        try:
            media_dir = self.storage_base / request_id
            if media_dir.exists():
                import shutil
                shutil.rmtree(media_dir)
                logger.info(f"Cleaned up media for request {request_id}")
                return True
        except Exception as e:
            logger.error(f"Error cleaning up media for request {request_id}: {str(e)}")
            return False

        return False


# Global instance
media_storage = MediaStorage()
