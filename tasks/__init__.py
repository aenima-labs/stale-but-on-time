"""Invoke tasks, grouped by experiment. List them with `uv run inv --list`.

    uv run inv analyze                         # analysis, figures, numbers, paper (no Ollama)
    uv run inv reproduce                       # everything from scratch (needs Ollama)
    uv run inv data.fetch
    uv run inv e1.replay
    uv run inv e2.run --args="--think --out results/e2-think"
    uv run inv paper.anon                      # anonymised review copy under dist/
    uv run inv e2.estimate --args="--provider openai"   # estimate only, nothing runs
    uv run inv gcp.run --run e2-cloudrun-l4    # Cloud Run GPU job (asks before spending)
"""

from invoke import Collection, task

from . import data, e1, e2, gcp, paper


@task(pre=[e1.analyze, e2.analyze, e2.analyze_product, paper.figures, paper.numbers, paper.build])
def analyze(c):
    """Everything that needs no model: analysis, figures, numbers, paper."""


@task(
    pre=[
        data.fetch, e1.replay, e1.analyze, e2.build_pack, e2.run, e2.analyze,
        paper.figures, paper.numbers, paper.build,
    ]
)
def reproduce(c):
    """The whole pipeline from scratch (needs Ollama; about 30 minutes)."""


ns = Collection(analyze, reproduce)
ns.add_collection(Collection.from_module(data), name="data")
ns.add_collection(Collection.from_module(e1), name="e1")
ns.add_collection(Collection.from_module(e2), name="e2")
ns.add_collection(Collection.from_module(paper), name="paper")
ns.add_collection(Collection.from_module(gcp), name="gcp")
