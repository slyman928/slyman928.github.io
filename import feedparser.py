import feedparser
import requests
import time
import os
import logging
import json
import argparse
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# === CONFIG ===
RSS_FEED_URL = "https://www.sciencedaily.com/rss/all.xml"
NUM_ARTICLES = 5   # How many to summarize per run
HTML_FILE = "news_digest.html"
CACHE_FILE = "article_cache.json"
LOG_FILE = "feed_parser.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Article:
    title: str
    link: str
    content: str
    published: Optional[str] = None
    summary: Optional[str] = None
    content_hash: Optional[str] = None

# Initialize OpenAI client
def get_openai_client():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)

def fetch_rss_articles(url: str, num_articles: int = 5) -> List[Article]:
    """Fetch and parse RSS articles with better error handling and content extraction."""
    try:
        logger.info(f"Fetching RSS feed from {url}")
        feed = feedparser.parse(url)
        
        if not feed.entries:
            logger.warning("No entries found in RSS feed")
            return []
            
        entries = feed.entries[:num_articles]
        articles = []
        
        for entry in entries:
            try:
                link = getattr(entry, 'link', '')
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '')
                published = getattr(entry, 'published', None)
                
                # Try to fetch full article text with better parsing
                article_text = extract_article_content(link, summary)
                
                # Create content hash for caching
                content_hash = hashlib.md5(article_text.encode()).hexdigest()
                
                article = Article(
                    title=title,
                    link=link,
                    content=article_text,
                    published=published,
                    content_hash=content_hash
                )
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Error processing entry: {e}")
                continue
                
        logger.info(f"Successfully fetched {len(articles)} articles")
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching RSS feed: {e}")
        return []

def extract_article_content(url: str, fallback_summary: str) -> str:
    """Extract article content with proper HTML parsing."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=15, headers=headers)
        
        if not resp.ok:
            return fallback_summary
            
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Try multiple selectors for ScienceDaily
        content_selectors = [
            '#text',
            '.story-body',
            '[id*="text"]',
            '.article-content'
        ]
        
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                # Remove unwanted elements
                for elem in content_div.find_all(['script', 'style', 'advertisement']):
                    elem.decompose()
                
                text = content_div.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Only use if substantial content
                    return text
        
        return fallback_summary
        
    except Exception as e:
        logger.warning(f"Could not extract content from {url}: {e}")
        return fallback_summary

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def summarize_article(article: Article, client: OpenAI) -> str:
    """Summarize article using OpenAI with retry logic."""
    prompt = (
        "Read the following science news article. Ignore clickbait, hype, and background. "
        "Distill it to one or two factual sentences covering the new finding or breakthrough only. "
        "Omit speculation and keep it neutral and concise.\n\n"
        f"Title: {article.title}\n\nArticle:\n{article.content[:3000]}"  # Limit content length
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # More cost-effective than gpt-4
            messages=[
                {"role": "system", "content": "You summarize science news articles to their bare essentials."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=120
        )
        summary = response.choices[0].message.content
        if summary:
            summary = summary.strip()
        else:
            summary = "[Empty response from AI]"
        logger.info(f"Successfully summarized: {article.title[:50]}...")
        return summary
        
    except Exception as e:
        logger.error(f"Summary failed for '{article.title}': {e}")
        return f"[Summary failed: {str(e)}]"

def load_cache() -> Dict[str, str]:
    """Load cached article summaries."""
    cache_path = Path(CACHE_FILE)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
    return {}

def save_cache(cache: Dict[str, str]):
    """Save article summaries to cache."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Could not save cache: {e}")

def write_html(articles: List[Article], html_file: str):
    """Generate improved HTML output with timestamps and better styling."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_head = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Science News Digest</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; padding: 40px; background: linear-gradient(135deg, #f6faff 0%, #e0f2fe 100%);
            line-height: 1.6;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 3em; }}
        .header h1 {{ color: #1e40af; margin-bottom: 0.5em; }}
        .timestamp {{ color: #6b7280; font-size: 0.9em; }}
        .article {{ 
            margin-bottom: 2em; padding: 2em; border-radius: 16px; 
            background: #fff; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border-left: 4px solid #3b82f6;
            transition: transform 0.2s ease;
        }}
        .article:hover {{ transform: translateY(-2px); }}
        .title {{ 
            font-size: 1.3em; font-weight: 600; margin-bottom: 0.8em; 
            line-height: 1.4;
        }}
        .title a {{ color: #1e40af; text-decoration: none; }}
        .title a:hover {{ text-decoration: underline; }}
        .summary {{ 
            color: #374151; font-size: 1.05em; 
            background: #f8fafc; padding: 1em; border-radius: 8px;
            border-left: 3px solid #e5e7eb;
        }}
        .published {{ 
            color: #6b7280; font-size: 0.85em; margin-top: 0.5em;
            font-style: italic;
        }}
        .footer {{ 
            text-align: center; margin-top: 3em; padding-top: 2em;
            border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 0.9em;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔬 Science News Digest</h1>
        <div class="timestamp">Generated on {timestamp}</div>
    </div>
'''
    
    html_end = '''
    <div class="footer">
        Powered by AI • Data from ScienceDaily
    </div>
</div>
</body>
</html>'''

    items = []
    for article in articles:
        published_info = ""
        if article.published:
            try:
                # Parse and format the published date
                from dateutil import parser
                pub_date = parser.parse(article.published)
                published_info = f'<div class="published">Published: {pub_date.strftime("%B %d, %Y")}</div>'
            except:
                published_info = f'<div class="published">Published: {article.published}</div>'
        
        block = f'''
<div class="article">
    <div class="title">
        <a href="{article.link}" target="_blank">{article.title}</a>
    </div>
    <div class="summary">{article.summary or "Summary not available"}</div>
    {published_info}
</div>'''
        items.append(block)

    html_full = html_head + "\n".join(items) + html_end
    
    try:
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_full)
        logger.info(f"HTML summary saved to: {html_file}")
    except Exception as e:
        logger.error(f"Could not write HTML file: {e}")

def main():
    """Main function with improved error handling and caching."""
    parser = argparse.ArgumentParser(description='RSS News Summarizer')
    parser.add_argument('--url', default=RSS_FEED_URL, help='RSS feed URL')
    parser.add_argument('--count', type=int, default=NUM_ARTICLES, help='Number of articles to process')
    parser.add_argument('--output', default=HTML_FILE, help='Output HTML file')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    
    args = parser.parse_args()
    
    try:
        # Initialize OpenAI client
        client = get_openai_client()
        
        # Load cache
        cache = {} if args.no_cache else load_cache()
        
        logger.info("Fetching latest articles...")
        articles = fetch_rss_articles(args.url, args.count)
        
        if not articles:
            logger.error("No articles found. Exiting.")
            return
        
        # Process articles with caching
        for article in articles:
            if article.content_hash and article.content_hash in cache:
                article.summary = cache[article.content_hash]
                logger.info(f"Using cached summary for: {article.title[:50]}...")
            else:
                logger.info(f"Summarizing: {article.title[:50]}...")
                article.summary = summarize_article(article, client)
                
                # Cache the result
                if article.content_hash and not args.no_cache:
                    cache[article.content_hash] = article.summary
                
                # Rate limiting
                time.sleep(1.5)
        
        # Save cache
        if not args.no_cache:
            save_cache(cache)
        
        # Generate HTML
        write_html(articles, args.output)
        logger.info("Process completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
