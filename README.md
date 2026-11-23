# Architecture Decision Records: Adoption, Impact, and Developer Engagement in Open-Source Software

Supplementary material of the paper presented at the **23rd IEEE International Conference on Software Architecture (ICSA 2026)**, Amsterdam, 22–26 June 2026. This repository contains the datasets, documentation, and scripts used in the study, made available for transparency and scientific collaboration.

**[Read the paper](https://doi.org/10.1109/ICSA66085.2026.00040)** · [ICSA 2026 research papers](https://conf.researchr.org/track/icsa-2026/icsa-2026-papers) · [How to cite](#how-to-cite)

## The study in brief

Architecture Decision Records (ADRs) are short documents that record an architectural decision and the reasons for it. They are spreading in open source, but little was known about what goes with their adoption. We mined the history of open-source repositories that use ADRs and asked two questions:

- **RQ1.** How does the adoption of ADRs influence open-source software projects?
- **RQ2.** What is the impact of ADR adoption on individual contributors?

| Dataset | |
|---|---|
| Repositories in the original dataset | 921 |
| Repositories analyzed | 859 |
| Repositories sampled for SonarQube quality measurements | 496 |
| Versions of ADR files with their status | 15,149 |
| Granularity of the metric tables | one row per project (or developer) and month |

The history of each repository was extracted with PyDriller and its code quality measured with SonarQube. ADR activity was then related to activity, quality, and productivity metrics with Spearman correlations at time lags from −36 to +36 months, averaged across projects.

### What we found

- ADR activity goes together with slightly more development activity and, in the following months, with slightly fewer defects and lower complexity. The correlations are small.
- Longer ADRs, and ADRs in the accepted or implemented status, are the ones most consistently associated with lower defect and complexity measures.
- About 63% of the ADRs are opened directly as accepted, so the discussion that led to the decision is not in the record.
- ADR work is concentrated in core developers, who maintain the records and work in the largest and most complex parts of the code.
- No clear gain or loss in individual productivity shows up for developers who write ADRs.

## What is in this repository

| Path | Content |
|---|---|
| `datasets/repositories/` | Complete list of repositories of the original dataset, indicating which were successfully cloned and which were excluded. |
| `datasets/metrics/` | ADR-, repository-, and developer-level monthly metric tables, including ADR histories, lifecycle transitions, software quality indicators, and developer activity measures. Split into parts; see [INSTALL.md](INSTALL.md) to assemble them. |
| `datasets/adr_status/` | Machine-readable ADR status labels and their mapping to normalized categories such as "proposed", "accepted", and "deprecated". |
| `scripts/pydriller/` | Data extraction scripts for mining the repositories and collecting commit and repository metadata with PyDriller. |
| `scripts/adr_processing/` | Scripts for processing ADR files, inferring ADR lifecycles, running the correlation pipeline, and exporting the datasets. |
| `scripts/sonarqube/` | Scripts for creating SonarQube projects, generating monthly quality reports, and aggregating SonarQube metrics. |
| `docs/metrics/metrics_catalog.md` | Catalog of all collected metrics, with definitions, scopes, and units when applicable. |
| `docs/status_mapping/status_mapping.md` | All ADR status labels observed in the repositories and their mapping to the status categories used in the study. |

## How to cite

E. G. de Santana Jr, G. B. Figueiredo, M. L. M. Peixoto, F. A. Durão, C. V. S. Prazeres, I. C. Machado, P. A. M. Silveira Neto, and E. S. de Almeida, "Architecture Decision Records: Adoption, Impact, and Developer Engagement in Open-Source Software," in *2026 IEEE 23rd International Conference on Software Architecture (ICSA)*, 2026, pp. 335–345. doi: [10.1109/ICSA66085.2026.00040](https://doi.org/10.1109/ICSA66085.2026.00040)

```bibtex
@inproceedings{santana2026adr,
  author    = {de Santana Jr, Enio Garcia and Figueiredo, Gustavo Bittencourt and Peixoto, Maycon Leone Maciel and Dur{\~a}o, Frederico Ara{\'u}jo and Prazeres, C{\'a}ssio Vin{\'i}cius Serafim and Machado, Ivan do Carmo and da Mota Silveira Neto, Paulo Anselmo and de Almeida, Eduardo Santana},
  title     = {Architecture Decision Records: Adoption, Impact, and Developer Engagement in Open-Source Software},
  booktitle = {2026 IEEE 23rd International Conference on Software Architecture (ICSA)},
  pages     = {335--345},
  year      = {2026},
  publisher = {IEEE},
  doi       = {10.1109/ICSA66085.2026.00040}
}
```

## License

The datasets and the documentation are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The scripts in `scripts/` are licensed under the [MIT License](LICENSE).

## Authors

Enio Garcia de Santana Jr, Gustavo Bittencourt Figueiredo, Maycon Leone Maciel Peixoto, Frederico Araújo Durão, Cássio Vinícius Serafim Prazeres, Ivan do Carmo Machado, and Eduardo Santana de Almeida, Institute of Computing, Federal University of Bahia (UFBA), Brazil. Paulo Anselmo da Mota Silveira Neto, Federal Rural University of Pernambuco (UFRPE), Brazil.

Questions about the data, or interest in building on it, are welcome: open an issue or reach the first author through [GitHub](https://github.com/EnioGS), [ORCID](https://orcid.org/0009-0000-7625-8583), or [LinkedIn](https://www.linkedin.com/in/eniosantana/).

--gse
