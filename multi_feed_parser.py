import feedparser
import requests
import time
import os
import logging
import json
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import concurrent.futures

# Load environment variables
load_dotenv()

# === CONFIG ===
FEEDS_CONFIG = {
    "science_daily": {
        "url": "https://www.sciencedaily.com/rss/all.xml",
        "max_articles": 10,
        "category": "Science"
    },
    "nature_news": {
        "url": "https://www.nature.com/news.rss",
        "max_articles": 8,
        "category": "Research"
    },
    "phys_org": {
        "url": "https://phys.org/rss-feed/",
        "max_articles": 8,
        "category": "Physics"
    },
    "mit_news": {
        "url": "https://news.mit.edu/rss/feed",
        "max_articles": 6,
        "category": "Technology"
    },
    "pcgamer": {
        "url": "https://www.pcgamer.com/rss/",
        "max_articles": 8,
        "category": "Gaming"
    },
    "techcrunch_ai": {
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "max_articles": 10,
        "category": "AI & Tech"
    },
    "the_verge": {
        "url": "https://www.theverge.com/rss/index.xml",
        "max_articles": 8,
        "category": "Technology"
    },
    "ai_news": {
        "url": "https://artificialintelligence-news.com/feed/",
        "max_articles": 6,
        "category": "AI & Tech"
    },
    "variety_movies": {
        "url": "https://variety.com/c/film/feed/",
        "max_articles": 3,
        "category": "Entertainment"
    },
    "hollywood_reporter": {
        "url": "https://www.hollywoodreporter.com/c/movies/feed/",
        "max_articles": 3,
        "category": "Entertainment"
    },    "entertainment_weekly": {
        "url": "https://ew.com/tag/movies/feed/",
        "max_articles": 3,
        "category": "Entertainment"
    },
    "hacker_news": {
        "url": "https://hnrss.org/frontpage",
        "max_articles": 10,
        "category": "Tech News"
    }
}

HTML_FILE = "news_digest.html"
CACHE_FILE = "article_cache.json"
LOG_FILE = "feed_parser.log"
CACHE_EXPIRY_DAYS = 7  # Keep summaries for a week

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
    source: str
    category: str
    published: Optional[str] = None
    summary: Optional[str] = None
    content_hash: Optional[str] = None
    fetch_date: Optional[str] = None

class SmartCache:
    """Smart caching system that avoids re-summarizing articles."""
    
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache = self.load_cache()
    
    def load_cache(self) -> Dict[str, Dict]:
        """Load cache with expiry checking."""
        if not Path(self.cache_file).exists():
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                raw_cache = json.load(f)
            
            # Clean expired entries
            cutoff_date = datetime.now() - timedelta(days=CACHE_EXPIRY_DAYS)
            cleaned_cache = {}
            
            for hash_key, entry in raw_cache.items():
                if 'fetch_date' in entry:
                    fetch_date = datetime.fromisoformat(entry['fetch_date'])
                    if fetch_date > cutoff_date:
                        cleaned_cache[hash_key] = entry
            
            logger.info(f"Loaded {len(cleaned_cache)} cached summaries (cleaned {len(raw_cache) - len(cleaned_cache)} expired)")
            return cleaned_cache
            
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
            return {}
    
    def get_summary(self, content_hash: str) -> Optional[str]:
        """Get cached summary if exists."""
        entry = self.cache.get(content_hash)
        return entry['summary'] if entry else None
    
    def set_summary(self, content_hash: str, summary: str, article_title: str):
        """Cache a summary."""
        self.cache[content_hash] = {
            'summary': summary,
            'fetch_date': datetime.now().isoformat(),
            'title': article_title[:100]  # Store partial title for debugging
        }
    
    def save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save cache: {e}")

def fetch_feed_articles(feed_name: str, feed_config: Dict) -> List[Article]:
    """Fetch articles from a single RSS feed."""
    try:
        logger.info(f"Fetching {feed_name} from {feed_config['url']}")
        feed = feedparser.parse(feed_config['url'])
        
        if not feed.entries:
            logger.warning(f"No entries found in {feed_name}")
            return []
        
        articles = []
        entries = feed.entries[:feed_config['max_articles']]
        
        for entry in entries:
            try:
                link = getattr(entry, 'link', '')
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '')
                published = getattr(entry, 'published', None)
                
                # Skip if no essential data
                if not title or not link:
                    continue
                
                # Get full article content
                article_text = extract_article_content(link, summary)
                content_hash = hashlib.md5(f"{title}{article_text}".encode()).hexdigest()
                
                article = Article(
                    title=title,
                    link=link,
                    content=article_text,
                    source=feed_name,
                    category=feed_config['category'],
                    published=published,
                    content_hash=content_hash,
                    fetch_date=datetime.now().isoformat()
                )
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Error processing entry from {feed_name}: {e}")
                continue
        
        logger.info(f"Fetched {len(articles)} articles from {feed_name}")
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching {feed_name}: {e}")
        return []

def extract_article_content(url: str, fallback_summary: str) -> str:
    """Extract article content with improved selectors."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=15, headers=headers)
        
        if not resp.ok:
            return fallback_summary
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Extended selectors for different sites
        content_selectors = [
            '#text', '.story-body', '[id*="text"]', '.article-content',
            '.post-content', '.entry-content', '.article-body',
            '.content', 'article', '.main-content', '[role="main"]'
        ]
        
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                # Remove unwanted elements
                for elem in content_div.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    elem.decompose()
                
                text = content_div.get_text(separator=' ', strip=True)
                if len(text) > 200:  # Require substantial content
                    return text
        
        return fallback_summary
        
    except Exception as e:
        logger.warning(f"Could not extract content from {url}: {e}")
        return fallback_summary

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def summarize_articles_batch(articles: List[Article], client: OpenAI) -> List[Article]:
    """Summarize multiple articles in a single API call to save tokens."""
    if not articles:
        return articles
    
    # Prepare batch content
    batch_content = []
    for i, article in enumerate(articles):
        batch_content.append(f"ARTICLE {i+1}:")
        batch_content.append(f"Title: {article.title}")
        batch_content.append(f"Content: {article.content[:1000]}")  # Limit per article
        batch_content.append("---")
    
    batch_text = "\n".join(batch_content)
    
    prompt = (
        "Summarize each of the following science/tech articles. For each article, provide a single factual sentence "
        "covering the main finding or breakthrough. Number your responses (1, 2, 3, etc.) to match the article numbers. "
        "Be concise and factual, avoiding hype or speculation.\n\n" + batch_text
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You summarize multiple science/tech articles efficiently."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=len(articles) * 50  # Scale tokens with article count
        )
        
        summary_text = response.choices[0].message.content
        if not summary_text:
            raise ValueError("Empty response from OpenAI")
        
        # Parse numbered responses
        summaries = parse_batch_summaries(summary_text, len(articles))
        
        # Assign summaries back to articles
        for i, article in enumerate(articles):
            if i < len(summaries):
                article.summary = summaries[i]
            else:
                article.summary = "[Summary not available]"
        
        logger.info(f"Successfully summarized {len(articles)} articles in batch")
        return articles
        
    except Exception as e:
        logger.error(f"Batch summary failed: {e}")
        # Fallback to individual summaries for failed batch
        return summarize_articles_individually(articles, client)

def parse_batch_summaries(text: str, expected_count: int) -> List[str]:
    """Parse numbered summaries from batch response."""
    summaries = []
    lines = text.strip().split('\n')
    
    current_summary = ""
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith(('1.', '2.', '3.'))):
            if current_summary:
                summaries.append(current_summary.strip())
            # Remove number prefix
            current_summary = line.split('.', 1)[-1].strip() if '.' in line else line
        elif current_summary and line:
            current_summary += " " + line
    
    if current_summary:
        summaries.append(current_summary.strip())
    
    return summaries[:expected_count]

def summarize_articles_individually(articles: List[Article], client: OpenAI) -> List[Article]:
    """Fallback: summarize articles one by one."""
    for article in articles:
        try:
            prompt = (
                f"Summarize this science/tech article in one factual sentence: "
                f"Title: {article.title}\nContent: {article.content[:2000]}"
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You summarize science articles concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=80
            )
            
            summary = response.choices[0].message.content
            article.summary = summary.strip() if summary else "[Summary not available]"
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Individual summary failed for '{article.title[:50]}': {e}")
            article.summary = "[Summary failed]"
    
    return articles

def generate_enhanced_html(articles: List[Article], html_file: str):
    """Generate improved HTML with categorization and filtering."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Group articles by category
    categories = {}
    for article in articles:
        if article.category not in categories:
            categories[article.category] = []
        categories[article.category].append(article)
    
    html_head = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Science & Tech News Digest</title>
    <style>
        /* ...existing CSS... */
        .category-section {{ margin-bottom: 3em; }}
        .category-title {{ 
            font-size: 1.5em; color: #1e40af; margin-bottom: 1em; 
            border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5em;
        }}
        .source-tag {{ 
            background: #3b82f6; color: white; padding: 0.2em 0.5em; 
            border-radius: 4px; font-size: 0.75em; margin-left: 0.5em;
        }}
        .stats {{ text-align: center; margin-bottom: 2em; color: #6b7280; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🔬 Science & Tech News Digest</h1>
        <div class="timestamp">Generated on {timestamp}</div>
        <div class="stats">
            {len(articles)} articles from {len(set(a.source for a in articles))} sources
        </div>
    </div>
'''
    
    # Generate category sections
    category_sections = []
    for category, cat_articles in categories.items():
        articles_html = []
        for article in cat_articles:
            published_info = ""
            if article.published:
                try:
                    from dateutil import parser
                    pub_date = parser.parse(article.published)
                    published_info = f'<div class="published">Published: {pub_date.strftime("%B %d, %Y")}</div>'
                except:
                    published_info = f'<div class="published">Published: {article.published}</div>'
            
            article_html = f'''
<div class="article">
    <div class="title">
        <a href="{article.link}" target="_blank">{article.title}</a>
        <span class="source-tag">{article.source}</span>
    </div>
    <div class="summary">{article.summary or "Summary not available"}</div>
    {published_info}
</div>'''
            articles_html.append(article_html)
        
        section_html = f'''
<div class="category-section">
    <h2 class="category-title">{category} ({len(cat_articles)} articles)</h2>
    {"".join(articles_html)}
</div>'''
        category_sections.append(section_html)
    
    html_end = '''
    <div class="footer">
        Powered by AI • Updated Daily
    </div>
</div>
</body>
</html>'''
    
    html_full = html_head + "".join(category_sections) + html_end
    
    try:
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_full)
        logger.info(f"Enhanced HTML saved to: {html_file}")
    except Exception as e:
        logger.error(f"Could not write HTML file: {e}")

def main():
    """Main function with multi-feed support and smart caching."""
    parser = argparse.ArgumentParser(description='Multi-Feed RSS News Summarizer')
    parser.add_argument('--feeds', nargs='+', help='Specific feeds to process')
    parser.add_argument('--output', default=HTML_FILE, help='Output HTML file')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--batch-size', type=int, default=5, help='Articles per batch for summarization')
    
    args = parser.parse_args()
    
    try:
        # Initialize
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        cache = SmartCache(CACHE_FILE) if not args.no_cache else None
        
        # Determine which feeds to process
        feeds_to_process = FEEDS_CONFIG
        if args.feeds:
            feeds_to_process = {k: v for k, v in FEEDS_CONFIG.items() if k in args.feeds}
        
        logger.info(f"Processing {len(feeds_to_process)} feeds...")
        
        # Fetch all articles (can be parallelized)
        all_articles = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_feed = {
                executor.submit(fetch_feed_articles, feed_name, config): feed_name 
                for feed_name, config in feeds_to_process.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_feed):
                articles = future.result()
                all_articles.extend(articles)
        
        if not all_articles:
            logger.error("No articles found from any feed. Exiting.")
            return
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        
        # Process with smart caching
        articles_to_summarize = []
        for article in all_articles:
            if cache and article.content_hash:
                cached_summary = cache.get_summary(article.content_hash)
                if cached_summary:
                    article.summary = cached_summary
                    logger.debug(f"Using cached summary for: {article.title[:50]}...")
                else:
                    articles_to_summarize.append(article)
            else:
                articles_to_summarize.append(article)
        
        # Batch summarize new articles
        if articles_to_summarize:
            logger.info(f"Summarizing {len(articles_to_summarize)} new articles...")
            
            # Process in batches
            batch_size = args.batch_size
            for i in range(0, len(articles_to_summarize), batch_size):
                batch = articles_to_summarize[i:i + batch_size]
                summarized_batch = summarize_articles_batch(batch, client)
                
                # Cache the results
                if cache:
                    for article in summarized_batch:
                        if article.content_hash and article.summary:
                            cache.set_summary(article.content_hash, article.summary, article.title)
                
                time.sleep(2)  # Rate limiting between batches
        
        # Save cache
        if cache:
            cache.save_cache()
        
        # Generate enhanced HTML
        generate_enhanced_html(all_articles, args.output)
        logger.info("Process completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
