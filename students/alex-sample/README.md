# Example Student — Alex Johnson (fictional)

This is a sample student instance included so you can see the tool in action
without providing your own data.  **All details are made up** — no real student
is represented here.

## Profile summary

| Field | Value |
| ----- | ----- |
| Name | Alex Johnson |
| State | Ohio |
| Major | Business Administration |
| GPA (UW) | 3.45 |
| SAT | 1180 / ACT 26 |
| Budget | $30,000 / year |
| Class of | 2027 |

## Run the pipeline

From the repo root:

```bash
college-finder --student alex-sample run
```

Outputs appear in `students/alex-sample/output/`.

## Adapting for your own student

1. Copy this folder: `cp -r students/alex-sample students/<your-name>`
2. Edit `students/<your-name>/input/student profile input.xlsx` with real data
3. Optionally update `config/pro.json` (shared tool config — research backend, logging)
4. Run: `college-finder --student <your-name> run`

Your outputs and catalog stay isolated inside your student folder.
The shared research cache (`data/college_research_cache.json`) is reused
automatically — no need to re-research schools already in the cache.
