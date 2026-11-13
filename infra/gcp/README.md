# Experiment 2 as a Cloud Run job with a GPU

`uv run inv gcp.run --run <name>` runs Experiment 2 as a Cloud Run job with an
NVIDIA L4 in europe-west1 and brings the sealed bundles and telemetry back to
`results/<name>/`. Kodama's Terraform is not read or changed: this folder has its
own configuration and local state (`infra/gcp/terraform.tfstate`, gitignored).

```bash
uv run inv gcp.estimate --run e2-cloudrun-l4-subset --args="--max-cases 2"   # creates nothing
uv run inv gcp.plan --run e2-cloudrun-l4-subset                              # terraform plan, creates nothing
uv run inv gcp.run --run e2-cloudrun-l4-subset --args="--max-cases 2"        # estimate, confirm, run
uv run inv gcp.destroy                                                       # remove job, registry, account
```

## What it creates

| Resource | Bills |
|---|---|
| Artifact Registry repository `stale-but-on-time` (images tagged by commit; 5 kept) | storage, ≈ $0.10 per GiB-month (image ≈ 4–5 GiB) |
| Bucket `kodama-500509-stale-but-on-time`: `models/` (the exact Ollama blobs of the local runs, ≈ 10 GB) and `results/<run>/` | ≈ $0.02 per GiB-month |
| Service account `sbot-e2-job` (object admin on that bucket only) | — |
| Cloud Run job `sbot-e2`: 1× L4, 6 vCPU, 24 GiB (24 GiB needs 6 vCPU), no retries, task timeout 1 h (longer is a Beta feature) | per second while running: ≈ $1.23/h |

The job bills only while an execution runs, and Cloud Run stops it at the task
timeout (`--max-hours`, default 1; up to 12 h for GPU jobs, but more than 1 h is a Beta feature), so a hung run cannot keep
billing past that. Ctrl-C in the task cancels the execution.

## What a run does

1. Estimate and confirmation (`--yes` skips it, `--estimate-only` stops).
2. `terraform apply` (idempotent).
3. Image (`Dockerfile`): `ollama/ollama:0.40.13` (the release of the stored
   runs) + uv 0.13.6 + `git archive HEAD` + `uv sync --frozen`, built for
   linux/amd64 with `docker buildx` and pushed tagged with the commit, as
   Kodama's `deploy.build` does. The working tree must be clean. Skipped when
   the tag exists.
4. The models' manifests and blobs are copied from `~/.ollama/models` to the
   bucket once, so the job uses byte-identical weights (`machine/ollama-list.txt`
   shows the same ids as `ollama list` here).
5. `gcloud run jobs execute` with `RUN_NAME` and `RUN_ARGS`. The entrypoint
   (`job.sh`) copies the models into the container, starts Ollama with the
   laptop's settings (flash attention, q8_0 KV cache), runs `inv e2.run`, and
   copies `results/<run>` to the bucket on exit, success or not, with status
   markers (STARTED, MODELS_COPIED, OLLAMA_READY, DONE or FAILED).
6. Results are copied to `results/<run>/` with `machine.json` (billed seconds
   from the execution's start and completion, and their cost), the telemetry
   summary and `estimate_vs_actual.md`.

## Hardware (DGX Spark comparison)

| | DGX Spark | Cloud Run L4 (this job) | Cloud Run RTX PRO 6000 |
|---|---|---|---|
| GPU | GB10 (Blackwell) | L4 (Ada) | RTX PRO 6000 Blackwell |
| GPU memory | 128 GB unified (shared with CPU) | 24 GB GDDR6 | 96 GB GDDR7 |
| Memory bandwidth | 273 GB/s | 300 GB/s | 1,597 GB/s |
| europe-west1 | — | yes, ≈ $1.23/h at 6 vCPU / 24 GiB | not offered for jobs (europe-west4 is) |

The L4 is the cheaper option and has about the Spark's memory bandwidth, which
bounds token generation, so its decode speed on `gemma4:e4b` is a fair stand-in
for the latency question. It has a fifth of the memory and an older
architecture, and neither GPU has unified memory: models above ~20 GB (e.g.
`gemma4:31b` at 8 bits) need the RTX PRO 6000 in europe-west4.

## Quota

New projects get 3 L4 GPUs for Cloud Run jobs (without zonal redundancy) on the
first deployment, subject to availability. If the deployment fails for quota,
request "Total Nvidia L4 GPU allocation without zonal redundancy, per project
per region" for europe-west1 under IAM & Admin → Quotas & System Limits.
