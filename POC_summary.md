# POC Overview

This proof of concept shows a compact social media insights pipeline that can run locally in a container.

The POC ingests data from files and from the Twitter API, cleans and standardizes the data, applies basic sentiment analysis, and generates trending topics.

## What this POC is trying to do

- Ingest data from multiple sources, including files and Twitter.
- Normalize and clean the raw data so it is easier to analyse.
- Store both raw and cleaned data for traceability.
- Extract trending topics from cleaned posts.
- Add simple sentiment analysis to the cleaned data.
- Support an automated mode that watches for new files and polls Twitter regularly.

## What it caters for

- Local development and evaluation on a standard machine.
- File formats such as JSON, CSV, and Excel.
- Data quality processing including deduplication, null handling, trimming, and date formatting.
- A containerized workflow that can run continuously.
- A simple persistence layer using SQLite.

## Libraries and technology used

- Python 3.12
- SQLite for local data storage
- requests for calling the Twitter API
- openpyxl for Excel file ingestion
- textblob for basic sentiment analysis
- watchdog for folder watching in daemon mode
- Docker for containerization and local deployment

## Architecture

The diagram below shows the high-level flow of the POC.

```
File Source (JSON/CSV/XLSX)   Twitter API
          |                     |
          +----- Ingestion -----+
                    |
                    v
                raw_posts
                  (SQLite)
                    |
                    v
       Cleaning and Enrichment
         (dedupe, normalize,
          trim, date format,
           sentiment)
                    |
                    v
             cleaned_posts
                (SQLite)
                    |
                    v
        Trending Topic Extraction
                    |
                    v
            trending_topics
                (SQLite)

Folder Watcher (daemon mode) -> Ingestion
Twitter Poller (every 60 sec) -> Ingestion
```

## How to use

- Build the Docker image: `docker build -t social-insights-poc .`
- Run a one-shot file ingestion: `docker run --rm -v "${PWD}:/app" -w /app social-insights-poc --mode file --file sample_data/posts.json`
- Run daemon mode: `docker run -d --name insights -v "${PWD}/data:/app/data" -w /app social-insights-poc --mode daemon --poll-interval 60`

## Notes

The POC stores three tables in SQLite:

- `raw_posts`: original ingested records
- `cleaned_posts`: normalized and enriched records
- `trending_topics`: extracted trending topic counts
