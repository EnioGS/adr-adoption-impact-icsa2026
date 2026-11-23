from database import Database
from correlation_engine import CorrelationEngine
from functools import reduce
import os
import traceback
from tqdm import tqdm
import hashlib
import time
from pingouin import partial_corr
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy.stats import spearmanr
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from scipy.stats import shapiro, pearsonr, spearmanr, kurtosis, skew, kstest, norm
import pandas as pd
import networkx as nx
from datetime import datetime
from pandas import Timestamp
import matplotlib
from matplotlib.patches import Patch
import matplotlib.dates as mdates
import numpy as np
matplotlib.use('Agg')

class CorrelationRountine:

    def __init__(self) -> None:
        self.default_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        self.db_path = os.path.join(self.default_path, 'main_dataset.db')
        self.db_path_corr = os.path.join(self.default_path, 'corr_dataset.db')
        self.db_path_output = os.path.join(self.default_path, 'main_dataset.db')
        self.db_output = Database(self.db_path_output)
        self.db = Database(self.db_path)
        self.db_corr = Database(self.db_path_corr)
        self.tables = ['repo_metrics', 'adr_metrics']
        self.repository_metrics = {'avg_mod_lines': 'REAL', 'avg_mod_files': 'REAL', 'avg_dmm_unit_size': 'REAL', 'avg_dmm_unit_complexity': 'REAL', 'avg_dmm_unit_interfacing': 'REAL', 'median_hunks': 'REAL', 'num_merge_commits': 'REAL', 'offhours_commits': 'REAL', 'number_of_commits': 'REAL', 'number_of_contributors': 'REAL', 'adr_maintainer_criteria_25': 'REAL', 'adr_maintainer_criteria_50': 'REAL', 'adr_maintainer_criteria_75': 'REAL', 'gini_coeff_cum_file_change_all': 'REAL', 'bugs': 'REAL', 'new_bugs': 'REAL', 'vulnerabilities': 'REAL', 'new_vulnerabilities': 'REAL', 'code_smells': 'REAL', 'new_code_smells': 'REAL', 'high_impact_accepted_issues': 'REAL', 'new_blocker_violations': 'REAL', 'new_critical_violations': 'REAL', 'new_major_violations': 'REAL', 'new_minor_violations': 'REAL', 'new_info_violations': 'REAL', 'blocker_violations': 'REAL', 'critical_violations': 'REAL', 'major_violations': 'REAL', 'minor_violations': 'REAL', 'info_violations': 'REAL', 'security_hotspots': 'REAL', 'complexity': 'REAL', 'cognitive_complexity': 'REAL', 'coverage': 'REAL', 'line_coverage': 'REAL', 'branch_coverage': 'REAL', 'ncloc': 'REAL', 'lines': 'REAL', 'files': 'REAL', 'functions': 'REAL', 'statements': 'REAL', 'comment_lines': 'REAL', 'comment_lines_density': 'REAL', 'software_quality_blocker_issues': 'REAL', 'software_quality_high_issues': 'REAL', 'software_quality_info_issues': 'REAL', 'software_quality_medium_issues': 'REAL', 'software_quality_low_issues': 'REAL', 'software_quality_maintainability_issues': 'REAL', 'software_quality_reliability_issues': 'REAL', 'software_quality_security_issues': 'REAL', 'new_software_quality_blocker_issues': 'REAL', 'new_software_quality_high_issues': 'REAL', 'new_software_quality_info_issues': 'REAL', 'new_software_quality_medium_issues': 'REAL', 'new_software_quality_low_issues': 'REAL', 'new_software_quality_maintainability_issues': 'REAL', 'new_software_quality_reliability_issues': 'REAL', 'new_software_quality_security_issues': 'REAL', 'duplicated_blocks': 'REAL', 'duplicated_lines': 'REAL', 'open_issues': 'REAL', 'uncovered_lines': 'REAL', 'confirmed_issues': 'REAL', 'core developer criteria author_commits': 'REAL', 'core developer criteria author_lines': 'REAL', 'core developer criteria author_files': 'REAL'}
        self.adr_metrics = {'total_adr_changes': 'REAL', 'avg_adr_len': 'REAL', 'avg_adr_changes': 'REAL', 'file_changeADD': 'REAL', 'file_changeMODIFY': 'REAL', 'file_changeDELETE': 'REAL', 'file_changeRENAME': 'REAL', 'file_changeALL_CHANGES': 'REAL', 'cumulative_file_changeADD': 'REAL', 'cumulative_file_changeMODIFY': 'REAL', 'cumulative_file_changeDELETE': 'REAL', 'cumulative_file_changeRENAME': 'REAL', 'cumulative_file_changeALL_CHANGES': 'REAL', 'status_type_withdrawn': 'REAL', 'status_type_suspended': 'REAL', 'status_type_rejected': 'REAL', 'status_type_proposed': 'REAL', 'status_type_implemented': 'REAL', 'status_type_deprecated': 'REAL', 'status_type_accepted': 'REAL', 'status_type_ALL_STATUS': 'REAL', 'cumulative_status_type_withdrawn': 'REAL', 'cumulative_status_type_suspended': 'REAL', 'cumulative_status_type_rejected': 'REAL', 'cumulative_status_type_proposed': 'REAL', 'cumulative_status_type_implemented': 'REAL', 'cumulative_status_type_deprecated': 'REAL', 'cumulative_status_type_accepted': 'REAL', 'cumulative_status_type_ALL_STATUS': 'REAL', 'core developer criteria author_commits': 'REAL', 'core developer criteria author_lines': 'REAL', 'core developer criteria author_files': 'REAL', 'adr_maintainer_criteria_25': 'REAL', 'adr_maintainer_criteria_50': 'REAL', 'adr_maintainer_criteria_75': 'REAL', 'gini_coeff_cum_file_change_all': 'REAL'}
        self.author_level_data = {'avg_mod_lines': 'REAL', 'avg_mod_files': 'REAL', 'avg_dmm_unit_size': 'REAL', 'avg_dmm_unit_complexity': 'REAL', 'avg_dmm_unit_interfacing': 'REAL', 'median_hunks': 'REAL', 'num_merge_commits': 'REAL', 'offhours_commits': 'REAL', 'number_of_commits': 'REAL', 'total_adr_changes': 'REAL', 'avg_adr_len': 'REAL', 'avg_adr_changes': 'REAL', 'file_changeADD': 'REAL', 'file_changeMODIFY': 'REAL', 'file_changeDELETE': 'REAL', 'file_changeRENAME': 'REAL', 'file_changeALL_CHANGES': 'REAL', 'cumulative_file_changeADD': 'REAL', 'cumulative_file_changeMODIFY': 'REAL', 'cumulative_file_changeDELETE': 'REAL', 'cumulative_file_changeRENAME': 'REAL', 'cumulative_file_changeALL_CHANGES': 'REAL', 'status_type_withdrawn': 'REAL', 'status_type_suspended': 'REAL', 'status_type_rejected': 'REAL', 'status_type_proposed': 'REAL', 'status_type_implemented': 'REAL', 'status_type_deprecated': 'REAL', 'status_type_accepted': 'REAL', 'status_type_ALL_STATUS': 'REAL', 'cumulative_status_type_withdrawn': 'REAL', 'cumulative_status_type_suspended': 'REAL', 'cumulative_status_type_rejected': 'REAL', 'cumulative_status_type_proposed': 'REAL', 'cumulative_status_type_implemented': 'REAL', 'cumulative_status_type_deprecated': 'REAL', 'cumulative_status_type_accepted': 'REAL', 'cumulative_status_type_ALL_STATUS': 'REAL', 'core developer criteria author_commits': 'REAL', 'core developer criteria author_lines': 'REAL', 'core developer criteria author_files': 'REAL', 'adr_maintainer_criteria_25': 'REAL', 'adr_maintainer_criteria_50': 'REAL', 'adr_maintainer_criteria_75': 'REAL'}

    def query_to_add_arb_columns(self, table_name, columns_to_add):
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except Exception as e:
                print(f'Error in adding columns {e}')

    def get_new_adr_data(self):
        df_adr_tracking_data = self.db.to_df('adr_tracking_info')
        results = df_adr_tracking_data.apply(get_adr_content_metrics)
        self.db.cache(results, 'adr_metrics')
        self.db.save()

    def start_correlation_analysis(self):
        correlation_engine = CorrelationEngine(self.author_level_data, self.repository_metrics, self.adr_metrics, self.default_path)
        correlation_engine.create_tables()
        columns = [('obs', 'TEXT'), ('status', 'TEXT'), ('len_data', 'INTEGER')]
        correlation_engine.query_to_add_arb_columns(table_name='variables', columns_to_add=columns)
        workers = 7
        chunk_size = 3000
        curr_runs = 0
        reached_max = False
        df_variables = self.db_corr.to_df('variables')
        print(f'df_variables columns {df_variables.columns}')
        df_variables = df_variables[df_variables['status'] != 'success'].copy()
        df_variables = df_variables[df_variables['scope_1'] != 'global_level']
        df_variables = df_variables[df_variables['scope_2'] != 'global_level']
        df_variables = df_variables[df_variables['scope_1'] == df_variables['scope_2']]
        variables = df_variables.to_dict(orient='records')
        correlation_engine.calculate_base_correlations(variables, workers)

    def aggregate_correlations(self, runs):
        correlation_engine = CorrelationEngine(self.author_level_data, self.repository_metrics, self.adr_metrics, self.default_path)
        correlation_engine.calculate_agg_correlations(runs=runs)

    def get_significant_correlations(self):
        correlation_engine = CorrelationEngine(self.author_level_data, self.repository_metrics, self.adr_metrics, self.default_path)
        correlation_engine.create_tables()
        correlation_engine.query_for_significant_correlations()

    def query_to_add_columns(self):
        columns_to_add = [('number_of_contributors', 'REAL'), ('adr_maintainer_criteria_25', 'REAL'), ('adr_maintainer_criteria_50', 'REAL'), ('adr_maintainer_criteria_75', 'REAL'), ('gini_coeff_cum_file_change_all', 'REAL')]
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE repo_metrics ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except:
                pass
        columns_to_add = [('gini_coeff_cum_file_change_all', 'REAL'), ('adr_maintainer_criteria_25', 'REAL'), ('adr_maintainer_criteria_50', 'REAL'), ('adr_maintainer_criteria_75', 'REAL')]
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE adr_metrics ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except:
                pass

    def get_monthly_contributors_and_adr_maintainer_status(self):
        self.query_to_add_columns()
        df_repo_metrics = self.db.to_df('repo_metrics')
        df_repo_metrics['number_of_contributors'] = None
        df_repo_metrics['gini_coeff_cum_file_change_all'] = None
        self.db.import_data(df_repo_metrics, 'repo_metrics')
        df_repo_metrics.drop(columns=['number_of_contributors'], inplace=True)
        df_repo_metrics_filtered = df_repo_metrics[(df_repo_metrics['author_name'].str.strip() != '') & ~df_repo_metrics['author_name'].str.contains('core_developers|peripheral_developers|adr_maintainer')].copy()
        df_repo_metrics_filtered_project = df_repo_metrics[df_repo_metrics['author_name'].str.strip() == ''].copy()
        if df_repo_metrics_filtered.empty:
            print('Warning: df_repo_metrics_filtered is empty.')
        df_contributor_counts = df_repo_metrics_filtered.groupby(['project_name', 'year', 'month'], as_index=False).agg(number_of_contributors=('author_name', 'nunique'))
        df_repo_metrics_with_counts = df_repo_metrics_filtered_project.merge(df_contributor_counts, on=['project_name', 'year', 'month'], how='left')
        self.db.import_data(df_repo_metrics_with_counts, 'repo_metrics')
        df_adr_metrics = self.db.to_df('adr_metrics')
        df_adr_metrics_filtered = df_adr_metrics[(df_adr_metrics['author_name'].str.strip() != '') & ~df_adr_metrics['author_name'].str.contains('core_developers|peripheral_developers|adr_maintainer')].copy()
        df_adr_metrics_filtered_project = df_adr_metrics[df_adr_metrics['author_name'].str.strip() == ''].copy()
        if df_adr_metrics_filtered.empty:
            print('Warning: df_adr_metrics_filtered is empty.')

        def gini_coefficient(values):
            if len(values) == 0:
                return None
            values_sorted = np.sort(values)
            n = len(values_sorted)
            cumulative_values = np.cumsum(values_sorted)
            total = cumulative_values[-1]
            if total == 0:
                return None
            gini = (n + 1 - 2 * np.sum(cumulative_values / total)) / n
            return gini
        gini_results = df_adr_metrics_filtered.groupby(['project_name', 'year', 'month']).apply(lambda group: gini_coefficient(group['cumulative_file_changeALL_CHANGES'].values)).reset_index(name='gini_coeff_cum_file_change_all')
        gini_results['project_name'] = gini_results['project_name'].astype(str)
        gini_results['year'] = gini_results['year'].astype(int)
        gini_results['month'] = gini_results['month'].astype(int)
        df_repo_metrics_with_counts.drop(columns=['gini_coeff_cum_file_change_all'], inplace=True)
        df_adr_metrics_filtered_project.drop(columns=['gini_coeff_cum_file_change_all'], inplace=True)
        df_repo_metrics_with_gini = df_repo_metrics_with_counts.merge(gini_results, on=['project_name', 'year', 'month'], how='left')
        df_adr_metrics_with_gini = df_adr_metrics_filtered_project.merge(gini_results, on=['project_name', 'year', 'month'], how='left')
        self.db.import_data(df_repo_metrics_with_gini, 'repo_metrics')
        self.db.import_data(df_adr_metrics_with_gini, 'adr_metrics')
        df_repo_metrics = self.db.to_df('repo_metrics')
        df_repo_metrics_filtered = df_repo_metrics[(df_repo_metrics['author_name'].str.strip() != '') & ~df_repo_metrics['author_name'].str.contains('core_developers|peripheral_developers|adr_maintainer')].copy()
        df_repo_metrics_filtered_project = df_repo_metrics[df_repo_metrics['author_name'].str.strip() == ''].copy()
        df_adr_metrics = self.db.to_df('adr_metrics')
        df_adr_metrics_filtered = df_adr_metrics[(df_adr_metrics['author_name'].str.strip() != '') & ~df_adr_metrics['author_name'].str.contains('core_developers|peripheral_developers|adr_maintainer')].copy()
        df_adr_metrics_filtered_project = df_adr_metrics[df_adr_metrics['author_name'].str.strip() == ''].copy()

        def determine_adr_maintainer_status(group):
            thresholds = {'25': np.percentile(group['cumulative_file_changeALL_CHANGES'], 25), '50': np.percentile(group['cumulative_file_changeALL_CHANGES'], 50), '75': np.percentile(group['cumulative_file_changeALL_CHANGES'], 75)}
            group['adr_maintainer_criteria_25'] = (group['cumulative_file_changeALL_CHANGES'] >= thresholds['25']).astype(float)
            group['adr_maintainer_criteria_50'] = (group['cumulative_file_changeALL_CHANGES'] >= thresholds['50']).astype(float)
            group['adr_maintainer_criteria_75'] = (group['cumulative_file_changeALL_CHANGES'] >= thresholds['75']).astype(float)
            return group
        df_adr_metrics_with_criteria = df_adr_metrics_filtered.groupby(['project_name', 'year', 'month'], group_keys=False).apply(determine_adr_maintainer_status)
        df_repo_metrics_filtered.drop(columns=['adr_maintainer_criteria_25', 'adr_maintainer_criteria_50', 'adr_maintainer_criteria_75'], inplace=True)
        df_repo_metrics_updated = df_repo_metrics_filtered.merge(df_adr_metrics_with_criteria[['project_name', 'year', 'month', 'author_name', 'adr_maintainer_criteria_25', 'adr_maintainer_criteria_50', 'adr_maintainer_criteria_75']], on=['project_name', 'year', 'month', 'author_name'], how='left')
        df_adr_metrics_filtered.drop(columns=['adr_maintainer_criteria_25', 'adr_maintainer_criteria_50', 'adr_maintainer_criteria_75'], inplace=True)
        df_adr_metrics_updated = df_adr_metrics_filtered.merge(df_adr_metrics_with_criteria[['project_name', 'year', 'month', 'author_name', 'adr_maintainer_criteria_25', 'adr_maintainer_criteria_50', 'adr_maintainer_criteria_75']], on=['project_name', 'year', 'month', 'author_name'], how='left')
        self.db.import_data(df_repo_metrics_updated, 'repo_metrics')
        self.db.import_data(df_adr_metrics_updated, 'adr_metrics')
        df_repo_metrics_updated_adr_maintainer_criteria_25 = df_repo_metrics_updated[df_repo_metrics_updated['adr_maintainer_criteria_25'] == 1].copy()
        df_repo_metrics_updated_adr_maintainer_criteria_50 = df_repo_metrics_updated[df_repo_metrics_updated['adr_maintainer_criteria_50'] == 1].copy()
        df_repo_metrics_updated_adr_maintainer_criteria_75 = df_repo_metrics_updated[df_repo_metrics_updated['adr_maintainer_criteria_75'] == 1].copy()
        df_repo_metrics_updated_adr_maintainer_not = df_repo_metrics_updated[(df_repo_metrics_updated['adr_maintainer_criteria_25'] != 1) & (df_repo_metrics_updated['adr_maintainer_criteria_50'] != 1) & (df_repo_metrics_updated['adr_maintainer_criteria_75'] != 1)].copy()
        df_adr_metrics_updated_adr_maintainer_criteria_25 = df_adr_metrics_updated[df_adr_metrics_updated['adr_maintainer_criteria_25'] == 1].copy()
        df_adr_metrics_updated_adr_maintainer_criteria_50 = df_adr_metrics_updated[df_adr_metrics_updated['adr_maintainer_criteria_50'] == 1].copy()
        df_adr_metrics_updated_adr_maintainer_criteria_75 = df_adr_metrics_updated[df_adr_metrics_updated['adr_maintainer_criteria_75'] == 1].copy()
        df_adr_metrics_updated_adr_maintainer_not = df_adr_metrics_updated[(df_adr_metrics_updated['adr_maintainer_criteria_25'] != 1) & (df_adr_metrics_updated['adr_maintainer_criteria_50'] != 1) & (df_adr_metrics_updated['adr_maintainer_criteria_75'] != 1)].copy()
        df_repo_mtn_agg_25 = df_repo_metrics_updated_adr_maintainer_criteria_25.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_repo_mtn_agg_50 = df_repo_metrics_updated_adr_maintainer_criteria_50.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_repo_mtn_agg_75 = df_repo_metrics_updated_adr_maintainer_criteria_75.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_repo_mtn_agg_not = df_repo_metrics_updated_adr_maintainer_not.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_adr_mtn_agg_25 = df_adr_metrics_updated_adr_maintainer_criteria_25.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_adr_mtn_agg_50 = df_adr_metrics_updated_adr_maintainer_criteria_50.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_adr_mtn_agg_75 = df_adr_metrics_updated_adr_maintainer_criteria_75.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_adr_mtn_agg_not = df_adr_metrics_updated_adr_maintainer_not.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_repo_mtn_agg_25['author_name'] = 'adr_maintainer_25'
        df_repo_mtn_agg_50['author_name'] = 'adr_maintainer_50'
        df_repo_mtn_agg_75['author_name'] = 'adr_maintainer_75'
        df_repo_mtn_agg_not['author_name'] = 'adr_maintainer_not'
        df_adr_mtn_agg_25['author_name'] = 'adr_maintainer_25'
        df_adr_mtn_agg_50['author_name'] = 'adr_maintainer_50'
        df_adr_mtn_agg_75['author_name'] = 'adr_maintainer_75'
        df_adr_mtn_agg_not['author_name'] = 'adr_maintainer_not'
        df_repo_new_authors = pd.concat([df_repo_mtn_agg_25, df_repo_mtn_agg_50, df_repo_mtn_agg_75, df_repo_mtn_agg_not], ignore_index=True)
        df_adr_new_authors = pd.concat([df_adr_mtn_agg_25, df_adr_mtn_agg_50, df_adr_mtn_agg_75, df_adr_mtn_agg_not], ignore_index=True)
        self.db.import_data(df_repo_new_authors, 'repo_metrics')
        self.db.import_data(df_adr_new_authors, 'adr_metrics')

    def create_new_representative_authors(self, table_name):
        df_current_metrics = self.db.to_df(table_name)
        df_current_metrics_filtered = df_current_metrics[df_current_metrics['author_name'].str.len() != 0].copy()
        df_current_metrics_filtered_core_dev = df_current_metrics_filtered[(df_current_metrics_filtered['core developer criteria author_commits'] == 1) | (df_current_metrics_filtered['core developer criteria author_lines'] == 1) | (df_current_metrics_filtered['core developer criteria author_files'] == 1)].copy()
        df_current_metrics_filtered_peripheral_dev = df_current_metrics_filtered[(df_current_metrics_filtered['core developer criteria author_commits'] != 1) & (df_current_metrics_filtered['core developer criteria author_lines'] != 1) & (df_current_metrics_filtered['core developer criteria author_files'] != 1)].copy()
        df_core_agg = df_current_metrics_filtered_core_dev.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_peripheral_agg = df_current_metrics_filtered_peripheral_dev.groupby(['project_name', 'year', 'month'], as_index=False).sum(numeric_only=True)
        df_core_agg['author_name'] = 'core_developers'
        df_peripheral_agg['author_name'] = 'peripheral_developers'
        df_new_authors = pd.concat([df_core_agg, df_peripheral_agg], ignore_index=True)
        self.db.import_data(df_new_authors, table_name)

    def replace_null_values(self, value, replacement_dict):
        for key, replacement in replacement_dict.items():
            if pd.isnull(value) and pd.isnull(key):
                return replacement
            elif value == key:
                return replacement
        return value

    def cleanup_repo_metrics(self):
        df_current_metrics = self.db.to_df('repo_metrics')
        replacement_dict = {None: np.nan, 'None': np.nan, np.nan: np.nan, 'nan': np.nan, 'NULL': np.nan, '': np.nan}
        for key, value in self.repository_metrics.items():
            if value == 'REAL':
                df_current_metrics[key] = df_current_metrics[key].apply(lambda x: self.replace_null_values(x, replacement_dict))
        self.db.import_data(df_current_metrics, 'repo_metrics')

    def cleanup_adr_metrics(self):
        df_current_metrics = self.db.to_df('adr_metrics')
        replacement_dict = {None: 0, 'None': 0, np.nan: 0, 'nan': 0, 'NULL': 0, '': 0}
        for key, value in self.adr_metrics.items():
            if value == 'REAL':
                df_current_metrics[key] = df_current_metrics[key].apply(lambda x: self.replace_null_values(x, replacement_dict))
        self.db.import_data(df_current_metrics, 'adr_metrics')

    def add_missing_columns(self, df, all_columns):
        for col in all_columns:
            if col not in df.columns:
                df[col] = ''
        return df

    def _ensure_columns_exist(self, table, variables):
        existing_columns = self.db.execute_sql(f'PRAGMA table_info({table});')
        existing_column_names = {col[1] for col in existing_columns}
        for column_name, column_type in variables.items():
            quoted_column_name = self._quote_column(column_name)
            if column_name not in existing_column_names:
                try:
                    self.db.execute_sql(f'ALTER TABLE {table} ADD COLUMN {quoted_column_name} {column_type};')
                except Exception as e:
                    print(f'Skipping column {quoted_column_name}. Error: {e}')

    def _quote_column(self, name):
        return f'"{name}"' if ' ' in name or '-' in name else name

    def create_tables(self):
        for table in self.tables:
            if table == 'repo_metrics':
                current_variables = self.repository_metrics
            elif table == 'adr_metrics':
                current_variables = self.adr_metrics
            drop_old_repo_metrics_table = f'\n            DROP TABLE IF EXISTS {table};\n            '
            self.db.execute_sql(drop_old_repo_metrics_table)
            create_repo_metrics_table = f'\n            CREATE TABLE {table} (\n                year INTEGER,\n                month INTEGER,\n                project_name TEXT,\n                author_name TEXT,\n                PRIMARY KEY (project_name, author_name, year, month)  \n            );\n            '
            self.db.execute_sql(create_repo_metrics_table)
            self._ensure_columns_exist(table, current_variables)
            pivot_columns = ',\n'.join([f"MAX(CASE WHEN variable_name = '{metric}' THEN value ELSE NULL END) AS {self._quote_column(metric)}" for metric in current_variables.keys()])
            pivot_query = f"""\n            INSERT OR IGNORE INTO {table} (year, month, project_name, author_name, {', '.join((self._quote_column(metric) for metric in current_variables.keys()))})\n            SELECT \n                year,\n                month,\n                project_name,\n                author_name,\n                {pivot_columns}\n            FROM metrics\n            WHERE variable_name IN ({', '.join((f"'{metric}'" for metric in current_variables.keys()))})\n            GROUP BY year, month, project_name, author_name;\n            """
            self.db.execute_sql(pivot_query)
        self.create_new_representative_authors('repo_metrics')
        self.create_new_representative_authors('adr_metrics')
        self.cleanup_repo_metrics()
        self.cleanup_adr_metrics()

def get_adr_content_metrics(row):
    return results
if __name__ == '__main__':
    routine = CorrelationRountine()
    print(f'create_tables off')
    routine.aggregate_correlations(['agg_correlation'])
    routine.get_significant_correlations()
