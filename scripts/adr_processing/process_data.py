class Results:

    def __init__(self):
        self.projects = []
        self.current_state = Committer()
        self.research_questions = {'RQ_1': None, 'RQ_1.1': None, 'RQ_1.2': None, 'RQ_1.3': None, 'RQ_1.4': None, 'RQ_1.5': None, 'RQ_2-1': None, 'RQ_2-2': None, 'RQ_2-3': None, 'RQ_3-1': None, 'RQ_3-2': None, 'RQ_3-3': None, 'RQ_3-4': None}

    def add_project(self, project):
        if isinstance(project, Project):
            self.projects.append(project)
        else:
            raise TypeError(f"Expected 'Project', got {type(project).__name__}.")

    def calculate_metrics(self):
        for project in self.projects:
            project.calculate_metrics()
        self.current_state.calculate_metrics()

    def get_summary(self):
        return {'projects': [project.get_summary() for project in self.projects], 'current_state': self.current_state.get_summary(), 'research_questions': self.research_questions}

class Author:

    def __init__(self):
        self.projects = []

    def add_project(self, project):
        if isinstance(project, Project):
            self.projects.append(project)
        else:
            raise TypeError(f"Expected 'Project', got {type(project).__name__}.")

    def calculate_metrics(self):
        for project in self.projects:
            project.calculate_metrics()

    def get_summary(self):
        return {'state': 'current', 'projects': [project.get_summary() for project in self.projects]}

class Project:

    def __init__(self, name):
        self.name = name
        self.branches = []

    def add_branch(self, branch):
        if isinstance(branch, Branch):
            self.branches.append(branch)
        else:
            raise TypeError(f"Expected 'Branch', got {type(branch).__name__}.")

    def calculate_metrics(self):
        for branch in self.branches:
            branch.calculate_metrics()

    def get_summary(self):
        return {'name': self.name, 'branches': [branch.get_summary() for branch in self.branches]}

class Branch:

    def __init__(self, name):
        self.name = name
        self.metrics = []

    def add_metric(self, metric):
        if isinstance(metric, Metric):
            self.metrics.append(metric)
        else:
            raise TypeError(f"Expected 'Metric', got {type(metric).__name__}.")

    def calculate_metrics(self):
        for metric in self.metrics:
            metric.calculate()

    def get_summary(self):
        return {'name': self.name, 'metrics': [metric.get_summary() for metric in self.metrics]}

class Metric:

    def __init__(self, name):
        self.name = name
        self.data = []

    def add_data(self, data):
        if isinstance(data, pd.DataFrame):
            self.data.append(self._validate_data(data))
        else:
            raise TypeError('Metric data must be a pandas DataFrame.')

    def _validate_data(self, df):
        required_columns = {'year', 'month', 'value'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f'Missing required columns: {required_columns - set(df.columns)}')
        return df.set_index(['year', 'month'])

    def calculate(self):
        if not self.data:
            self.summary = None
            return
        combined_data = pd.concat(self.data)
        combined_data['average'] = combined_data['value'].mean()
        self.summary = combined_data

    def get_summary(self):
        return {'name': self.name, 'summary': getattr(self, 'summary', 'No data available')}
