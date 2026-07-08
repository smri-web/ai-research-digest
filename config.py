MODEL_ID = "claude-haiku-4-5-20251001"
MAX_ITEMS = 10
WINDOW_DAYS = 7
PER_SOURCE_CAP = 3
PROCESSED_IDS_PATH = "processed_ids.json"

# Each track: display name, arXiv query, Semantic Scholar keywords, relevance keywords.
TRACKS = {
    "models": {
        "name": "AI models & research",
        "arxiv": '(cat:cs.AI OR cat:cs.CL OR cat:cs.LG) AND (abs:"large language model" OR abs:"foundation model" OR abs:"reasoning model" OR abs:"multimodal model")',
        "s2": ["large language models", "frontier AI models"],
        "keywords": ["language model", "foundation model", "reasoning", "multimodal", "llm"],
    },
    "systems": {
        "name": "AI system design & engineering",
        "arxiv": '(cat:cs.SE OR cat:cs.AI OR cat:cs.LG) AND (abs:"agent" OR abs:"retrieval-augmented" OR abs:"evaluation" OR abs:"prompting" OR abs:"inference")',
        "s2": ["LLM agents", "retrieval augmented generation", "LLM evaluation"],
        "keywords": ["agent", "rag", "retrieval", "eval", "prompt", "inference", "pipeline"],
    },
    "psychology": {
        "name": "AI & psychology / mental health",
        "arxiv": '(cat:cs.HC OR cat:cs.CY OR cat:cs.AI) AND (abs:psychology OR abs:"mental health" OR abs:cognitive OR abs:emotional OR abs:therapy OR abs:wellbeing)',
        "s2": ["AI psychology", "human-AI interaction mental health", "LLM therapy"],
        "keywords": ["psychology", "mental health", "cognitive", "emotional", "therapy", "wellbeing"],
    },
    "behavior": {
        "name": "AI & human behavior",
        "arxiv": '(cat:cs.HC OR cat:cs.CY) AND (abs:"human-AI interaction" OR abs:"behavior change" OR abs:"AI companion" OR abs:anthropomorphism OR abs:"cognitive offloading" OR abs:"AI reliance" OR abs:"trust in AI")',
        "s2": ["AI human behavior", "cognitive offloading AI", "AI companionship"],
        "keywords": ["human-ai", "behavior", "companion", "anthropomorphism", "offloading", "reliance", "trust"],
    },
}

# RSS/Atom feeds, tagged with the track they feed. Verified at build time (scripts/verify_feeds.py);
# any that 404 or aren't valid feeds are removed.
RSS_FEEDS = [
    {"source": "Simon Willison", "track": "systems", "url": "https://simonwillison.net/atom/everything/"},
    {"source": "Ahead of AI", "track": "systems", "url": "https://magazine.sebastianraschka.com/feed"},
    {"source": "Hugging Face", "track": "models", "url": "https://huggingface.co/blog/feed.xml"},
    {"source": "Import AI", "track": "models", "url": "https://importai.substack.com/feed"},
    {"source": "The Gradient", "track": "psychology", "url": "https://thegradient.pub/rss/"},
    {"source": "Quanta Magazine", "track": "psychology", "url": "https://api.quantamagazine.org/feed/"},
    {"source": "MIT Technology Review", "track": "behavior", "url": "https://www.technologyreview.com/feed/"},
    {"source": "Ars Technica", "track": "behavior", "url": "https://feeds.arstechnica.com/arstechnica/index"},
]
# General-relevance keywords: an item must match at least one of these OR its track keywords.
AI_KEYWORDS = ["ai", "artificial intelligence", "machine learning", "neural", "model",
               "llm", "gpt", "transformer", "deep learning", "agent"]
