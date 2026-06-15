# EFCB Changelog

## v0.3: Prerelease: Migrate to PR (instead of Issue-to-PR) and Expands to 6 Repositories

**Date**: June 6, 2025

- Repalces the "issue-to-pull request" approach with a "pull-request-only" approach:
  - Given any pull request that is currently closed, scrape the code patches from this pull request only.
- Expands data from a single repository (mastodon/mastodon) to the following
  five, with 300 questions before filtering:
  - mastodon/mastodon
  - cloudflare/cloudflared
  - duckdb/duckb
  - chroma-core/chroma
  - bluesky-social/indigo
  - tailscale/tailscale

## v0.2 - Prerelease: 5 Tasks

- Introduces five different tasks and a larger number of questions from the
  mastodon/mastodon repository:
  - GMCQ-Easy
  - GMCQ-Hard
  - MPR-Gen
  - Reverse-QA
  - Reverse-QA-Hallu

## v0.1 - Initial Prerelease

- Introduces GMCQ: 82 questions on the mastodon/mastodon repository
- Uses an issue-to-pull request format:
  - Given an issue, scrape the code patches from the pull request that closes the issue. At this stage, only issues with the bug label are scraped. One challenge is the references in the issue can also reference unrelated issues or pull requests, thus adding noise to the data.
