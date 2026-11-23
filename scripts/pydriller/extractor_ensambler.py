import os
import json
import csv
import asyncio
import shutil
from tqdm import trange, tqdm
import sqlite3
import git
import sys
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor, TimeoutError
from database import Database
from extractor import Extractor
from run_sonarqube import SonarqubeReport
import pandas as pd
import traceback
import openpyxl
import time
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, PrimaryKeyConstraint, case, delete
from sqlalchemy.sql import select, func, text
from scipy.stats import pearsonr, spearmanr
import pandas as pd
sys.setrecursionlimit(2000)

class ExtractorEnsambler:

    def __init__(self, limit=None):
        base_repos_root = os.getenv('ADR_REPOS_ROOT', '/path/to/adr_repositories_root/')
        self.default_path = os.path.join(base_repos_root)
        self.db_path = os.path.join(self.default_path, 'main_dataset.db')
        self.main_dataset_db = Database(self.db_path)
        self.repo_names_and_info = self.grab_paths_from_source(limit)
        self.projects = None
        self.dynamic_commands_path = os.path.join(os.getcwd(), 'commands.md')

    def sync_db_status(self):
        local_db = Database(self.db_path)
        remote_db = Database()

    def cleanup_empty_db_files(self):
        self.cleanup_journal_files()
        threshold_size = 10 * 1024
        base_path = os.getenv('ADR_REPOS_ROOT', '/path/to/adr_repositories_root/')
        for dirpath, dirnames, filenames in os.walk(base_path):
            for filename in filenames:
                if filename.endswith('.db'):
                    filepath = os.path.join(dirpath, filename)
                    file_size = os.path.getsize(filepath)
                    if file_size < threshold_size:
                        os.remove(filepath)
                        print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')

    def cleanup_empty_git_lock(self):
        threshold_size = 1 * 1
        base_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        for dirpath, dirnames, filenames in os.walk(base_path):
            for filename in filenames:
                if '.lock' in filename:
                    filepath = os.path.join(dirpath, filename)
                    file_size = os.path.getsize(filepath)
                    os.remove(filepath)
                    print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')

    def cleanup_md_files(self):
        threshold_size = 1 * 1024
        base_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        for dirname in os.listdir(base_path):
            if os.path.isdir(os.path.join(base_path, dirname)):
                for second_dirname in os.listdir(os.path.join(base_path, dirname)):
                    if second_dirname.endswith('.md'):
                        filepath = os.path.join(base_path, dirname, second_dirname)
                        file_size = os.path.getsize(filepath)
                        if file_size < threshold_size:
                            os.remove(filepath)
                            print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')
            elif dirname.endswith('.md'):
                filepath = os.path.join(base_path, dirname)
                file_size = os.path.getsize(filepath)
                if file_size < threshold_size:
                    os.remove(filepath)
                    print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')

    def cleanup_nuke_local(self):
        threshold_size = 1 * 1024
        base_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        for dirname in os.listdir(base_path):
            if os.path.isdir(os.path.join(base_path, dirname)):
                for second_dirname in os.listdir(os.path.join(base_path, dirname)):
                    filepath = os.path.join(base_path, dirname, second_dirname)
                    file_size = os.path.getsize(filepath)
                    try:
                        shutil.rmtree(filepath)
                    except:
                        os.remove(filepath)
                    print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')
            else:
                filepath = os.path.join(base_path, dirname)
                file_size = os.path.getsize(filepath)
                os.remove(filepath)
                print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')

    def cleanup_journal_files(self):
        threshold_size = 100000
        base_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        for dirname in os.listdir(base_path):
            if os.path.isdir(os.path.join(base_path, dirname)):
                for second_dirname in os.listdir(os.path.join(base_path, dirname)):
                    if second_dirname.endswith('.db_journal'):
                        filepath = os.path.join(base_path, dirname, second_dirname)
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        print(f'Deleted {filepath} (Size: {file_size / 1024:.2f} KB)')

    async def _async_copy_and_delete(self, db_local_path, hardcoded_path, second_dirname):
        loop = asyncio.get_event_loop()
        try:
            os.makedirs(os.path.dirname(hardcoded_path), exist_ok=True)
            if os.path.exists(hardcoded_path) and os.path.getsize(db_local_path) == os.path.getsize(hardcoded_path) or '_hash_' in second_dirname:
                if os.path.isdir(db_local_path):
                    await loop.run_in_executor(None, shutil.rmtree, db_local_path)
            else:
                print(f'File integrity check failed for: {db_local_path}')
        except Exception as e:
            print(f'Error processing {db_local_path}: {e}')

    async def _process_db_files(self, mode, workers=500):
        base_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        prefix = os.getenv('ADR_STUDY_BACKUP_ROOT', '/path/to/research_root')
        tasks = []
        limit = 300
        current = 0
        with ThreadPoolExecutor(workers) as executor:
            for dirname in os.listdir(base_path):
                dir_path = os.path.join(base_path, dirname)
                if current > limit:
                    break
                if os.path.isdir(dir_path):
                    for second_dirname in os.listdir(dir_path):
                        if mode == 'hard':
                            if '_hash_' in second_dirname:
                                db_local_path = os.path.join(dir_path, second_dirname)
                                projects_root = os.getenv('ADR_STUDY_PROJECTS_ROOT', '/path/to/projects_root')
                                relative_path = os.path.relpath(db_local_path, start=projects_root)
                                hardcoded_path = os.path.join(prefix, relative_path)
                                tasks.append(self._async_copy_and_delete(db_local_path, hardcoded_path, second_dirname))
                                if len(tasks) >= workers:
                                    await asyncio.gather(*tasks)
                                    tasks.clear()
                                current += 1
            if tasks:
                await asyncio.gather(*tasks)

    def cleanup_db_files(self, mode):
        asyncio.run(self._process_db_files(mode))

    def grab_paths_from_source(self, limit, test='', instruction=None, source=os.path.join(os.getcwd(), 'extracted_dataset.csv')):
        values = []
        selected = set()
        add_last = []
        done_files = []
        eliminated = 0
        eliminated_redundant = 0
        string_to_select = 'select' if test != 'test' else 'test'
        with open(source, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for i, row in enumerate(csv_reader):
                if limit is not None and len(values) >= limit:
                    print(f'Warning: limit != None. limit: {limit}')
                    break
                select = row['select']
                github_address = row['repositoryUrl']
                target_repo_path = row['repositoryUrl'].split('github.com/')[1].split('.git')[0].replace('/', '_')
                if not ('github.com/' in row['repositoryUrl'] and '.git' in row['repositoryUrl']):
                    raise Exception(f'Irregular github address: {github_address}')
                if target_repo_path in selected:
                    eliminated_redundant += 1
                    continue
                if target_repo_path in done_files:
                    eliminated += 1
                    continue
                if select != string_to_select:
                    continue
                values.append((target_repo_path, github_address))
                selected.add(target_repo_path)
        values.extend(add_last)
        return values

    def create_tables(self):
        create_metric_table = f'\n            CREATE TABLE IF NOT EXISTS metrics (  \n            project_name TEXT NOT NULL,  \n            author_name TEXT ,  \n            year NUMERIC NOT NULL,  \n            month NUMERIC NOT NULL,  \n            variable_name TEXT NOT NULL,  \n            value TEXT,  \n            PRIMARY KEY (project_name, author_name, year, month, variable_name)  \n        );\n        '
        self.main_dataset_db.execute_sql(create_metric_table)
        create_adr_tracking_table = f'\n        CREATE TABLE IF NOT EXISTS adr_tracking_info (\n            adr_id TEXT NOT NULL,\n            adr_name TEXT NOT NULL, \n            project_name TEXT NOT NULL,           \n            hash TEXT NOT NULL,                   \n            adr_current_path TEXT,       \n            adr_current_content TEXT,             \n            adr_current_status TEXT,              \n            adr_file_change_type TEXT NOT NULL,   \n            adr_old_path TEXT,                    \n            adr_old_content TEXT,                 \n            adr_old_status TEXT,                  \n            timestamp DATETIME NOT NULL,          \n            year NUMERIC NOT NULL,                   \n            month NUMERIC NOT NULL,                  \n            author_name TEXT,                     \n            branches TEXT NOT NULL,               \n            points_to_hash TEXT,   \n            points_to_adr_id TEXT,                   \n            is_oldest TEXT,                   \n            PRIMARY KEY (project_name, adr_id)      \n        )\n        '
        self.main_dataset_db.execute_sql(create_adr_tracking_table)

    def rename_instruction(self, instruction):
        if instruction == 'run_random':
            return 'run_xtr'
        if instruction == 'run':
            return 'run_xtr'
        print(f'Warning: instruction not renamed {instruction}')
        return instruction

    def extract_pydriller_data_from_projects(self, instruction, first_repo_included=None, last_repo_included=None, workers=1, timeout=4000):
        repos_to_do = self.repo_names_and_info[first_repo_included:last_repo_included]
        if instruction == 'run_random':
            random.shuffle(repos_to_do)
        instruction = self.rename_instruction(instruction)
        total_repos = len(repos_to_do)
        progress_bar_done = tqdm(total=total_repos, desc='Repos done', position=0, unit='repo')
        progress_bar_succeeded = tqdm(total=total_repos, desc='Repos succeeded', position=1, unit='repo')
        futures = {}
        port_numbers = list(range(9000, total_repos + 9000))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for (repo_name, github_address), port_number in zip(repos_to_do, port_numbers):
                future = executor.submit(self.run_extractor, instruction, repo_name, github_address, port_number)
                futures[future] = (repo_name, github_address, port_number)
            for future in as_completed(futures):
                outcome, df_outcome, df_adr_tracking_info = future.result()
                if outcome == 'success':
                    print(f'outcome = {outcome}')
                    progress_bar_done.update(1)
                    progress_bar_succeeded.update(1)
                    if df_adr_tracking_info is not None:
                        dictlist_adr_tracking_info = df_adr_tracking_info.to_dict(orient='records')
                        self.create_tables()
                        for dict_content in dictlist_adr_tracking_info:
                            self.main_dataset_db.cache(dict_content, 'adr_tracking_info')
                    if df_outcome is not None:
                        for index, row in df_outcome.iterrows():
                            aggregate_metric_data = {'project_name': row['project_name'], 'author_name': row['author_name'], 'year': row['year'], 'month': row['month'], 'variable_name': row['variable_name'], 'value': row['value']}
                            self.main_dataset_db.cache(aggregate_metric_data, 'metrics')
                else:
                    print(f'outcome = fail')
                    progress_bar_done.update(1)
                self.main_dataset_db.save()
        self.main_dataset_db.save()
        progress_bar_done.close()
        progress_bar_succeeded.close()

    def run_extractor(self, instruction, repo_name, github_address, port_number):
        try:
            extractor = Extractor(repo_name, github_address, port_number)
            outcome_status, df_outcome_value, df_adr_tracking_info = extractor.run_routines(instruction)
            if df_outcome_value is not None:
                print(f'CAPTURING OUTCOME')
                print(f'this is the current outcome {len(df_outcome_value)}')
            return (outcome_status, df_outcome_value, df_adr_tracking_info)
        except git.exc.GitCommandError as e:
            print(f'Error processing repository {repo_name}: {e}')
            return ('failed', None, None)
        except Exception as e:
            print(f'Error in thread execution: {e}, from task: {repo_name}')
            traceback.print_exc()
            return ('failed', None, None)

    def get_db_paths(self):
        base_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        db_paths = []
        for dirname in os.listdir(base_path):
            if os.path.isdir(os.path.join(base_path, dirname)):
                for second_dirname in os.listdir(os.path.join(base_path, dirname)):
                    if second_dirname.endswith('_adr_study.db'):
                        filepath = os.path.join(base_path, dirname, second_dirname)
                        db_paths.append(filepath)
        return db_paths

    def import_metric_tables(self):
        db_paths = self.get_db_paths()
        print(f'importing_metric_tables')
        data_commiter = []
        data_author = []
        data_stored = 0
        data_stored_max = 1000
        table_comm = 'commiter_metrics'
        table_auth = 'developer_metrics'
        hashlines_done = set()
        new_data = False
        for db_path in db_paths:
            db = Database(db_path)
            try:
                try:
                    current_data_commiter = db.export_data(table_comm)
                except:
                    print(f'inexistent table {table_comm}')
                try:
                    current_data_author = db.export_data(table_auth)
                except:
                    print(f'inexistent table {table_auth}')
                if current_data_commiter:
                    current_data_commiter_to_add = [data for data in self.get_hashlines(current_data_commiter) if data['hashline'] not in hashlines_done]
                    if len(current_data_commiter_to_add) > 0:
                        data_commiter += current_data_commiter_to_add
                        data_stored += 1
                if current_data_author:
                    current_data_author_to_add = [data for data in self.get_hashlines(current_data_author) if data['hashline'] not in hashlines_done]
                    if len(current_data_author_to_add) > 0:
                        data_author += current_data_author_to_add
                        data_stored += 1
                if data_stored >= data_stored_max:
                    print(f'importing data: {len(data_commiter)}-{data_author}')
                    self.main_dataset_db.import_data(data_commiter, table_comm)
                    self.main_dataset_db.save()
                    data_commiter = []
                    self.main_dataset_db.import_data(data_author, table_auth)
                    self.main_dataset_db.save()
                    data_author = []
                    data_stored = 0
                    new_data = True
                    print(f'got new data')
            except Exception as e:
                error_message = str(e)
                print(f'This project {db_path}, in table {(table_comm, table_auth)} encountered an error: {error_message}')
                if "'branch'" in error_message:
                    tables_to_drop = [table for table in db.list_tables() if 'status' in table.lower() and 'adr_metrics' not in table.lower() or table.lower() in ['commiter_metrics', 'developer_metrics']]
                    try:
                        for table in tables_to_drop:
                            db.drop_table(table)
                            print(f'Dropped table: {table}')
                    except Exception as e:
                        print(f"Table '{table}' excepts: {e}")
        if len(data_commiter) > 0 or len(data_author) > 0:
            new_data = True
            self.main_dataset_db.import_data(data_commiter, table_comm)
            self.main_dataset_db.save()
            self.main_dataset_db.import_data(data_author, table_auth)
            self.main_dataset_db.save()
            print('final importing data')
            print(f'got new data')
        return new_data

def main():
    if len(sys.argv) < 2:
        print('Please provide instructions.\nInstructions:\n\nextract_pydriller_data\nprocess_pydriller_datan\nrun_all [num_workers]')
        print(f'tip: try the command   docker run --rm -it $(docker build -q .)')
        sys.exit(1)
    EE = ExtractorEnsambler(limit=None)
    instruction = sys.argv[1]
    if len(sys.argv) == 5:
        first_repo_included = int(sys.argv[2])
        last_repo_included = int(sys.argv[3])
        sim_workers = int(sys.argv[4])
    else:
        first_repo_included = 0
        last_repo_included = 1000
    if instruction == 'clean':
        EE.cleanup_db_files('soft')
        EE.cleanup_empty_git_lock()
        EE.cleanup_empty_db_files()
        EE.cleanup_journal_files()
    elif instruction == 'clean_hard':
        EE.cleanup_db_files('hard')
        EE.cleanup_md_files()
    elif instruction == 'gather_data':
        EE.extract_pydriller_data_from_projects(instruction=instruction, first_repo_included=first_repo_included, last_repo_included=last_repo_included, workers=sim_workers)
    elif instruction == 'run' or instruction == 'run_random':
        EE.extract_pydriller_data_from_projects(instruction=instruction, first_repo_included=first_repo_included, last_repo_included=last_repo_included, workers=sim_workers)
    elif instruction == 'run_test':
        instruction == 'test'
        EE.extract_pydriller_data_from_projects(instruction=instruction, first_repo_included=first_repo_included, last_repo_included=last_repo_included, workers=sim_workers)
    elif instruction == 'run_snqb':
        EE.extract_pydriller_data_from_projects(instruction=instruction, first_repo_included=first_repo_included, last_repo_included=last_repo_included, workers=sim_workers)
    elif instruction == 'return_snqb_data':
        EE.return_snqb_data()
    else:
        print(f'Unknown instruction: {instruction}.\nPlease provide instructions.\nInstructions:\n\nextract_pydriller_data\nprocess_pydriller_datan\nrun_all [num_workers]')
        print('tip: adjust docker volume mounts so that your repository dataset directory is available at /app/datasets/project_repositories inside the container')

def suppress_output(enabled=True):
    if enabled:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    else:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
if __name__ == '__main__':
    main()
