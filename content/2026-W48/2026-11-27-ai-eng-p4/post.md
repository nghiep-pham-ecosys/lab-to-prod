---
date: 2026-11-27
series: ai-engineering
part: 4
title: "RAG without a vector database: BM25 that runs locally"
channels: [linkedin, facebook, telegram, x_manual]
short_publish_at: null
sources: []
image_alt: "A table card, toy example on a made-up 7-page handbook: with the chunk text only, BM25 ranked the right chunk 14th of 28; with the document title and section copied into each chunk, it ranked 4th."
status: approved
work: cfe-rag-bm25
card:
  layout: table
  theme: ink
  headline: "Put the title back in the chunk"
  rows:
    - ["Chunk only", "Right chunk at rank 14 of 28"]
    - ["Title first", "Right chunk at rank 4 of 28"]
    - ["Corpus", "Toy example: 7 made-up pages"]
  lesson: "Measure the rank of the right chunk first."
---

## linkedin

14 of 28. That is where BM25 ranked the one chunk that answered my test question.

I met this while building a RAG module for a Claude course I am writing in Vietnamese. Retrieval is plain BM25 in the Python standard library. It runs locally: no API key, no embedding model, no vector database. The corpus is a toy example: a made-up lab handbook, 7 pages cut into 28 chunks.

The question asked how long until a pH meter needs calibrating again. The right chunk said when to repeat the step, but never named the step or the meter. Those words were in the page title, and chunking cut it off.

The fix costs nothing. Before indexing, copy the title and the section name into each chunk:

f"Document: {title}. Section: {section}.\n{chunk}"

Same question, same BM25: the right chunk moved from rank 14 to rank 4.

Rank 4 still misses a top-3 cut. The question said "how long", the heading said "frequency", and BM25 matches words, not meaning. A top 5 would include it. Embeddings might close the gap too; I have not measured that yet. One question on a small made-up corpus is a demo, not a benchmark.

When a RAG answer is wrong, check first whether the right chunk was retrieved at all. The model cannot cite a chunk it never saw.

The lesson: before you add a vector database, put the title back in every chunk and measure the rank of the right chunk.

In your own RAG setups, what helped retrieval most: more context in each chunk, a larger top-k, or adding embeddings?

Part 4 of my AI Engineering notes.

#RAG #AIEngineering #LLM #InformationRetrieval

## x

14 of 28: where BM25 ranked the chunk that answered my RAG test question. The chunk never named the meter. The page title did, and chunking cut it off.

Copying title + section into each chunk moved it to rank 4. Toy corpus, no vector database, no API call.

## facebook

My search ranked the right answer 14th out of 28 pieces of text.

I was building a small search step for an AI assistant, using a classic keyword method called BM25. It runs on a laptop, no paid service. The documents: a made-up lab handbook (a toy example), cut into 28 pieces.

The piece with the answer never named the instrument. Only the page title did, and the title was lost when the page was cut up.

Copying the page title and section name into each piece moved the answer from 14th to 4th place. It cost nothing. 4th is still not 1st: sending only the top 3 pieces would still miss it.

Part 4 of my AI Engineering notes.

## telegram

14 of 28: where BM25 ranked the chunk that answered my RAG test question.

The chunk never named the instrument. The page title did, and chunking cut it off. BM25 only matches words that are in the chunk.

Fix, at zero cost: copy the document title and section name into every chunk before indexing. The right chunk moved from rank 14 to rank 4. No vector database, no API call: BM25 in the Python standard library, on a toy corpus of 7 made-up pages.

Rank 4 still misses a top-3 cut, because "how long" and "frequency" are different words to BM25. Measure the rank of the right chunk before you add embeddings.

Part 4 of my AI Engineering notes.
