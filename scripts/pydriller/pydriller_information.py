from pydriller import Repository
from pydriller.git import Git
from pydriller.metrics.process.contributors_count import ContributorsCount
from pydriller.metrics.process.contributors_experience import ContributorsExperience
from pydriller.metrics.process.hunks_count import HunksCount
from pydriller.metrics.process.lines_count import LinesCount
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from statistics import mean
import hashlib
from tqdm import tqdm
import pandas as pd
import os
import pytz
import numpy as np
import re
import spacy
from difflib import get_close_matches
import subprocess
import shutil
from database import Database

class PydrillerExtractor:

    def __init__(self, repo_name, github_address):
        self.repo_name = repo_name
        base_repos_root = os.getenv('ADR_REPOS_ROOT', '/path/to/adr_repositories_root/')
        self.repo_dir_path = os.path.join(base_repos_root, repo_name)
        self.repo_path = os.path.join(self.repo_dir_path, self.repo_name.split('_', 1)[1] + '/')
        try:
            self.db_old_path = os.path.join(self.repo_dir_path, repo_name + '_adr_study.db')
            self.old_db = Database(self.db_old_path)
            self.table_names = self.old_db.list_tables()
            self.adr_metrics_table = [table_name for table_name in self.table_names if 'adr_metrics' in table_name]
            if len(self.adr_metrics_table) >= 1:
                self.adr_metrics_table = self.adr_metrics_table[0]
                self.old_db_dict = self.old_db.export_data(self.adr_metrics_table)
                self.old_db_dict = {element['hash']: {k: v for k, v in element.items() if k != 'hash'} for element in self.old_db_dict}
            else:
                self.adr_metrics_table = ''
                self.old_db_dict = {}
        except:
            self.adr_metrics_table = ''
            self.old_db_dict = {}
        self.github_address = github_address
        first_commit_date, last_commit_date = self._map_periods()
        self.first_commit_date = first_commit_date
        self.last_commit_date = last_commit_date

    def _map_periods(self, retries=0):
        try:
            for commit in Repository(self.github_address, clone_repo_to=self.repo_dir_path, include_remotes=True, include_refs=True).traverse_commits():
                first_date = (commit.author_date.year, commit.author_date.month)
                break
        except Exception as e:
            error_message = str(e)
            if 'git config --global --add safe.directory' in error_message and retries <= 2:
                subprocess.run(['git', 'config', '--global', '--add', 'save.directory', self.repo_dir_path])
                return self._map_periods(retries=retries + 1)
            elif 'Please make sure you have the correct access rights' in error_message or retries > 2:
                if retries <= 2:
                    if os.path.exists(self.repo_path):
                        shutil.rmtree(self.repo_path)
                    os.makedirs(self.repo_path)
                    subprocess.run(['git', 'config', '--global', '--add', 'save.directory', self.repo_dir_path])
                    return self._map_periods(retries=retries + 1)
                elif retries > 2:
                    if os.path.exists(self.repo_path):
                        subprocess.run(['rm', '-rf', self.repo_path], check=True)
                    os.makedirs(self.repo_path)
                    subprocess.run(['git', 'clone', '--all', '--remotes', self.github_address, '.'], cwd=self.repo_path, check=True)
                    subprocess.run(['git', 'config', '--global', '--add', 'save.directory', self.repo_dir_path])
                    return self._map_periods(retries=retries + 1)
                else:
                    return ('fail', 'fail')
            else:
                return ('fail', 'fail')
        for commit in Repository(self.github_address, clone_repo_to=self.repo_dir_path, include_remotes=True, include_refs=True, order='reverse').traverse_commits():
            last_date = (commit.author_date.year, commit.author_date.month)
            break
        return (first_date, last_date)

    def get_time_periods(self, initial_time, final_time):
        result = {}
        current_year = initial_time['year']
        current_month = initial_time['month']
        while current_year < final_time['year'] or (current_year == final_time['year'] and current_month <= final_time['month']):
            first_instant = datetime(current_year, current_month, 1, 0, 0, 0)
            if current_month == 12:
                next_month = datetime(current_year + 1, 1, 1, 0, 0, 0)
            else:
                next_month = datetime(current_year, current_month + 1, 1, 0, 0, 0)
            last_instant = next_month - timedelta(microseconds=1)
            result[str(current_month) + '_' + str(current_year)] = [first_instant, last_instant]
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
        return result

    def pydriller_from_times(self, initial_time, final_time):
        periods = self.get_time_periods(initial_time, final_time)
        output = {}
        for key, period in periods.items():
            initial_period_time, final_period_time = period
            empty_results = {}
            results_aggregated = self.get_info_pdr(initial_period_time, final_period_time, empty_results)
            output[key] = results_aggregated
        return output

    def get_info_pdr(self, initial_period_time, final_period_time, results_aggregated):

        def get_value(key, fallback):
            value = current_data_line.get(key) or fallback
            return None if value == 'None' else value
        df_results = pd.DataFrame()
        pydriller_results = {}
        index = 0
        for commit in Repository(self.github_address, since=initial_period_time, to=final_period_time, clone_repo_to=self.repo_dir_path, num_workers=50, include_remotes=True, include_refs=True).traverse_commits():
            commit_hash = commit.hash
            if commit_hash in self.old_db_dict:
                current_data_line = self.old_db_dict[commit_hash]
                try:
                    author_time = datetime.strptime(current_data_line['author_date'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone(timedelta(seconds=int(current_data_line['author_timezone']))))
                except Exception as e:
                    print(f'Error processing author_time: {e}. Setting as None.')
                    author_time = None
                df_results.at[index, 'hash'] = str(commit_hash)
                df_results.at[index, 'in_main_branch'] = str(commit.in_main_branch)
                df_results.at[index, 'author_name'] = current_data_line.get('author_name', '')
                df_results.at[index, 'author_email'] = current_data_line.get('author_email', '')
                df_results.at[index, 'author_time'] = author_time
                df_results.at[index, 'author_timezone'] = int(current_data_line['author_timezone']) if current_data_line.get('author_timezone') else 0
                df_results.at[index, 'branches'] = ''
                df_results.at[index, 'modf_lines'] = commit.lines
                df_results.at[index, 'modf_files'] = int(current_data_line.get('commit_number_modified_files', 0))
                df_results.at[index, 'is_merge'] = commit.merge
                value = get_value('dmm_unit_size', commit.dmm_unit_size)
                df_results.at[index, 'dmm_unit_size'] = float(value) if value is not None else None
                value = get_value('dmm_unit_complexity', commit.dmm_unit_complexity)
                df_results.at[index, 'dmm_unit_complexity'] = float(value) if value is not None else None
                value = get_value('dmm_unit_interfacing', commit.dmm_unit_interfacing)
                df_results.at[index, 'dmm_unit_interfacing'] = float(value) if value is not None else None
                index += 1
                df_results.at[index, 'hash'] = str(commit_hash)
                df_results.at[index, 'in_main_branch'] = str(commit.in_main_branch)
                df_results.at[index, 'author_name'] = ''
                df_results.at[index, 'author_email'] = ''
                df_results.at[index, 'author_time'] = author_time
                df_results.at[index, 'branches'] = '_branch_ADRS_'.join(commit.branches)
                df_results.at[index, 'modf_lines'] = commit.lines
                df_results.at[index, 'modf_files'] = int(current_data_line.get('commit_number_modified_files', 0))
                df_results.at[index, 'is_merge'] = commit.merge
                value = get_value('dmm_unit_size', commit.dmm_unit_size)
                df_results.at[index, 'dmm_unit_size'] = float(value) if value is not None else None
                value = get_value('dmm_unit_complexity', commit.dmm_unit_complexity)
                df_results.at[index, 'dmm_unit_complexity'] = float(value) if value is not None else None
                value = get_value('dmm_unit_interfacing', commit.dmm_unit_interfacing)
                df_results.at[index, 'dmm_unit_interfacing'] = float(value) if value is not None else None
                index += 1
            else:
                author_time = commit.author_date
                if author_time and author_time.tzinfo is None:
                    author_time = author_time.replace(tzinfo=timezone.utc)
                df_results.at[index, 'hash'] = str(commit_hash)
                df_results.at[index, 'in_main_branch'] = str(commit.in_main_branch)
                df_results.at[index, 'author_name'] = commit.author.name
                df_results.at[index, 'author_email'] = commit.author.email
                df_results.at[index, 'author_time'] = author_time
                df_results.at[index, 'author_timezone'] = commit.author_timezone or 0
                df_results.at[index, 'branches'] = ''
                df_results.at[index, 'modf_lines'] = commit.lines
                df_results.at[index, 'modf_files'] = commit.files
                df_results.at[index, 'is_merge'] = commit.merge
                df_results.at[index, 'dmm_unit_size'] = commit.dmm_unit_size
                df_results.at[index, 'dmm_unit_complexity'] = commit.dmm_unit_complexity
                df_results.at[index, 'dmm_unit_interfacing'] = commit.dmm_unit_interfacing
                index += 1
                df_results.at[index, 'hash'] = str(commit_hash)
                df_results.at[index, 'in_main_branch'] = str(commit.in_main_branch)
                df_results.at[index, 'author_name'] = ''
                df_results.at[index, 'author_email'] = ''
                df_results.at[index, 'author_time'] = author_time
                df_results.at[index, 'author_timezone'] = commit.author_timezone or 0
                df_results.at[index, 'branches'] = '_branch_ADRS_'.join(commit.branches)
                df_results.at[index, 'modf_lines'] = commit.lines
                df_results.at[index, 'modf_files'] = commit.files
                df_results.at[index, 'is_merge'] = commit.merge
                df_results.at[index, 'dmm_unit_size'] = commit.dmm_unit_size
                df_results.at[index, 'dmm_unit_complexity'] = commit.dmm_unit_complexity
                df_results.at[index, 'dmm_unit_interfacing'] = commit.dmm_unit_interfacing
                index += 1
        if len(df_results) == 0:
            return results_aggregated
        number_of_commits, offhours_commits, offhours_percent = self.get_commit_metrics(df_results)
        pydriller_results['number_of_commits'] = number_of_commits
        pydriller_results['offhours_commits'] = offhours_commits
        pydriller_results['offhours_percent'] = offhours_percent
        avg_mod_lines, percentile_75_lines, percentile_25_lines = self.get_modf_lines(df_results)
        pydriller_results['avg_mod_lines'] = avg_mod_lines
        pydriller_results['percentile_75_mod_lines'] = percentile_75_lines
        pydriller_results['percentile_25_mod_lines'] = percentile_25_lines
        avg_mod_files, percentile_75_files, percentile_25_files = self.get_modf_files(df_results)
        pydriller_results['avg_mod_files'] = avg_mod_files
        pydriller_results['percentile_75_mod_files'] = percentile_75_files
        pydriller_results['percentile_25_mod_files'] = percentile_25_files
        avg_dmm_unit_size, percentile_75_dmm_unit_size, percentile_25_dmm_unit_size = self.get_dmm_unit_size(df_results)
        pydriller_results['avg_dmm_unit_size'] = avg_dmm_unit_size
        pydriller_results['percentile_75_dmm_unit_size'] = percentile_75_dmm_unit_size
        pydriller_results['percentile_25_dmm_unit_size'] = percentile_25_dmm_unit_size
        avg_dmm_unit_complexity, percentile_75_dmm_unit_complexity, percentile_25_dmm_unit_complexity = self.get_dmm_unit_complexity(df_results)
        pydriller_results['avg_dmm_unit_complexity'] = avg_dmm_unit_complexity
        pydriller_results['percentile_75_dmm_unit_complexity'] = percentile_75_dmm_unit_complexity
        pydriller_results['percentile_25_dmm_unit_complexity'] = percentile_25_dmm_unit_complexity
        avg_dmm_unit_interfacing, percentile_75_dmm_unit_interfacing, percentile_25_dmm_unit_interfacing = self.get_dmm_unit_interfacing(df_results)
        pydriller_results['avg_dmm_unit_interfacing'] = avg_dmm_unit_interfacing
        pydriller_results['percentile_75_dmm_unit_interfacing'] = percentile_75_dmm_unit_interfacing
        pydriller_results['percentile_25_dmm_unit_interfacing'] = percentile_25_dmm_unit_interfacing
        pydriller_results['num_merge_commits'] = self.get_num_merge_commits(df_results)
        ref_hash, ref_branch = self.get_ref_hash_and_branch(df_results)
        pydriller_results['hash'] = {'': ref_hash}
        pydriller_results['branch'] = {'': ref_branch}
        return pydriller_results

    def get_ref_hash_and_branch(self, df_results):

        def most_frequent_element(my_list):
            if not my_list:
                return None
            return max(my_list, key=my_list.count)
        branches = []
        df_results_copy = df_results[df_results['author_name'] == ''].copy()
        for index, row in df_results_copy.iterrows():
            branches = branches + row['branches'].split('_branch_ADRS_')
        ref_branch = most_frequent_element(branches)
        df_ref_branch = df_results_copy[df_results_copy['branches'].str.contains(ref_branch, na=False)]
        if not df_ref_branch.empty:
            most_recent_row = df_ref_branch.loc[df_ref_branch['author_time'].idxmax()]
            return (most_recent_row['hash'], ref_branch)
        else:
            raise Exception('no ref hash found')

    def get_commit_metrics(self, df_results):
        df_results = df_results.copy()

        def is_off_hours(commit_datetime):
            local_hour = commit_datetime.hour
            return local_hour < 9 or local_hour > 17
        df_results['author_time'] = pd.to_datetime(df_results['author_time'], errors='coerce')

        def ensure_timezone_awareness(dt):
            if pd.isna(dt):
                return dt
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        df_results['author_time'] = df_results['author_time'].apply(ensure_timezone_awareness)
        invalid_rows = df_results[df_results['author_time'].isna()]
        df_results = df_results.dropna(subset=['author_time']).copy()
        df_results['author_timezone'] = pd.to_timedelta(df_results['author_timezone'].fillna(0).astype(int), unit='s')
        df_results['local_commit_time'] = df_results['author_time'] + df_results['author_timezone']
        df_grouped = df_results.groupby('author_name')
        number_of_commits = {}
        offhours_commits = {}
        offhours_percent = {}
        for author, group in df_grouped:
            total_commits = len(group)
            off_hours_commits = group['local_commit_time'].apply(is_off_hours).sum()
            off_hours_percent = round(off_hours_commits / total_commits * 100, 2) if total_commits > 0 else 0.0
            number_of_commits[author] = int(total_commits)
            offhours_commits[author] = int(off_hours_commits)
            offhours_percent[author] = float(off_hours_percent)
        return (number_of_commits, offhours_commits, offhours_percent)

    def get_modf_lines(self, df_results):
        df_results = df_results.copy()
        df_grouped = df_results.groupby('author_name')
        avg_mod_lines = {}
        percentile_75_lines = {}
        percentile_25_lines = {}
        for author, group in df_grouped:
            total_commits = len(group)
            if total_commits == 0:
                continue
            avg_mod_lines[author] = float(round(group['modf_lines'].mean(), 2))
            percentile_75_lines[author] = float(round(np.percentile(group['modf_lines'], 75), 2))
            percentile_25_lines[author] = float(round(np.percentile(group['modf_lines'], 25), 2))
        return (avg_mod_lines, percentile_75_lines, percentile_25_lines)

    def get_modf_files(self, df_results):
        df_results = df_results.copy()
        df_grouped = df_results.groupby('author_name')
        avg_mod_files = {}
        percentile_75_files = {}
        percentile_25_files = {}
        for author, group in df_grouped:
            total_commits = len(group)
            if total_commits == 0:
                continue
            avg_mod_files[author] = float(round(group['modf_files'].mean(), 2))
            percentile_75_files[author] = float(round(np.percentile(group['modf_files'], 75), 2))
            percentile_25_files[author] = float(round(np.percentile(group['modf_files'], 25), 2))
        return (avg_mod_files, percentile_75_files, percentile_25_files)

    def get_dmm_unit_size(self, df_results):
        df_results = df_results.copy()
        df_grouped = df_results.groupby('author_name')
        avg_dmm_unit_size = {}
        percentile_75_dmm_unit_size = {}
        percentile_25_dmm_unit_size = {}
        for author, group in df_grouped:
            valid_data = group['dmm_unit_size'].dropna()
            if valid_data.empty:
                avg_dmm_unit_size[author] = None
                percentile_75_dmm_unit_size[author] = None
                percentile_25_dmm_unit_size[author] = None
                continue
            avg_dmm_unit_size[author] = float(round(valid_data.mean(), 2))
            percentile_75_dmm_unit_size[author] = float(round(np.percentile(valid_data, 75), 2))
            percentile_25_dmm_unit_size[author] = float(round(np.percentile(valid_data, 25), 2))
        return (avg_dmm_unit_size, percentile_75_dmm_unit_size, percentile_25_dmm_unit_size)

    def get_dmm_unit_complexity(self, df_results):
        df_results = df_results.copy()
        df_grouped = df_results.groupby('author_name')
        avg_dmm_unit_complexity = {}
        percentile_75_dmm_unit_complexity = {}
        percentile_25_dmm_unit_complexity = {}
        for author, group in df_grouped:
            valid_data = group['dmm_unit_complexity'].dropna()
            if valid_data.empty:
                avg_dmm_unit_complexity[author] = None
                percentile_75_dmm_unit_complexity[author] = None
                percentile_25_dmm_unit_complexity[author] = None
                continue
            avg_dmm_unit_complexity[author] = float(round(valid_data.mean(), 2))
            percentile_75_dmm_unit_complexity[author] = float(round(np.percentile(valid_data, 75), 2))
            percentile_25_dmm_unit_complexity[author] = float(round(np.percentile(valid_data, 25), 2))
        return (avg_dmm_unit_complexity, percentile_75_dmm_unit_complexity, percentile_25_dmm_unit_complexity)

    def get_dmm_unit_interfacing(self, df_results):
        df_results = df_results.copy()
        df_grouped = df_results.groupby('author_name')
        avg_dmm_unit_interfacing = {}
        percentile_75_dmm_unit_interfacing = {}
        percentile_25_dmm_unit_interfacing = {}
        for author, group in df_grouped:
            valid_data = group['dmm_unit_interfacing'].dropna()
            if valid_data.empty:
                avg_dmm_unit_interfacing[author] = None
                percentile_75_dmm_unit_interfacing[author] = None
                percentile_25_dmm_unit_interfacing[author] = None
                continue
            avg_dmm_unit_interfacing[author] = float(round(valid_data.mean(), 2))
            percentile_75_dmm_unit_interfacing[author] = float(round(np.percentile(valid_data, 75), 2))
            percentile_25_dmm_unit_interfacing[author] = float(round(np.percentile(valid_data, 25), 2))
        return (avg_dmm_unit_interfacing, percentile_75_dmm_unit_interfacing, percentile_25_dmm_unit_interfacing)

    def get_num_merge_commits(self, df_results):
        df_results = df_results.copy()
        df_grouped = df_results.groupby('author_name')
        num_merge_commits = {}
        for author, group in df_grouped:
            total_commits = len(group)
            if total_commits == 0:
                continue
            num_merge_commits[author] = int(group['is_merge'].sum())
        return num_merge_commits

    def find_filepath_by_partial_filename(self, filename):
        matched_filepaths = set()
        for commit in Repository(self.github_address, filepath='*' + filename, clone_repo_to=self.repo_dir_path, include_remotes=True, include_refs=True, order='reverse').traverse_commits():
            for modified_file in commit.modified_files:
                if filename.lower() in modified_file.filename.lower():
                    if modified_file.new_path:
                        matched_filepaths.add(modified_file.new_path)
        return list(matched_filepaths)

    def track_adr_through_time(self, adr_filenames):
        adr_life_info = []
        possible_adr_files = {}
        adr_path_names = set()
        added_filepaths = set()
        ASE = ADRStatusExtractor()
        commits = []
        gr = Git(self.repo_path)
        if not isinstance(adr_filenames, list):
            adr_filenames = [adr_filenames]
        for adr_filename in adr_filenames:
            matched_filenames = self.find_filepath_by_partial_filename(adr_filename)
            if matched_filenames and len(matched_filenames) > 0:
                print(f'Tracking ADR modifications for: {adr_filename}')
                adr_path_names = list(adr_path_names)
                adr_path_names += matched_filenames
                adr_path_names = set(adr_path_names)
        for matched_filename in adr_path_names:
            commits_found = gr.get_commits_modified_file(matched_filename, include_deleted_files=True)
            commits += commits_found
        for c_number, commit_hash in enumerate(commits):
            commit = gr.get_commit(commit_hash)
            for modified_file in commit.modified_files:
                if modified_file.new_path in adr_path_names:
                    if modified_file.old_path is not None:
                        adr_path_names.add(modified_file.old_path)
                    adr_info = {'adr_id': commit.hash + '_adr_id_' + modified_file.filename, 'adr_name': modified_file.filename, 'project_name': self.repo_name, 'hash': commit.hash, 'adr_current_path': modified_file.new_path, 'adr_current_content': modified_file.source_code, 'adr_current_status': ASE.get_adr_status(modified_file.source_code), 'adr_file_change_type': modified_file.change_type.name, 'adr_old_path': modified_file.old_path, 'adr_old_content': modified_file.source_code_before, 'adr_old_status': ASE.get_adr_status(modified_file.source_code_before), 'timestamp': commit.author_date, 'year': commit.author_date.year, 'month': commit.author_date.month, 'author_name': commit.author.name, 'branches': '_-_'.join(commit.branches), 'points_to_hash': '', 'points_to_adr_id': '', 'is_oldest': False}
                    adr_life_info.append(adr_info)
                else:
                    possible_adr_files[modified_file.new_path] = commit_hash
        reset = True
        new_possible_adr_files = possible_adr_files
        while reset:
            reset = False
            possible_adr_files = new_possible_adr_files
            for modified_filepath, commit_hash in possible_adr_files.items():
                if modified_filepath in adr_path_names:
                    new_possible_adr_files = possible_adr_files.copy()
                    commit_hash = new_possible_adr_files.pop(modified_filepath)
                    commit = gr.get_commit(commit_hash)
                    for modified_file in commit.modified_files:
                        if modified_file.new_path == modified_filepath:
                            if modified_file.old_path is not None:
                                adr_path_names.add(modified_file.old_path)
                            reset = True
                            adr_info = {'adr_id': commit.hash + '_adr_id_' + modified_file.filename, 'adr_name': modified_file.filename, 'project_name': self.repo_name, 'hash': commit.hash, 'adr_current_path': modified_file.new_path, 'adr_current_content': modified_file.source_code, 'adr_current_status': ASE.get_adr_status(modified_file.source_code), 'adr_file_change_type': modified_file.change_type.name, 'adr_old_path': modified_file.old_path, 'adr_old_content': modified_file.source_code_before, 'adr_old_status': ASE.get_adr_status(modified_file.source_code_before), 'timestamp': commit.author_date, 'year': commit.author_date.year, 'month': commit.author_date.month, 'author_name': commit.author.name, 'branches': '_-_'.join(commit.branches), 'points_to_hash': '', 'points_to_adr_id': '', 'is_oldest': False}
                            adr_life_info.append(adr_info)
        return adr_life_info

class ADRStatusExtractor:

    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.do_close_match = False
        self.max_distance = 5
        self.adr_status_dict = {'proposed': ['proposed', 'draft', 'suggested', 'pending', 'in progress', 'under review', 'awaiting approval', 'undecided'], 'accepted': ['accepted', 'approved', 'finalized', 'confirmed', 'ratified', 'endorsed'], 'deprecated': ['deprecated', 'obsolete', 'archived', 'abandoned', 'retired', 'phased out'], 'rejected': ['rejected', 'declined', 'not approved', 'dismissed', 'disapproved'], 'superseded': ['superseded', 'replaced', 'updated', 'overridden', 'substituted'], 'implemented': ['implemented', 'executed', 'deployed', 'realized', 'put into practice'], 'under revision': ['under revision', 'being updated', 'modifying', 'revising', 'amending'], 'withdrawn': ['withdrawn', 'retracted', 'pulled back', 'rescinded', 'revoked']}
        self.context_patterns = ['status', 'state']
        self._preprocess_status_dict()
        self._preprocess_context_patterns()

    def _preprocess_text(self, text):
        doc = self.nlp(text.lower())
        tokens = [re.sub('[^a-zA-Z]', '', token.text) for token in doc if not token.is_stop]
        return ' '.join(tokens).replace('-', ' ')

    def _preprocess_status_dict(self):
        preprocessed_dict = {}
        for status, keywords in self.adr_status_dict.items():
            preprocessed_keywords = [self._preprocess_text(keyword) for keyword in keywords]
            preprocessed_dict[status] = preprocessed_keywords
        self.adr_status_dict = preprocessed_dict

    def _preprocess_context_patterns(self):
        self.context_patterns = [self._preprocess_text(pattern) for pattern in self.context_patterns]

    def _normalize_status(self, potential_status):
        for normalized_status, keywords in self.adr_status_dict.items():
            if potential_status in keywords:
                return normalized_status
        return None

    def get_distance(self, keyword, pattern, text):
        words = text.split()
        try:
            keyword_index = words.index(keyword)
            pattern_index = words.index(pattern)
            return abs(keyword_index - pattern_index)
        except ValueError:
            return float('inf')

    def get_adr_status(self, adr_content):
        if not adr_content:
            return None
        preprocessed_text = self._preprocess_text(adr_content)
        keywords_found = []
        patterns_found = []
        keywords_close_match_found = []
        patterns_close_match_found = []
        for normalized_status, keywords in self.adr_status_dict.items():
            for keyword in keywords:
                if keyword in preprocessed_text:
                    keywords_found.append((keyword, normalized_status))
        if not keywords_found and self.do_close_match:
            for threshold in range(95, 79, -5):
                for normalized_status, keywords in self.adr_status_dict.items():
                    close_matches = get_close_matches(preprocessed_text, keywords, n=1, cutoff=threshold / 100.0)
                    if close_matches:
                        keywords_found.append((close_matches[0], normalized_status))
                        break
        for pattern in self.context_patterns:
            if pattern in preprocessed_text:
                patterns_found.append(pattern)
        if not patterns_found and self.do_close_match:
            for threshold in range(95, 79, -5):
                close_matches = get_close_matches(preprocessed_text, self.context_patterns, n=1, cutoff=threshold / 100.0)
                if close_matches:
                    patterns_found.append(close_matches[0])
                    break
        best_status = None
        best_score = float('inf')
        for pattern_found in patterns_found:
            for keyword_found, normalized_status in keywords_found:
                dist = self.get_distance(keyword_found, pattern_found, preprocessed_text)
                if dist <= self.max_distance:
                    if dist < best_score:
                        best_score = dist
                        best_status = normalized_status
                    elif dist == best_score:
                        if len(keyword_found) > len(best_status or ''):
                            best_status = normalized_status
        return best_status

class ADRContentInfoExtractor:

    def __init__(self, output_format, adr_content):
        self.adr_content = adr_content
        self.output_format = output_format
        self.adr_sections = {'date': ['date', 'adr date', 'decision date', 'date created', 'date:', 'date of decision', 'recorded date', 'creation date'], 'status': ['status', 'current status', 'state', 'status:', 'adr status', 'status info', 'status of this adr', 'approval status'], 'context': ['context', 'background', 'rationale', 'problem statement', 'context:', 'background and context', 'contextual background', 'problem background', 'justification'], 'decision': ['decision', 'chosen option', 'decision made', 'selected decision', 'decision outcome', 'resolution', 'decision detail', 'final decision'], 'consequence': ['consequence', 'implication', 'impact', 'effects', 'risk', 'benefit', 'consequences of decision', 'implications of the decision', 'risks and benefits'], 'example': ['example', 'examples', 'example usage', 'sample', 'use case', 'illustration', 'example scenario', 'sample implementation'], 'options': ['options', 'considered options', 'alternatives', 'ideas', 'suggestionoptions considered', 'possible choices', 'alternative options', 'alternatives considered', 'options evaluated', 'candidate options']}
        self.adr_section_data = {k: {'found': False, 'content': '', 'length': 0, 'num_topics': 0, 'num_subsections': 0} for k in self.adr_sections.keys()}
        self.find_adr_section_data()

    def find_adr_section_data(self):
        if not any((line.strip().startswith('#') for line in self.adr_content.split('\n'))):
            return
        headers = []
        lines = self.adr_content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                header = stripped.lstrip('#').strip().lower()
                headers.append((header, i))
        for section, keywords in self.adr_sections.items():
            for header, line_num in headers:
                matches = get_close_matches(header, keywords, n=1, cutoff=0.8)
                if matches:
                    self._process_section(section, lines, line_num)
                    break

    def _process_section(self, section, lines, line_num):
        start_line = line_num + 1
        end_line = self._find_next_header_line(lines, line_num)
        content = '\n'.join(lines[start_line:end_line]).strip()
        self.adr_section_data[section].update({'found': True, 'content': content, 'length': len(content), 'num_topics': self._count_list_items(content), 'num_subsections': self._count_subsections(content)})

    def _find_next_header_line(self, lines, current_line_num):
        for i in range(current_line_num + 1, len(lines)):
            if lines[i].strip().startswith('#'):
                return i
        return len(lines)

    def _count_list_items(self, content):
        return sum((1 for line in content.split('\n') if re.match('^\\s*[-*+]', line.strip())))

    def _count_subsections(self, content):
        return sum((1 for line in content.split('\n') if line.strip().startswith('#')))

    def output_results(self):
        outputs = []
        for section_name, section_info in self.adr_section_data.items():
            if section_info['found']:
                new_output = self.output_format
                new_output['variable_name']
        return outputs
if __name__ == '__main__':
    repo_name = 'ADDC-IAAS-prototyping_adr-generation-tool'
    github_address = 'https://github.com/ADDC-IAAS-prototyping/adr-generation-tool.git'
    EP = Extractor(repo_name, github_address)
    EP.run_data_processing()
