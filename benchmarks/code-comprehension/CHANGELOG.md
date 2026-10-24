# Code Comprehension Changelog

This track originated as the standalone *Environment-Free Coding Benchmark (EFCB)*;
the versions below predate its move into SRE-skills-bench.

## v0.3 — Prerelease: migrate to PR-only and expand to 6 repositories

**Date**: June 6, 2025

- Replaces the "issue-to-pull request" approach with a "pull-request-only" approach:
  - Given any currently-closed pull request, scrape the code patches from that pull
    request only.
- Expands data from a single repository (mastodon/mastodon) to six, with 300
  questions before filtering:
  - mastodon/mastodon
  - cloudflare/cloudflared
  - duckdb/duckdb
  - chroma-core/chroma
  - bluesky-social/indigo
  - tailscale/tailscale

## v0.2 — Prerelease: 5 tasks

- Introduces five tasks and a larger set of questions from the mastodon/mastodon
  repository:
  - GMCQ-Easy
  - GMCQ-Hard
  - MPR-Gen
  - Reverse-QA
  - Reverse-QA-Hallu

## v0.1 — Initial prerelease

- Introduces GMCQ: 82 questions on the mastodon/mastodon repository.
- Uses an issue-to-pull-request format: given an issue, scrape the code patches
  from the pull request that closes it. At this stage, only issues with the bug
  label are scraped. One challenge is that references in the issue can also point to
  unrelated issues or pull requests, adding noise to the data.
