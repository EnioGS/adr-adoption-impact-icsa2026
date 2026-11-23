import subprocess
import requests
import os
import time
import shutil
from git import Repo
import aiohttp
import asyncio
import pandas as pd
from datetime import datetime
import hashlib

class SonarqubeReport:

    def __init__(self, repo_name, repo_path, base_port=9000, cache_dir='tmp/sonar_cache/', context_extractor=None):
        project_id = repo_name + str(base_port)
        project_hash = hashlib.sha256(project_id.encode('utf-8')).hexdigest()[:15]
        self.repo_name = repo_name
        self.container_name = f'sonarqube'
        self.network_name = 'sonar_network'
        self.base_port = base_port
        self.sonar_url = f'http://172.17.0.1:9000'
        self.sonar_url_inside_docker = f'http://172.17.0.1:9000'
        self.login_info_sq = {'user': os.getenv('SONAR_USERNAME', 'admin'), 'password': os.getenv('SONAR_PASSWORD', 'admin')}
        if context_extractor is not None:
            self.routine_name, self.db, self.current_step_name, self.mode = context_extractor
        self.headers = {}
        self.api_token = None
        base_repos_root = os.getenv('ADR_REPOS_ROOT', '/path/to/adr_repositories_root/')
        self.default_repos_path = base_repos_root
        self.cache_dir = os.path.join(self.default_repos_path, cache_dir)
        self.sonarqube_on = False
        self.docker_reset()
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def docker_reset(self):
        subprocess.run(['docker', 'compose', 'down', '--remove-orphans', '--volumes'], check=True)
        subprocess.run(['docker', 'compose', 'up', 'sonarqube', '-d'], check=True)
        pass

    async def run_analysis_instance(self, project_info):
        project_name, project_key, commit_hash, year, month = project_info
        await self._create_project(project_name, project_key, commit_hash)
        project_hash_dir_path = self._mk_hashdir(self._get_original_dir(project_name), commit_hash)
        project_hash_name = self._mk_hashdir(project_name, commit_hash)
        project_hash_key = self._mk_hashdir(project_key, commit_hash)
        await self._run_scanner(project_hash_name, project_hash_key, project_hash_dir_path)
        metrics = await self._gather_metrics(project_hash_key)
        await self.format_output_data(metrics, project_hash_key, self.default_repos_path, project_info)
        await self._delete_project(project_name, project_key, commit_hash)
        return True

    async def run_analysis(self, project_set, limit=4):
        results = []
        semaphore = asyncio.Semaphore(limit)
        total_tasks = len(project_set)
        completed_tasks = 0

        async def limited_run(project_info):
            async with semaphore:
                return await self.run_analysis_instance(project_info)
        tasks = [asyncio.create_task(limited_run(project_info)) for project_info in project_set]
        for finished_task in asyncio.as_completed(tasks):
            result = await finished_task
            completed_tasks += 1
            print(f'Progress: {completed_tasks}/{total_tasks} tasks completed')

    async def _run_scanner(self, project_hash_name, project_hash_key, project_hash_dir_path, retries=5):
        for attempt in range(retries):
            try:
                print(f"Running SonarScanner for project '{project_hash_name}' at '{project_hash_dir_path}'...")
                process = await asyncio.create_subprocess_exec('docker-compose', 'run', '--rm', '-v', f'{project_hash_dir_path}:/usr/src/{project_hash_name}', 'sonar-scanner-cli', '-Dsonar.projectKey=' + project_hash_key, '-Dsonar.projectName=' + project_hash_name, '-Dsonar.sources=' + project_hash_name, '-Dsonar.host.url=' + self.sonar_url_inside_docker, '-Dsonar.login=' + self.api_token, '-D', 'sonar.exclusions=**/*.java', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await process.communicate()
                if process.returncode == 0:
                    print(f'sonarscanner ran successfuly {stdout.decode()} {stderr.decode()}')
                    return
                else:
                    print(f'SonarScanner failed with return code {process.returncode}')
                    print(stderr.decode())
                    await asyncio.sleep(2)
                    raise Exception('SonarScanner failed')
            except Exception as e:
                print(f'Attempt {attempt + 1}/{retries} failed: {e}')
                await asyncio.sleep(2)
        raise Exception('SonarScanner analysis failed after multiple attempts.')

    async def _gather_metrics(self, project_hash_key, max_retries=5000):
        metric_keys = ['bugs', 'new_bugs', 'vulnerabilities', 'new_vulnerabilities', 'code_smells', 'new_code_smells', 'high_impact_accepted_issues', 'new_blocker_violations', 'new_critical_violations', 'new_major_violations', 'new_minor_violations', 'new_info_violations', 'blocker_violations', 'critical_violations', 'major_violations', 'minor_violations', 'info_violations', 'security_hotspots', 'complexity', 'cognitive_complexity', 'coverage', 'line_coverage', 'branch_coverage', 'ncloc', 'lines', 'files', 'functions', 'statements', 'comment_lines', 'comment_lines_density', 'software_quality_blocker_issues', 'software_quality_high_issues', 'software_quality_info_issues', 'software_quality_medium_issues', 'software_quality_low_issues', 'software_quality_maintainability_issues', 'software_quality_reliability_issues', 'software_quality_security_issues', 'new_software_quality_blocker_issues', 'new_software_quality_high_issues', 'new_software_quality_info_issues', 'new_software_quality_medium_issues', 'new_software_quality_low_issues', 'new_software_quality_maintainability_issues', 'new_software_quality_reliability_issues', 'new_software_quality_security_issues']
        url = f'{self.sonar_url}/api/measures/component'
        params = {'component': project_hash_key, 'metricKeys': ','.join(metric_keys)}
        retries = 0
        info = {}
        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth('admin', 'admin')) as session:
            while retries < max_retries:
                try:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            measures = data.get('component', {}).get('measures', [])
                            if measures:
                                print(f'received')
                                info[project_hash_key] = measures
                                return info
                        elif response.status in [404, 503]:
                            print(f"The Server returned {response.status} for project '{project_hash_key}', retrying...")
                            await asyncio.sleep(5)
                            retries += 1
                        else:
                            print(f"Failed to gather metrics for project '{project_hash_key}'. Status Code: {response.status}")
                            response_text = await response.text()
                            return response_text
                except aiohttp.ClientError as e:
                    print(f'Network error occurred: {e}')

    async def format_output_data(self, metrics_info, project_hash_key, output_dir, project_info):
        project_name, project_key, commit_hash, year, month = project_info
        metrics = []
        for metric_info in metrics_info.get(project_hash_key, []):
            metric = {'project_name': project_key, 'author_name': '', 'year': year, 'month': month, 'variable_name': metric_info.get('metric'), 'value': str(metric_info.get('value'))}
            self.db.cache(metric, 'metrics')
        is_saved = self.db.save()
        if is_saved:
            print('saved this report')
            raw_info_self_substeps = [month, year]
            substep_name = self.db.get_steps_tag(self.current_step_name, self.mode, raw_info_self_substeps)
            self.db.mark_step_complete(self.routine_name, self.mode, substep_name)

    def _get_original_dir(self, project_name):
        project_dir_path = os.path.join(self.default_repos_path, project_name)
        dirs_in_repo = [os.path.join(project_dir_path, dir) for dir in os.listdir(project_dir_path) if os.path.isdir(os.path.join(project_dir_path, dir)) and ('_hash_' not in dir and 'tmp' not in dir)]
        if len(dirs_in_repo) == 1:
            project_path = dirs_in_repo[0]
            return project_path
        else:
            raise Exception(f'More than one directory inside the project_dir_path {project_dir_path}, {dirs_in_repo}')

    def _mk_hashdir(self, project_path, commit_hash):
        if project_path.endswith('/'):
            project_path = project_path[:-1]
        return project_path + '_hash_' + commit_hash

    async def _create_project(self, project_name, project_key, commit_hash):
        await self._delete_project(project_name, project_key, commit_hash)
        url = f'{self.sonar_url}/api/projects/create'
        src_project_path = self._get_original_dir(project_name)
        dst_project_path = self._mk_hashdir(self._get_original_dir(project_name), commit_hash)
        if not os.path.exists(dst_project_path):
            await asyncio.to_thread(shutil.copytree, src_project_path, dst_project_path)
        await asyncio.to_thread(self._checkout_repo, dst_project_path, commit_hash)
        await self._create_sonar_project(project_name, project_key, commit_hash)

    def _checkout_repo(self, repo_path, commit_hash):
        repo = Repo(repo_path)
        try:
            repo.git.checkout(commit_hash, force=True)
            dirs_to_remove = ['.git', '.github']
            for dir_name in dirs_to_remove:
                dir_path = os.path.join(repo_path, dir_name)
                if os.path.isdir(dir_path):
                    shutil.rmtree(dir_path)
        except Exception as e:
            raise Exception(f'Failed to checkout to commit {commit_hash}: {e}')

    async def _create_sonar_project(self, project_name, project_key, commit_hash):
        url = f'{self.sonar_url}/api/projects/create'
        data = {'name': self._mk_hashdir(project_name, commit_hash), 'project': self._mk_hashdir(project_key, commit_hash)}
        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth('admin', 'admin')) as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    print(f"Project '{data['name']}' created successfully.")
                    pass
                else:
                    response_text = await response.text()
                    print(f"Failed to create project '{data['name']}'. Status Code: {response.status}")
                    print(f'Response: {response_text}')

    async def _is_project_present(self, project_key, retries=20):
        url = f'{self.sonar_url}/api/projects/search'
        params = {'projects': project_key}
        retry = 0
        async with aiohttp.ClientSession(auth=aiohttp.BasicAuth('admin', 'admin')) as session:
            while retry < retries:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        project_data = await response.json()
                        if 'components' in project_data and len(project_data['components']) > 0:
                            return True
                        else:
                            return False
                    else:
                        retry += 1
                        await asyncio.sleep(2)
            raise Exception(f'Error checking project presence after {retries} retries.')

    async def _delete_project(self, project_name, project_key, commit_hash, retries=20):
        is_present_online = await self._is_project_present(project_key)
        if is_present_online:
            url = f'{self.sonar_url}/api/projects/delete'
            data = {'name': self._mk_hashdir(project_name, commit_hash), 'project': self._mk_hashdir(project_key, commit_hash)}
            retry = 0
            async with aiohttp.ClientSession(auth=aiohttp.BasicAuth('admin', 'admin')) as session:
                while retry < retries:
                    try:
                        async with session.post(url, data=data) as response:
                            if response.status == 200:
                                is_deleted = not await self._is_project_present(project_key)
                                if is_deleted:
                                    break
                                else:
                                    return False
                            else:
                                retry += 1
                                await asyncio.sleep(2)
                        if retry >= retries:
                            raise Exception(f'Error deleting project after {retries} retries.')
                    except aiohttp.ClientError as e:
                        print(f'Network error occurred: {e}')
                        retry += 1
                        await asyncio.sleep(2)
                    if retry >= retries:
                        raise Exception(f'Error deleting project after {retries} retries.')
        to_delete_path = self._mk_hashdir(self._get_original_dir(project_name), commit_hash)
        if os.path.isdir(to_delete_path):
            await asyncio.to_thread(shutil.rmtree, to_delete_path)

    def run_and_is_on_sonarqube(self, max_retries=1800, delay=1):
        import subprocess
        import socket
        hostname = socket.gethostname()
        if self.sonarqube_on:
            return
        time.sleep(10)
        url = f'{self.sonar_url}/api/system/status'
        retries = 0
        while retries < max_retries:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    try:
                        json_response = response.json()
                        status = json_response.get('status')
                        if status in 'UP':
                            print(f'SonarQube is operational (status: {status}).')
                            self._login()
                            self._get_api_key()
                            self.sonarqube_on = True
                            return True
                        else:
                            print(f'SonarQube is not fully operational (status: {status}), retrying...')
                    except ValueError:
                        print('Received non-JSON response, SonarQube is still starting up, retrying...')
                else:
                    print(f'Unexpected status code {response.status_code}, retrying...')
            except requests.ConnectionError as e:
                print(f'SonarQube server not reachable, retrying... {e}')
            time.sleep(delay)
            retries += 1
        raise Exception('SonarQube server did not become operational in time.')

    def _get_api_key(self):
        if self.api_token is not None:
            return
        url = f'{self.sonar_url}/api/user_tokens/generate'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        parameters = {'name': f'global_admin_token_{timestamp}', 'type': 'GLOBAL_ANALYSIS_TOKEN'}
        self.headers = {}
        try:
            response = requests.post(url, data=parameters, auth=('admin', 'admin'))
            if response.status_code == 200:
                json_response = response.json()
                self.api_token = json_response.get('token')
                self.headers = {'Authorization': f'Bearer {self.api_token}'}
            else:
                print(f'Token failed: {response.status_code}, token: {self.api_token}')
                print(f'Response: {response.text}')
                raise Exception
        except requests.RequestException as e:
            print(f'An error occurred while trying to login: {e}')
            raise Exception(f'An error occurred while trying to login: {e}')

    def _login(self):
        url = f'{self.sonar_url}/api/authentication/login'
        data = {'login': self.login_info_sq['user'], 'password': self.login_info_sq['password']}
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                return
            else:
                print(f'Login failed. Status code: {response.status_code}')
                print(f'Response: {response.text}')
        except requests.RequestException as e:
            print(f'An error occurred while trying to login: {e}')

async def main():
    sonar_report = SonarqubeReport()
    try:
        commit_hash = '0301b03'
        project_name = 'kits-ab_LogLady'
        project_key = 'kits-ab_LogLady'
        project_set = [(project_name, project_key, commit_hash)]
        sonar_report.run_and_is_on_sonarqube()
        await sonar_report.run_analysis(project_set)
    except Exception as e:
        print(f'process failed: {e}')
    sonar_report.docker_reset()
if __name__ == '__main__':
    asyncio.run(main())
