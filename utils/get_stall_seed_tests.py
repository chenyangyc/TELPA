# This file is used to extract testcases from 'codamosa_testcases_new' 
# to 'test_case_codamosa_{date}_{type}' with a given time

import os
import csv
import ast
import astor
from glob import glob
from tqdm import tqdm
from collections import defaultdict
import pickle


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


def src2exe(baseline_tests:str, baseline_outputs: str, target_path:str, stall_time:int):
    all_modules = glob(baseline_tests + '/*')
    module_stall_times = construct_module_stall_time(baseline_outputs, stall_time)
    missed = 0
    for single_module in all_modules:
        module_name = os.path.basename(single_module)
        
        # stall_time = 600
        stall_time = module_stall_times.get(module_name, None)
        if stall_time:
            all_times_list = glob(single_module + '/*')
            all_times = []
            for var in all_times_list:
                all_times.append(int(os.path.basename(var)))
            all_times.sort()
            
            nearest_time = str(find_nearest_time(all_times, stall_time))
            
            org_path = os.path.join(single_module, nearest_time)
            to_path = os.path.join(target_path, module_name, str(nearest_time))
            if os.path.exists(to_path):
                os.system(f'rm -rf {to_path}')
            os.makedirs(to_path)
            all_test_cases = glob(org_path + '/test_case_*.py')
            if all_test_cases == []:
                missed += 1
                continue
            for index, single_case in enumerate(all_test_cases):
                tmp_name = module_name.replace('.', '_')
                new_file_name = f'test_case_{tmp_name}_{index}.py'
                new_case_path = os.path.join(to_path, new_file_name)
                os.system('cp ' + single_case + ' ' + new_case_path)
            # os.system('cp -r ' + org_path + '/* ' + to_path)
        else:
            missed += 1
    print(missed)


def post_process_imports(target_test_case_path):
    all_modules = glob(f'{target_test_case_path}/*')
    print(len(all_modules))
    missed = 0
    module_imports = defaultdict(list)
    for single_module in all_modules:
        module_name = os.path.basename(single_module)
        
        all_origin_cases = glob(f'{single_module}/*/*.py')

        if all_origin_cases == []:
            missed += 1
            continue

        all_imports = defaultdict()
        import_index = 0
        for case in all_origin_cases:
            with open(case, 'r') as f:
                content = f.read()
            try:
                imports_in_case = extract_imports_for_case(content)
            except:
                os.system(f'rm -f {case}')
                continue
            for single_import, asname in imports_in_case.items():
                if single_import not in all_imports:
                    if asname is not None:
                        all_imports[single_import] = import_index
                        # all_imports[single_import] = asname
                        import_index += 1
                    # else:
                    #     all_imports[single_import] = 'randomstringrandomstring'
                # elif single_import in all_imports and asname is None:
                #     if asname != all_imports[single_import]:
                #         all_imports[single_import] = f'import_{import_index}'
                #         import_index += 1
        # continue
        # if module_name == 'ansible.playbook.role.metadata':
        #     pass
        # for origin_name, v in all_imports.items():
        #     if v != 'randomstringrandomstring':
        #         import_statement = f'import {origin_name} as module_{str(v)}'
        #     else:
        #         import_statement = f'import {origin_name}'
            
        #     module_imports[module_name].append(import_statement)
        
        all_origin_cases = glob(f'{single_module}/*/*.py')
        if all_origin_cases == []:
            missed += 1
            os.system(f'rm -rf {single_module}')
            continue
        for case in all_origin_cases:
            with open(case, 'r') as f:
                content = f.read()
            try:
                imports_in_case = extract_imports_for_case(content)
            except:
                os.system(f'rm -f {case}')
                continue

            asname_dict = defaultdict()
            for single_import, asname in imports_in_case.items():
                if asname is not None:
                    tmp_name = 'hahaha' + asname + 'hahaha'
                    content = content.replace(asname, tmp_name)
                    new_name = f'module_{all_imports[single_import]}'
                    
                    asname_dict[tmp_name] = new_name
                    
            for replace_name, real_name in asname_dict.items():
                content = content.replace(replace_name, real_name)
  
            with open(case, 'w') as f:
                f.write(content)
    print(missed)
    # with open('/data/yangchen/llm4unit/data/module_imports_pynguin.pkl', 'wb') as fw:
    #     pickle.dump(module_imports, fw)


if __name__ == '__main__':
    stall_time = 120
    
    baseline_tests = '/path/to/CODAMOSA/codamosa_testcases'
    baseline_outputs = '/path/to/CODAMOSA/output'
    target_path = f'/path/to/CODAMOSA/test_case_codamosa_{stall_time}'
    
    # if os.path.exists(target_path):
    #     os.system(f'rm -rf {target_path}')
    # os.makedirs(target_path)
    src2exe(baseline_tests, baseline_outputs, target_path, stall_time)
    post_process_imports(target_test_case_path = target_path)