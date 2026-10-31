# Technology News Search Engine

A search engine for technology news and major software developments. This project collects technology-related news articles from selected websites, processes the content, builds an inverted index, and provides keyword-based search using TF-IDF with Cosine Similarity and BM25.

## 1. Project Overview

### Research Topic

**English Technology News Search Engine**

The system focuses on English technology news, artificial intelligence, and major software developments.

### Main Features

- Web crawling with domain allowlist and robots.txt compliance.
- HTML content extraction and text preprocessing.
- Duplicate URL detection.
- Inverted index construction.
- TF-IDF with Cosine Similarity retrieval.
- BM25 ranking.
- Top 10 search results.
- Article title, URL, and text snippet display.
- Search algorithm selection through a Flask web interface.
- Search quality evaluation using Precision@5.

## 2. System Architecture

```text
Seed URLs
    |
    v
Web Crawler
    |
    |-- robots.txt checking
    |-- Domain allowlist
    |-- URL normalization
    |-- Request delay
    |
    v
HTML Parser
    |
    v
Raw Article Data (JSON)
    |
    v
Text Preprocessing
    |
    v
Index Construction
    |
    |-- TF
    |-- DF
    |-- IDF
    |-- TF-IDF
    |-- Inverted Index
    |-- Document Norms
    |
    v
Search Engine
    |
    |-- TF-IDF + Cosine Similarity
    |-- BM25
    |
    v
Top 10 Search Results
    |
    v
Flask Web Interface
```

## 3. Project Structure

```text
project/
│
├── database/
│   ├── pages_Ａ.json
│   └── pages_B.json
│
├── index/
│   ├── df.json
│   ├── idf.json
│   ├── tf.json
│   ├── tfidf.json
│   ├── postings.json
│   └── document_norms.json
│
├── robots_data/
│   └── robots.txt cache files
│
├── templates/
│   └── index.html
│
├── test/
│   └── test_app.py
│
├── preprocessor.py
├── robots_checker.py
├── robots_downloader.py
├── html_parser.py
├── link_collector.py
├── crawler.py
├── tf_df.py
├── indexer.py
├── search.py
├── bm25.py
├── app.py
│
├── requirements.txt
└── README.md
```

## 4. Development Environment

### Python Version

- Python 3.13

### Main Packages

| Package | Version |
|---|---|
| Python | 3.13 |
| Requests | 2.33.1 |
| BeautifulSoup4 | 4.14.3 |
| Flask | Check installed version |
| NumPy | Check installed version |

The actual package versions can be obtained using:

```powershell
python --version
pip show requests beautifulsoup4 flask numpy
pip freeze
```

### Install Dependencies

Install the required packages:

```powershell
pip install requests beautifulsoup4 flask numpy
```

To save the installed package versions:

```powershell
pip freeze > requirements.txt
```

To install dependencies from the saved file:

```powershell
pip install -r requirements.txt
```

## 5. Seed URLs

The crawler uses seven technology news websites as its seed sources.

| Website | Seed URL |
|---|---|
| The New Stack | https://thenewstack.io/ |
| TechCrunch | https://techcrunch.com/category/artificial-intelligence/ |
| IEEE Spectrum | https://spectrum.ieee.org/topic/artificial-intelligence |
| Ars Technica | https://arstechnica.com/ai/ |
| InfoQ | https://www.infoq.com/ai-ml-data-eng/news/ |
| Engadget | https://www.engadget.com/ai/ |
| VentureBeat | https://venturebeat.com/category/technology/ |

**Note:** The seed URLs should match the actual `TARGET_SITES` configuration in the crawler. Update this table if the program uses different entry URLs.

## 6. Domain Allowlist

The crawler restricts its requests to the selected websites.

The configured website domains include:

```python
TARGET_LINKS = [
    "thenewstack.io",
    "techcrunch.com",
    "spectrum.ieee.org",
    "arstechnica.com",
    "infoq.com",
    "engadget.com",
    "venturebeat.com/technology/"
]
```

The crawler should only follow URLs that match the configured allowlist.

External websites outside the allowlist are excluded from crawling.

## 7. Crawling Rules

The crawler follows these rules:

1. Only public HTTP and HTTPS HTML pages are collected.
2. URLs are checked against the domain allowlist.
3. The crawler checks robots.txt before accessing pages.
4. A descriptive User-Agent is used.
5. Requests to the same host are separated by at least 2 seconds, or longer when required by the website.
6. Request timeout is limited to 10 seconds.
7. Duplicate URLs are not collected more than once.
8. Login pages, CAPTCHA pages, downloadable files, and unsupported JavaScript-rendered pages are excluded.
9. Only pages containing non-empty main text are stored.
10. Failed requests are not counted as valid documents.

### User-Agent

```text
StudentWebCrawler/1.0
(Educational Research; contact: your-email@example.com)
```

Replace the contact information with an appropriate project contact address.

## 8. Data Storage

Collected articles are stored in JSON format.

The raw article records contain:

| Field | Description |
|---|---|
| url | Original article URL |
| title | Article title |
| text | Extracted article text |
| fetch_time | Time when the article was collected |

Example:

```json
{
    "url": "https://example.com/article",
    "title": "Example Technology News",
    "text": "Article content...",
    "fetch_time": "2026-10-01T10:00:00"
}
```

The collected data is stored in:

```text
database/
├── pages_Ａ.json
└── pages_B.json
```

The current dataset contains approximately 670 raw article records, with 669 documents included in the index.

## 9. Text Preprocessing

The preprocessing procedure is applied consistently to documents and search queries.

### Processing Steps

1. HTML Cleaning
   - Remove HTML tags.
   - Remove script, style, navigation, header, footer, and other irrelevant HTML elements.
   - Decode HTML entities.
   - Normalize whitespace.

2. Lowercase Conversion
   - Convert English text to lowercase.

3. Tokenization
   - Split text into individual tokens.
   - Preserve technical terms such as C++, C#, Node.js, and GPT-4.
   - Split hyphenated terms such as machine-learning into machine and learning.

4. Duplicate Removal
   - Remove duplicate documents based on normalized URLs.

5. Invalid Document Handling
   - Skip documents with missing URLs or empty text.
   - Skip documents that produce no valid tokens.

### Stop Word Removal

Stop word removal is not applied in the current implementation.

### Metadata

The following metadata is retained:

- Document ID
- Article URL
- Article title
- Fetch time
- Token count

The original article text is retained separately for displaying search result snippets.

## 10. Index Construction

The system implements TF, DF, IDF, and TF-IDF manually.

### Term Frequency (TF)

Log Frequency Weighting:

\[
TF(t,d)=
\begin{cases}
1+\log_{10}(f_{t,d}), & f_{t,d}>0\\
0, & f_{t,d}=0
\end{cases}
\]

Where:

- \(f_{t,d}\): Number of occurrences of term \(t\) in document \(d\).

### Document Frequency (DF)

DF represents the number of distinct documents containing a term.

\[
DF(t)=|\{d:t\in d\}|
\]

### Inverse Document Frequency (IDF)

Smoothed IDF:

\[
IDF(t)=1+\ln\left(\frac{N+1}{DF(t)+1}\right)
\]

Where:

- \(N\): Total number of indexed documents.

### TF-IDF

\[
TFIDF(t,d)=TF(t,d)\times IDF(t)
\]

### Document Vector Norm

\[
\|D\|=\sqrt{\sum_t TFIDF(t,D)^2}
\]

The calculated values are stored in the `index/` directory.

## 11. Search Algorithms

The web interface provides two search methods.

### 11.1 TF-IDF + Cosine Similarity

The first search method calculates the cosine similarity between the query vector and document vectors.

\[
Cosine(Q,D)=
\frac{Q\cdot D}{\|Q\|\|D\|}
\]

The system:

1. Preprocesses the query.
2. Calculates query TF-IDF using the existing corpus IDF.
3. Retrieves candidate documents using the inverted index.
4. Calculates cosine similarity.
5. Removes documents with scores less than or equal to zero.
6. Returns the top 10 results.

### 11.2 BM25

BM25 is used as an alternative document ranking method.

\[
BM25(q,d)=
\sum_{t\in q}
IDF(t)
\cdot
\frac{TF(t,d)(k_1+1)}
{TF(t,d)+k_1(1-b+b\frac{|d|}{avgdl})}
\]

Parameters:

| Parameter | Value |
|---|---:|
| \(k_1\) | 1.5 |
| \(b\) | 0.75 |

BM25 considers term frequency, inverse document frequency, and document length normalization.

The system returns the top 10 documents with positive BM25 scores.

**Note:** BM25 uses raw term frequencies and its own IDF calculation. It does not use the TF-IDF weights.

## 12. Running the Project

### Step 1: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 2: Run the Crawler

Run the crawler according to its entry point:

```powershell
python crawler.py
```

The crawler collects articles and saves them into the `database/` directory.

### Step 3: Build TF-IDF Index

```powershell
python tf_df.py
```

This generates:

- tf.json
- df.json
- idf.json
- tfidf.json
- postings.json

### Step 4: Calculate Document Norms

```powershell
python indexer.py
```

This generates:

- document_norms.json

### Step 5: Start the Search Engine

```powershell
python app.py
```

Open the following URL in a web browser:

```text
http://127.0.0.1:5000
```

### Step 6: Select a Search Method

Users can select either:

- TF-IDF + Cosine Similarity
- BM25

Enter an English technology-related query and click Search.

Example queries:

```text
Google Gemini latest news
OpenAI latest AI models
artificial intelligence developments
machine learning technology
cloud computing security
```

## 13. Evaluation and Reproducibility

The search engine is evaluated using Precision@5.

### Evaluation Dataset

Prepare 10 representative queries before conducting the evaluation.

Each query should represent a different information need related to technology news.

Example:

| Query | Information Need |
|---|---|
| Google Gemini latest news | Find recent Gemini-related news |
| OpenAI latest AI models | Find OpenAI model announcements |
| artificial intelligence developments | Find general AI developments |
| machine learning technology | Find machine learning news |
| cloud computing security | Find cloud security articles |
| software development tools | Find software development tools |
| cybersecurity attacks | Find cybersecurity news |
| data center technology | Find data center developments |
| GPU computing | Find GPU-related news |
| technology industry updates | Find major technology industry news |

### Relevance Judgement

For each query:

1. Run the query using TF-IDF + Cosine Similarity.
2. Run the same query using BM25.
3. Record the top 5 results from each method.
4. Read the full article content.
5. Manually determine whether each article is relevant to the query.
6. Assign a relevance label:
   - 1 = Relevant
   - 0 = Not relevant

The relevance criteria should be defined before evaluating the results and applied consistently to both methods.

### Precision@5

\[
P@5=\frac{\text{Number of relevant documents in top 5}}{5}
\]

The denominator is always 5, even when fewer than five results are returned.

### Mean Precision@5

\[
Mean\ P@5=
\frac{1}{Q}\sum_{i=1}^{Q}P@5_i
\]

Where:

- \(Q\): Number of evaluation queries.

Calculate Mean Precision@5 separately for TF-IDF and BM25.

### Reproduction Steps

1. Use the same crawled JSON dataset for both search methods.
2. Keep the same preprocessing procedure.
3. Prepare and freeze the 10 evaluation queries.
4. Run every query using both algorithms.
5. Save the top 5 results for each query and method.
6. Manually label each result as relevant or not relevant.
7. Calculate Precision@5 for every query.
8. Calculate Mean Precision@5 for each algorithm.
9. Compare the results and discuss differences.
10. Analyze at least two queries with poor search performance.

The evaluation records should be saved in a CSV or JSON file.

Suggested filename:

```text
evaluation/
├── evaluation_queries.csv
└── evaluation_results.csv
```

## 14. Limitations

- The search engine uses keyword-based retrieval rather than semantic search.
- Documents with similar vocabulary may receive high scores even when their topics are different.
- Search results depend on the quality and coverage of the crawled dataset.
- BM25 and TF-IDF scores use different scales and should not be directly compared numerically.
- Relevance judgements are manually assigned and may involve subjective decisions.
- The current system focuses on English technology news.

## 15. Future Improvements

Potential improvements include:

- Comparing additional ranking methods.
- Improving title and body text weighting.
- Adding phrase search and Boolean search.
- Improving snippet extraction.
- Optimizing inverted index retrieval.
- Expanding the news dataset.

## 16. Team Project

This project is developed as a university information retrieval course project.

The system demonstrates web crawling, text preprocessing, inverted indexing, TF-IDF retrieval, BM25 ranking, web-based search, and search quality evaluation.
