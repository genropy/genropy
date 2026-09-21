# GEP 0 — GenroPy Enhancement Proposals

| | |
|---|---|
| **Area** | process |
| **Status** | Discussion |
| **Author** | Giovanni Porcari |
| **Created** | 2026-09-20 |
| **Refs** | GEP 1, GEP 2 |

## 1. Abstract

A GenroPy Enhancement Proposal (GEP) is a document that describes a change
to GenroPy that is too wide for an issue: a new syntax, a new architectural
layer, a deprecation plan, a change in a public contract. It records the
motivation, the options considered, the choice made and the transition
plan, so that the decision is discussed once, in one place, and stays
readable after the code has changed.

This GEP proposes the process itself.

## 2. When a GEP is needed

A GEP is written when a change:

- introduces or changes a grammar, a public API or a model declaration used
  by application code;
- adds a component that other components will depend on (a compiler, a
  handler, a proxy, a protocol);
- deprecates something in use, and needs a migration path;
- has more than one reasonable design and the choice must be argued.

Bug fixes, refactorings with no visible change and features with a single
obvious design stay in issues and pull requests.

## 3. Format

One Markdown file per GEP in `docs/gep/`, named
`GEP-NNNN-short-title.md`, written in English. The header is a table:

| field | content |
|---|---|
| **Area** | the part of GenroPy concerned: `sql`, `web`, `client`, `app`, `model`, `process`, ... |
| **Status** | see section 4 |
| **Author** | who proposes |
| **Created** | date |
| **Refs** | issues, PRs and other GEPs it relates to |

Suggested sections: Abstract, Motivation (with verified data, not
reasoning alone), Current state (what the code does today, with file
references), Proposal, Options considered (each with its decision and
date), Transition plan, Consequences, Open points.

The options section is kept after the decision: it is the record of why
the other paths were not taken.

## 4. Lifecycle

| status | meaning |
|---|---|
| Draft | being written by the author, on a branch; not yet in `develop` |
| Discussion | in `develop`; the substance is discussed in issues that name the GEP and changed by pull requests on the document |
| Accepted | the discussion is closed; the plan is the reference for implementation PRs |
| Implemented | the code is in `develop`; the GEP stays as documentation of the choice |
| Rejected | the discussion closed against it; the reasons stay recorded, so the question is not reopened |
| Superseded | replaced by a later GEP, named in the header |

The author decides when the document is ready, sets its status to
Discussion and opens a pull request on `develop` that contains only the
document. The review of that pull request is on the form: clarity of the
concepts, structure, verifiable data. It may refuse or ask for changes, but
it is not the discussion of the substance. The merge puts the document in
the corpus as its version 0. From then on every change is a pull request on
the document and the substance is discussed in issues. A pull request sets
Accepted or Rejected when the discussion closes, and Implemented when the
code is in `develop`.

## 5. Numbering

Sequential, assigned when the PR is opened. GEP 0 is this process. Numbers
are never reused.

## 6. Index

| GEP | area | title | status |
|---|---|---|---|
| 0 | process | GenroPy Enhancement Proposals | Discussion |
| 1 | sql | Relation functions in the column grammar | Discussion |
| 2 | sql | `manyRelation`: filtered many-side relations declared on the one-side table | Discussion |
