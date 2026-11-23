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
        self.db_path_input = os.path.join(self.default_path, 'main_dataset.db')
        self.db_path_output = os.path.join(self.default_path, 'main_dataset_clean.db')
        self.db_output = Database(self.db_path_output)
        self.db_input = Database(self.db_path_input)
        self.o_jeito_burro()

    def add_column(self, column_name):
        query = f'\n        ALTER TABLE table_name\n        ADD COLUMN "{column_name}" TEXT;'
        self.db_input.execute_sql(query)

    def o_jeito_burro(self):
        pass
if __name__ == '__main__':
    routine = CorrelationRountine()
