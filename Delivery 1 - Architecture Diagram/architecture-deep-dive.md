
# Proposed Architecture: Cost-Conscious Social Media Insights Data Platform

## 1) Design intent

The platform should enable us to ingest, process, store, and analyze social media data related to insurance product perception, while prioritizing:

1. Low total cost of ownership
2. Operational simplicity
3. Elastic scalability
4. Near-real-time trend detection
5. Reliable analytics access for analysts and data scientists
6. Strong data security, PII handling, and governance

This design deliberately avoids expensive always-on compute where batch or micro-batch approaches are sufficient, and prefers cheap storage, serverless/managed services, and decoupled components over high-performance but high-cost architectures.



# 2) Architectural approach

## Recommended design

Instead of designing for ultra-low-latency sub-second streaming everywhere, the platform should use a tiered timing model:

 Near-real-time where it matters
   trending topic updates every few minutes
 Batch or micro-batch where possible
   enrichment, quality checks, model refreshes, historical recomputation
 Cheap long-term storage as the system of record
   object storage
 Managed services to reduce operational overhead
   lower platform maintenance burden often reduces cost more than raw infrastructure optimization

This means the platform should be designed as a stream-enabled but storage-centric analytics platform, not a fully high-performance streaming estate.


# 3) Detailed component design


## 3.1 Data ingestion

Use source-specific ingestion services to connect to each social platform or approved provider. 
Each service should normalize events into a common schema and write them into an ingestion buffer before landing them into storage.

### Supported ingestion methods

Depending on platform support and budget:

1. Polling APIs
    best when webhooks or streaming APIs are unavailable
    lower implementation complexity
    cost-effective
    suitable if a small delay is acceptable

2. Webhooks
    preferred when supported
    event-driven and cost-efficient
    lower unnecessary polling traffic

3. Third-party licensed feeds
    useful if broad social coverage is needed beyond public APIs
    usually easier operationally, but licensing cost must be justified

4. Streaming APIs
    use selectively where low-latency matters
    not every source needs continuous streaming if the use case tolerates minute-level freshness



## Recommended ingestion technology

### Preferred choice: managed Kafka-compatible streaming only if justified

If the volume and consumer variety are high enough, use a managed Kafka-compatible service as the event backbone.

However, because this design gives more weight to cost:

 do not assume a large, always-on streaming cluster is necessary from day one
 if update frequency of a few minutes is acceptable, a managed queue + object storage landing pattern can be cheaper than a full streaming estate

### Practical cost-conscious recommendation

Use:

 a lightweight ingestion layer
 event buffering
 direct landing into object storage
 processing triggered in short intervals

This reduces:

 infrastructure complexity
 always-on compute cost
 operational overhead

### Ingestion responsibilities

Each source connector should handle:

 authentication and token refresh
 source-specific rate limiting
 retries and backoff
 schema normalization
 event timestamp normalization
 source metadata tagging
 optional source filtering for only relevant content

### Canonical event structure

Each record should include:

 source platform
 source post ID
 event time
 ingestion time
 text content
 language
 region / geo if available
 author identifier (hashed or tokenized if needed)
 source metadata
 raw payload reference
 ingestion batch ID / stream partition metadata



## 3.2 Data processing

### Objective

Convert noisy social media data into trusted, enriched, queryable datasets and near-real-time trending outputs.

## Cost-conscious processing principle

Instead of running expensive, continuously scaled stream processing for every transformation, split processing into:

### A. Near-real-time processing

Used only for:

 trending topics
 top mention counts
 rapid sentiment indicators
 anomaly detection for sudden spikes

### B. Batch / micro-batch processing

Used for:

 heavy text cleaning
 expensive enrichment
 taxonomy refinement
 historical recomputation
 feature generation for ML
 quality checks and reconciliation

This keeps the “hot path” lean and shifts more expensive workloads to cheaper scheduled processing.



## Processing model recommendation

### Recommended pattern: micro-batch first

A micro-batch architecture running every 1–5 minutes is often sufficient for social media insights, especially for trending use cases. This gives near-real-time behavior without the cost of ultra-low-latency full streaming.

This approach is attractive because it:

 reduces continuous compute cost
 simplifies operations
 is easier to recover and replay
 often performs well enough for business insight needs

### When full streaming is warranted

Use continuous stream processing only for:

 immediate trending updates
 event-driven alerts
 use cases requiring minute-level freshness or better

Even then, keep the continuous path narrow and focused.



## Core processing steps

Every post should move through a standard transformation pipeline:

1. Schema validation
    reject malformed records
    route invalid events to a failure store

2. Deduplication
    use `platform + source_post_id` as the primary dedupe key

3. Missing value handling
    default optional fields where reasonable
    reject records missing critical identifiers
    tag records with quality indicators

4. Text normalization
    lowercase
    clean spacing / Unicode
    remove empty noise
    preserve hashtags, mentions, and emojis where analytically useful

5. Language detection
    classify for routing and analysis

6. PII handling
    detect and mask sensitive fields early
    tokenize user identifiers where retention is required

7. NLP enrichment
    keyword extraction
    insurance product tagging
    topic/category assignment
    named entity extraction
    sentiment scoring

8. Aggregation
    per topic
    per platform
    per region
    per product
    by rolling time windows

9. Trend scoring
    identify not just frequent terms, but emerging topics



## Trending topic logic

Trending should not be raw count only.

A better trend score should combine:

 current mention count
 growth rate vs prior window
 growth vs recent baseline
 unique author count
 cross-platform spread
 sentiment shift or volatility

This ensures the platform surfaces emerging conversation, not just permanently common terms.



# 3.3 Data storage

### Objective

Store data cheaply, durably, and in a layout aligned to consumption patterns.

## Recommended storage architecture: object storage-centered

The most cost-effective design is to make object storage the primary data store and organize it into multiple zones.

This should be the system of record.

## Storage zones

### Bronze: Raw data

Purpose:

 immutable source landing
 auditability
 replay and reprocessing
 low-cost retention

Format:

 compressed JSON or Parquet

Location:

 object storage

### Silver: Cleaned and standardized data

Purpose:

 deduplicated
 normalized
 security-filtered
 enriched base-level records

Format:

 columnar storage such as Parquet
 open table format if available

### Gold: Curated analytics outputs

Purpose:

 trend aggregates
 sentiment summaries
 product perception tables
 ML-ready feature extracts

Format:

 optimized for queries
 partitioned based on analyst filters



## Recommended storage principle

### Use object storage as the default data platform foundation

This should be preferred because it is:

 cheap at scale
 durable
 easy to retain historically
 well-suited to replay
 flexible for multiple compute engines
 better for evolving data products than storing everything in expensive serving databases



## Data layout and partitioning strategy

Partitioning should be driven by access patterns, not ingestion convenience alone.

### Bronze partitioning

Partition by:

 `ingest_date`
 `platform`

Example:


/bronze/social/platform=twitter/ingest_date=2026-06-06/hour=15/
/bronze/social/platform=reddit/ingest_date=2026-06-06/hour=15/


Why:

 low-cost operational management
 easy replay and retention
 good source isolation

### Silver partitioning

Partition by:

 `event_date`
 `platform`
 optional `language`

Why:

 aligns to common analytical filters
 avoids excessive small partitions
 supports efficient downstream scans

### Gold partitioning

Partition differently depending on use case.

For trend tables:

 `window_date`
 `topic_category`
 optional `region`

For sentiment/product reporting:

 `event_date`
 `product_family`
 `platform`



## Partitioning principles

1. Partition by time first for most analytical workloads
2. Use medium-cardinality fields such as platform or product family as secondary partition keys
3. Avoid partitioning by:
    post ID
    user ID
    hashtags
    free-text topic labels
4. Use file compaction and clustering to improve read efficiency over time
5. Optimize for common analyst filters rather than ingestion uniqueness



## Should Cassandra / InfluxDB be used?

For this use case, I would not recommend Cassandra or InfluxDB as the primary storage layer.

### Why not Cassandra?

Although it handles write-heavy workloads well:

 it increases operational complexity
 it is less flexible for broad analytical workloads
 it often leads to query-specific data modeling
 total cost and maintenance effort may not be justified for this problem

### Why not InfluxDB?

This data is time-stamped, but it is not a classical time-series-only workload. Social media insight requires:

 text analysis
 topic search
 flexible aggregation
 exploratory analytics
 ML feature extraction

A lakehouse/object-storage-first design is more versatile and usually more cost-effective.

### Better fit

Use:

 object storage for durable history
 warehouse/lake SQL for analytics
 search index only when text search is needed
 cache only for high-traffic top-N views



# 3.4 Data retrieval and analytics consumption

### Objective

Enable analysts and data scientists to access trusted data efficiently without forcing all data into expensive serving systems.

## Recommended consumption model

### Analysts

Analysts should primarily access:

 curated Gold datasets
 queryable Silver datasets
 semantic reporting layers where needed

Supported workloads:

 topic trends over time
 product perception by region and platform
 sentiment analysis
 marketing/campaign effectiveness
 issue and reputation monitoring

### Data scientists

Data scientists should access:

 raw historical text where permitted
 cleaned and enriched datasets
 historical aggregates
 feature extraction datasets
 labeled training sets

Supported workloads:

 topic modelling
 sentiment model training
 classification models
 anomaly detection
 feature engineering



## Query layer recommendation

Because cost is weighted above performance, the query platform should favor:

 serverless or elastic SQL
 separation of compute and storage
 ability to query object storage directly
 pay-for-use instead of always-on clusters

### Preferred approach

Use a modern analytical query engine or warehouse that can:

 query curated lake data efficiently
 scale compute up and down
 support analysts with SQL
 avoid permanent high-cost infrastructure



## Search and fast exploration

A search engine such as OpenSearch / Elasticsearch should be introduced only if there is a real need for:

 full-text search
 post-level drill-through
 analyst exploration by keyword
 filtered exploration across large text datasets

Because search clusters can become expensive, this layer should remain narrowly scoped.

### Cost-conscious search strategy

Index only:

 recent period data
 selected enriched fields
 top-priority analytical subsets

Do not index the full historical corpus unless there is a clear business need.



## Caching

A caching layer is optional.

Use it only for:

 top trending topics
 dashboard summary endpoints
 frequent repeat queries

This should be a small optimization, not a central architectural dependency.



# 3.5 Orchestration and scheduling

### Objective

Coordinate workloads in a transparent, maintainable, and cost-efficient way.

## Recommended orchestration strategy

Use a central orchestrator for all non-continuous workloads.

### Scheduled workloads include:

 ingestion polling jobs
 micro-batch processing
 enrichment tasks
 quality checks
 compaction and optimization
 baseline trend recomputation
 historical backfills
 model refresh jobs
 retention and archival processes

### Guiding principle

Keep orchestration explicit and centralized so that:

 dependencies are visible
 retries are controlled
 failures are observable
 operations remain maintainable



## Orchestration model

Use orchestration to coordinate:

 hourly and daily jobs
 dependency-aware transformations
 backfills and reprocessing
 SLA tracking for data freshness

Continuous event listeners or lightweight processing services can still exist, but the majority of platform mechanics should be orchestrated in scheduled workflows for cost efficiency.



# 5.6 Scalability and reliability

### Objective

Handle growth in data volume without major redesign, while maintaining resilience.

## Scalability principles

### 1. Scale storage independently from compute

Object storage should absorb historical growth at low cost.

### 2. Scale compute elastically

Processing and query engines should scale up only when needed.

### 3. Keep ingestion stateless

Connector services should be horizontally scalable and easy to replace.

### 4. Decouple ingestion and processing

Event buffering prevents downstream slowdowns from causing source ingestion failure.

### 5. Reprocess from raw

Raw landing must support replay when:

 logic changes
 taxonomy changes
 models improve
 failures occur



## Reliability patterns

### Durable raw retention

All source records should land durably before complex transformation.

### Idempotent writes

Transformations should be safe to rerun.

### Failure isolation

Bad records should be routed to a quarantine/failure zone instead of blocking the pipeline.

### Recovery support

The platform should support restart and replay from persisted raw storage.

### Monitoring

The platform should expose:

 ingestion success/failure counts
 freshness lag
 processing duration
 failed record counts
 storage growth
 query performance
 cost metrics
 trend publication latency



# 3.7 Data security and compliance

### Objective

Ensure the platform protects customer and user-related data appropriately.

## Security design principles

### 1. Data classification at ingestion

Each dataset or event should be tagged with:

 sensitivity level
 PII presence
 retention policy
 source system
 approved usage classification

### 2. Minimize retained PII

Only ingest and retain fields necessary for the use case.

Where possible:

 hash user identifiers
 remove direct personal identifiers
 redact phone numbers and emails
 avoid persisting unnecessary profile data

### 3. Zone-based access separation

Restrict access more tightly for:

 raw datasets
 sensitive enriched datasets
 user-level data

Broader access may be granted for:

 aggregated trends
 product-level sentiment views
 de-identified outputs

### 4. Encryption

Use encryption:

 in transit
 at rest

### 5. Fine-grained authorization

Role-based controls should govern access to:

 raw text
 enriched events
 aggregates
 notebooks
 model training datasets

### 6. Auditability

All access to sensitive data should be logged and reviewable.

### 7. Retention and deletion controls

The platform should support:

 controlled retention windows
 data deletion obligations where applicable
 versioned processing
 lineage traceability

### 8. Approved data usage only

Only ingest and process social media data in line with:

 legal agreements
 platform terms of use
 internal compliance policy


# 4) Proposed data model

## Core entities

The platform should maintain at least these logical datasets:

 `raw_social_event`
 `clean_social_post`
 `post_enrichment`
 `topic_reference`
 `topic_trend_window`
 `product_sentiment_window`
 `platform_topic_summary`
 `entity_mentions`
 `model_feature_snapshot`



## Example curated outputs

### `gold.topic_trend_window`

Fields:

 window\_start
 window\_end
 topic
 topic\_category
 platform
 region
 language
 mention\_count
 unique\_author\_count
 sentiment\_score
 trend\_score
 rank

### `gold.product_sentiment_window`

Fields:

 event\_date
 product\_family
 platform
 region
 positive\_count
 neutral\_count
 negative\_count
 sentiment\_average

### `gold.topic_velocity`

Fields:

 topic
 current\_window\_count
 prior\_window\_count
 baseline\_count
 velocity\_ratio
 anomaly\_score



# 5) Recommended trend computation model

Trending topics should be produced using a layered approach.

## Step 1: Extract candidate terms

From each post:

 hashtags
 named entities
 normalized phrases
 insurance product keywords
 category labels

## Step 2: Map to controlled taxonomy

Where possible, map noisy raw terms into:

 product categories
 brand categories
 risk/claim/premium/service themes
 market topics

## Step 3: Aggregate by rolling windows

Recommended windows:

 5 minutes
 15 minutes
 1 hour

## Step 4: Score trend strength

Trend score should combine:

 current frequency
 acceleration
 deviation from recent baseline
 cross-platform occurrence
 unique account spread
 sentiment shift

## Step 5: Publish ranked trend outputs

Only publish the top-N and top materialized aggregates to the serving layer to control cost.



# 6) Architecture principles to explicitly call out

These are the principles I included:

1. Object storage is the system of record
2. Compute is elastic and temporary where possible
3. Micro-batch is preferred over continuous streaming unless latency justifies cost
4. Raw, cleaned, and curated data are separated clearly
5. Open and decoupled architecture is preferred over tightly coupled serving-specific stores
6. Search and cache are used selectively, not by default
7. Governance, masking, and access control are embedded from ingestion onward
8. The platform supports both analyst-friendly SQL and data science access
9. Replayability and auditability are first-class architectural requirements
10. Cost efficiency is prioritized over maximum performance when business latency requirements allow


