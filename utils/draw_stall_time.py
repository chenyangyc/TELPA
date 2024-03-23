# This file is used to extract testcases from 'codamosa_testcases_new' 
# to 'test_case_codamosa_{date}_{type}' with a given time

import os
import csv
import ast
import astor
from glob import glob
from tqdm import tqdm
from collections import defaultdict


def extract_imports_for_case(content):
    tree = ast.parse(content)

    imports = defaultdict()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    imports[alias.name] = alias.asname
                else:
                    imports[alias.name] = None
        # elif isinstance(node, ast.ImportFrom):
        #     module = node.module
        #     if module is not None:
        #         if node.names[0].asname:
        #             full_name = f"{module}.{node.names[0].name} as {node.names[0].asname}"
        #         else:
        #             full_name = f"{module}.{node.names[0].name}"
        #         imports.add(full_name)
    return imports


def construct_module_stall_time(baseline_output:str, stall_time:int):
    module_stall_time = defaultdict()
    for root, dirs, files in os.walk(baseline_output):
        for file in files:
            if file == 'statistics.csv':
                module_name = os.path.basename(root)
                #一个模块一个图
                csv_file_path = os.path.join(root, file)
                x=[]
                y=[]
                with open(csv_file_path, 'r') as csvfile:
                    reader = csv.reader(csvfile, delimiter=',')
                    header_row = next(reader)
                    data_row = next(reader)
                    coverage_row = [float(char) for char in data_row[17:]]
                    
                    # 找到y中是否有连续gap个没变化的值，并返回下标
                    gap = stall_time
                    index = len(coverage_row)
                    for i in range(len(coverage_row)-gap):
                        if coverage_row[i+gap] == coverage_row[i]:
                            index = i + gap
                            break
                    if index != len(coverage_row):
                        module_stall_time[module_name] = index
    return module_stall_time


def find_nearest_time(all_times:list, required_time:int):
    for index, time in enumerate(all_times):
        if time > required_time:
            # return all_times[index]
            return all_times[index]
            # if index > 1:
            #     return all_times[index-1]
            # else:
            #     return all_times[1]
    return all_times[-1]


def src2exe(baseline_tests:str, baseline_outputs: str, stall_time:int):
    all_modules = glob(baseline_tests + '/*')
    module_stall_times = construct_module_stall_time(baseline_outputs, stall_time)
    return module_stall_times

import numpy as np
if __name__ == '__main__':
    stall_time = 120
    baseline_tests = '/data/yangchen/dingyuquan/CODAMOSA/codamosa_testcases_new_all_1200'
    baseline_outputs = '/data/yangchen/dingyuquan/CODAMOSA/output_1200'

    codamosa_time = src2exe(baseline_tests, baseline_outputs, stall_time)
    
    baseline_tests = '/data/yangchen/dingyuquan/CODAMOSA/pynguin_testcases_1200_1'
    baseline_outputs = '/data/yangchen/dingyuquan/CODAMOSA/output_pynguin'

    pynguin_time = src2exe(baseline_tests, baseline_outputs, stall_time)
    
    data1 = []
    data2 = []
    for key, value in codamosa_time.items():
        data1.append(value / 60)
        p_time = pynguin_time.get(key)
        if p_time is not None:
            data2.append(p_time / 60)
        else:
            data2.append(p_time)
        
    print(len(data1))
    print(len(data2))
    
    
    avg_1 = np.mean(data1)
    avg_2 = np.mean([i for i in data2 if i is not None])
    print(avg_1)
    print(avg_2)
    
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd
    data = pd.DataFrame({'CODAMOSA': data1, 'Pynguin': data2})

    plt.ylabel('Time', fontdict={'size': 18})
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    # plt.title("Violin Plot Example")
    plt.ylabel("Activation Time (Minutes)")
    # plt.xlabel("Time for method switch")
    # Create the violin plot
    # '#82e2b6', '01': '#80e2fc', '11': '#00d0cf'
    colors = ['#82E2B6', "#80E2FC"]
    sns.violinplot(data=data, inner="quartile", palette=colors)
    # plt.grid(True)
    # Show the plot
    plt.savefig(f'/data/yangchen/llm4unit/data/stall_time.png')

    # plt.show()

    