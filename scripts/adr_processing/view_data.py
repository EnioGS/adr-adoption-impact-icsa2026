from database import Database
from functools import reduce
import numpy as np
import os
import traceback
from tqdm import tqdm
import hashlib
from pingouin import partial_corr
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy.stats import spearmanr
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from scipy.stats import shapiro, pearsonr, spearmanr, kurtosis, skew
import pandas as pd
import networkx as nx
from datetime import datetime
from pandas import Timestamp
import matplotlib
from matplotlib.patches import Patch
import matplotlib.dates as mdates
import numpy as np
matplotlib.use('Agg')

class ViewData:

    def __init__(self):
        self.default_path = os.path.join(os.getcwd(), 'datasets', 'project_repositories')
        self.db_path = os.path.join(self.default_path, 'main_dataset.db')
        self.db = Database(self.db_path)

    def render_area_graph(self):
        df = self.db.to_df('adr_tracking_info')
        adr_generational_info = self.get_gen_info(df, filter={})
        df['generation'] = -1
        for generation_number, adr_list in adr_generational_info.items():
            adr_ids = [row['adr_id'] for row in adr_list]
            df.loc[df['adr_id'].isin(adr_ids), 'generation'] = generation_number
        df_grouped = df.groupby(['generation', 'adr_current_status']).size().unstack(fill_value=0)
        generations = range(df_grouped.index.min(), df_grouped.index.max() + 1)
        categories = df['adr_current_status'].dropna().unique()
        df_grouped = df_grouped.reindex(index=generations, columns=categories, fill_value=0)
        plt.figure(figsize=(16, 8))
        df_grouped.plot.area(stacked=True, figsize=(16, 8), alpha=0.8)
        plt.title(f'ADR Distribution by Status')
        plt.xlabel('Generations')
        plt.ylabel('Number of ADRs')
        plt.legend(title='Status', loc='upper right')
        output_path = os.path.join(self.default_path, f'graph_by_status_area.png')
        plt.savefig(output_path, format='png', dpi=300)
        plt.close()
        plotly

    def render_change_tree(self):
        filters = [{}, {'adr_current_status': 'accepted'}, {'adr_current_status': 'proposed'}, {'adr_current_status': 'rejected'}, {'adr_current_status': 'superseded'}]
        for filter in filters:
            if filter == {}:
                G_status, G_change_type = self.build_graph(filter=filter)
                pos, y_categories = self.calculate_positions(G_status, mode='status')
                output_path = f'{self.default_path}/graph_by_status.png'
                self.visualize_graph(G_status, pos, output_path, mode='status', y_categories=y_categories)
            for key, value in filter.items():
                G_status, G_change_type = self.build_graph(filter=filter)
                subname = f'{key}_-_{value}'
                pos, y_categories = self.calculate_positions(G_status, mode='status')
                output_path = f'{self.default_path}/graph_by_status.png'
                self.visualize_graph(G_status, pos, output_path, mode='status', y_categories=y_categories, subname=subname)

    def get_gen_info(self, df_adr_tracking_info, filter={}):
        history = []
        adr_data = {}
        pending = []
        next_pending = []
        df_adr_tracking_info_filtered = df_adr_tracking_info[df_adr_tracking_info['is_oldest'] == '1']
        print(f'arrived here')
        for index, row in df_adr_tracking_info_filtered.iterrows():
            if filter != {}:
                for row_name, row_value in filter.items():
                    if row[row_name] != row_value:
                        continue
            print(f'and here also')
            adr_id = row['adr_id']
            generation_number = 0
            child_adr_ids = row['points_to_adr_id'].split('_-_')
            current_adr_data = row.copy()
            if generation_number not in adr_data:
                adr_data[generation_number] = []
            adr_data[generation_number].append(current_adr_data)
            for child_adr_id in child_adr_ids:
                pending.append(child_adr_id)
                print(f'appending to pending')
        while len(pending) > 0:
            generation_number += 1
            print(f'beginning scan for generation: {generation_number}, number of pending {len(pending)} first pending is: {pending[0]}')
            for index, row in df_adr_tracking_info.iterrows():
                adr_id = row['adr_id']
                if adr_id in pending:
                    child_adr_ids = row['points_to_adr_id'].split('_-_')
                    current_adr_data = row.copy()
                    if generation_number not in adr_data:
                        adr_data[generation_number] = []
                    adr_data[generation_number].append(current_adr_data)
                    for child_adr_id in child_adr_ids:
                        if adr_id != child_adr_id and child_adr_id not in history:
                            next_pending.append(child_adr_id)
                        elif adr_id == child_adr_id:
                            print(f'Warning: adr pointing to itself: {child_adr_id}')
            pending = list(set(next_pending))
            history = history + [adr_id for adr_id in list(set(next_pending))]
            next_pending = []
        return adr_data

    def build_graph(self, filter={}):
        df_adr_tracking_info = self.db.to_df('adr_tracking_info')
        G_status = nx.DiGraph()
        G_change_type = nx.DiGraph()
        times = []
        adr_generational_info = self.get_gen_info(df_adr_tracking_info, filter=filter)
        for generation_number, values in adr_generational_info.items():
            df_values = pd.DataFrame(values)
            adr_current_status = df_values['adr_current_status'].unique()
            adr_file_change_type = df_values['adr_file_change_type'].unique()
            for status in adr_current_status:
                if status is None:
                    continue
                node_id = str(generation_number) + '_-_' + status
                df_filtered_status = df_values[df_values['adr_current_status'] == status].copy()
                points_to_adr_id = []
                adr_ids = []
                for index, row in df_filtered_status.iterrows():
                    current_points_to_adr_id = [{row['adr_id']: row['points_to_adr_id'].split('_-_')}]
                    adr_id = row['adr_id']
                    adr_ids.append(adr_id)
                    points_to_adr_id = points_to_adr_id + current_points_to_adr_id
                points_to_adr_id = points_to_adr_id
                G_status.add_node(node_id, number_of_instances=len(df_filtered_status), generation=generation_number, status=status, points_to_adr_id=points_to_adr_id, adr_ids=adr_ids)
            for change_type in adr_file_change_type:
                node_id = str(generation_number) + '_-_' + change_type
                df_filtered_change_type = df_values[df_values['adr_file_change_type'] == change_type].copy()
                points_to_adr_id = []
                adr_ids = []
                for index, row in df_filtered_change_type.iterrows():
                    current_points_to_adr_id = [{row['adr_id']: row['points_to_adr_id'].split('_-_')}]
                    adr_id = row['adr_id']
                    adr_ids.append(adr_id)
                    points_to_adr_id = points_to_adr_id + current_points_to_adr_id
                points_to_adr_id = points_to_adr_id
                G_change_type.add_node(node_id, number_of_instances=len(df_filtered_change_type), generation=generation_number, change_type=change_type, points_to_adr_id=points_to_adr_id, adr_ids=adr_ids)
        generations = sorted(adr_generational_info.keys())
        for generation_number in generations:
            current_gen_nodes = adr_generational_info[generation_number]
            next_gen_nodes = adr_generational_info.get(generation_number + 1, [])
            current_gen_status_ids = [node['adr_id'] for node in current_gen_nodes]
            next_gen_status_ids = [node['adr_id'] for node in next_gen_nodes]
            for node, data in G_status.nodes(data=True):
                current_points_to_adr_id = data['points_to_adr_id']
                for next_node_id, next_data in G_status.nodes(data=True):
                    if next_data['generation'] == data['generation'] + 1:
                        if any((adr_id in next_data['adr_ids'] for mapping in current_points_to_adr_id for adr_id, points_to_list in mapping.items() if adr_id in data['adr_ids'] and any((pt_id in next_data['adr_ids'] for pt_id in points_to_list)))):
                            G_status.add_edge(node, next_node_id)
            for node, data in G_change_type.nodes(data=True):
                current_points_to_adr_id = data['points_to_adr_id']
                for next_node_id, next_data in G_change_type.nodes(data=True):
                    if next_data['generation'] == data['generation'] + 1:
                        if any((adr_id in next_data['adr_ids'] for mapping in current_points_to_adr_id for adr_id, points_to_list in mapping.items() if adr_id in data['adr_ids'] and any((pt_id in next_data['adr_ids'] for pt_id in points_to_list)))):
                            G_change_type.add_edge(node, next_node_id)
        return (G_status, G_change_type)

    def calculate_positions(self, G, mode):
        pos = {}
        y_categories = sorted(set((value for value in nx.get_node_attributes(G, mode).values() if value is not None)))
        y_mapping = {category: idx for idx, category in enumerate(y_categories)}
        generations = sorted(set(nx.get_node_attributes(G, 'generation').values()))
        x_mapping = {generation: idx for idx, generation in enumerate(generations)}
        for node, data in G.nodes(data=True):
            x_position = x_mapping.get(data['generation'], -1)
            y_position = y_mapping.get(data[mode], -1)
            pos[node] = (x_position, y_position)
        return (pos, y_categories)

    def visualize_graph(self, G, pos, output_path, mode, y_categories, subname=f'macro'):
        plt.figure(figsize=(24, 8))
        for idx, category in enumerate(y_categories):
            plt.axhspan(idx - 0.5, idx + 0.5, color=f'C{idx % 10}', alpha=0.2, zorder=-1)
        node_labels = {node: data['number_of_instances'] for node, data in G.nodes(data=True)}
        nx.draw(G, pos, labels=node_labels, node_size=500, edgelist=[])
        plt.xlabel('Generations')
        plt.ylabel(mode.capitalize())
        plt.title(f'Macro View: Graph by {mode.capitalize()}')
        plt.legend(handles=[Patch(color=f'C{idx % 10}', label=category) for idx, category in enumerate(y_categories)], loc='upper right', title=mode.capitalize())
        plt.savefig(f"{output_path.replace('.png', f'_{subname}.png')}", format='png', dpi=300)
        plt.close()
if __name__ == '__main__':
    vd = ViewData()
    vd.render_change_tree()
    vd.render_area_graph()
