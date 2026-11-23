import pandas as pd
import os
from datetime import datetime
import matplotlib
from matplotlib.patches import Patch
import matplotlib.dates as mdates
import numpy as np
from pingouin import partial_corr
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy.stats import spearmanr
from tqdm import trange, tqdm
import traceback
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from scipy.stats import shapiro, pearsonr, spearmanr, kurtosis, skew, kstest, norm
from database import Database

class CorrelationEngine:

    def __init__(self, author_level_data, repository_metrics, adr_metrics, path):
        self.metrics = {}
        self.correlates_with = {}
        self.main_data = ''
        self.adr_data = ''
        self.results = []
        self.author_level_data = author_level_data
        self.repository_metrics = repository_metrics
        self.adr_metrics = adr_metrics
        self.min_data_len = 5
        self.source_db_path = os.path.join(path, 'main_dataset.db')
        self.source_db = Database(self.source_db_path)
        self.db_path = os.path.join(path, 'corr_dataset.db')
        self.db = Database(self.db_path)

    def create_tables(self):
        try:
            query_drop_significant_table = '\n            DROP TABLE sign_corr_table;\n            '
            self.db.execute_sql(query_drop_significant_table)
        except:
            pass
        create_variable_properties_table = f'\n            CREATE TABLE IF NOT EXISTS variable_properties (\n                variable_1 TEXT NOT NULL,\n                variable_2 TEXT NOT NULL,\n                scope_1 TEXT NOT NULL,\n                scope_2 TEXT NOT NULL,\n                weight REAL NOT NULL,\n                project_name TEXT NOT NULL,\n                author_name TEXT NOT NULL,\n                status TEXT,\n                obs TEXT,\n                timestamp TIMESTAMP NOT NULL,\n                PRIMARY KEY (variable_1, variable_2, scope_1, scope_2, project_name, author_name, status) ON CONFLICT REPLACE\n            );\n            '
        self.db.execute_sql(create_variable_properties_table)
        create_raw_corr_table = f'\n            CREATE TABLE IF NOT EXISTS raw_corr_table (\n                variable_1 TEXT NOT NULL,\n                variable_2 TEXT NOT NULL,\n                scope_1 TEXT NOT NULL,\n                scope_2 TEXT NOT NULL,\n                aggregation_type TEXT,\n                mode TEXT,\n                submode TEXT,\n                weight REAL NOT NULL,\n                project_name TEXT NOT NULL,\n                author_name TEXT NOT NULL,\n                delay REAL NOT NULL,\n                method TEXT NOT NULL,\n                corr_coef REAL,\n                p_value REAL,\n                status TEXT,\n                obs TEXT,\n                timestamp TIMESTAMP NOT NULL,\n                PRIMARY KEY (variable_1, variable_2, scope_1, scope_2, method, aggregation_type, mode, submode, project_name, author_name, delay, status) ON CONFLICT REPLACE\n            );\n            '
        self.db.execute_sql(create_raw_corr_table)
        create_sign_corr_table = f'\n            CREATE TABLE IF NOT EXISTS sign_corr_table (\n                variable_1 TEXT NOT NULL,\n                variable_2 TEXT NOT NULL,\n                scope_1 TEXT NOT NULL,\n                scope_2 TEXT NOT NULL,\n                aggregation_type TEXT,\n                mode TEXT,\n                submode TEXT,\n                weight REAL NOT NULL,\n                project_name TEXT NOT NULL,\n                author_name TEXT NOT NULL,\n                delay REAL NOT NULL,\n                method TEXT NOT NULL,\n                corr_coef REAL,\n                p_value REAL,\n                status TEXT,\n                obs TEXT,\n                timestamp TIMESTAMP NOT NULL,\n                PRIMARY KEY (variable_1, variable_2, scope_1, scope_2, method, aggregation_type, mode, submode, project_name, author_name, delay, status) \n            );\n            '
        self.db.execute_sql(create_sign_corr_table)
        create_variables_table = f'\n            CREATE TABLE IF NOT EXISTS variables (\n                variable_1 TEXT NOT NULL,\n                scope_1 TEXT NOT NULL,\n                variable_2 TEXT NOT NULL,\n                scope_2 TEXT NOT NULL,\n                timestamp TIMESTAMP,\n                PRIMARY KEY (variable_1, scope_1, variable_2, scope_2)\n            );\n        '
        self.db.execute_sql(create_variables_table)
        create_agg_variables_table = f'\n            CREATE TABLE IF NOT EXISTS agg_variables (\n                variable_1 TEXT NOT NULL,\n                scope_1 TEXT NOT NULL,\n                variable_2 TEXT NOT NULL,\n                scope_2 TEXT NOT NULL,\n                agg_type TEXT NOT NULL,\n                agg_mode TEXT NOT NULL,\n                len_data INTEGER,\n                agg_timestamp TIMESTAMP,\n                PRIMARY KEY (variable_1, scope_1, variable_2, scope_2, agg_type, agg_mode)\n            );\n        '
        self.db.execute_sql(create_agg_variables_table)
        create_final_results_table = f'\n            CREATE TABLE IF NOT EXISTS final_results (\n                result_name TEXT,\n                compl_info TEXT,\n                result_value TEXT,\n                rationale TEXT,\n                PRIMARY KEY (result_name)\n            );\n        '
        self.db.execute_sql(create_final_results_table)
        df_variables = self.db.to_df('variables')
        scopes = ['author_level', 'project_level']
        timestamp = datetime.now()
        for metric_1 in self.repository_metrics:
            for scope_1 in scopes:
                for metric_2 in self.adr_metrics:
                    for scope_2 in scopes:
                        if metric_1 in self.author_level_data and metric_2 in self.author_level_data or (scope_1 == 'project_level' and scope_2 == 'project_level'):
                            pass_line = 'variable_1' in df_variables.columns and 'scope_1' in df_variables.columns and ('variable_2' in df_variables.columns) and ('scope_2' in df_variables.columns) and ('timestamp' in df_variables.columns) and (len(df_variables[(df_variables['variable_1'] == metric_1) & (df_variables['scope_1'] == scope_1) & (df_variables['variable_2'] == metric_2) & (df_variables['scope_2'] == scope_2)]) != 0)
                            if not pass_line and metric_1 != metric_2 and (scope_1 == scope_2):
                                metric_data = {'variable_1': metric_1, 'scope_1': scope_1, 'variable_2': metric_2, 'scope_2': scope_2}
                                self.db.cache(metric_data, 'variables')
            self.db.save()

    def query_for_significant_correlations(self):
        table_name = 'sign_corr_table'
        self.query_to_add_column_agg_lines_and_agg_timestamp(table_name=table_name)
        query_insert_significant_correlations = "\n        INSERT INTO sign_corr_table\n        SELECT *\n        FROM raw_corr_table AS rc\n        WHERE rc.p_value <= 0.05\n        AND rc.variable_2 NOT LIKE '%cumulative_%'\n        AND rc.variable_2 NOT LIKE '%criteria_%'\n        AND rc.weight >= 50\n        AND rc.method = 'weighted_average'\n        AND rc.submode = 'global_level';\n        "
        self.db.execute_sql(query_insert_significant_correlations)

    def reset_agg_rows(self):
        print(f'RESETING AGG ROWS')
        reset_query = "\n        DELETE FROM raw_corr_table\n        WHERE aggregation_type LIKE '%agg_%';\n        "
        self.db.execute_sql(reset_query)

    def query_to_add_column_agg_lines_and_agg_timestamp(self, table_name='raw_corr_table'):
        columns_to_add = [('len_aggregated_lines', 'REAL')]
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except Exception as e:
                pass

    def query_to_add_columns_aggvariables(self, table_name='agg_variables'):
        columns_to_add = [('obs', 'TEXT'), ('len_data', 'INTEGER')]
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except Exception as e:
                pass

    def setup_variables_table_for_agg_run(self):
        self.query_to_add_columns_aggvariables()
        agg_modes = ['base_correlation', 'base_correlation', 'agg_corr_author_level_and_author_level']
        agg_types = ['base_correlation', 'base_correlation', 'agg_correlation']
        variables = self.db.to_df('variables').to_dict(orient='records')
        count = 0
        for variable in variables:
            timestamp_data = {'variable_1': variable['variable_1'], 'variable_2': variable['variable_2'], 'scope_1': variable['scope_1'], 'scope_2': variable['scope_2'], 'agg_type': agg_types[0], 'agg_mode': agg_modes[0], 'len_data': None, 'obs': None, 'agg_timestamp': None}
            self.db.cache(timestamp_data, 'agg_variables')
            timestamp_data = {'variable_1': variable['variable_1'], 'variable_2': variable['variable_2'], 'scope_1': variable['scope_1'], 'scope_2': variable['scope_2'], 'agg_type': agg_types[1], 'agg_mode': agg_modes[1], 'len_data': None, 'obs': None, 'agg_timestamp': None}
            self.db.cache(timestamp_data, 'agg_variables')
            if variable['scope_1'] == 'author_level':
                timestamp_data = {'variable_1': variable['variable_1'], 'variable_2': variable['variable_2'], 'scope_1': variable['scope_1'], 'scope_2': variable['scope_2'], 'agg_type': agg_types[2], 'agg_mode': agg_modes[2], 'len_data': None, 'obs': None, 'agg_timestamp': None}
                self.db.cache(timestamp_data, 'agg_variables')
            print(count)
            count += 1
        self.db.save()

    def get_variables_ready_to_agg(self, agg_variables_raw, variables_raw):
        variables_raw_ready = variables_raw[variables_raw['status'] == 'success']
        filter_columns = ['variable_1', 'variable_2', 'scope_1', 'scope_2']
        variables_filter = variables_raw_ready[filter_columns]
        agg_variables_ready = agg_variables_raw.merge(variables_filter, on=filter_columns, how='inner')
        return agg_variables_ready

    def calculate_agg_correlations(self, runs):
        skip_dones = False
        agg_variables_raw = self.db.to_df('agg_variables')
        variables_raw = self.db.to_df('variables')
        agg_variables_ready = self.get_variables_ready_to_agg(agg_variables_raw, variables_raw)
        print(f'Selected the variables ready for aggregation: {len(agg_variables_ready)} from a total of {len(agg_variables_raw)}')
        if skip_dones and 'agg_timestamp' in agg_variables_ready:
            agg_variables = agg_variables_ready
        else:
            agg_variables = agg_variables_ready[agg_variables_ready['obs'] != 'success'].copy()
        columns_to_group = {('author_level', 'author_level', 'base_correlation', 'base_correlation'): ['variable_1', 'scope_1', 'variable_2', 'scope_2', 'aggregation_type', 'mode', 'submode', 'delay', 'method', 'project_name'], ('project_level', 'project_level', 'base_correlation', 'base_correlation'): ['variable_1', 'scope_1', 'variable_2', 'scope_2', 'aggregation_type', 'mode', 'submode', 'delay', 'method', 'author_name'], ('author_level', 'author_level', 'agg_corr_author_level_and_author_level', 'agg_correlation'): ['variable_1', 'scope_1', 'variable_2', 'scope_2', 'aggregation_type', 'mode', 'submode', 'delay', 'method']}
        workers = 10
        futures = {}
        count = 0
        max_count = 20000000000000
        total_pbar = tqdm(total=len(agg_variables_ready), desc='total_agg')
        success_run_pbar = tqdm(total=len(agg_variables_ready), desc='success_run_agg')
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for run in runs:
                agg_variables_filtered = agg_variables[agg_variables['agg_type'] == run]
                if len(agg_variables_filtered) > 0:
                    for index, row in agg_variables_filtered.iterrows():
                        variable_1 = row['variable_1']
                        variable_2 = row['variable_2']
                        scope_1 = row['scope_1']
                        scope_2 = row['scope_2']
                        agg_type = row['agg_type']
                        agg_mode = row['agg_mode']
                        len_data = row['len_data']
                        to_group = columns_to_group[scope_1, scope_2, agg_mode, agg_type]
                        self.to_group = to_group
                        if count >= max_count:
                            count = 0
                        db_target_path = self.db_path.replace('corr_dataset.db', f'corr_dataset_piece_-_{count}.db')
                        future = executor.submit(get_agg_correlation, variable_1, variable_2, scope_1, scope_2, self.db_path, agg_type, agg_mode, self.to_group, len_data)
                        futures[future] = (variable_1, variable_2, scope_1, scope_2, self.db_path, agg_type, agg_mode, self.to_group, len_data)
                        count += 1
                for future in as_completed(futures):
                    result, timestamp_data = future.result()
                    try:
                        self.db.cache(result, 'raw_corr_table')
                        self.db.cache(timestamp_data, 'agg_variables')
                        _ = futures.pop(future)
                        total_pbar.update(1)
                        success_run_pbar.update(1)
                    except Exception as e:
                        print(f'----Error in future collection: {e}')
                        total_pbar.update(1)
                        traceback.print_exc()
                    self.db.save()
        total_pbar.close()
        success_run_pbar.close()

    def query_to_add_columns(self, table_name='raw_corr_table'):
        columns_to_add = [('variable_1_norm_Shapiro_Wilk_statistic', 'REAL DEFAULT NULL'), ('variable_1_norm_Shapiro_Wilk_p_value', 'REAL DEFAULT NULL'), ('variable_1_norm_Shapiro_Wilk_result', 'TEXT DEFAULT NULL'), ('variable_1_norm_Shapiro_Wilk_status', 'TEXT DEFAULT NULL'), ('variable_1_norm_Kolmogorov_Smirnov_statistic', 'REAL DEFAULT NULL'), ('variable_1_norm_Kolmogorov_Smirnov_p_value', 'REAL DEFAULT NULL'), ('variable_1_norm_Kolmogorov_Smirnov_result', 'TEXT DEFAULT NULL'), ('variable_1_norm_Kolmogorov_Smirnov_status', 'TEXT DEFAULT NULL'), ('variable_1_norm_Anderson_Darling_statistic', 'REAL DEFAULT NULL'), ('variable_1_norm_Anderson_Darling_critical_values', 'TEXT DEFAULT NULL'), ('variable_1_norm_Anderson_Darling_result', 'TEXT DEFAULT NULL'), ('variable_1_norm_Anderson_Darling_status', 'TEXT DEFAULT NULL'), ('variable_1_norm_D_Agostino_and_Pearson_statistic', 'REAL DEFAULT NULL'), ('variable_1_norm_D_Agostino_and_Pearson_p_value', 'REAL DEFAULT NULL'), ('variable_1_norm_D_Agostino_and_Pearson_result', 'TEXT DEFAULT NULL'), ('variable_1_norm_D_Agostino_and_Pearson_status', 'TEXT DEFAULT NULL'), ('variable_1_skewness', 'REAL DEFAULT NULL'), ('variable_1_skewness_status', 'TEXT DEFAULT NULL'), ('variable_1_kurtosis', 'REAL DEFAULT NULL'), ('variable_1_kurtosis_status', 'TEXT DEFAULT NULL'), ('variable_1_outliers_count', 'INTE DEFAULT NULLGER'), ('variable_1_outliers_status', 'TEXT DEFAULT NULL'), ('variable_2_norm_Shapiro_Wilk_statistic', 'REAL DEFAULT NULL'), ('variable_2_norm_Shapiro_Wilk_p_value', 'REAL DEFAULT NULL'), ('variable_2_norm_Shapiro_Wilk_result', 'TEXT DEFAULT NULL'), ('variable_2_norm_Shapiro_Wilk_status', 'TEXT DEFAULT NULL'), ('variable_2_norm_Kolmogorov_Smirnov_statistic', 'REAL DEFAULT NULL'), ('variable_2_norm_Kolmogorov_Smirnov_p_value', 'REAL DEFAULT NULL'), ('variable_2_norm_Kolmogorov_Smirnov_result', 'TEXT DEFAULT NULL'), ('variable_2_norm_Kolmogorov_Smirnov_status', 'TEXT DEFAULT NULL'), ('variable_2_norm_Anderson_Darling_statistic', 'REAL DEFAULT NULL'), ('variable_2_norm_Anderson_Darling_critical_values', 'TEXT DEFAULT NULL'), ('variable_2_norm_Anderson_Darling_result', 'TEXT DEFAULT NULL'), ('variable_2_norm_Anderson_Darling_status', 'TEXT DEFAULT NULL'), ('variable_2_norm_D_Agostino_and_Pearson_statistic', 'REAL DEFAULT NULL'), ('variable_2_norm_D_Agostino_and_Pearson_p_value', 'REAL DEFAULT NULL'), ('variable_2_norm_D_Agostino_and_Pearson_result', 'TEXT DEFAULT NULL'), ('variable_2_norm_D_Agostino_and_Pearson_status', 'TEXT DEFAULT NULL'), ('variable_2_skewness', 'REAL DEFAULT NULL'), ('variable_2_skewness_status', 'TEXT DEFAULT NULL'), ('variable_2_kurtosis', 'REAL DEFAULT NULL'), ('variable_2_kurtosis_status', 'TEXT DEFAULT NULL'), ('variable_2_outliers_count', 'INTEGER DEFAULT NULL'), ('variable_2_outliers_status', 'TEXT DEFAULT NULL'), ('homoscedasticity_p_value', 'REAL DEFAULT NULL')]
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except Exception as e:
                print(f'Error in adding columns {e}')

    def get_data_properties(self):
        df_variables = self.db.to_df('variables')
        source_db_path = self.source_db_path
        max_iterations = len(df_variables)
        iterations = 0
        with ProcessPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(get_single_data_properties, row, source_db_path): idx for idx, row in df_variables.iterrows()}
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    self.db.cache([result], 'variables')
                    self.db.save()
                    iterations += 1
                    print(f'Finished: {iterations} from a total of {max_iterations}')
                except Exception as e:
                    print(f'Error processing row {futures[future]}: {e}')

    def query_to_add_arb_columns(self, table_name, columns_to_add):
        for column_name, column_type in columns_to_add:
            query_to_add_columns = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};'
            try:
                self.db.execute_sql(query_to_add_columns)
            except Exception as e:
                print(f'Error in adding columns {e}')

    def calculate_base_correlations(self, variables_set, workers, delay_range=(-36, 36)):
        self.query_to_add_column_agg_lines_and_agg_timestamp()
        max_len_df = len(variables_set)
        futures = {}
        workers = workers
        reached_max = False
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for index, variables in enumerate(variables_set):
                variable_1 = variables['variable_1']
                scope_1 = variables['scope_1']
                variable_2 = variables['variable_2']
                scope_2 = variables['scope_2']
                print(f'RUN NUMBER: {index}')
                if not (scope_1 == 'global_level' or scope_2 == 'global_level'):
                    print(f'Correlation between {variable_1}, scope: {scope_1} and {variable_2}, scope: {scope_2} ')
                    future = executor.submit(get_base_correlation, variable_1, scope_1, variable_2, scope_2, delay_range, self.source_db_path)
                    futures[future] = (variable_1, scope_1, variable_2, scope_2)
            results = []
            for future in as_completed(futures):
                results, properties, timestamp_data = future.result()
                self.db.cache(results, 'raw_corr_table')
                self.db.cache(properties, 'variable_properties')
                self.db.cache(timestamp_data, 'variables')
                self.db.save()
                _ = futures.pop(future)
            self.db.save()
            return reached_max

class Worker:

    def __init__(self, variable_1, scope_1, variable_2, scope_2, delay_range):
        self.variable_1 = variable_1
        self.scope_1 = scope_1
        self.variable_2 = variable_2
        self.scope_2 = scope_2
        self.delay_range = delay_range

    def apply_delays_and_scope(self, df, metric_1_name, scope_1, metric_2_name, scope_2, delay_range):
        to_concat = []
        delay_range_list = range(delay_range[0], delay_range[1] + 1)
        for delay in delay_range_list:
            if delay == 0:
                df_base = df.copy()
                df_base['delay'] = delay
                df_base['scope_1'] = scope_1
                df_base['scope_2'] = scope_2
                to_concat.append(df_base)
            else:
                filtered_df_1 = df[['year', 'month', 'author_name', 'project_name', metric_1_name]].copy()
                filtered_df_2 = df[['year', 'month', 'author_name', 'project_name', metric_2_name]].copy()
                filtered_df_1['month'] += delay
                overflow_mask = filtered_df_1['month'] > 12
                filtered_df_1.loc[overflow_mask, 'year'] += 1
                filtered_df_1.loc[overflow_mask, 'month'] -= 12
                underflow_mask = filtered_df_1['month'] < 1
                filtered_df_1.loc[underflow_mask, 'year'] -= 1
                filtered_df_1.loc[underflow_mask, 'month'] += 12
                merged_df = filtered_df_1.merge(filtered_df_2, on=['year', 'month', 'author_name', 'project_name'], how='inner')
                merged_df = merged_df.dropna()
                merged_df['delay'] = delay
                merged_df['scope_1'] = scope_1
                merged_df['scope_2'] = scope_2
                to_concat.append(merged_df)
        output_df = pd.concat(to_concat, ignore_index=True)
        return output_df

    def corr_base_methods(self, group):
        try:
            if group.shape[0] < 8:
                return ([], [])
            grouping_columns = ['project_name', 'author_name', 'delay', 'year', 'month', 'scope_1', 'scope_2']
            variable_names = [col for col in group.columns if col not in grouping_columns]
            if len(variable_names) < 2:
                raise ValueError('Not enough metric columns found!')
            metric_1_name, metric_2_name = variable_names[:2]
            metric_1_data = group[metric_1_name]
            metric_2_data = group[metric_2_name]
            status = ['fail', 'fail']
            obs = [None, None]
            if metric_1_data.nunique() <= 1 or metric_2_data.nunique() <= 1:
                return ([], [])
            else:
                try:
                    pearson_corr, pearson_p_value = pearsonr(metric_1_data, metric_2_data)
                    status[0] = 'success'
                    obs[0] = None
                except Exception as e:
                    pearson_corr, pearson_p_value = (None, None)
                    status[0] = 'fail'
                    obs[0] = str(e)
                try:
                    spearman_corr, spearman_p_value = spearmanr(metric_1_data, metric_2_data)
                    status[1] = 'success'
                    obs[1] = None
                except Exception as e:
                    spearman_corr, spearman_p_value = (None, None)
                    status[1] = 'fail'
                    obs[1] = str(e)
            project_name = group['project_name'].iloc[0]
            author_name = group['author_name'].iloc[0]
            delay = int(group['delay'].iloc[0])
            scope_1 = group['scope_1'].iloc[0]
            scope_2 = group['scope_2'].iloc[0]
            weight = len(group)
            timestamp = datetime.now()
            result = [{'variable_1': metric_1_name, 'variable_2': metric_2_name, 'scope_1': scope_1, 'scope_2': scope_2, 'aggregation_type': 'base_correlation', 'mode': 'base_correlation', 'submode': 'base_correlation', 'weight': weight, 'project_name': project_name, 'author_name': author_name, 'delay': delay, 'method': 'pearson', 'corr_coef': pearson_corr, 'p_value': pearson_p_value, 'status': status[0], 'obs': obs[0], 'timestamp': timestamp, 'len_aggregated_lines': None}, {'variable_1': metric_1_name, 'variable_2': metric_2_name, 'scope_1': scope_1, 'scope_2': scope_2, 'aggregation_type': 'base_correlation', 'mode': 'base_correlation', 'submode': 'base_correlation', 'weight': weight, 'project_name': project_name, 'author_name': author_name, 'delay': delay, 'method': 'spearman', 'corr_coef': spearman_corr, 'p_value': spearman_p_value, 'status': status[1], 'obs': obs[1], 'timestamp': timestamp, 'len_aggregated_lines': None}]
            if delay == 0:
                normality_results_1 = self.get_data_info('variable_1', metric_1_data, delay)
                normality_results_2 = self.get_data_info('variable_2', metric_2_data, delay)
                homoscedasticity_result = self.check_homoscedasticity(metric_1_data, metric_2_data, delay)
                prop = [{'variable_1': metric_1_name, 'variable_2': metric_2_name, 'scope_1': scope_1, 'scope_2': scope_2, 'weight': weight, 'project_name': project_name, 'author_name': author_name, 'status': status[0], 'obs': obs[0], 'timestamp': timestamp, **normality_results_1, **normality_results_2, **homoscedasticity_result}, {'variable_1': metric_1_name, 'variable_2': metric_2_name, 'scope_1': scope_1, 'scope_2': scope_2, 'weight': weight, 'project_name': project_name, 'author_name': author_name, 'status': status[1], 'obs': obs[1], 'timestamp': timestamp, **normality_results_1, **normality_results_2, **homoscedasticity_result}]
            else:
                prop = []
            return (result, prop)
        except Exception as e:
            print(f'Error in grouping: {e}')
            traceback.print_exc()
            return ([], [])

    def check_homoscedasticity(self, x, y, delay):
        from statsmodels.api import add_constant, OLS
        from statsmodels.stats.diagnostic import het_breuschpagan
        try:
            if delay == 0:
                x = add_constant(x)
                model = OLS(y, x).fit()
                _, pval, _, _ = het_breuschpagan(model.resid, x)
                return {f'homoscedasticity_p_value': pval}
            else:
                return {f'homoscedasticity_p_value': None}
        except Exception as e:
            print(f'exception: {e}')
            return {f'homoscedasticity_p_value': None}

    def get_data_info(self, var_name, data, delay):
        from scipy.stats import shapiro, kstest, anderson, normaltest, skew, kurtosis, zscore
        from statsmodels.api import add_constant, OLS
        from statsmodels.stats.diagnostic import het_breuschpagan
        if delay == 0:
            results = {}
            min_sample_size = 8
            recommended_size = 20
            stat, p = shapiro(data)
            if len(data) >= min_sample_size:
                Shapiro_Wilk_status = 'success'
            else:
                Shapiro_Wilk_status = f'sample size < {min_sample_size}'
            results[f'{var_name}_norm_Shapiro_Wilk_statistic'] = stat
            results[f'{var_name}_norm_Shapiro_Wilk_p_value'] = p
            results[f'{var_name}_norm_Shapiro_Wilk_result'] = str(p > 0.05)
            results[f'{var_name}_norm_Shapiro_Wilk_status'] = Shapiro_Wilk_status
            stat, p = kstest(data, 'norm')
            if len(data) >= min_sample_size:
                Kolmogorov_Smirnov_status = 'success'
            else:
                Kolmogorov_Smirnov_status = f'sample size < {min_sample_size}'
            results[f'{var_name}_norm_Kolmogorov_Smirnov_statistic'] = stat
            results[f'{var_name}_norm_Kolmogorov_Smirnov_p_value'] = p
            results[f'{var_name}_norm_Kolmogorov_Smirnov_result'] = str(p > 0.05)
            results[f'{var_name}_norm_Kolmogorov_Smirnov_status'] = Kolmogorov_Smirnov_status
            stat = anderson(data)
            if len(data) >= min_sample_size:
                Anderson_Darling_status = 'success'
            else:
                Anderson_Darling_status = f'sample size < {min_sample_size}'
            results[f'{var_name}_norm_Anderson_Darling_statistic'] = stat.statistic
            results[f'{var_name}_norm_Anderson_Darling_critical_values'] = str(stat.critical_values)
            results[f'{var_name}_norm_Anderson_Darling_result'] = stat.statistic < stat.critical_values[2]
            results[f'{var_name}_norm_Anderson_Darling_status'] = Anderson_Darling_status
            stat, p = kstest(data, 'norm')
            if len(data) >= recommended_size:
                D_Agostino_and_Pearson_status = 'success'
            else:
                D_Agostino_and_Pearson_status = f'sample size < {min_sample_size}'
            results[f'{var_name}_norm_D_Agostino_and_Pearson_statistic'] = stat
            results[f'{var_name}_norm_D_Agostino_and_Pearson_p_value'] = p
            results[f'{var_name}_norm_D_Agostino_and_Pearson_result'] = str(p > 0.05)
            results[f'{var_name}_norm_D_Agostino_and_Pearson_status'] = D_Agostino_and_Pearson_status
            skew_result = skew(data)
            if len(data) >= min_sample_size:
                skewness_status = 'success'
            else:
                skewness_status = f'sample size < {min_sample_size}'
            results[f'{var_name}_skewness'] = skew_result
            results[f'{var_name}_skewness_status'] = skewness_status
            kurtosis_result = kurtosis(data)
            if len(data) >= recommended_size:
                kurtosis_status = 'success'
            else:
                kurtosis_status = 'kurtosistest p_value may be inaccurate with fewer than 20 observations. only n=9 observations were given.'
            results[f'{var_name}_kurtosis'] = kurtosis_result
            results[f'{var_name}_kurtosis_status'] = kurtosis_status
            z_scores = zscore(data)
            outliers = (abs(z_scores) > 3).sum()
            if len(data) >= min_sample_size:
                outliers_status = 'success'
            else:
                outliers_status = f'sample size < {min_sample_size}'
            results[f'{var_name}_outliers_count'] = outliers
            results[f'{var_name}_outliers_status'] = outliers_status
            return results
        else:
            results = {}
            results[f'{var_name}_norm_Shapiro_Wilk_statistic'] = None
            results[f'{var_name}_norm_Shapiro_Wilk_p_value'] = None
            results[f'{var_name}_norm_Shapiro_Wilk_result'] = None
            results[f'{var_name}_norm_Shapiro_Wilk_status'] = None
            results[f'{var_name}_norm_Kolmogorov_Smirnov_statistic'] = None
            results[f'{var_name}_norm_Kolmogorov_Smirnov_p_value'] = None
            results[f'{var_name}_norm_Kolmogorov_Smirnov_result'] = None
            results[f'{var_name}_norm_Kolmogorov_Smirnov_status'] = None
            results[f'{var_name}_norm_Anderson_Darling_statistic'] = None
            results[f'{var_name}_norm_Anderson_Darling_critical_values'] = None
            results[f'{var_name}_norm_Anderson_Darling_result'] = None
            results[f'{var_name}_norm_Anderson_Darling_status'] = None
            results[f'{var_name}_norm_D_Agostino_and_Pearson_statistic'] = None
            results[f'{var_name}_norm_D_Agostino_and_Pearson_p_value'] = None
            results[f'{var_name}_norm_D_Agostino_and_Pearson_result'] = None
            results[f'{var_name}_norm_D_Agostino_and_Pearson_status'] = None
            results[f'{var_name}_skewness'] = None
            results[f'{var_name}_skewness_status'] = None
            results[f'{var_name}_kurtosis'] = None
            results[f'{var_name}_kurtosis_status'] = None
            results[f'{var_name}_outliers_count'] = None
            results[f'{var_name}_outliers_status'] = None
            return results

    def calculate_correlation_base(self, df_variables_data, len_data):

        def clean_output(input_data):

            def clean_value(x):
                if np.isscalar(x):
                    return {} if pd.isna(x) or (isinstance(x, float) and x != x) else x
                return x

            def clean_dict(d):
                return {k: clean_value(v) for k, v in d.items()}
            if isinstance(input_data, pd.DataFrame):
                return input_data.map(clean_value)
            else:
                return [clean_dict(record) for record in input_data]
        try:
            tqdm.pandas()
            df_variables_ready = self.apply_delays_and_scope(df_variables_data, self.variable_1, self.scope_1, self.variable_2, self.scope_2, self.delay_range)
            grouped = df_variables_ready.groupby(['project_name', 'author_name', 'delay'])
            outputs = grouped.progress_apply(self.corr_base_methods)
            final_results = []
            final_props = []
            for output in outputs:
                result, prop = output
                if result != []:
                    final_results.append(result[0])
                    final_results.append(result[1])
                if prop != []:
                    final_props.append(prop[0])
                    final_props.append(prop[1])
            timestamp_data = {'variable_1': self.variable_1, 'variable_2': self.variable_2, 'scope_1': self.scope_1, 'scope_2': self.scope_2, 'timestamp': datetime.now(), 'len_data': len_data, 'obs': None, 'status': 'success'}
            return (final_results, final_props, timestamp_data)
        except Exception as e:
            print(f'error {e}')
            timestamp_data = {'variable_1': self.variable_1, 'variable_2': self.variable_2, 'scope_1': self.scope_1, 'scope_2': self.scope_2, 'timestamp': datetime.now(), 'len_data': len_data, 'obs': f'Exception: {e}', 'status': 'fail'}
            traceback.print_exc()
            return ([], [], timestamp_data)

def get_single_data_properties(group, source_db_path):
    variable_1 = group['variable_1']
    scope_1 = group['scope_1']
    variable_2 = group['variable_2']
    scope_2 = group['scope_2']
    df_variables_data = query_for_formated_df(variable_1, scope_1, variable_2, scope_2, source_db_path)
    data_1 = df_variables_data[variable_1]
    data_2 = df_variables_data[variable_2]
    normality_results_1 = get_any_data_info('variable_1', data_1)
    normality_results_2 = get_any_data_info('variable_2', data_2)
    homoscedasticity_result = check_any_homoscedasticity(data_1, data_2)
    timestamp_data = {'variable_1': variable_1, 'variable_2': variable_2, 'scope_1': scope_1, 'scope_2': scope_2, 'timestamp': None, **normality_results_1, **normality_results_2, **homoscedasticity_result}
    return timestamp_data

class WorkerAgg:

    def __init__(self, to_group):
        self.to_group = to_group
        pass

    def replace_modes(self, row_mode, scope_1, scope_2):
        if row_mode == 'base_correlation':
            row_mode = f'agg_corr_{scope_1}_and_{scope_2}'
        elif 'agg_corr' in row_mode:
            row_mode = row_mode.replace('agg_corr_', 'agg_agg_corr_')
        return row_mode

    def calculate_agg_corr(self, group, agg_lvl, agg_mode):
        output_dict = {col_name: [group[col_name].iloc[0], group[col_name].iloc[0]] for col_name in self.to_group}
        fisher_result = self.fisher_agg(group)
        weighted_average_result = self.weighted_average_agg(group)
        result_dicts = [fisher_result, weighted_average_result]
        for key in fisher_result.keys():
            output_dict[key] = [result[key] for result in result_dicts]
        output_df = pd.DataFrame(output_dict)
        output_df['timestamp'] = str(datetime.now())
        old_o_mode = output_df['mode'].copy()
        output_df['mode'] = output_df.apply(lambda row: self.replace_modes(row['mode'], row['scope_1'], row['scope_2']), axis=1)
        if any(old_o_mode == output_df['mode']):
            print('MODE NOT CHANGED')
        old_a_type = output_df['aggregation_type'].copy()
        output_df['aggregation_type'] = output_df['aggregation_type'].str.replace('agg_correlation', 'agg_agg_correlation').str.replace('base_correlation', 'agg_correlation')
        if any(old_a_type == output_df['aggregation_type']):
            print('AGREGATION TYPE NOT CHANGED')
        if agg_mode != 'base_correlation':
            output_df['author_name'] = 'aggregated_all_authors'
            output_df['project_name'] = 'aggregated_all_projects'
            output_df['submode'] = 'global_level'
        elif agg_lvl == 'author_level':
            output_df['author_name'] = 'aggregated_all_authors'
            output_df['submode'] = 'project_level'
        elif agg_lvl == 'project_level':
            output_df['project_name'] = 'aggregated_all_projects'
            output_df['submode'] = 'global_level'
        output = output_df.to_dict(orient='records')
        return output

    def fisher_agg(self, df_corr_raw):
        from scipy.stats import chi2
        try:
            return {'len_aggregated_lines': 0, 'weight': 0, 'method': 'fisher', 'corr_coef': 0, 'p_value': 0, 'status': 'fail', 'obs': 'Not_done'}
        except Exception as e:
            return {'len_aggregated_lines': None, 'weight': None, 'method': 'fisher', 'corr_coef': None, 'p_value': None, 'status': 'fail', 'obs': f'Exception: [{e}]'}

    def weighted_average_agg(self, df_corr_raw):
        from scipy.stats import norm
        try:
            col_corr = 'corr_coef'
            col_pval = 'p_value'
            weights = df_corr_raw['weight']
            total_weight = np.sum(weights)
            weighted_corr = np.sum(weights * df_corr_raw[col_corr]) / total_weight
            z_scores = norm.ppf(1 - df_corr_raw[col_pval])
            weighted_z = np.sum(weights * z_scores) / np.sqrt(np.sum(weights ** 2))
            agg_p_value = 1 - norm.cdf(weighted_z)
            return {'len_aggregated_lines': len(df_corr_raw), 'weight': total_weight, 'method': 'weighted_average', 'corr_coef': weighted_corr, 'p_value': agg_p_value, 'status': 'success', 'obs': None}
        except Exception as e:
            return {'len_aggregated_lines': None, 'weight': None, 'method': 'weighted_average', 'corr_coef': None, 'p_value': None, 'status': 'fail', 'obs': f'Exception: [{e}]'}

def check_any_homoscedasticity(x, y):
    from statsmodels.api import add_constant, OLS
    from statsmodels.stats.diagnostic import het_breuschpagan
    try:
        x = add_constant(x)
        model = OLS(y, x).fit()
        _, pval, _, _ = het_breuschpagan(model.resid, x)
        return {f'homoscedasticity_p_value': pval}
    except Exception as e:
        print(f'exception: {e}')
        return {f'homoscedasticity_p_value': None}

def get_any_data_info(var_name, data):
    from scipy.stats import shapiro, kstest, anderson, normaltest, skew, kurtosis, zscore
    from statsmodels.api import add_constant, OLS
    from statsmodels.stats.diagnostic import het_breuschpagan
    results = {}
    min_sample_size = 8
    recommended_size = 20
    stat, p = shapiro(data)
    if len(data) >= min_sample_size:
        Shapiro_Wilk_status = 'success'
    else:
        Shapiro_Wilk_status = f'sample size < {min_sample_size}'
    results[f'{var_name}_norm_Shapiro_Wilk_statistic'] = stat
    results[f'{var_name}_norm_Shapiro_Wilk_p_value'] = p
    results[f'{var_name}_norm_Shapiro_Wilk_result'] = str(p > 0.05)
    results[f'{var_name}_norm_Shapiro_Wilk_status'] = Shapiro_Wilk_status
    stat, p = kstest(data, 'norm')
    if len(data) >= min_sample_size:
        Kolmogorov_Smirnov_status = 'success'
    else:
        Kolmogorov_Smirnov_status = f'sample size < {min_sample_size}'
    results[f'{var_name}_norm_Kolmogorov_Smirnov_statistic'] = stat
    results[f'{var_name}_norm_Kolmogorov_Smirnov_p_value'] = p
    results[f'{var_name}_norm_Kolmogorov_Smirnov_result'] = str(p > 0.05)
    results[f'{var_name}_norm_Kolmogorov_Smirnov_status'] = Kolmogorov_Smirnov_status
    stat = anderson(data)
    if len(data) >= min_sample_size:
        Anderson_Darling_status = 'success'
    else:
        Anderson_Darling_status = f'sample size < {min_sample_size}'
    results[f'{var_name}_norm_Anderson_Darling_statistic'] = stat.statistic
    results[f'{var_name}_norm_Anderson_Darling_critical_values'] = str(stat.critical_values)
    results[f'{var_name}_norm_Anderson_Darling_result'] = stat.statistic < stat.critical_values[2]
    results[f'{var_name}_norm_Anderson_Darling_status'] = Anderson_Darling_status
    stat, p = kstest(data, 'norm')
    if len(data) >= recommended_size:
        D_Agostino_and_Pearson_status = 'success'
    else:
        D_Agostino_and_Pearson_status = f'sample size < {min_sample_size}'
    results[f'{var_name}_norm_D_Agostino_and_Pearson_statistic'] = stat
    results[f'{var_name}_norm_D_Agostino_and_Pearson_p_value'] = p
    results[f'{var_name}_norm_D_Agostino_and_Pearson_result'] = str(p > 0.05)
    results[f'{var_name}_norm_D_Agostino_and_Pearson_status'] = D_Agostino_and_Pearson_status
    skew_result = skew(data)
    if len(data) >= min_sample_size:
        skewness_status = 'success'
    else:
        skewness_status = f'sample size < {min_sample_size}'
    results[f'{var_name}_skewness'] = skew_result
    results[f'{var_name}_skewness_status'] = skewness_status
    kurtosis_result = kurtosis(data)
    if len(data) >= recommended_size:
        kurtosis_status = 'success'
    else:
        kurtosis_status = 'kurtosistest p_value may be inaccurate with fewer than 20 observations. only n=9 observations were given.'
    results[f'{var_name}_kurtosis'] = kurtosis_result
    results[f'{var_name}_kurtosis_status'] = kurtosis_status
    z_scores = zscore(data)
    outliers = (abs(z_scores) > 3).sum()
    if len(data) >= min_sample_size:
        outliers_status = 'success'
    else:
        outliers_status = f'sample size < {min_sample_size}'
    results[f'{var_name}_outliers_count'] = outliers
    results[f'{var_name}_outliers_status'] = outliers_status
    return results

def query_for_corrs(variable_1, variable_2, scope_1, scope_2, db_path, aggregation_type='base_correlation', mode='base_correlation', submode='base_correlation', limit=None):
    columns_to_select = f'rct.variable_1, rct.scope_1, rct.variable_2, rct.scope_2, rct.aggregation_type, rct.mode, rct.submode, rct.weight, rct.project_name, rct.author_name, rct.delay, rct.method, rct.corr_coef, rct.p_value'
    if variable_1 == None:
        condition_variable_1 = ''
    else:
        condition_variable_1 = f'AND rct.variable_1 = "{variable_1}"'
    if variable_2 == None:
        condition_variable_2 = ''
    else:
        condition_variable_2 = f'AND rct.variable_2 = "{variable_2}"'
    if scope_1 == None:
        condition_scope_1 = ''
    else:
        condition_scope_1 = f'AND rct.scope_1 = "{scope_1}"'
    if scope_2 == None:
        condition_scope_2 = ''
    else:
        condition_scope_2 = f'AND rct.scope_2 = "{scope_2}"'
    if aggregation_type == None:
        condition_aggregation_type = ''
    else:
        condition_aggregation_type = f'AND rct.aggregation_type = "{aggregation_type}"'
    if mode == None:
        condition_mode = ''
    else:
        condition_mode = f'AND rct.mode = "{mode}"'
    if submode == None:
        condition_submode = ''
    else:
        condition_submode = f'AND rct.submode = "{submode}"'
    limit_clause = f'LIMIT {limit}' if limit else ''
    query_for_base_corrs = f'\n    SELECT {columns_to_select}\n    \n    FROM raw_corr_table AS rct\n    \n    WHERE rct.status = "success"\n        AND rct.weight > 0\n        {condition_variable_1}\n        {condition_variable_2}\n        {condition_scope_1}\n        {condition_scope_2}\n        {condition_aggregation_type}\n        {condition_mode}\n        {condition_submode}\n    {limit_clause};\n    '
    db = Database(db_path)
    columns_to_select = columns_to_select.replace('rct.', '').split(', ')
    rows = db.execute_sql(query_for_base_corrs)
    df = pd.DataFrame(rows, columns=columns_to_select)
    return df

def query_for_formated_df(variable_1, scope_1, variable_2, scope_2, source_db_path):
    source_db = Database(source_db_path)
    non_author_names = "('', 'core_developers', 'peripheral_developers', 'adr_maintainer_25', 'adr_maintainer_50', 'adr_maintainer_75', 'adr_maintainer_not')"
    if scope_1 == 'author_level':
        author_1_condition = f'NOT IN {non_author_names}'
    else:
        author_1_condition = f'IN {non_author_names}'
    if scope_2 == 'author_level':
        author_2_condition = f'NOT IN {non_author_names}'
    else:
        author_2_condition = f'IN {non_author_names}'
    query_for_formatted_df = f'\n    SELECT rm.project_name, rm.author_name, rm.year, rm.month, rm."{variable_1}", am."{variable_2}"\n    \n    FROM repo_metrics AS rm\n    \n    INNER JOIN adr_metrics AS am ON rm.project_name = am.project_name AND rm.author_name = am.author_name AND rm.year = am.year AND rm.month = am.month\n    \n    WHERE rm.author_name {author_1_condition} \n        AND am.author_name {author_2_condition}\n        ;\n    '
    rows = source_db.execute_sql(query_for_formatted_df)
    df = pd.DataFrame(rows, columns=['project_name', 'author_name', 'year', 'month', variable_1, variable_2])
    return df

def get_base_correlation(variable_1, scope_1, variable_2, scope_2, delay_range, source_db_path):
    try:
        df_variables_data = query_for_formated_df(variable_1, scope_1, variable_2, scope_2, source_db_path)
        len_data = len(df_variables_data)
        print(f'Query returned df with len {len_data}')
        if len_data > 0:
            worker = Worker(variable_1, scope_1, variable_2, scope_2, delay_range)
            final_results, final_props, timestamp_data = worker.calculate_correlation_base(df_variables_data, len_data)
        else:
            timestamp_data = {'variable_1': variable_1, 'variable_2': variable_2, 'scope_1': scope_1, 'scope_2': scope_2, 'len_data': len_data, 'agg_timestamp': datetime.now(), 'obs': f'len_data_filtered == {len_data}', 'status': f'success'}
            final_results, final_props, timestamp_data = ([], [], timestamp_data)
    except Exception as e:
        final_results = []
        final_props = []
        timestamp_data = {'variable_1': variable_1, 'variable_2': variable_2, 'scope_1': scope_1, 'scope_2': scope_2, 'len_data': len_data, 'agg_timestamp': datetime.now(), 'obs': f'0-Exception: {e}', 'status': f'fail'}
        print(f'0-Exception: {e}')
    return (final_results, final_props, timestamp_data)

def get_agg_correlation(variable_1, variable_2, scope_1, scope_2, db_path, agg_type, agg_mode, to_group, len_data):
    try:
        worker_agg = WorkerAgg(to_group)
        df_corr_data = query_for_corrs(variable_1, variable_2, scope_1, scope_2, db_path, aggregation_type=agg_type, mode=agg_mode, submode=None)
        len_data = len(df_corr_data)
        print(f'here is is agg_type: {agg_type} agg_mode: {agg_mode}, resulted in len: {len_data} for a scope {scope_1}')
        if len_data > 1:
            grouped = df_corr_data.groupby(to_group)
            results = []
            result = grouped.apply(worker_agg.calculate_agg_corr, agg_lvl=scope_1, agg_mode=agg_mode)
            for result_i in result:
                results = results + list(result_i)
            timestamp_data = {'variable_1': variable_1, 'variable_2': variable_2, 'scope_1': scope_1, 'scope_2': scope_2, 'len_data': len_data, 'agg_type': agg_type, 'agg_mode': agg_mode, 'agg_timestamp': datetime.now(), 'obs': 'success'}
        else:
            results = []
            timestamp_data = {'variable_1': variable_1, 'variable_2': variable_2, 'scope_1': scope_1, 'scope_2': scope_2, 'agg_type': agg_type, 'agg_mode': agg_mode, 'len_data': len_data, 'agg_timestamp': datetime.now(), 'obs': f'len_data_filtered == {len_data}'}
    except Exception as e:
        results = []
        timestamp_data = {'variable_1': variable_1, 'variable_2': variable_2, 'scope_1': scope_1, 'scope_2': scope_2, 'agg_type': agg_type, 'agg_mode': agg_mode, 'len_data': len_data, 'agg_timestamp': datetime.now(), 'obs': f'0-Exception: {e}'}
        print(f'0-Exception: {e}')
    return (results, timestamp_data)
