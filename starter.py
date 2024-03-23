'''    
# function类可以用method signature作为索引，第一步提取module里所有的function，第二步提取调用关系并通过索引过滤匹配 -> 建立调用图
# all target function就是调用图里的callable（public）以及，被public调用了的private的函数
# 为了方便第二步的选择和后续测试程序的选择，我们可以在建图时存下每个函数的called functions，以及callee functions（都以对象来存）

# 对于每个待测函数，program的池子范围都是：
# 1. 自己的 direct invoke 的program池 （对于private来说这个池子是空的）
# 2. 自己的 indirect invoke program池 （来自caller function的program，这时的 prompt 信息里要给出 call chain (caller function -> target function)）
# 那么就是说，每次都去遍历自己的caller，对于每个caller，去找caller对应的direct里满足覆盖要求的program，更新也更新caller的direct池
# 每一步的停止标志都可以是覆盖率不提升

# 那么覆盖率的要求可以在池子里进行选择的时候进行过滤：选择那些有覆盖率且尽可能大的program

# 以上解决few shot example以及direct invoke -> target之间的call chain
# 下面分析 target -> called 之间的依赖call chain

# 选定一个target，获得它所有的called functions，判断called functions是否与分支相关 

# 两个需要新做的功能：
# 1. caller function -> target function 的call chain（找到图上两点间的最短路径/所有路径）
# 2. 判断called functions是否与分支相关 
'''

import os
import ast
import sys
import copy
import json
import astor
import pickle
import random
import traceback
from tqdm import tqdm
from collections import defaultdict
from core.chatbot import ChatBot
from core.base_module import Module
from core.base_selection import RouletteWheelSelection
from core.base_test_program import TestProgram
from utils.benchmark_parse_util import extract_classes, extract_functions, extract_called_functions,\
                                        extract_initilized_class, extract_branch_related_called_functions
from utils.llm_util import *
from utils.program_parse_util import select_examples
from utils.run_test_util import assemble_test_file, run_test_and_collect_cov
from data.configuration import good_modules_path, benchmark_base, base_report, base_cases, example_response
import time


def find_python_files(directory):
    python_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    return python_files


def are_last_three_sets_same(lst):
    # 确保列表至少有三个元素
    if len(lst) < 3:
    # if len(lst) < 2:
        return False

    # 检查最后三个集合是否相同
    return lst[-1] == lst[-2] == lst[-3]
    # return lst[-1] == lst[-2]


def get_modules(proj_base, good_modules_path):
    all_modules = []
    classes_dict = {}
    functions_dict = {}
    
    with open(good_modules_path, 'r') as f:
        for line in tqdm(f):
            line = line.strip()
            proj_path = os.path.join(proj_base, line.split(',')[0])
            
            module_name = line.split(',')[-1]
            module_path = module_name.replace('.', os.path.sep) + '.py'
            module_path = os.path.join(proj_path, module_path)
            
            with open(module_path, 'r') as module_file:
                module_content = module_file.read()
            single_module = Module(name=module_name, content=module_content, module_dir=proj_path, module_path=module_path)
            
            for i in extract_classes(module_content):
                single_module.add_class(i)
            for i in extract_functions(module_content):
                single_module.add_function(i)

            classes_dict.setdefault(module_name, dict())
            functions_dict.setdefault(module_name, dict())
        
            for single_class in single_module.classes:
                class_name = single_class.name
                classes_dict[module_name].setdefault(class_name, single_class)
                
            for single_func in single_module.functions:
                name = single_func.name
                signature = single_func.signature
                # NOTE: name or signature?
                functions_dict[module_name].setdefault(name, single_func)

            all_modules.append(single_module)
    return all_modules, classes_dict, functions_dict


def find_all_chains(start_node, visited=None, path=None):
    if visited is None:
        visited = set()
    if path is None:
        path = [start_node]

    # path = path + [start_node]
    visited.add(start_node)
    start_node.set_target()
    
    all_paths = []

    for next_node in start_node.called_functions:
        # print(f"{start_node.name} -> {next_node.name}")
        if next_node not in visited:
            new_paths = find_all_chains(next_node, visited | {next_node}, path + [next_node])
            # tmp_path = path + [start_node]
            tmp_path = path + [next_node]
            next_node.add_callee_chain(tmp_path)
            all_paths.extend(new_paths)
        else:
            # Detect cycle - stop the path here to avoid infinite loop
            cycle_index = path.index(next_node)
            # tmp_path = path + [start_node]
            tmp_path = path[:cycle_index] + [next_node]
            next_node.add_callee_chain(tmp_path)
            all_paths.append(path)
    
    # 如果 start_node.called_functions 是空的，添加当前路径
    if not start_node.called_functions:
        all_paths.append(path)
        
    return all_paths


# 查找最短的链
def find_shortest_chains(chains):
    shortest_chains = list()
    # shortest_chain = None
    min_object_count = float('inf')
    min_line_range_sum = float('inf')

    min_length = min(len(chain) for chain in chains)
    shortest_chains = [chain for chain in chains if len(chain) == min_length]
    
    # for chain in chains:
    #     object_count = len(chain)
    #     line_range_sum = sum((len(func.covered_lines) / len(func.line_range)) for func in chain)

    #     if object_count < min_object_count:
    #         shortest_chain = chain
    #         min_object_count = object_count
    #         min_line_range_sum = line_range_sum
    #     elif object_count == min_object_count and line_range_sum < min_line_range_sum:
    #         shortest_chain = chain
    #         min_line_range_sum = line_range_sum

    return shortest_chains

# 处理调用链
def called_chain_filtering(single_func):
    # print(single_func.name)
    callee_chains = [i for i in single_func.callee_chains if i not in single_func.used_callee_chains]

    # 处理callee_chains
    startpoint_chains = {}
    for chain in callee_chains:
        startpoint = chain[0]  # 链的起点

        if startpoint not in startpoint_chains:
            startpoint_chains[startpoint] = []

        startpoint_chains[startpoint].append(chain)

    callee_chains.clear()
    for chains_with_same_startpoint in startpoint_chains.values():
        shortest_callee_chains = find_shortest_chains(chains_with_same_startpoint)
        callee_chains.extend(shortest_callee_chains)
        # 处理 shortest_callee_chain
    # 注意这里用深拷贝
    single_func.using_callee_chains = callee_chains

    # # 处理called_chains
    # endpoint_chains = {}
    # for chain in called_chains:
    #     endpoint = chain[-1]  # 链的终点

    #     if endpoint not in endpoint_chains:
    #         endpoint_chains[endpoint] = []

    #     endpoint_chains[endpoint].append(chain)
        
    # called_chains.clear()
    # for chains_with_same_endpoint in endpoint_chains.values():
    #     shortest_called_chain = find_shortest_chain(chains_with_same_endpoint)
    #     called_chains.append(shortest_called_chain)
    #     # 处理 shortest_called_chain

    # single_func.called_chains = called_chains


def setup_single_modules(all_functions_in_module, name_2_class, name_2_function):
    for single_func in all_functions_in_module:
        # 构造调用图
        # 提取调用的所有函数
        called_functions = extract_called_functions(single_func.content)
        for caller, called_name in called_functions:
            # 如果存在的话，在当前module的function dict里找对应的函数
            called_function = name_2_function.get(called_name)
            
            # 如果找到了，并且 1. 没有caller， 2. caller和该函数所属类一致，则加入called function
            if called_function and called_name != single_func.name and (not caller or caller == 'self' or (called_function.belong_class and caller.lower() == called_function.belong_class.lower())):
                single_func.add_called_function(called_function)
                called_function.add_callee_function(single_func)
        pass
        
        # 构造分支有关的函数调用
        branch_related_called_functions = extract_branch_related_called_functions(single_func.content)
        for caller, called_name in branch_related_called_functions:
            called_function = name_2_function.get(called_name)
            
            # 如果找到了，并且 1. 没有caller， 2. caller和该函数所属类一致，则加入called function
            if called_function and called_name != single_func.name and (not caller or caller == 'self' or (called_function.belong_class and caller.lower() == called_function.belong_class.lower())):
                single_func.add_branch_related_called_functions(called_function)
        pass
    
        # 构造instance creation
        initilized_classes = extract_initilized_class(single_func.content)
        for initilized_class in initilized_classes:
            # 如果存在的话，在当前module的class dict里找对应的类
            initilized_class = name_2_class.get(initilized_class)
            if initilized_class:
                single_func.add_instance_creation(initilized_class)
        pass
    pass
    # print('Begin extracting call graph.')
    
    for single_func in all_functions_in_module:   
        # 以每个public的函数作为起点，提取不带环的所有路径，路径上的函数都是target function，路径本身就 是called chain 和calee chain
        if not single_func.name.startswith('_'):
            paths_from_single_func = find_all_chains(single_func)
            for i in paths_from_single_func:
                if len(i[1:]) != 0:
                    single_func.add_called_chain(i[1:])
    pass



def setup_existing_cases(module_name, all_functions_in_module, name_2_function, module_cases):
    existing_cases_in_module = find_python_files(module_cases)
    existing_report_dir = module_cases.replace('llm_test_cases', 'llm_report').replace('test_case', 'report')
    
    for index, test_file in enumerate(existing_cases_in_module):
        try:
            test_file_name = test_file.split('/')[-1].split('.')[0].strip()
            with open(test_file, 'r') as f:
                test_content = f.read()
            
            coverage_file = os.path.join(existing_report_dir, 'final', test_file_name+'_report.json')
            
            with open(coverage_file, 'r') as f:
                raw_coverage = json.load(f)

            # file_info = list(raw_coverage['files'].values())[0]
            # executed_lines = set(file_info['executed_lines'])
            # missing_lines = set(file_info['missing_lines'])
            
            # coverage = {
            #     'file': file_info,
            #     'exec': executed_lines,
            #     'miss': missing_lines,
            #     'all': executed_lines.union(missing_lines)
            # }
            
            file_info = list(raw_coverage['files'].values())[0]
            executed_lines = set(file_info['executed_lines'])
            missing_lines = set(file_info['missing_lines'])
            executed_branches = file_info['executed_branches']
            missing_branches = file_info['missing_branches']
            
            coverage = {
                'file': file_info,
                'exec': executed_lines,
                'miss': missing_lines,
                'exec_branch': executed_branches,
                'miss_branch': missing_branches,
                'all': executed_lines.union(missing_lines)
            }
        
            new_test_case = TestProgram(content=test_content, target_function=None, coverage=coverage)

            case_called_functions = extract_called_functions(test_content)

            for caller, called_name in case_called_functions:
                # 如果存在的话，在当前module的function dict里找对应的函数
                called_function = name_2_function.get(called_name)
                
                # 如果找到了，则加入called function
                if called_function:
                    new_test_case.add_called_function(called_function)
                    called_function.add_direct_program(new_test_case)
            
            covered_by_case = coverage['exec']
            
            for single_target in all_functions_in_module:
                covered_by_case_in_target = covered_by_case.intersection(single_target.line_range)
                if len(covered_by_case_in_target) > 0: 
                    single_target.add_covered_lines(covered_by_case_in_target)
            pass
        except:
            print('1')
            continue


def setup_all_modules(all_modules, classes_dict, functions_dict):
    for single_module in all_modules:
        module_name = single_module.name
        module_content = single_module.content
        module_dir = single_module.module_dir
        module_path = single_module.module_path

        name_2_class = classes_dict[module_name]
        name_2_function = functions_dict[module_name]
                
        coveragerc_file = os.path.join(module_dir, '.coveragerc')
        with open(coveragerc_file, 'w') as file:
            file.write('[run]\ndynamic_context = test_function')
        
        # 拿到当前module里所有的函数
        all_functions_in_module = single_module.functions
        
        # 拿到当前module对应的测试用例
        module_cases = os.path.join(base_existing_cases_path, module_name)
        
        setup_single_modules(all_functions_in_module, name_2_class, name_2_function)
        setup_existing_cases(module_name, all_functions_in_module, name_2_function, module_cases)
    pass
    
    
def record_module_info(callable_functions, module_preprocess_dir, module_content, module_name):
    if callable_functions:
        module_preprocess_res_file = os.path.join(module_preprocess_dir, module_name + '.jsonl')
        module_preprocess_writer = open(
            module_preprocess_res_file,
            "w",
        )
        
        for single_target in callable_functions:
            called_chain_filtering(single_target)
            callee_chains = single_target.using_callee_chains
            all_callee_chains = set()
            if callee_chains:
                for chain in callee_chains:
                    single_chain = ' -> '.join([i.name for i in chain])
                    all_callee_chains.add(single_chain)
            all_callee_chains = list(all_callee_chains)
            
            module_preprocessed = {
                'module_name': module_name,
                'module_content': module_content,
                'target_function_content': single_target.content,
                'called_functions': '\n'.join([i.name for i in single_target.called_functions]) if single_target.called_functions else 'empty',
                'branch_related_called_functions': '\n'.join([i.name for i in single_target.branch_related_called_functions]) if single_target.branch_related_called_functions else 'empty',
                'callee_chains': '\n\n'.join(all_callee_chains) if all_callee_chains else 'empty'
            }
            module_preprocess_writer.write(json.dumps(module_preprocessed) + '\n')
            module_preprocess_writer.flush()
        module_preprocess_writer.flush()
        module_preprocess_writer.close()


def run(date, proj_base, part, api_base, json_res_file, module_preprocess_dir, obj_origin_res_file, obj_after_res_file, module_after_res_dir, debugging_mode=False):
    os.makedirs(module_preprocess_dir, exist_ok=True)
    
    all_modules, classes_dict, functions_dict = get_modules(proj_base, good_modules_path)
    setup_all_modules(all_modules, classes_dict, functions_dict)

    # # save all modules to pickle
    # with open(obj_origin_res_file, 'wb') as f:
    #     pickle.dump(all_modules, f)
    
    # with open(obj_origin_res_file, 'rb') as f:
    #     all_modules = pickle.load(f)
        
    json_writer = open(
        json_res_file,
        "w",
        # encoding="utf-8",
    )
    
    part1_module = []
    part2_module = []
    part3_module = []
    part4_module = []
    module_wheel = [part1_module, part2_module, part3_module, part4_module]
    module_callable_dict = defaultdict()
    
    all_callable_function_number = 0
    for tmp_tmp_module in all_modules:
        callable_functions = [i for i in tmp_tmp_module.functions if i.is_target == True and 0 < len(i.covered_lines) < len(i.line_range)]
        all_callable_function_number += len(callable_functions)
        module_callable_dict[tmp_tmp_module.name] = len(callable_functions)
    threshold = all_callable_function_number / 4
    current_number = 0
    current_index = 0
    for tmp_tmp_module in all_modules:
        if current_number <= threshold + 1:
            module_wheel[current_index].append(tmp_tmp_module)
            current_number += module_callable_dict[tmp_tmp_module.name]
        else:
            current_index += 1
            module_wheel[current_index].append(tmp_tmp_module)
            current_number = module_callable_dict[tmp_tmp_module.name]
            
    total = 0
    usable = 0
    all_parts = {'part1': part1_module, 
                 'part2': part2_module, 
                 'part3': part3_module, 
                 'part4': part4_module
                }
    runnable_modules = []
    print(len(part1_module))
    print(len(part2_module))
    print(len(part3_module))
    print(len(part4_module))
    # exit()
    run_parts = [i for i in part.split(',') if i != '']
    for to_be_run in run_parts:
        runnable_modules.extend(all_parts[to_be_run])
    # if half == 'prev':
    #     runnable_modules = all_modules[:200]
    # else:
    #     runnable_modules = all_modules[200:]
    # runnable_modules = all_modules
    for single_module in runnable_modules:
        module_name = single_module.name
        module_content = single_module.content
        module_dir = single_module.module_dir
        module_path = single_module.module_path
        
        name_2_class = classes_dict[module_name]
        name_2_function = functions_dict[module_name]
        
        module_after_res = os.path.join(module_after_res_dir, module_name + '.pkl')
        
        module_tmp_dir = os.path.join(tmp_dir_for_test, module_name)
        
        # 拿到当前module里所有的函数
        all_functions_in_module = single_module.functions
        
        total += 1
        callable_functions = [i for i in all_functions_in_module if i.is_target == True and 0 < len(i.covered_lines) < len(i.line_range)]
        
        if callable_functions:
            usable += 1
            report_dir = os.path.join(base_report, date, module_name)
            case_dir = os.path.join(base_cases, date, module_name)
            os.makedirs(report_dir, exist_ok=True)
            os.makedirs(case_dir, exist_ok=True)
        
        print(f"{module_name}: {len(callable_functions)} callable functions.")
        record_module_info(callable_functions, module_preprocess_dir, module_content, module_name)
        
        # continue
        case_index = -1
        total_start_time = time.time()
        for single_target in callable_functions:
            print(single_target.name)
            single_target_start_time = time.time()
            '''
            对于每个target，先去它的direct program找，没有的话就去indirect program找，还没有的话就直接生成新的
            direct program是直接调用了该函数的
                    1. 有的话直接利用这个生成，没有的话转下一步
            indirect program是该函数calee chain上的函数对应的direct program
                    1. 遍历每个calee chain，由于我们的chain是冗余的，只考虑起点函数就可以了
                    2. 对于每个起点函数，找它的direct program
                    3. 有的话就用这个生成，没有的话就换下一个chain
                    4. chain遍历结束以后转下一步
                直接用context信息以及called chain的dependency生成新的
                
                notes:  1. 这个过程里涉及到chain的过滤，包括在第二步中过滤掉覆盖较高的chain和第三步中过滤掉分支无关的chain
                        2. 从哪个函数选的seed program，就更新哪个函数的test program属性
            '''
            try:
                generated = False
                
                strtegies = {
                    #有直接调用的测试样例
                    'direct': list(),
                    'indirect': list(),  
                    'new': list()
                }
                
                is_direct_available = True if single_target.direct_programs else False
                
                # 处理可选的链
                called_chain_filtering(single_target)
                available_callee_chains = [i for i in single_target.using_callee_chains if i[0].direct_programs]
                # available_callee_chains = [i for i in single_target.callee_chains if i[0].direct_programs]
                is_indirect_available = True if available_callee_chains else False
                
                all_conditions = [is_direct_available, is_indirect_available]
                
                direct_selected_examples = list()
                
                prompt_cache_dict = {}
                
                while any(all_conditions):
                    chosen_strategy = None
                    if is_direct_available:
                        candidate_programs = [i for i in single_target.direct_programs if i not in direct_selected_examples]
                        is_direct_available = True if candidate_programs else False
                    
                    # 处理可选的链
                    if is_indirect_available:
                        called_chain_filtering(single_target)
                        available_callee_chains = [i for i in single_target.using_callee_chains if i[0].direct_programs]
                        is_indirect_available = True if available_callee_chains else False
                
                
                    if is_direct_available and single_target.direct_programs:
                        
                        selected_examples = select_examples(single_target, candidate_programs)
                        direct_selected_examples.extend(selected_examples)
                        
                        # selected_examples = select_examples(single_target, single_target.direct_programs)
                        
                        context = construct_context(single_target, name_2_class, chosen_chain=None)
                        prompt = construct_prompt_from_direct_program(single_target, selected_examples)
                        
                        chosen_strategy = 'direct'
                        generated = True
                        
                    elif is_indirect_available and available_callee_chains:
                        # 现在是随机选择一个chain
                        chosen_chain = random.choice(available_callee_chains)

                        single_target.used_callee_chains.append(chosen_chain)
                        start_function = chosen_chain[0]
                        
                        # 注意这里用的是start_function的direct program
                        selected_examples = select_examples(single_target, start_function.direct_programs)
                        
                        context = construct_context(single_target, name_2_class, chosen_chain)
                        prompt = construct_prompt_from_calee_program(single_target, selected_examples, chosen_chain)
                        
                        chosen_strategy = 'indirect'
                        generated = True
                    
                    if chosen_strategy is None:
                        break  # As no strategy was chosen, exit the loop.

                    if not debugging_mode:
                        chat_bot = ChatBot(api_base)
                        stage1_prompt = construct_summarize_function_prompt(single_target, module_name, context)
                        
                        if stage1_prompt in prompt_cache_dict.keys():
                            stage1_response = prompt_cache_dict.get(stage1_prompt)
                        else:
                            stage1_response = invoke_llm_cache(chat_bot, stage1_prompt, stage1_response=None, stage2_prompt=None)
                            prompt_cache_dict[stage1_prompt] = stage1_response
                        
                        new_prop = f"{stage1_prompt}\n{stage1_response}\n{prompt}"
                        if new_prop in prompt_cache_dict.keys():
                            stage2_response = prompt_cache_dict.get(new_prop)
                            code_content = '' 
                            test_cases = []
                        else:
                            stage2_response = invoke_llm_cache(chat_bot, stage1_prompt, stage1_response, prompt)
                            prompt_cache_dict[new_prop] = stage2_response
                            code_content, test_cases = reindent_model_output(stage2_response)
                    else:
                        stage1_prompt = ''
                        stage1_response =  ''
                        stage2_response = example_response

                    # code_content, test_cases = reindent_model_output(stage2_response)
                    
                    # 为每个module提取出一批可用的imports。1.从模型输出里提取，没有的话2.TODO:从原有case里提取
                    try:
                        processed_imports = extract_imports_for_llm(code_content)
                    except:
                        processed_imports = []

                    if 'import timeout_decorator' not in processed_imports:
                        processed_imports.append('import timeout_decorator')
                    if 'import sys' not in processed_imports:
                        processed_imports.append('import sys')
                    if 'import unittest' not in processed_imports:
                        processed_imports.append('import unittest')
                    if 'import os' not in processed_imports:
                        processed_imports.append('import os')
                    # if 'import request' not in processed_imports:
                    #     processed_imports.append('import request')
                    
                    origin_target_coverage = copy.deepcopy(single_target.get_covered_lines())
                    origin_cov_rate = len(single_target.get_covered_lines()) / len(single_target.line_range)
                    
                    current_time = time.time()
                    single_target_time = current_time - single_target_start_time
                    total_time = current_time - total_start_time
                    
                    wrong_cases = []
                    wrong_output = []
                    for index, test_case in enumerate(test_cases):
                        case_index += 1
                        test_file, test_content = assemble_test_file(module_dir, module_name, case_index, processed_imports, test_case)
                    
                        run_output, report_output, coverage = run_test_and_collect_cov(module_dir, module_path, test_file, report_dir, case_index, module_tmp_dir)

                        os.system(f'mv {test_file} {case_dir}/test_case_{case_index}.py')
                        
                        
                        if coverage is not None:
                            new_test_case = TestProgram(content=test_content, target_function=single_target, coverage=coverage, single_target_time=single_target_time, total_time=total_time)

                            case_called_functions = extract_called_functions(test_content)
                    
                            for caller, called_name in case_called_functions:
                                # 如果存在的话，在当前module的function dict里找对应的函数
                                called_function = name_2_function.get(called_name)
                                
                                # 如果找到了，则加入called function
                                if called_function:
                                    new_test_case.add_called_function(called_function)
                                    called_function.add_direct_program(new_test_case)
                            
                            covered_by_case = coverage['exec']
            
                            for single_func_in_module in all_functions_in_module:
                                covered_by_case_in_target = covered_by_case.intersection(single_func_in_module.line_range)
                                if len(covered_by_case_in_target) > 0: 
                                    single_func_in_module.add_covered_lines(covered_by_case_in_target)
                        
                        wrong_output.append(run_output)
                        wrong_cases.append(test_content)

                    new_candidate_callable_functions = [i for i in all_functions_in_module if i.is_target == True and 0 < len(i.covered_lines) < len(i.line_range)]
                    new_callable_functions = [i for i in new_candidate_callable_functions if i not in callable_functions]
                    
                    callable_functions.extend(new_callable_functions)
        
                    if len(single_target.get_covered_lines() - origin_target_coverage) > 0:
                        res = 'better!'
                    else:
                        res = 'useless!'
                                        
                    after_cov_rate = len(single_target.get_covered_lines()) / len(single_target.line_range)
                    
                    if after_cov_rate == 1:
                        break
                        
                    strtegies[chosen_strategy].append(single_target.get_covered_lines())
                                
                    is_direct_available = not are_last_three_sets_same(strtegies['direct'])
                    is_indirect_available = not are_last_three_sets_same(strtegies['indirect'])
                
                    expr_info = {
                        'module_name': module_name,
                        "res": res,
                        "target_function_name": single_target.name,
                        'wrong_output': '\n\n'.join(wrong_output),
                        "origin_cov_rate": origin_cov_rate,
                        "after_cov_rate": after_cov_rate,
                        # 'module_content': module_content,
                        'module_dir': module_dir,
                        'module_path': module_path,
                        "target_function_content": single_target.content,
                        "stage1_prompt": stage1_prompt,
                        "stage1_response": stage1_response,
                        "stage2_prompt": prompt,
                        "stage2_response": stage2_response,
                        "code_content": code_content,
                        "test_cases": '\n\n'.join(test_cases),
                        "processed_imports": '\n\n'.join(processed_imports),
                        'wrong_cases': '\n\n'.join(wrong_cases)
                    }
                    json_writer.write(json.dumps(expr_info) + '\n')
                    json_writer.flush()
                pass
            
                if not generated:
                    expr_info = {
                        'module_name': module_name,
                        "res": 'No program generated.',
                        "target_function": single_target.name,
                        # 'module_content': module_content,
                        'module_dir': module_dir,
                        'module_path': module_path
                    }
                    json_writer.write(json.dumps(expr_info) + '\n')
                    json_writer.flush()
            except Exception as e:
                expr_info = {
                        'module_name': module_name,
                        "res": 'Function error: ' + str(e),
                        "target_function": single_target.name,
                        # 'module_content': module_content,
                        'module_dir': module_dir,
                        'module_path': module_path,
                }
                print("Stack Trace:\n", traceback.format_exc())
                json_writer.write(json.dumps(expr_info)+ '\n')
                json_writer.flush()
        pass
    
        with open(module_after_res, 'wb') as fr:
            pickle.dump(single_module, fr)
    
    print(f"Total: {total}, Usable: {usable}")
    # exit()
    json_writer.flush()
    json_writer.close()
   
    #  Save all modules to pickle
    with open(obj_after_res_file, 'wb') as f:
        pickle.dump(all_modules, f)
    

if __name__ == '__main__':
    proj_base = benchmark_base
    
    base_existing_cases_path = sys.argv[1]
    # '/path/to/existing_test_cases/test_case_codamosa_0223_codamosa_stall_120'
    # '/data/yangchen/dingyuquan/llm_test_cases/test_case_codamosa_0223_codamosa_stall_120'
    
    part = sys.argv[2]
    # 'part1,'
    # 'part1,part2'
    # 'part1,part2,part3,part4'
    
    api_base = sys.argv[3]
    # http://host_ip:port/v1

    date = base_existing_cases_path.split('/')[-1].replace('test_case_', '') + '_' + part.replace(',', '_')
  
    code_base = os.path.abspath(os.path.dirname(__file__))

    json_res_file = os.path.join(code_base, 'data', 'res_info', f'{date}.jsonl')
   
    module_preprocess_dir = os.path.join(code_base, 'data', 'module_preprocess_res', date)
  
    obj_origin_res_file = os.path.join(code_base, 'data', 'res_obj', f'{date}_origin.pkl')
 
    obj_after_res_file = os.path.join(code_base, 'data', 'res_obj', f'{date}_after.pkl')

    module_after_res_dir = os.path.join(code_base, 'data', 'res_obj', date)
    if not os.path.exists(module_after_res_dir):
        os.makedirs(module_after_res_dir)
    
    tmp_dir_for_test = os.path.join(code_base, 'data', f'tmp_dir_{date}')
    os.makedirs(tmp_dir_for_test, exist_ok=True)

    run(date, proj_base, part, api_base, json_res_file, module_preprocess_dir, obj_origin_res_file, obj_after_res_file, module_after_res_dir, debugging_mode=False)

            
# # 1. 从module的所有函数里选择一个待测的 target function
# function_roulette_wheel = RouletteWheelSelection(all_callable_options)
# chosen_function = function_roulette_wheel.select_item()

