"""Content extraction service for fetching and extracting content from URLs"""

import asyncio
import hashlib
import ipaddress
import logging
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from src.core.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Represents a media item (image, audio, video)"""
    url: str
    media_type: str  # 'image', 'audio', 'video'
    title: Optional[str] = None
    local_path: Optional[str] = None
    storage_path: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    download_error: Optional[str] = None
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContentExtract:
    """Extracted content from a URL"""
    url: str
    text_content: str
    images: List[MediaItem] = field(default_factory=list)
    audio: List[MediaItem] = field(default_factory=list)
    video: List[MediaItem] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    extraction_errors: List[str] = field(default_factory=list)

    def has_content(self) -> bool:
        """Check if extraction found any content"""
        return bool(
            self.text_content or 
            self.images or 
            self.audio or 
            self.video
        )


class ContentExtractionError(Exception):
    """Base exception for content extraction errors"""
    pass


class URLValidationError(ContentExtractionError):
    """Exception for invalid URLs"""
    pass


class ContentFetchError(ContentExtractionError):
    """Exception for URL fetch failures"""
    pass


class ContentExtractionService:
    """Service for extracting content from URLs"""

    # Media type detection patterns
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
    VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.m3u8'}
    MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
    MEDIA_CONTENT_PREFIXES = {
        "image": ("image/",),
        "audio": ("audio/",),
        "video": ("video/", "application/vnd.apple.mpegurl"),
    }

    # Headers to mimic browser
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    def __init__(self):
        """Initialize the extraction service"""
        self.timeout = aiohttp.ClientTimeout(total=settings.CONTENT_EXTRACTION_TIMEOUT)
        self.max_content_size = settings.MAX_CONTENT_SIZE
        self.media_dir = Path(settings.DOWNLOADED_MEDIA_DIR)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    async def extract(self, url: str) -> ContentExtract:
        """
        Extract content from a URL
        
        **Satisfies**: FR-001 (Accept URL and extract content)
        
        Args:
            url: URL to extract from
            
        Returns:
            ContentExtract: Extracted content with text, images, audio, video
            
        Raises:
            URLValidationError: If URL is invalid
            ContentFetchError: If URL cannot be fetched
        """
        # Validate URL
        self._validate_url(url)

        # Fetch content
        try:
            html_content = await self._fetch_url(url)
        except Exception as e:
            logger.error(f"Failed to fetch URL: {url}", exc_info=True)
            raise ContentFetchError(f"Failed to fetch URL: {str(e)}")

        # Parse content
        extract = await self._parse_content(url, html_content)

        if settings.DOWNLOAD_EXTRACTED_MEDIA:
            await self._download_extracted_media(extract)
        
        logger.info(f"Successfully extracted content from {url}")
        return extract

    def _validate_url(self, url: str) -> None:
        """
        Validate URL for security and format
        
        **Satisfies**: T-203 (URL Validation & Security)
        """
        if not isinstance(url, str):
            raise URLValidationError("URL must be a string")

        if len(url) > 2048:
            raise URLValidationError("URL too long (max 2048 characters)")

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise URLValidationError(f"Invalid URL format: {str(e)}")

        if parsed.scheme not in {"http", "https"}:
            raise URLValidationError("URL must start with http:// or https://")

        hostname = parsed.hostname
        if not hostname:
            raise URLValidationError("URL must include a valid hostname")

        if parsed.username or parsed.password:
            raise URLValidationError("URLs with embedded credentials are blocked")

        if hostname.lower() in {"localhost", "localhost.localdomain"}:
            raise URLValidationError("URLs to private hosts are blocked")

        try:
            ip = ipaddress.ip_address(hostname.strip("[]"))
        except ValueError:
            if "." not in hostname:
                raise URLValidationError("URL must include a fully qualified domain name")
            return

        if any(
            (
                ip.is_private,
                ip.is_loopback,
                ip.is_link_local,
                ip.is_multicast,
                ip.is_reserved,
                ip.is_unspecified,
            )
        ):
            raise URLValidationError("URLs to private or reserved IP addresses are blocked")

    async def _fetch_url(self, url: str, max_retries: int = 3) -> str:
        """
        Fetch URL content with retries
        
        **Satisfies**: FR-001 (Fetch URL content with proper headers and timeout)
        """
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(
                        url,
                        headers=self.DEFAULT_HEADERS,
                        ssl=False,  # For testing; should be True in production
                        allow_redirects=True
                    ) as response:
                        if response.status == 200:
                            # Check content size
                            content_length = response.headers.get('Content-Length')
                            if content_length and int(content_length) > self.max_content_size:
                                raise ContentFetchError("Content exceeds size limit")

                            text = await response.text()
                            return text
                        else:
                            logger.warning(f"URL returned status {response.status}: {url}")
                            if response.status >= 400:
                                raise ContentFetchError(f"HTTP {response.status}")

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching URL (attempt {attempt + 1}): {url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.warning(f"Error fetching URL (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise ContentFetchError(f"Failed to fetch URL after {max_retries} attempts")

    async def _parse_content(self, url: str, html_content: str) -> ContentExtract:
        """
        Parse HTML content and extract text, images, audio, video
        
        **Satisfies**: FR-001 (Extract text, images, audio, video)
        """
        extract = ContentExtract(url=url, text_content="")

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract text content
            extract.text_content = self._extract_text(soup)

            # Extract media URLs
            extract.images = self._extract_images(soup, url)
            extract.audio = self._extract_audio(soup, url)
            extract.video = self._extract_video(soup, url)

        except Exception as e:
            logger.error(f"Error parsing content: {str(e)}", exc_info=True)
            extract.extraction_errors.append(f"Parsing error: {str(e)}")

        return extract

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """
        Extract text content from HTML
        
        **Satisfies**: T-301 (Extract text and clean HTML tags)
        """
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text[:10000]  # Limit to first 10k chars for now

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[MediaItem]:
        """Extract image URLs"""
        images = []
        for img in soup.find_all('img', limit=50):  # Limit to first 50
            src = img.get('src')
            if src:
                abs_url = urljoin(base_url, src)
                alt = img.get('alt', '')
                images.append(MediaItem(
                    url=abs_url,
                    media_type='image',
                    title=alt
                ))
        return images

    def _extract_audio(self, soup: BeautifulSoup, base_url: str) -> List[MediaItem]:
        """Extract audio URLs"""
        audio_items = []
        
        # Find audio tags
        for audio in soup.find_all('audio', limit=20):
            src = audio.get('src')
            if src:
                audio_items.append(MediaItem(
                    url=urljoin(base_url, src),
                    media_type='audio',
                    title=audio.get('title', 'Audio')
                ))
            for source in audio.find_all('source'):
                src = source.get('src')
                if src:
                    abs_url = urljoin(base_url, src)
                    audio_items.append(MediaItem(
                        url=abs_url,
                        media_type='audio',
                        title='Audio'
                    ))
        
        return audio_items

    def _extract_video(self, soup: BeautifulSoup, base_url: str) -> List[MediaItem]:
        """Extract video URLs"""
        videos = []
        
        # Find video tags
        for video in soup.find_all('video', limit=20):
            src = video.get('src')
            if src:
                videos.append(MediaItem(
                    url=urljoin(base_url, src),
                    media_type='video',
                    title=video.get('title', 'Video')
                ))
            for source in video.find_all('source'):
                src = source.get('src')
                if src:
                    abs_url = urljoin(base_url, src)
                    videos.append(MediaItem(
                        url=abs_url,
                        media_type='video',
                        title='Video'
                    ))
        
        # Find iframe embeds (YouTube, Vimeo, etc.)
        for iframe in soup.find_all('iframe', limit=20):
            src = iframe.get('src')
            if src and any(host in src for host in ['youtube', 'vimeo', 'dailymotion']):
                videos.append(MediaItem(
                    url=src,
                    media_type='video',
                    title=iframe.get('title', 'Embedded Video')
                ))
        
        return videos

    async def _download_extracted_media(self, extract: ContentExtract) -> None:
        """Download a bounded number of extracted media assets to local object-store style paths."""
        media_items = (extract.images + extract.audio + extract.video)[: settings.MEDIA_DOWNLOAD_LIMIT]
        if not media_items:
            return

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            await asyncio.gather(
                *(self.download_media_item(session, item) for item in media_items),
                return_exceptions=True,
            )

    async def download_media_item(self, session: aiohttp.ClientSession, item: MediaItem) -> MediaItem:
        """Download and validate one media item.

        The MVP stores files locally under DOWNLOADED_MEDIA_DIR while exposing a stable
        ``storage_path`` that mirrors the object key shape expected from S3-backed storage.
        """
        try:
            self._validate_url(item.url)
            extension = self._extension_for_url(item.url)
            if extension not in self._extensions_for_type(item.media_type):
                raise ContentFetchError(f"Unsupported {item.media_type} file type")

            async with session.get(item.url, headers=self.DEFAULT_HEADERS, ssl=False) as response:
                if response.status >= 400:
                    raise ContentFetchError(f"HTTP {response.status}")

                content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                if content_type and not self._content_type_matches(item.media_type, content_type):
                    raise ContentFetchError(f"Unexpected content type: {content_type}")

                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > settings.MAX_MEDIA_FILE_SIZE:
                    raise ContentFetchError("Media file exceeds size limit")

                data = await response.read()
                if len(data) > settings.MAX_MEDIA_FILE_SIZE:
                    raise ContentFetchError("Media file exceeds size limit")
                if not data:
                    raise ContentFetchError("Media file is empty")

            digest = hashlib.sha256(item.url.encode("utf-8")).hexdigest()[:20]
            media_dir = self.media_dir / item.media_type
            media_dir.mkdir(parents=True, exist_ok=True)
            file_path = media_dir / f"{digest}{extension}"
            file_path.write_bytes(data)

            item.local_path = str(file_path)
            item.storage_path = f"media/{item.media_type}/{file_path.name}"
            item.content_type = content_type or None
            item.size_bytes = len(data)
            item.download_error = None
        except Exception as exc:
            item.download_error = str(exc)
            logger.warning("Media download failed", extra={"url": item.url, "error": item.download_error})

        return item

    def _extension_for_url(self, url: str) -> str:
        """Return lowercase extension from a media URL path."""
        return Path(urlparse(url).path).suffix.lower()

    def _extensions_for_type(self, media_type: str) -> set[str]:
        if media_type == "image":
            return self.IMAGE_EXTENSIONS
        if media_type == "audio":
            return self.AUDIO_EXTENSIONS
        if media_type == "video":
            return self.VIDEO_EXTENSIONS
        return set()

    def _content_type_matches(self, media_type: str, content_type: str) -> bool:
        prefixes = self.MEDIA_CONTENT_PREFIXES.get(media_type, ())
        return any(content_type.startswith(prefix) for prefix in prefixes)


# Global instance
extraction_service = ContentExtractionService()
