from database import Database
from pydriller_information import PydrillerExtractor
import os
from datetime import datetime
from pandas import Timestamp
import hashlib
import asyncio
from git import Repo
from tqdm import tqdm
import re
import csv
from difflib import get_close_matches
from collections import Counter
from run_sonarqube import SonarqubeReport
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import traceback
from sqlalchemy.sql import func
from sqlalchemy import inspect, create_engine, text, column, Column, Integer, Float, String, Text, Boolean, DateTime, LargeBinary, MetaData, Table, select, bindparam, literal
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoSuchTableError, IntegrityError
from matplotlib.patches import Patch
import matplotlib.dates as mdates
import numpy as np
import math
import difflib

class Extractor(Database):

    def __init__(self, repo_name, github_address, port_number):
        self.repo_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories', repo_name)
        self.db_path = os.path.join(self.repo_path, repo_name + '_new_adr_study.db')
        super().__init__(db_local_path=self.db_path)
        self.repo_name = repo_name
        self.github_address = github_address
        self.current_step_name = None
        self.port_number = port_number
        self.metrics_output = None
        self.adr_tracking_info = None
        base_repos_root = os.getenv('ADR_REPOS_ROOT', '/path/to/adr_repositories_root/')
        self.repo_dir_path = os.path.join(base_repos_root, repo_name)
        self.snqb_exceptions = {'alphagov_smart-answers': 'long filename', 'SAP_cloud-sdk-js': 'No inputs were found in config file', 'department-of-veterans-affairs_va.gov-team': 'file too big to handle', 'raster-foundry_raster-foundry': 'ERROR Unable to parse file: file:///usr/src/raster-foundry_raster-foundry_hash_0ac326035393164dff4ad2b97597b25039ee5d34/app-server/migrations/src/main/scala/migrations/13.scala', 'inovex_elements': 'The bridge server is unresponsive', 'mozilla_nimbus-shared': 'java.lang.IllegalStateException: java.lang.IllegalStateException: Unable to read file /usr/src/mozilla_nimbus-shared_hash_fe36111813b17f3404edacf2be25a34bb2baf1a9/python/mozilla_nimbus_shared/data.json', 'psu-libraries_scholarsphere': 'No inputs were found in onfig file', 'transcom_mymove': 'file too big to handle', 'ministryofjustice_opg-digideps': 'org.sonar.plugins.php.AnalysisException: Unable to read file ministryofjustice_opg-digideps_hash_08c51161ef3531f338209b9f4f59eab282a549ad/client/bin/jp.php'}
        self.run_exceptions = {'mozilla_fxa': 'java.lang.IllegalStateException: java.lang.IllegalStateException: Unable to read file /usr/src/mozilla_fxa/data.json', 'JabRef_jabref': 'long filename', 'elastic_cloud-on-k8s': 'long filename', 'liatrio_backstage-internal': "fail to process 'ino-markdown-editor.entry.cac1b73d.js' with RecursionError - maximum recursion depth exceeded", 'inovex_elements': "fail to process 'ino-markdown-editor.entry.cac1b73d.js' with RecursionError - maximum recursion depth exceeded"}

    def run_routines(self, mode):
        self.mode = mode
        'Run through metric computations and store them in tables.'
        self.steps = [('create_metrics', 'run_xtr', self.create_metrics_table, 'nosave'), ('extract_pydriller', 'run_xtr', self.get_pydriller_information, 'nosave'), ('adr_status_change', 'run_xtr', self.get_adr_status_change_info, 'nosave'), ('adr_status_transition', 'run_xtr', self.calculate_status_transition_frequency, 'nosave'), ('adr_file_change', 'run_xtr', self.adr_file_change, 'nosave'), ('sonarqube_report', 'run_snqb', self.gather_sonarqube_report, 'nosave'), ('core_developer_status', 'run_xtr', self.core_developer_status, 'nosave'), ('export_results', 'gather_data', self.export_results, 'nosave')]
        total_steps = len(self.steps)
        self.drop_tables = False
        print(f'THIS IS REPONAME {self.repo_name}')
        if self.repo_name in self.snqb_exceptions.keys() and self.mode == 'run_snqb':
            print(f'SONARQUBE EXCEPTION: {self.repo_name}: {self.snqb_exceptions[self.repo_name]}')
            return (f'SONARQUBE EXCEPTION: {self.repo_name}: {self.snqb_exceptions[self.repo_name]} ', None, None)
        if self.repo_name in self.run_exceptions.keys() and self.mode == 'run_xtr':
            print(f'run_xtr EXCEPTION: {self.repo_name}: {self.run_exceptions[self.repo_name]}')
            return (f'run_xtr EXCEPTION: {self.repo_name}: {self.run_exceptions[self.repo_name]} ', None, None)
        self.routine_name = self.initialize_processing_steps(f'{self.repo_name}_extractor_STATUS_', total_steps, reset=False)
        print(f'mode: {self.mode}')
        for index, (step_name, mode_req, step_function, save_status_step) in enumerate(self.steps):
            if (self.get_step_status(self.routine_name, self.mode, step_name) != 'complete' or mode_req in 'test' or 'nosave' in save_status_step) and self.mode == mode_req:
                self.current_step_name = step_name
                if step_function:
                    print(f'from {self.repo_name} started step {step_name}')
                    output = step_function()
                    if output == 'success' or output is None:
                        print(f'success, on step {step_name}')
                        self.mark_step_complete(self.routine_name, self.mode, step_name)
                        self.current_step_name = None
                    else:
                        print(f'failed, returning with output {output}')
                        return ('failed', None, None)
        return ('success', self.metrics_output, self.adr_tracking_info)

    def create_metrics_table(self):
        sql_drop_metrics_table = 'DROP TABLE IF EXISTS metrics;'
        sql_create_table_query = '\n        CREATE TABLE IF NOT EXISTS metrics (  \n            project_name TEXT NOT NULL,  \n            author_name TEXT ,  \n            year TEXT NOT NULL,  \n            month TEXT NOT NULL,  \n            variable_name TEXT NOT NULL,  \n            value TEXT,  \n            PRIMARY KEY (project_name, author_name, year, month, variable_name)  \n        );'
        sql_drop_adrs_table = 'DROP TABLE IF EXISTS adr_tracking_info;'
        sql_create_adr_table_query = '\n        CREATE TABLE IF NOT EXISTS adr_tracking_info (\n            adr_id TEXT NOT NULL,\n            adr_name TEXT NOT NULL, \n            project_name TEXT NOT NULL,           \n            hash TEXT NOT NULL,                   \n            adr_current_path TEXT,       \n            adr_current_content TEXT,             \n            adr_current_status TEXT,              \n            adr_file_change_type TEXT NOT NULL,   \n            adr_old_path TEXT,                    \n            adr_old_content TEXT,                 \n            adr_old_status TEXT,                  \n            timestamp DATETIME NOT NULL,          \n            year TEXT NOT NULL,                   \n            month TEXT NOT NULL,                  \n            author_name TEXT,                     \n            branches TEXT NOT NULL,               \n            points_to_hash TEXT,   \n            points_to_adr_id TEXT,                   \n            is_oldest TEXT,                   \n            PRIMARY KEY (project_name, adr_id)      \n        );'
        with self.engine.connect() as conn:
            if self.drop_tables:
                conn.execute(text(sql_drop_metrics_table))
                conn.execute(text(sql_drop_adrs_table))
            conn.execute(text(sql_create_table_query))
            conn.execute(text(sql_create_adr_table_query))
            conn.commit()

    def get_pydriller_information(self):
        pydriller_Extractor = PydrillerExtractor(self.repo_name, self.github_address)
        first_commit_date = pydriller_Extractor.first_commit_date
        last_commit_date = pydriller_Extractor.last_commit_date
        if first_commit_date == 'fail' or last_commit_date == 'fail':
            return 'fail'
        print(first_commit_date)
        print(last_commit_date)

        def generate_year_month_pairs(first_date, last_date):
            first_year, first_month = first_date
            last_year, last_month = last_date
            current_year, current_month = (last_year, last_month)
            while (current_year, current_month) >= (first_year, first_month):
                yield (current_year, current_month)
                if current_month == 1:
                    current_year -= 1
                    current_month = 12
                else:
                    current_month -= 1
        for year, month in generate_year_month_pairs(first_commit_date, last_commit_date):
            raw_info_self_substeps = [month, year]
            step_name_monthly = self.get_steps_tag(self.current_step_name, self.mode, raw_info_self_substeps)
            if self.get_step_status(self.routine_name, self.mode, step_name_monthly) != 'complete':
                initial_time = {'year': year, 'month': month}
                final_time = {'year': year, 'month': month}
                output = None
                print(f'from {self.repo_name} started step {step_name_monthly}')
                pydr_output = pydriller_Extractor.pydriller_from_times(initial_time, final_time)
                for month_year, pydr_outputs in pydr_output.items():
                    pydr_output_month, pydr_output_year = month_year.split('_')
                    for variable_name, values_per_author in pydr_outputs.items():
                        for author_name, value in values_per_author.items():
                            if value == {}:
                                value = ''
                            to_cache = {'project_name': self.repo_name, 'author_name': author_name, 'year': pydr_output_year, 'month': pydr_output_month, 'variable_name': variable_name, 'value': str(value)}
                            self.cache(to_cache, 'metrics')
                self.save()
                if output is not None and output == 'success' or output is None:
                    self.mark_step_complete(self.routine_name, self.mode, step_name_monthly)
            elif self.get_step_status(self.routine_name, self.mode, step_name_monthly) == 'complete':
                pass
        return 'success'

    def adr_adoption_and_mod_points(self):
        source = os.path.join(os.getcwd(), 'extracted_dataset.csv')
        adr_filenames = []
        adr_status = []
        adr_templates = []
        with open(source, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for i, row in enumerate(csv_reader):
                if self.github_address == row['repositoryUrl']:
                    adr_filenames.append(str(row['path']))
                    adr_status.append(str(row['status']))
                    adr_templates.append(str(row['template']))
        return (adr_filenames, adr_status, adr_templates)

    def get_adr_status_change_info(self):
        if self.get_step_status(self.routine_name, self.mode, 'extract_pydriller') != 'complete':
            return 'not ready yet'
        pydriller_Extractor = PydrillerExtractor(self.repo_name, self.github_address)
        try:
            adr_filenames, adr_status, adr_templates = self.adr_adoption_and_mod_points()
            if not adr_filenames:
                print('No ADR filenames to process.')
                return 'fail'
            adr_filenames = list(set(adr_filenames))
            for adr_filename in adr_filenames:
                is_saved = False
                raw_info_self_substeps = [adr_filename]
                step_name_monthly = self.get_steps_tag(self.current_step_name, self.mode, raw_info_self_substeps)
                if self.get_step_status(self.routine_name, self.mode, step_name_monthly) != 'complete':
                    adr_life_info = pydriller_Extractor.track_adr_through_time(adr_filename)
                    if not adr_life_info or adr_life_info == []:
                        print('No ADR lifecycle data collected...')
                        return 'fail'
                    is_saved = self.import_data(adr_life_info, 'adr_tracking_info')
                    if is_saved:
                        self.mark_step_complete(self.routine_name, self.mode, step_name_monthly)
                        step_name_monthly = None
            adr_life_info = []
            df = self.to_df('adr_tracking_info')
            adr_life_info = df.to_dict(orient='records')
            if not adr_life_info or adr_life_info == []:
                print('No ADR lifecycle data collected.')
                return 'fail'
            self.find_adr_hierarchy(adr_life_info)
            adr_life_info = []
            df = self.to_df('adr_tracking_info')
            adr_life_info = df.to_dict(orient='records')
            if not adr_life_info or adr_life_info == []:
                print('No ADR lifecycle data collected.')
                return 'fail'
            self.add_year_month_columns(adr_life_info)
            df_outputs = self.to_df('adr_tracking_info')
            if not adr_life_info or adr_life_info == []:
                print('No ADR lifecycle data collected.')
                return 'fail'
            self.get_avg_count_adr_changes(df_outputs)
            self.get_avg_adr_len(df_outputs)
            print(f'finished')
            return 'success'
        except Exception as e:
            print(f'An error occurred: {e}')
            traceback.print_exc()
            return 'fail'

    def get_avg_adr_len(self, adr_data):

        def generate_year_month_pairs(start_ts, end_ts):
            start_year, start_month = (start_ts.year, start_ts.month)
            end_year, end_month = (end_ts.year, end_ts.month)
            pairs = []
            y, m = (start_year, start_month)
            while y < end_year or (y == end_year and m <= end_month):
                pairs.append((y, m))
                m += 1
                if m > 12:
                    m = 1
                    y += 1
            return pairs
        if adr_data.empty:
            print('No ADR data available for adr changes calculation.')
            return
        authors = list(adr_data['author_name'].unique())
        authors.append('')
        authors = list(set(authors))
        global_min_ts = adr_data['timestamp'].min()
        global_max_ts = pd.Timestamp('2024-12-01')
        metrics_to_cache = []
        for author_name in authors:
            current_adr_data = adr_data.copy()
            if author_name != '':
                author_df = current_adr_data[current_adr_data['author_name'] == author_name]
            else:
                author_df = current_adr_data
            if pd.isna(global_min_ts) or pd.isna(global_max_ts):
                continue
            year_months = generate_year_month_pairs(global_min_ts, global_max_ts)
            for year, month in year_months:
                author_subset = author_df[(author_df['year'] == str(year)) & (author_df['month'] == str(month))]
                avg_len = author_subset['adr_current_content'].str.len().mean()
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'avg_adr_len', 'value': str(avg_len)})
        for metric in metrics_to_cache:
            self.cache(metric, 'metrics')
        self.save()
        return 'success'

    def make_lists_oneline(self, adr_life_info):
        new_adr_life_info = []
        for adr_info in adr_life_info:
            adr_info_copied = adr_info.copy()
            adr_info_copied['points_to_hash'] = '_-_'.join(adr_info_copied['points_to_hash'].copy())
            adr_info_copied['points_to_adr_id'] = '_-_'.join(map(str, adr_info_copied['points_to_adr_id'].copy()))
            new_adr_life_info.append(adr_info_copied)
        return new_adr_life_info

    def find_adr_hierarchy(self, adr_life_info):
        new_adr_life_info = []
        oldest_timestamp = None
        for index_x, adr_i_x in enumerate(adr_life_info):
            adr_info_x = adr_i_x.copy()
            adr_info_x['points_to_hash'] = []
            adr_info_x['points_to_adr_id'] = []
            if adr_info_x['adr_old_content'] is None:
                adr_info_x['is_oldest'] = True
            timestamp_x = None
            if isinstance(adr_info_x['timestamp'], (Timestamp, datetime)):
                timestamp_x = adr_info_x['timestamp'].to_pydatetime() if isinstance(adr_info_x['timestamp'], Timestamp) else adr_info_x['timestamp']
            else:
                try:
                    timestamp_x = datetime.strptime(adr_info_x['timestamp'], '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    print(f"Invalid timestamp for adr_info_x: {adr_info_x['timestamp']}. Skipping...")
                    continue
            for index_y, adr_info_y in enumerate(adr_life_info):
                timestamp_y = None
                if index_x == index_y:
                    continue
                if isinstance(adr_info_y['timestamp'], (Timestamp, datetime)):
                    timestamp_y = adr_info_y['timestamp'].to_pydatetime() if isinstance(adr_info_y['timestamp'], Timestamp) else adr_info_y['timestamp']
                else:
                    try:
                        timestamp_y = datetime.strptime(adr_info_y['timestamp'], '%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        print(f"Invalid timestamp for adr_info_y: {adr_info_y['timestamp']}. Skipping...")
                        continue
                if adr_info_y['adr_old_path'] is None:
                    continue
                if adr_info_y['adr_old_content'] is None:
                    continue
                if adr_info_x['adr_current_content'] is None:
                    continue
                hash_current_content = hashlib.md5(adr_info_x['adr_current_content'].lower().strip().encode()).hexdigest()
                hash_old_content = hashlib.md5(adr_info_y['adr_old_content'].lower().strip().encode()).hexdigest()
                if adr_info_x['adr_current_path'].lower() == adr_info_y['adr_old_path'].lower() and hash_current_content == hash_old_content:
                    adr_info_x['points_to_hash'].append(adr_info_y['hash'])
                    adr_info_x['points_to_adr_id'].append(adr_info_y['adr_id'])
                elif adr_info_x['adr_current_path'].lower() != adr_info_y['adr_old_path'].lower():
                    pass
                elif hash_current_content != hash_old_content:
                    current_content = adr_info_x['adr_current_content'].lower().strip()
                    old_content = adr_info_y['adr_old_content'].lower().strip()
                    diff = difflib.unified_diff(old_content.splitlines(), current_content.splitlines(), lineterm='', fromfile='Old Content', tofile='Current Content')
            new_adr_life_info.append(adr_info_x)
        new_adr_life_info = self.make_lists_oneline(new_adr_life_info)
        is_saved = self.import_data(new_adr_life_info, 'adr_tracking_info')

    def add_year_month_columns(self, adr_life_info):
        df = pd.DataFrame(adr_life_info)
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        self.import_data(df, 'adr_tracking_info')

    def get_avg_count_adr_changes(self, adr_data):

        def generate_year_month_pairs(start_ts, end_ts):
            start_year, start_month = (start_ts.year, start_ts.month)
            end_year, end_month = (end_ts.year, end_ts.month)
            pairs = []
            y, m = (start_year, start_month)
            while y < end_year or (y == end_year and m <= end_month):
                pairs.append((y, m))
                m += 1
                if m > 12:
                    m = 1
                    y += 1
            return pairs
        if adr_data.empty:
            print('No ADR data available for adr changes calculation.')
            return
        authors = list(adr_data['author_name'].unique())
        authors.append('')
        authors = list(set(authors))
        global_min_ts = adr_data['timestamp'].min()
        global_max_ts = pd.Timestamp('2024-12-01')
        metrics_to_cache = []
        for author_name in authors:
            current_adr_data = adr_data.copy()
            if author_name != '':
                author_df = current_adr_data[current_adr_data['author_name'] == author_name]
            else:
                author_df = current_adr_data
            if pd.isna(global_min_ts) or pd.isna(global_max_ts):
                continue
            year_months = generate_year_month_pairs(global_min_ts, global_max_ts)
            for year, month in year_months:
                author_subset = author_df[(author_df['year'] == str(year)) & (author_df['month'] == str(month))]
                total_changes = len(author_subset)
                distinct_adrs = author_subset['hash'].nunique()
                avg_changes = total_changes / distinct_adrs if distinct_adrs > 0 else 0
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'total_adr_changes', 'value': str(total_changes)})
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'avg_adr_changes', 'value': str(avg_changes)})
        print(f'metrics_to_cache: {len(metrics_to_cache)}')
        for metric in metrics_to_cache:
            self.cache(metric, 'metrics')
        self.save()
        return 'success'

    def calculate_status_transition_frequency(self):

        def generate_year_month_pairs(start_ts, end_ts):
            start_year, start_month = (start_ts.year, start_ts.month)
            end_year, end_month = (end_ts.year, end_ts.month)
            pairs = []
            y, m = (start_year, start_month)
            while y < end_year or (y == end_year and m <= end_month):
                pairs.append((y, m))
                m += 1
                if m > 12:
                    m = 1
                    y += 1
            return pairs

        def determine_previous_status(row):
            if pd.isna(row['adr_old_status']) and row['adr_file_change_type'] == 'ADD':
                return 'CREATED'
            elif pd.isna(row['adr_old_status']):
                return 'NOT_FOUND'
            else:
                return row['adr_old_status']
        df_adr_data = self.to_df('adr_tracking_info')
        if df_adr_data.empty:
            print('Warning: DataFrame is empty. Cannot calculate status transitions.')
            return 'fail'
        df_adr_data['previous_status'] = df_adr_data.apply(determine_previous_status, axis=1)
        df_adr_data['transition'] = df_adr_data['previous_status'] + ' -> ' + df_adr_data['adr_current_status'].fillna('NOT_FOUND')
        transitions = df_adr_data['transition'].unique()
        authors = list(df_adr_data['author_name'].unique())
        authors.append('')
        authors = list(set(authors))
        global_min_ts = df_adr_data['timestamp'].min()
        global_max_ts = pd.Timestamp('2024-12-01')
        metrics_to_cache = []
        for author_name in authors:
            current_adr_data = df_adr_data.copy()
            if author_name != '':
                author_df = current_adr_data[current_adr_data['author_name'] == author_name]
            else:
                author_df = current_adr_data
            if pd.isna(global_min_ts) or pd.isna(global_max_ts):
                continue
            year_months = generate_year_month_pairs(global_min_ts, global_max_ts)
            for year, month in year_months:
                author_subset = author_df[(author_df['year'] == str(year)) & (author_df['month'] == str(month))]
                for transition in transitions:
                    author_sub_subset = author_subset[author_subset['transition'] == transition]
                    frequency = len(author_sub_subset)
                    metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': str(transition), 'value': str(frequency)})
        for metric in metrics_to_cache:
            self.cache(metric, 'metrics')
        self.save()
        return 'success'

    def adr_file_change(self):

        def generate_year_month_pairs(start_ts, end_ts):
            start_year, start_month = (start_ts.year, start_ts.month)
            end_year, end_month = (end_ts.year, end_ts.month)
            pairs = []
            y, m = (start_year, start_month)
            while y < end_year or (y == end_year and m <= end_month):
                pairs.append((y, m))
                m += 1
                if m > 12:
                    m = 1
                    y += 1
            return pairs
        df_adr_data = self.to_df('adr_tracking_info')
        if df_adr_data.empty:
            print('No ADR data available for adr changes calculation.')
            return
        authors = list(df_adr_data['author_name'].unique())
        authors.append('')
        authors = list(set(authors))
        global_min_ts = df_adr_data['timestamp'].min()
        global_max_ts = pd.Timestamp('2024-12-01')
        metrics_to_cache = []
        adr_file_change_types = list(df_adr_data['adr_file_change_type'].unique())
        adr_file_change_types.append('ADD')
        adr_file_change_types.append('MODIFY')
        adr_file_change_types.append('RENAME')
        adr_file_change_types.append('DELETE')
        adr_file_change_types = list(set(adr_file_change_types))
        adr_status_types = list(df_adr_data['adr_current_status'].dropna().unique())
        cumulative_counts = {author: {change_type: 0 for change_type in adr_file_change_types} for author in authors}
        cumulative_status_type_counts = {author: {adr_status_type: 0 for adr_status_type in adr_status_types} for author in authors}
        for author_name in authors:
            current_df_adr_data = df_adr_data.copy()
            if author_name != '':
                author_df = current_df_adr_data[current_df_adr_data['author_name'] == author_name]
            else:
                author_df = current_df_adr_data
            if pd.isna(global_min_ts) or pd.isna(global_max_ts):
                continue
            year_months = generate_year_month_pairs(global_min_ts, global_max_ts)
            for year, month in year_months:
                author_subset = author_df[(author_df['year'] == str(year)) & (author_df['month'] == str(month))]
                status_type_frequency_all = 0
                status_type_cumulative_frequency_all = 0
                for adr_status_type in adr_status_types:
                    status_type_current_frequency = len(author_subset[author_subset['adr_current_status'] == adr_status_type])
                    status_type_frequency_all += status_type_current_frequency
                    cumulative_status_type_counts[author_name][adr_status_type] += status_type_current_frequency
                    status_type_cumulative_frequency = cumulative_status_type_counts[author_name][adr_status_type]
                    status_type_cumulative_frequency_all += status_type_cumulative_frequency
                    metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'status_type_' + str(adr_status_type), 'value': str(status_type_current_frequency)})
                    metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': f'cumulative_status_type_{adr_status_type}', 'value': str(status_type_cumulative_frequency)})
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'status_type_ALL_STATUS', 'value': str(status_type_frequency_all)})
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': f'cumulative_status_type_ALL_STATUS', 'value': str(status_type_cumulative_frequency_all)})
                change_frequency_all = 0
                cumulative_frequency_all = 0
                for adr_file_change_type in adr_file_change_types:
                    current_frequency = len(author_subset[author_subset['adr_file_change_type'] == adr_file_change_type])
                    change_frequency_all += current_frequency
                    cumulative_counts[author_name][adr_file_change_type] += current_frequency
                    cumulative_frequency = cumulative_counts[author_name][adr_file_change_type]
                    cumulative_frequency_all += cumulative_frequency
                    metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'file_change' + str(adr_file_change_type), 'value': str(current_frequency)})
                    metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': f'cumulative_file_change{adr_file_change_type}', 'value': str(cumulative_frequency)})
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': 'file_changeALL_CHANGES', 'value': str(change_frequency_all)})
                metrics_to_cache.append({'project_name': self.repo_name, 'author_name': author_name, 'year': year, 'month': month, 'variable_name': f'cumulative_file_changeALL_CHANGES', 'value': str(cumulative_frequency_all)})
        for metric in metrics_to_cache:
            self.cache(metric, 'metrics')
        self.save()
        return 'success'

    def gather_sonarqube_report(self):
        try:
            project_set = self.gather_sonarqube_project_set()
            if len(project_set) == 0:
                return 'empty: project_set'
        except:
            raise Exception
        self.run_sonarqube_report(project_set)

    def complement_sonarqube_data(self):
        default_path = os.getenv('ADR_REPOS_ROOT', '/path/to/adr_repositories_root/')
        db_path = os.path.join(default_path, 'main_dataset.db')
        self.main_dataset_db = Database(db_path)
        filter_main = {'project_name': self.repo_name}
        df_commiter_metrics = self.main_dataset_db.to_df('commiter_metrics', filter_dict=filter_main)
        filter__ref_branch = {'variable_name': 'branch'}
        df_ref_branch = self.to_df('metrics', filter_dict=filter__ref_branch)
        for index, row in df_ref_branch.iterrows():
            project_name = row['project_name']
            branch_name = row['value']
            month = row['month']
            year = row['year']
            metric_keys = ['code_smells', 'bugs', 'vulnerabilities', 'complexity', 'cognitive_complexity', 'coverage', 'line_coverage', 'branch_coverage', 'uncovered_lines', 'duplicated_lines', 'duplicated_blocks', 'ncloc', 'lines', 'files', 'functions', 'statements', 'comment_lines', 'comment_lines_density']
            df_commiter_filtered_project_jik = df_commiter_metrics[df_commiter_metrics['project_name'] == project_name].copy()
            if len(df_commiter_filtered_project_jik) == 0:
                continue
            df_commiter_filtered_branch = df_commiter_filtered_project_jik[df_commiter_filtered_project_jik['branch'] == branch_name]
            if len(df_commiter_filtered_branch) == 0:
                continue
            df_commiter_filtered_month = df_commiter_filtered_branch[df_commiter_filtered_branch['month'] == month]
            if len(df_commiter_filtered_month) == 0:
                continue
            df_commiter_filtered_year = df_commiter_filtered_month[df_commiter_filtered_month['year'] == year]
            if len(df_commiter_filtered_year) == 0:
                continue
            df_commiter_filtered_metrics = df_commiter_filtered_year[df_commiter_filtered_year['variable_name'].isin(metric_keys)]
            if len(df_commiter_filtered_metrics) == 0:
                continue
            for index, row in df_commiter_filtered_metrics.iterrows():
                data = {'project_name': row['project_name'], 'author_name': '', 'month': row['month'], 'year': row['year'], 'variable_name': row['variable_name'], 'value': row['value']}
                self.cache(data, 'metrics')
            self.save()

    def mark_complementary_data_as_done(self):
        df_full = self.to_df('metrics')
        sonarqube_metrics = ['code_smells', 'complexity', 'cognitive_complexity', 'coverage', 'ncloc']
        for index, data_dict in df_full.iterrows():
            if data_dict['variable_name'] in sonarqube_metrics:
                year = data_dict['year']
                month = data_dict['month']
                raw_info_self_substeps = [month, year]
                substep_name = self.get_steps_tag(self.current_step_name, self.mode, raw_info_self_substeps)
                self.mark_step_complete(self.routine_name, self.mode, substep_name)

    def gather_sonarqube_project_set(self):
        project_set = []
        project_hash_included = []
        filter = {'variable_name': 'hash'}
        df = self.to_df('metrics', filter_dict=filter)
        if len(df) == 0:
            raise Exception('no reference hash values found on the current project. maybe it is not ready yet')
        for index, data_dict in df.iterrows():
            hash_ref = data_dict['value']
            year = data_dict['year']
            month = data_dict['month']
            raw_info_self_substeps = [month, year]
            substep_name = self.get_steps_tag(self.current_step_name, self.mode, raw_info_self_substeps)
            if hash_ref not in project_hash_included and self.get_step_status(self.routine_name, self.mode, substep_name) != 'complete':
                project_name = data_dict['project_name']
                project_key = project_name
                commit_hash = hash_ref
                year = data_dict['year']
                month = data_dict['month']
                project_hash_included.append(commit_hash)
                project_set.append((project_name, project_key, commit_hash, year, month))
        return project_set

    def run_sonarqube_report(self, project_set):
        db = Database(self.db_path)
        context_extractor = (self.routine_name, db, self.current_step_name, self.mode)
        sonar_report = SonarqubeReport(self.repo_name, self.repo_path, base_port=self.port_number, context_extractor=context_extractor)
        sonar_report.run_and_is_on_sonarqube()
        print(f'project_set: {project_set}')
        return asyncio.run(sonar_report.run_analysis(project_set))

    def gather_results_sonarqube_report(self, results_from_snqb):
        for results in results_from_snqb:
            for result in results:
                year = result['year']
                month = result['month']
                self.cache(result, 'metrics')
            self.save()
            raw_info_self_substeps = [month, year]
            substep_name = self.get_steps_tag(self.current_step_name, self.mode, raw_info_self_substeps)
            self.mark_step_complete(self.routine_name, self.mode, substep_name)

    def core_developer_status(self):
        if self.get_step_status(self.routine_name, self.mode, 'extract_pydriller') != 'complete':
            return 'not ready yet'
        filter_number_of_commits = {'variable_name': 'number_of_commits'}
        df_number_of_commits = self.to_df('metrics', filter_dict=filter_number_of_commits)
        filter_avg_mod_lines = {'variable_name': 'avg_mod_lines'}
        df_avg_mod_lines = self.to_df('metrics', filter_dict=filter_avg_mod_lines)
        filter_avg_mod_files = {'variable_name': 'avg_mod_files'}
        df_avg_mod_files = self.to_df('metrics', filter_dict=filter_avg_mod_files)
        for df in [df_number_of_commits, df_avg_mod_lines, df_avg_mod_files]:
            df['value'] = pd.to_numeric(df['value'], errors='raise')
            df['month'] = pd.to_numeric(df['month'], errors='raise')
            df['year'] = pd.to_numeric(df['year'], errors='raise')
        df_avg_mod_lines.rename(columns={'value': 'avg_mod_lines'}, inplace=True)
        df_avg_mod_files.rename(columns={'value': 'avg_mod_files'}, inplace=True)
        df_number_of_commits['number_of_commits'] = pd.to_numeric(df_number_of_commits['value'], errors='raise')
        df_unified = df_number_of_commits[['year', 'month', 'number_of_commits']].copy()
        df_unified = df_number_of_commits.copy()
        df_unified = df_unified.merge(df_avg_mod_lines[['year', 'month', 'avg_mod_lines']], on=['year', 'month'], how='outer')
        df_unified = df_unified.merge(df_avg_mod_files[['year', 'month', 'avg_mod_files']], on=['year', 'month'], how='outer')
        if df_unified.isnull().any(axis=1).any():
            missing_rows = df_unified[df_unified.isnull().any(axis=1)]
            raise ValueError(f'There are mismatched rows where not all DataFrames have data for the same year/month:\n{missing_rows}')
        processed_groups = []
        df_unified['cum_number_of_commits'] = 0
        df_unified['cum_number_mod_lines'] = 0
        df_unified['cum_number_mod_files'] = 0
        df_unified['is_core_dev_number_of_commits'] = None
        df_unified['is_core_dev_number_mod_lines'] = None
        df_unified['is_core_dev_number_mod_files'] = None
        groups_by_author = df_unified.groupby('author_name')
        for author_name, df_grouped in groups_by_author:
            df_grouped.sort_values(by=['year', 'month'], ascending=[True, True], inplace=True)
            df_grouped.reset_index(drop=True, inplace=True)
            cum_number_of_commits = 0
            cum_number_mod_lines = 0
            cum_number_mod_files = 0
            for index, row in df_grouped.iterrows():
                number_of_commits = int(row['number_of_commits']) if not pd.isna(row['number_of_commits']) else 0
                avg_mod_lines = int(row['avg_mod_lines']) if not pd.isna(row['avg_mod_lines']) else 0
                avg_mod_files = int(row['avg_mod_files']) if not pd.isna(row['avg_mod_files']) else 0
                cum_number_of_commits += number_of_commits
                cum_number_mod_lines += number_of_commits * avg_mod_lines
                cum_number_mod_files += number_of_commits * avg_mod_files
                df_grouped.at[index, 'cum_number_of_commits'] = cum_number_of_commits
                df_grouped.at[index, 'cum_number_mod_lines'] = cum_number_mod_lines
                df_grouped.at[index, 'cum_number_mod_files'] = cum_number_mod_files
            processed_groups.append(df_grouped)
        df_combined = pd.concat(processed_groups, ignore_index=True)
        df_combined.sort_values(by=['year', 'month'], ascending=[True, True], inplace=True)
        grouped_by_year_month = df_combined.groupby(['year', 'month'], as_index=False)
        for (year, month), df_grouped in grouped_by_year_month:
            df_grouped['threshold_to_be_core'] = None
            number_of_authors = len([author for author in df_grouped['author_name'] if author.replace(' ', '') != ''])
            number_of_core_devs_month = math.ceil(number_of_authors * 0.2)
            if number_of_core_devs_month < 1:
                number_of_core_devs_month = 1
            valid_authors = df_grouped[df_grouped['author_name'].str.strip() != ''].copy()
            valid_authors['is_core_dev_number_of_commits'] = False
            valid_authors['is_core_dev_number_mod_lines'] = False
            valid_authors['is_core_dev_number_mod_files'] = False
            top_commits = valid_authors.nlargest(number_of_core_devs_month, 'cum_number_of_commits', 'all')
            top_mod_lines = valid_authors.nlargest(number_of_core_devs_month, 'cum_number_mod_lines', 'all')
            top_mod_files = valid_authors.nlargest(number_of_core_devs_month, 'cum_number_mod_files', 'all')
            valid_authors.loc[top_commits.index, 'is_core_dev_number_of_commits'] = True
            valid_authors.loc[top_mod_lines.index, 'is_core_dev_number_mod_lines'] = True
            valid_authors.loc[top_mod_files.index, 'is_core_dev_number_mod_files'] = True
            df_grouped.update(valid_authors)
            for index, row in df_grouped.iterrows():
                self.cache({'project_name': row['project_name'], 'author_name': row['author_name'], 'year': row['year'], 'month': row['month'], 'variable_name': 'core developer criteria author_commits', 'value': bool(row['is_core_dev_number_of_commits'])}, 'metrics')
                self.cache({'project_name': row['project_name'], 'author_name': row['author_name'], 'year': row['year'], 'month': row['month'], 'variable_name': 'core developer criteria author_lines', 'value': bool(row['is_core_dev_number_mod_lines'])}, 'metrics')
                self.cache({'project_name': row['project_name'], 'author_name': row['author_name'], 'year': row['year'], 'month': row['month'], 'variable_name': 'core developer criteria author_files', 'value': bool(row['is_core_dev_number_mod_files'])}, 'metrics')
        self.save()

    def _preprocess_dataframe(self, df):
        df = df.copy()
        for col in ['month', 'year']:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except Exception as e:
                    print(f'Warning: Could not convert column {col} to numeric. Error: {e}')
        existing_cols = [col for col in ['month', 'year'] if col in df.columns]
        if existing_cols:
            df = df.dropna(subset=existing_cols)
        return df

    def export_results(self):
        df_metrics = self.to_df('metrics')
        df_metrics = self._preprocess_dataframe(df_metrics)
        df_adr_tracking_info = self.to_df('adr_tracking_info')
        df_adr_tracking_info = self._preprocess_dataframe(df_adr_tracking_info)
        self.metrics_output = df_metrics
        self.adr_tracking_info = df_adr_tracking_info
        return 'success'
if __name__ == '__main__':
    repo_name = 'ADDC-IAAS-prototyping_adr-generation-tool'
    github_address = 'https://github.com/ADDC-IAAS-prototyping/adr-generation-tool.git'
    EP = Extractor(repo_name, github_address)
    EP.run_data_processing()
