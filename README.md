# Social Media Insights POC

This containerized POC ingests social media posts from a local file or the Twitter API, processes them for trending topics with sentiment analysis, and stores results in SQLite.

# What it includes

- 'app.py': CLI entry point for file, Twitter, or daemon (scheduler) mode
- 'scheduler_app.py': daemon mode for continuous file watching and Twitter polling
- 'ingest.py': file ingestion (JSON, CSV, XLSX) and Twitter API v2
- 'cleaner.py': data cleaning with camelCase conversion, date formatting (dd-mm-yyyy), null handling, and sentiment analysis
- 'processing.py': trending topic extraction and sentiment summarization
- 'storage.py': SQLite storage with 3 tables: raw_posts, cleaned_posts, trending_topics
- 'scheduler.py': file watcher and job scheduler
- 'twitter_client.py': Twitter API v2 connector
- 'sample_data/posts.json': sample post payload
- 'sample_data/Consolidated United Nations Security Council Sanctions List.xlsx': sample Excel data
- 'Dockerfile': container build

# Database Schema

# raw_posts
- 'id' (TEXT PRIMARY KEY): unique identifier
- 'text' (TEXT): post content
- 'author' (TEXT): post author
- 'created_at' (TEXT): original creation timestamp
- 'source' (TEXT): data source (file, twitter, etc.)

# cleaned_posts
- 'id' (TEXT PRIMARY KEY): unique identifier
- 'text' (TEXT): cleaned content
- 'author' (TEXT): author name
- 'createdAt' (TEXT): date in dd-mm-yyyy format
- 'source' (TEXT): data source
- 'sentiment' (TEXT): positive/negative/neutral
- 'sentimentScore' (REAL): sentiment polarity (-1 to 1)
- 'processedAt' (TEXT): processing timestamp

# trending_topics
- 'topic' (TEXT): trending term
- 'count' (INTEGER): frequency count
- 'source' (TEXT): source of trend
- 'updated_at' (TEXT): last update timestamp

# Local usage
Install dependencies:

powershell
python -m pip install -r requirements.txt


# Mode 1: One-shot file ingestion
powershell
python app.py --mode file --file sample_data/posts.json


Supports JSON, CSV, and XLSX files.

# Mode 2: One-shot Twitter ingestion
powershell
$env:TWITTER_BEARER_TOKEN = "<your_token>"
python app.py --mode twitter --query "insurance" --limit 50


# Mode 3: Daemon mode (continuous processing)
Start the scheduler to watch a folder and poll Twitter every 60 seconds:

powershell
$env:TWITTER_BEARER_TOKEN = "<your_token>"
python app.py --mode daemon --watch-folder data/incoming --poll-interval 60


Drop files into 'data/incoming/' and they will be processed automatically. Tweets will be polled every 60 seconds.

# Docker usage
Build the image:

powershell
docker build -t social-insights-poc .


# One-shot file ingestion in Docker
powershell
docker run --rm -v "${PWD}:/app" -w /app social-insights-poc --mode file --file "sample_data/Consolidated United Nations Security Council Sanctions List.xlsx"


# one-shot Twitter ingestion in Docker
powershell
docker run --rm -e TWITTER_BEARER_TOKEN="<your_token>" social-insights-poc --mode twitter --query "insurance" --limit 50


# Daemon mode in Docker (file watching + Twitter polling)
powershell
docker run -d --name insights-daemon '
  -v "${PWD}/data/incoming:/app/data/incoming" '
  -v "${PWD}/data/social_insights.db:/app/data/social_insights.db" '
  -e TWITTER_BEARER_TOKEN="<your_token>" '
  -e TWITTER_QUERY="insurance" '
  social-insights-poc --mode daemon --poll-interval 60


Then drop files into the host 'data/incoming' folder:

powershell
cp "path/to/file.xlsx" data/incoming/


Watch the logs:
powershell
docker logs -f insights-daemon


Stop the daemon:
powershell
docker stop insights-daemon
docker rm insights-daemon


# Data processing pipeline
1. **Ingestion**: Posts ingested from file or Twitter API into 'raw_posts'
2. **Cleaning**: Posts cleaned (null handling, trim, de-duplication) and moved to 'cleaned_posts'
3. **Enrichment**: Sentiment analysis applied during cleaning
4. **Trending**: Topics extracted from cleaned posts and stored in 'trending_topics'
5. **Scheduling**: Daemon mode watches for new files and polls Twitter periodically

# Data cleaning features

- **De-duplication**: Posts with duplicate IDs are skipped and removed if already ingested
- **Null handling**: Missing values replaced
- **Trimming**: Leading/trailing whitespace removed
- **camelCase conversion**: Field names converted for consistency (e.g., 'created_at' → 'createdAt')
- **Date normalization**: Dates converted to dd-mm-yyyy format
- **Sentiment analysis**: TextBlob polarity analysis (positive/negative/neutral)

# Querying the database
Query the database directly on the host:

powershell
sqlite3 data/social_insights.db "SELECT topic, count FROM trending_topics ORDER BY count DESC LIMIT 20;"


Or from Python:

python
import sqlite3
conn = sqlite3.connect('data/social_insights.db')
cur = conn.cursor()
for row in cur.execute("SELECT sentiment, COUNT(*) as count FROM cleaned_posts GROUP BY sentiment"):
    print(row)
conn.close()


# Example workflow
1. Build the Docker image:
   powershell
   docker build -t social-insights-poc .

2. Start the daemon:
   powershell
   docker run -d --name insights -v "${PWD}/data:/app/data" social-insights-poc --mode daemon
   
3. Drop a file into 'data/incoming/':
   powershell
   cp sample_data/posts.json data/incoming/
   
4. Monitor processing:
   powershell
   docker logs -f insights

5. Query results:
   powershell
   sqlite3 data/social_insights.db "SELECT * FROM trending_topics;"
   
# Useful Commnds
remove all containers: docker rm -f $(docker ps -aq)
build container: docker build -t social-insights-poc .
run daemon: docker run -d --name insights -v "${PWD}/data/incoming:/app/data/incoming" -w /app social-insights-poc --mode daemon --poll-interval 60

check logs: docker logs -f insights