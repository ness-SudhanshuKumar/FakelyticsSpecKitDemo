"""Content extraction service for fetching and extracting content from URLs"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
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
    size_bytes: Optional[int] = None
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

    # Headers to mimic browser
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    def __init__(self):
        """Initialize the extraction service"""
        self.timeout = aiohttp.ClientTimeout(total=settings.CONTENT_EXTRACTION_TIMEOUT)
        self.max_content_size = settings.MAX_CONTENT_SIZE
        self.media_dir = Path(settings.DOWNLOADED_MEDIA_DIR)
        self.media_dir.mkdir(exist_ok=True)

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
        
        logger.info(f"Successfully extracted content from {url}")
        return extract

    def _validate_url(self, url: str) -> None:
        """
        Validate URL for security and format
        
        **Satisfies**: T-203 (URL Validation & Security)
        """
        if not isinstance(url, str):
            raise URLValidationError("URL must be a string")

        if not url.startswith(("http://", "https://")):
            raise URLValidationError("URL must start with http:// or https://")

        if len(url) > 2048:
            raise URLValidationError("URL too long (max 2048 characters)")

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise URLValidationError(f"Invalid URL format: {str(e)}")

        # Check for private IPs (basic check)
        hostname = parsed.hostname
        if hostname:
            # Block common private IP patterns
            private_patterns = [
                '127.', '192.168.', '10.', '172.16.', '172.17.',
                'localhost', '0.0.0.0'
            ]
            if any(hostname.startswith(p) for p in private_patterns):
                raise URLValidationError("URLs to private IP addresses are blocked")

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


# Global instance
extraction_service = ContentExtractionService()
