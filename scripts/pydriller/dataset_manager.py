import os
import json
import csv
import threading
import concurrent.futures
from git import Repo

class DatasetManager:

    def __init__(self):
        self.directory = ''
        self.target_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        self.file_format = ''
        self.adr_data = []

    def extract(self):
        files = [f for f in os.listdir(self.directory) if f.endswith(self.file_format)]
        for json_file in files:
            self.process_file(os.path.join(self.directory, json_file))

    def process_file(self, filepath):
        pass

    def get_data(self):
        return self.adr_data

    def print_data(self):
        for adr_instance in self.adr_data:
            print(json.dumps(adr_instance, indent=2))

    def save_data_to_csv(self):
        if not self.adr_data:
            print('No data to save.')
            return
        csv_file_path = os.path.join(self.directory, 'extracted_dataset.csv')
        try:
            keys = self.adr_data[0].keys()
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.adr_data)
            print(f'Data successfully saved to {csv_file_path}')
        except Exception as e:
            print(f'Error saving data to CSV: {e}')

class AdrStudyDM(DatasetManager):

    def __init__(self):
        super().__init__()
        self.directory = os.path.join(os.getcwd(), 'datasets', 'ADR-Study-Dataset-main', 'repositories')
        self.file_format = '.json'
        self.lock = threading.Lock()
        self.repo_cache = {}

    def extract(self):
        files = [f for f in os.listdir(self.directory) if f.endswith(self.file_format)]
        for json_file in files:
            self.process_file_metadata(os.path.join(self.directory, json_file))
        repo_groups = self.group_by_repo(self.adr_data)
        max_workers = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.clone_repo_thread, repo_url) for repo_url in repo_groups.keys()]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        for repo_url in repo_groups.keys():
            repo_dir = self.repo_cache.get(repo_url)
            if repo_dir:
                try:
                    repo = Repo(repo_dir)
                except Exception as e:
                    print(f'Error fetching repository {repo_url}: {e}')
        for adr_instance in self.adr_data:
            self.process_adr_instance(adr_instance)

    def clone_repo_thread(self, repository_url):
        repo_dir = self.clone_repo(repository_url)
        if repo_dir:
            with self.lock:
                self.repo_cache[repository_url] = repo_dir

    def group_by_repo(self, adr_data):
        repo_groups = {}
        for adr_instance in adr_data:
            repo_url = adr_instance['repositoryUrl']
            if repo_url not in repo_groups:
                repo_groups[repo_url] = []
            repo_groups[repo_url].append(adr_instance)
        return repo_groups

    def process_adr_instance(self, adr_instance):
        repository_url = adr_instance['repositoryUrl']
        adr_authors = adr_instance['adrAuthors']
        adr_directory = adr_instance['adrDirectory']
        adr_filename = adr_instance['path']
        adr_file_content = self.fetch_adr_file_from_repo(repository_url, adr_authors, adr_directory, adr_filename)
        adr_instance['adrFileContent'] = adr_file_content

    def process_file_metadata(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            repository_data = {'repositoryUrl': data.get('repositoryUrl', ''), 'crawlDateTime': data.get('crawlDateTime', ''), 'numAdrDirectories': data.get('numAdrDirectories', ''), 'adrDirectories': data.get('adrDirectories', []), 'numAdrFiles': data.get('numAdrFiles', ''), 'firstAdrCommit': data.get('firstAdrCommit', ''), 'lastAdrCommit': data.get('lastAdrCommit', ''), 'firstCommit': data.get('firstCommit', ''), 'lastCommit': data.get('lastCommit', ''), 'adrDirFile': data.get('adrDirFile', ''), 'repositoryAuthors': data.get('authors', [])}
            adr_files = data.get('adrFiles', [])
            for adr in adr_files:
                adr_instance = repository_data.copy()
                adr_instance.update({'adrDirectory': adr.get('adrDirectory', ''), 'path': adr.get('path', ''), 'template': adr.get('template', ''), 'status': adr.get('status', ''), 'firstCommitAdr': adr.get('firstCommit', ''), 'lastCommitAdr': adr.get('lastCommit', ''), 'numberOfCommitsAdr': adr.get('numberOfCommits', ''), 'adrAuthors': adr.get('authors', [])})
                self.adr_data.append(adr_instance)

    def fetch_adr_file_from_repo(self, repository_url, adr_authors, adr_directory, adr_filename):
        repo_dir = self.repo_cache.get(repository_url)
        if not repo_dir:
            print(f'Repository {repository_url} not found in cache.')
            return None
        commit_hash = self.extract_commit_hash_from_authors(adr_authors)
        if commit_hash:
            self.checkout_commit(repo_dir, commit_hash)
        else:
            print(f'No valid commit hash found for {repository_url}')
            return None
        adr_file_path = os.path.join(repo_dir, adr_directory, adr_filename)
        if os.path.exists(adr_file_path):
            with open(adr_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f'ADR file not found at {adr_file_path}')
            return None

    def clone_repo(self, repository_url):
        repo_dir = os.path.join(self.target_path, os.path.basename(repository_url).replace('.git', ''))
        if not os.path.exists(repo_dir):
            print(f'Cloning repository: {repository_url}')
            try:
                Repo.clone_from(repository_url, repo_dir)
            except Exception as e:
                print(f'Error cloning repository {repository_url}: {e}')
                return None
        else:
            print(f'Repository {repository_url} already cloned.')
        return repo_dir

    def extract_commit_hash_from_authors(self, adr_authors):
        try:
            if adr_authors and 'commitSet' in adr_authors[0]:
                commit_hashes = adr_authors[0]['commitSet']
                if commit_hashes:
                    return commit_hashes[0]
        except (KeyError, IndexError) as e:
            print(f'Error extracting commit hash from adrAuthors: {e}')
        return None

    def checkout_commit(self, repo_dir, commit_hash):
        try:
            repo = Repo(repo_dir)
            repo.git.checkout(commit_hash)
            print(f'Checked out to commit {commit_hash}')
        except Exception as e:
            print(f'Error checking out commit {commit_hash}: {e}')
            try:
                repo = Repo(repo_dir)
                repo.git.fetch('--all')
                repo.git.fetch('--tags')
                repo.git.checkout(commit_hash)
                print(f'Checked out to commit {commit_hash} after fetching.')
            except Exception as e:
                print(f'Error checking out commit {commit_hash} after fetching: {e}')
if __name__ == '__main__':
    adr_manager = AdrStudyDM()
    adr_manager.extract()
    adr_manager.save_data_to_csv()
