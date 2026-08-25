#!/usr/bin/env python3
"""sessionarchive — semantic search + knowledge graph over a folder of session logs.

One entrypoint, three subcommands:
    sessionarchive ingest [options]
    sessionarchive query "<question>" [options]
    sessionarchive query --like <slug> [options]
    sessionarchive label
"""
import argparse

from . import ingest, query, label


def main():
    ap = argparse.ArgumentParser(prog="sessionarchive", description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    ingest_ap = sub.add_parser("ingest", help="Ingest a corpus into Neo4j + FAISS")
    ingest.add_arguments(ingest_ap)

    query_ap = sub.add_parser("query", help="Semantic search / similarity search over the index")
    query.add_arguments(query_ap)

    label_ap = sub.add_parser("label", help="Interactive relevance-labeling loop (needs a real TTY)")
    label.add_arguments(label_ap)

    args = ap.parse_args()

    if args.command == "ingest":
        ingest.run(args)
    elif args.command == "query":
        query.run(args)
    elif args.command == "label":
        label.run(args)


if __name__ == "__main__":
    main()
