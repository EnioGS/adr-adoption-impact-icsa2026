# Metrics Catalog

This document summarizes the metrics collected and used in the study, including their intent, scope, and approximate units. Unless otherwise stated, metrics are aggregated at monthly granularity for each project, and in many cases further broken down by author to enable developer-centric and ADR-centric analyses.

## Repository and developer activity metrics (PyDriller-based)

### `number_of_commits`
- Description: Total number of commits observed in the month.
- Scope: Project (and, when applicable, project–author) per month; unit is commits.

### `avg_mod_lines`
- Description: Average number of lines modified per commit, computed over all commits in the month.
- Scope: Project (and project–author) per month; unit is lines per commit.

### `avg_mod_files`
- Description: Average number of files modified per commit, computed over all commits in the month.
- Scope: Project (and project–author) per month; unit is files per commit.

### `number_of_contributors`
- Description: Number of distinct contributors (authors) who made at least one commit in the month.
- Scope: Project per month; unit is contributors.

### `num_merge_commits`
- Description: Number of merge commits in the month, as identified from the Git history.
- Scope: Project (and project–author) per month; unit is commits.

### `median_hunks`
- Description: Median number of diff hunks per commit across all commits in the month.
- Scope: Project (and project–author) per month; unit is hunks per commit.

### `offhours_commits`
- Description: Number of commits authored outside local working hours (before 09:00 or after 17:00) in the month.
- Scope: Project (and project–author) per month; unit is commits.

### `avg_dmm_unit_size`
- Description: Average size of modified units (e.g., classes or files) according to the DMM size metric over commits in the month.
- Scope: Project (and project–author) per month; unit is tool-specific DMM size.

### `avg_dmm_unit_complexity`
- Description: Average complexity of modified units according to the DMM complexity metric over commits in the month.
- Scope: Project (and project–author) per month; unit is tool-specific DMM complexity.

### `avg_dmm_unit_interfacing`
- Description: Average interfacing score of modified units according to the DMM interfacing metric over commits in the month.
- Scope: Project (and project–author) per month; unit is tool-specific DMM interfacing.

### `gini_coeff_cum_file_change_all`
- Description: Gini coefficient computed over cumulative file-change activity, capturing how unevenly modifications are distributed across ADR files or contributors.
- Scope: Project (and project–author) per month; unit is a dimensionless value between 0 and 1.

## ADR-centric metrics

### `total_adr_changes`
- Description: Total number of ADR file changes (additions, modifications, renames, deletions) observed in the month.
- Scope: Project (and project–author) per month; unit is ADR file changes.

### `avg_adr_len`
- Description: Average length of ADR files, approximated by character count, among ADR versions observed in the month.
- Scope: Project (and project–author) per month; unit is characters per ADR.

### `avg_adr_changes`
- Description: Average number of recorded changes per ADR file (e.g., updates to content or status) in the month.
- Scope: Project (and project–author) per month; unit is changes per ADR.

### `file_changeADD`
- Description: Number of ADR file additions (new ADR files created) in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `file_changeMODIFY`
- Description: Number of ADR file modifications (content updates to existing ADRs) in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `file_changeDELETE`
- Description: Number of ADR file deletions (ADRs removed from the repository) in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `file_changeRENAME`
- Description: Number of ADR file renames in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `file_changeALL_CHANGES`
- Description: Total number of ADR file change events of any type (add, modify, delete, rename) in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_file_changeADD`
- Description: Cumulative count of ADR file additions up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_file_changeMODIFY`
- Description: Cumulative count of ADR file modifications up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_file_changeDELETE`
- Description: Cumulative count of ADR file deletions up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_file_changeRENAME`
- Description: Cumulative count of ADR file renames up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_file_changeALL_CHANGES`
- Description: Cumulative count of all ADR file change events (add, modify, delete, rename) up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_proposed`
- Description: Number of ADRs whose current status is mapped to the normalized category “proposed” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_accepted`
- Description: Number of ADRs whose current status is mapped to the normalized category “accepted” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_implemented`
- Description: Number of ADRs whose current status is mapped to the normalized category “implemented” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_deprecated`
- Description: Number of ADRs whose current status is mapped to the normalized category “deprecated” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_rejected`
- Description: Number of ADRs whose current status is mapped to the normalized category “rejected” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_suspended`
- Description: Number of ADRs whose current status is mapped to the normalized category “suspended” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_withdrawn`
- Description: Number of ADRs whose current status is mapped to the normalized category “withdrawn” in the month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `status_type_ALL_STATUS`
- Description: Total number of ADRs with any recognized status in the month, summing all normalized status categories.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_proposed`
- Description: Cumulative count of ADRs that have ever been in the “proposed” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_accepted`
- Description: Cumulative count of ADRs that have ever been in the “accepted” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_implemented`
- Description: Cumulative count of ADRs that have ever been in the “implemented” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_deprecated`
- Description: Cumulative count of ADRs that have ever been in the “deprecated” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_rejected`
- Description: Cumulative count of ADRs that have ever been in the “rejected” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_suspended`
- Description: Cumulative count of ADRs that have ever been in the “suspended” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_withdrawn`
- Description: Cumulative count of ADRs that have ever been in the “withdrawn” status category up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

### `cumulative_status_type_ALL_STATUS`
- Description: Cumulative count of ADRs across all normalized status categories up to and including the current month.
- Scope: Project (and project–author) per month; unit is ADR files.

## SonarQube-based quality metrics

### `bugs`
- Description: Number of issues classified as bugs by SonarQube for the analyzed snapshot.
- Scope: Project per month (based on the monthly snapshot); unit is issues.

### `new_bugs`
- Description: Number of newly introduced bug issues since the previous SonarQube baseline.
- Scope: Project per month; unit is issues.

### `vulnerabilities`
- Description: Number of issues classified as security vulnerabilities by SonarQube.
- Scope: Project per month; unit is issues.

### `new_vulnerabilities`
- Description: Number of newly introduced vulnerability issues since the previous SonarQube baseline.
- Scope: Project per month; unit is issues.

### `code_smells`
- Description: Number of maintainability-related issues (“code smells”) reported by SonarQube.
- Scope: Project per month; unit is issues.

### `new_code_smells`
- Description: Number of newly introduced code-smell issues since the previous SonarQube baseline.
- Scope: Project per month; unit is issues.

### `security_hotspots`
- Description: Number of identified security hotspots that may require manual review.
- Scope: Project per month; unit is hotspots.

### `complexity`
- Description: Overall cyclomatic complexity reported by SonarQube across the analyzed codebase.
- Scope: Project per month; unit is a dimensionless complexity count.

### `cognitive_complexity`
- Description: Overall cognitive complexity reported by SonarQube, reflecting how difficult code is to understand.
- Scope: Project per month; unit is a dimensionless complexity count.

### `coverage`
- Description: Overall test coverage ratio (percentage of covered lines) reported by SonarQube.
- Scope: Project per month; unit is percentage.

### `line_coverage`
- Description: Line-based coverage ratio, measuring the fraction of lines executed by tests.
- Scope: Project per month; unit is percentage.

### `branch_coverage`
- Description: Branch coverage ratio, measuring the fraction of control-flow branches executed by tests.
- Scope: Project per month; unit is percentage.

### `ncloc`
- Description: Number of non-comment lines of code (NCLOC) reported by SonarQube.
- Scope: Project per month; unit is lines of code.

### `lines`
- Description: Total number of lines in the analyzed codebase, including code and comments.
- Scope: Project per month; unit is lines.

### `files`
- Description: Number of source files in the analyzed codebase.
- Scope: Project per month; unit is files.

### `functions`
- Description: Number of functions or methods identified by SonarQube.
- Scope: Project per month; unit is functions.

### `statements`
- Description: Number of executable statements identified by SonarQube.
- Scope: Project per month; unit is statements.

### `comment_lines`
- Description: Number of comment lines in the analyzed codebase.
- Scope: Project per month; unit is lines.

### `comment_lines_density`
- Description: Density of comment lines relative to total lines, as reported by SonarQube.
- Scope: Project per month; unit is percentage.

### `duplicated_lines`
- Description: Number of lines that SonarQube considers duplicated.
- Scope: Project per month; unit is lines.

### `duplicated_blocks`
- Description: Number of duplicated code blocks detected by SonarQube.
- Scope: Project per month; unit is blocks.

### `open_issues`
- Description: Count of open issues in issue trackers or SonarQube at the time of the snapshot (as captured in the dataset).
- Scope: Project per month; unit is issues.

### `confirmed_issues`
- Description: Count of issues that have been confirmed or verified.
- Scope: Project per month; unit is issues.

### `uncovered_lines`
- Description: Number of lines not covered by tests according to SonarQube.
- Scope: Project per month; unit is lines.

### `blocker_violations`
- Description: Number of SonarQube violations with severity level “blocker”.
- Scope: Project per month; unit is violations.

### `critical_violations`
- Description: Number of SonarQube violations with severity level “critical”.
- Scope: Project per month; unit is violations.

### `major_violations`
- Description: Number of SonarQube violations with severity level “major”.
- Scope: Project per month; unit is violations.

### `minor_violations`
- Description: Number of SonarQube violations with severity level “minor”.
- Scope: Project per month; unit is violations.

### `info_violations`
- Description: Number of SonarQube violations with severity level “info”.
- Scope: Project per month; unit is violations.

### `new_blocker_violations`
- Description: Number of newly introduced blocker violations since the previous baseline.
- Scope: Project per month; unit is violations.

### `new_critical_violations`
- Description: Number of newly introduced critical violations since the previous baseline.
- Scope: Project per month; unit is violations.

### `new_major_violations`
- Description: Number of newly introduced major violations since the previous baseline.
- Scope: Project per month; unit is violations.

### `new_minor_violations`
- Description: Number of newly introduced minor violations since the previous baseline.
- Scope: Project per month; unit is violations.

### `new_info_violations`
- Description: Number of newly introduced informational violations since the previous baseline.
- Scope: Project per month; unit is violations.

### `software_quality_blocker_issues`
- Description: Number of software-quality issues categorized as “blocker” by the study’s software quality aggregation.
- Scope: Project per month; unit is issues.

### `software_quality_high_issues`
- Description: Number of high-severity software-quality issues after reclassification of SonarQube metrics.
- Scope: Project per month; unit is issues.

### `software_quality_medium_issues`
- Description: Number of medium-severity software-quality issues after reclassification of SonarQube metrics.
- Scope: Project per month; unit is issues.

### `software_quality_low_issues`
- Description: Number of low-severity software-quality issues after reclassification of SonarQube metrics.
- Scope: Project per month; unit is issues.

### `software_quality_info_issues`
- Description: Number of informational software-quality issues after reclassification of SonarQube metrics.
- Scope: Project per month; unit is issues.

### `software_quality_maintainability_issues`
- Description: Number of software-quality issues mapped to the maintainability dimension.
- Scope: Project per month; unit is issues.

### `software_quality_reliability_issues`
- Description: Number of software-quality issues mapped to the reliability dimension.
- Scope: Project per month; unit is issues.

### `software_quality_security_issues`
- Description: Number of software-quality issues mapped to the security dimension.
- Scope: Project per month; unit is issues.

### `new_software_quality_blocker_issues`
- Description: Number of newly introduced blocker-level software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_high_issues`
- Description: Number of newly introduced high-severity software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_medium_issues`
- Description: Number of newly introduced medium-severity software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_low_issues`
- Description: Number of newly introduced low-severity software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_info_issues`
- Description: Number of newly introduced informational software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_maintainability_issues`
- Description: Number of newly introduced maintainability-related software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_reliability_issues`
- Description: Number of newly introduced reliability-related software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `new_software_quality_security_issues`
- Description: Number of newly introduced security-related software-quality issues since the previous baseline.
- Scope: Project per month; unit is issues.

### `open_issues`
- Description: Count of open issues in issue trackers or SonarQube at the time of the snapshot (as captured in the dataset), highlighted here for its role as an input to quality-related analyses.
- Scope: Project per month; unit is issues.

### `confirmed_issues`
- Description: Count of issues that have been confirmed or verified, highlighted here for its role as an input to quality-related analyses.
- Scope: Project per month; unit is issues.

## Developer classification and ADR maintainer metrics

### `core developer criteria author_commits`
- Description: Boolean indicator that a developer belongs to the top fraction of contributors in the project based on cumulative number of commits up to the current month.
- Scope: Project–author–month; unit is a binary flag (1 for core, 0 otherwise).

### `core developer criteria author_lines`
- Description: Boolean indicator that a developer belongs to the top fraction of contributors based on cumulative modified lines of code up to the current month.
- Scope: Project–author–month; unit is a binary flag (1 for core, 0 otherwise).

### `core developer criteria author_files`
- Description: Boolean indicator that a developer belongs to the top fraction of contributors based on cumulative number of modified files up to the current month.
- Scope: Project–author–month; unit is a binary flag (1 for core, 0 otherwise).

### `adr_maintainer_criteria_25`
- Description: Boolean indicator that a developer belongs to the top 25th percentile of ADR maintainers in the project, based on cumulative ADR file changes (`cumulative_file_changeALL_CHANGES`).
- Scope: Project–author–month; unit is a binary flag (1 for ADR maintainer in the top 25%, 0 otherwise).

### `adr_maintainer_criteria_50`
- Description: Boolean indicator that a developer belongs to the top 50th percentile of ADR maintainers in the project, based on cumulative ADR file changes.
- Scope: Project–author–month; unit is a binary flag (1 for ADR maintainer in the top 50%, 0 otherwise).

### `adr_maintainer_criteria_75`
- Description: Boolean indicator that a developer belongs to the top 75th percentile of ADR maintainers in the project, based on cumulative ADR file changes.
- Scope: Project–author–month; unit is a binary flag (1 for ADR maintainer in the top 75%, 0 otherwise).
