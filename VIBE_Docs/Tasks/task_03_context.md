You are the senior developer on PManghan91/boardroom-repo.

TASK 03 – Harden & automate “hello-boardroom”
────────────────────────────────────────────

1 Database migration
  • Create Alembic revision **20240627_add_gin_snapshot**
    ```
    ALTER TABLE boardroom_snapshots
      ALTER COLUMN snapshot SET DATA TYPE JSONB USING snapshot::jsonb;
    CREATE INDEX IF NOT EXISTS boardroom_snapshot_gin
      ON boardroom_snapshots USING gin (snapshot);
    ```
    (GIN index keeps JSONB queries fast.)

2 Extra tests
  • Payload-size guard – add `test_snapshot_size` asserting
    `octet_length(snapshot::text) < 10_240`.
  • Idempotence – with **fakeredis**, push a stream entry, run the worker,
    restart the worker, confirm the message is not re-processed
    (pending-entries list stays empty).

3 Docker health-checks polish
  • In `docker-compose.yml` add:
    ```
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 3
    ```
    Do the same for `worker` but target `:8001/health`.

4 GitHub Actions CI
  • Add `.github/workflows/ci.yml`
    ```yaml
    name: test-and-build
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: docker://ghcr.io/docker/compose-action:latest
            with:
              compose-file: ./docker-compose.yml
              up-flags: --build -d
              run-tests: |
                docker compose exec api pytest -q
          - run: docker compose down -v
    ```

5 Documentation
  • Append “Performance & Indexing” section to `docs/ARCHITECTURE.md`
    explaining JSONB + GIN choice and 10 KB snapshot cap.

6 PR procedure
  • Branch: `feat/hardening-ci`.
  • Commit: migration, new tests, health-check tweaks, CI workflow, doc update.
  • PR title: **“feat: GIN index, size tests & CI pipeline”**.
  • PR description must include:
      – `docker compose ps` (show “healthy”)  
      – `pytest -q` output  
      – GitHub Actions run link  
      – Observed snapshot byte size.
  • Answer in a comment:
      1. Any messages re-queued after worker restart?  
      2. Average “XADD → snapshot” latency (ms).  
      3. CI runtime on ubuntu-latest.

Merge once all checks pass; then we start Sprint 1 (Browserbase & Fetch integration).
