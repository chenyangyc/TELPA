import pickle
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from glob import glob
import os
import json
import scipy.stats as stats


def load_file_results(res_file):
    with open(res_file, 'rb') as f:
        res = pickle.load(f)
    return res

def load_dir_results(res_dirs):
    res = []
    for single_dir in res_dirs:
        all_res_objs = glob(os.path.join(single_dir, '*.pkl'))
        for single_res_file in all_res_objs:
            with open(single_res_file, 'rb') as f:
                single_module_res = pickle.load(f)
                res.append(single_module_res)
    return res


def is_func_target(function):
    chains = [i for i in func.callee_chains if i[0].direct_programs]
    
    has_chain = False
    
    for single_chain in chains:
        start_func = single_chain[0]
        for single_p in start_func.direct_programs:
            if len(single_p.coverage['exec'].intersection(func.line_range)) > 0:
                has_chain = True
                break
                
    has_case = False 
    if func.direct_programs:
        for single_p in func.direct_programs:
            if len(single_p.coverage['exec'].intersection(func.line_range)) > 0:
                has_case = True
                break
    
    is_target = False
    if func.is_target and 0 < len(func.covered_lines) < len(func.line_range) and (has_chain or has_case):
        is_target = True
    
    return is_target
        
def collect_func_cov(function):
    all_executed_lines = set()
    all_lines = set()
    all_executed_branch = set()
    all_branches = set()
    direct_programs = function.direct_programs
    if direct_programs:
        for p in direct_programs:
            single_cov = p.coverage
    
            executed_lines = single_cov['exec']
            missing_lines = single_cov['miss']
            executed_branches = set([str(i) for i in single_cov['exec_branch']])
            missing_branches = set([str(i) for i in single_cov['miss_branch']])
            
            all_executed_lines.update(executed_lines)
            all_lines.update(executed_lines)
            all_lines.update(missing_lines)
            
            all_executed_branch.update(executed_branches)
            all_branches.update(executed_branches)
            all_branches.update(missing_branches)
                
    try:
        new_programs = function.new_programs
    except:
        new_programs = []
    if new_programs:
        for p in new_programs:
            single_cov = p.coverage
    
            executed_lines = single_cov['exec']
            missing_lines = single_cov['miss']
            executed_branches = set([str(i) for i in single_cov['exec_branch']])
            missing_branches = set([str(i) for i in single_cov['miss_branch']])
            
            all_executed_lines.update(executed_lines)
            all_lines.update(executed_lines)
            all_lines.update(missing_lines)
    
            all_executed_branch.update(executed_branches)
            all_branches.update(executed_branches)
            all_branches.update(missing_branches)
    pass
    return all_executed_lines, all_lines, all_executed_branch, all_branches

      

run_type = 'p'

code_base = '/data/yangchen/llm4unit/'

if run_type == 'p':
    pynguin_all_context_dir = glob(code_base + 'data/res_obj/all_context_pynguin_0224_pynguin_stall_120_*')
    pynguin_all_context = load_dir_results(pynguin_all_context_dir)
    
    pynguin_stall_file = code_base + 'data/res_obj/pynguin_stall_120_origin.pkl'
    pynguin_stall = load_file_results(pynguin_stall_file)
    
    pynguin_baseline_file = code_base + 'data/res_obj/pynguin_1200_origin.pkl'
    pynguin_baseline = load_file_results(pynguin_baseline_file)
    
    pynguin_our_dir = glob(code_base + 'data/res_obj/pynguin_0224_pynguin_stall_120_*')
    pynguin_our = load_dir_results(pynguin_our_dir)

else:
    codamosa_no_feedback_dir = glob(code_base + 'data/res_obj/no_feedback_codamosa_0223_codamosa_stall_120_*')
    codamosa_no_feedback = load_dir_results(codamosa_no_feedback_dir)
    
    codamosa_no_forward_dir = glob(code_base + 'data/res_obj/no_forward_codamosa_0223_codamosa_stall_120_*')
    codamosa_no_forward = load_dir_results(codamosa_no_forward_dir)
    
    # codamosa_no_context_dir = glob(code_base + 'data/res_obj/no_context_codamosa_0223_codamosa_stall_120_*')
    # codamosa_no_context = load_dir_results(codamosa_no_context_dir)
    
    codamosa_no_shot_dir = glob(code_base + 'data/res_obj/no_shot_codamosa_0223_codamosa_stall_120_*')
    codamosa_no_shot = load_dir_results(codamosa_no_shot_dir)
    
    # codamosa_random_shot_dir = glob(code_base + 'data/res_obj/random_shot_codamosa_0223_codamosa_stall_120_*')
    # codamosa_random_shot = load_dir_results(codamosa_random_shot_dir)
    
    # codamoda_all_context_dir = glob(code_base + 'data/res_obj/all_context_codamosa_0223_codamosa_stall_120_*')
    # codamoda_all_context = load_dir_results(codamoda_all_context_dir)
    
    codamosa_stall_file = code_base + 'data/res_obj/codamosa_stall_120_origin.pkl'
    codamosa_stall = load_file_results(codamosa_stall_file)
    
    codamosa_baseline_file = code_base + 'data/res_obj/codamosa_600_origin.pkl'
    codamosa_baseline = load_file_results(codamosa_baseline_file)
    
    codamosa_our_file = code_base + 'data/res_obj/codamosa_stall_120_after.pkl'
    codamosa_our = load_file_results(codamosa_our_file)
    
    codamosa_ds_dir = glob(code_base + 'data/res_obj/deepseek_codamosa*')
    codamosa_ds = load_dir_results(codamosa_ds_dir)
    
scratch_dir = code_base + 'data/res_obj/new'
scratch = load_dir_results([scratch_dir])

# scratch_dir = glob(code_base + 'data/res_obj/new_2_*')
# scratch = load_dir_results(scratch_dir)

# print(len(codamosa_no_feedback), len(codamosa_no_forward), len(codamosa_no_context), len(codamosa_no_shot), len(codamosa_random_shot), len(codamoda_all_context), len(codamosa_stall), len(codamosa_baseline), len(codamosa_our), len(scratch))

# main_names = ['codamosa_stall', 'codamosa_baseline', 'codamoda_all_context', 'codamosa_our', 'scratch']
# main_res = [codamosa_stall, codamosa_baseline, codamoda_all_context, codamosa_our, scratch]

# print(len(codamosa_stall), len(codamosa_baseline), len(codamosa_our), len(scratch))

if run_type == 'p':
    stall_key = 'pynguin_stall'
    our_key = 'pynguin_our'
    
    main_names = ['pynguin_stall', 'pynguin_baseline', 'pynguin_all_context', 'pynguin_our', 'scratch']
    main_res = [pynguin_stall, pynguin_baseline, pynguin_all_context, pynguin_our, scratch]
else:
    stall_key = 'codamosa_stall'
    our_key = 'codamosa_our'
    main_names = ['codamosa_stall', 'codamosa_baseline', 'codamosa_our', 'scratch']
    main_res = [codamosa_stall, codamosa_baseline, codamosa_our, scratch]
    main_names = ['codamosa_stall', 'codamosa_baseline', 'codamosa_our', 'codamosa_no_feedback', 'codamosa_no_forward', 'codamosa_no_shot','scratch', 'codamosa_ds']
    main_res = [codamosa_stall, codamosa_baseline, codamosa_our, codamosa_no_feedback, codamosa_no_forward, codamosa_no_shot, scratch, codamosa_ds]



all_module_dict = defaultdict()
for name, res_obj in zip(main_names, main_res):
    all_module_dict[name] = defaultdict()
    for i in res_obj:
        all_module_dict[name][i.name] = i


stall_dict = all_module_dict[stall_key]

all_modules_total_cov = defaultdict()

benchmark_total_methods = 0
for module_name, origin_module_info in stall_dict.items():
    if module_name not in all_modules_total_cov:
        all_modules_total_cov[module_name] = defaultdict()
        
    module_info_dict = defaultdict()
    for single_tech in main_names:
        module_info_dict[single_tech] = all_module_dict[single_tech].get(module_name, origin_module_info)
    
    func_info_dict = defaultdict()
    for single_tech, single_module_info in module_info_dict.items():
        func_dict = {}
        for i in single_module_info.functions:
            func_dict[i.content] = i
        func_info_dict[single_tech] = func_dict
    
    all_lines = set()
    all_branches = set()
    
    has_target = False
    for func in origin_module_info.functions:
        benchmark_total_methods += 1
        func_content = func.content
        target = is_func_target(func)
        is_useful = False
        is_covered_after = False
        
        scratch_func = func_info_dict['scratch'].get(func_content)

        if scratch_func is not None and len(func.covered_lines) == 0 and len(scratch_func.covered_lines) > 0:
            is_useful = True
        
        if scratch_func is not None and len(scratch_func.covered_lines) > 0:
            is_useful = True


        if target:
            has_target = True
            
            for tech_name, single_func_dict in func_info_dict.items():
                
                if tech_name == 'scratch':
                    tech_keys = [our_key, tech_name]
                   
                else:
                    tech_keys = [tech_name]
                
                for tech_key in tech_keys:
                    if tech_key not in all_modules_total_cov[module_name]:
                        all_modules_total_cov[module_name][tech_key] = {
                                                                        'exec_lines': set(),
                                                                        'exec_branches': set()
                                                                        }
                    
                    single_func = single_func_dict.get(func_content)
                    if single_func is not None:
                        executed_lines, lines, executed_branch, branches = collect_func_cov(single_func)
                        all_modules_total_cov[module_name][tech_key]['exec_lines'].update(executed_lines)
                        all_modules_total_cov[module_name][tech_key]['exec_branches'].update(executed_branch)
                        
                        # if tech_name == 'scratch':
                        #     if is_useful:
                        #         if 'scratch' not in all_modules_total_cov[module_name]:
                        #             all_modules_total_cov[module_name]['scratch'] = {
                        #                                 'exec_lines': set(),
                        #                                 'exec_branches': set()
                        #                             }
                        #         all_modules_total_cov[module_name]['scratch']['exec_lines'].update(executed_lines)
                        #         all_modules_total_cov[module_name]['scratch']['exec_branches'].update(executed_branch)
                        #     else:
                        #         continue
                    
                        all_lines.update(lines)
                        all_branches.update(branches)
    
    # if 'scratch' not in all_modules_total_cov[module_name]:
    #     all_modules_total_cov[module_name]['scratch'] = {
    #         'exec_lines': set(),
    #         'exec_branches': set()
    #     }
    all_modules_total_cov[module_name].update({
        "all_lines": all_lines,
        "all_branches": all_branches
    })
   
    if not has_target and module_name in all_modules_total_cov:
        del all_modules_total_cov[module_name]
pass

project_coverage = defaultdict()

bench_mark_total_lines = 0
for module_name, cov_info in all_modules_total_cov.items():
    all_lines = cov_info['all_lines']
    all_branches = cov_info['all_branches']
    bench_mark_total_lines += len(all_lines)
    
    project_name = module_name.split('.')[0]
    if project_name not in project_coverage:
        project_coverage[project_name] = defaultdict()
    
    for tech_name, tech_cov in cov_info.items():
        if tech_name in ['all_lines', 'all_branches']:
            continue
        
        if tech_name not in project_coverage[project_name]:
            project_coverage[project_name][tech_name] = {
                'exec_lines': 0,
                'exec_branches': 0,
                'all_lines': 0,
                'all_branches': 0
            }
            
        exec_lines = tech_cov['exec_lines']
        exec_branches = tech_cov['exec_branches']
   
        project_coverage[project_name][tech_name]['exec_lines'] += len(exec_lines)
        project_coverage[project_name][tech_name]['exec_branches'] += len(exec_branches)
        project_coverage[project_name][tech_name]['all_lines'] += len(all_lines)
        project_coverage[project_name][tech_name]['all_branches'] += len(all_branches)

print(f"Total lines: {bench_mark_total_lines}")
print(f"Total methods: {benchmark_total_methods}")


project_total = 0
project_better = 0

project_rate = defaultdict()
project_bottle = []
project_new_rate = []
project_baseline_rate = []

for project_name, project_tech_cov in project_coverage.items():
    if project_name not in project_rate:
        project_rate[project_name] = defaultdict()
    
    for tech_name, tech_cov in project_tech_cov.items():
        all_line = tech_cov['all_lines']
        all_branch = tech_cov['all_branches']
        
        exec_line = tech_cov['exec_lines']
        exec_branch = tech_cov['exec_branches']
        
        try:
            line_rate = exec_line / all_line
        except:
            line_rate = 0
        try:
            branch_rate = exec_branch / all_branch
        except:
            branch_rate = 0
        project_rate[project_name][tech_name] = {
            'line_rate': line_rate,
            'branch_rate': branch_rate
        }


for project_name, tech_cov in project_rate.items():
    first_column = True
    for tech_name, cov_rate in tech_cov.items():
        if first_column:
            print(f" ,{tech_name},", end='')
            first_column = False
        else:
            print(f"{tech_name},", end='')
    break
print()

tech_average_line = defaultdict(list)
for project_name, tech_cov in project_rate.items():
    first_column = True
    for tech_name, cov_rate in tech_cov.items():
        if first_column:
            print(f"{project_name}, {cov_rate['line_rate']}, ", end='')
            first_column = False
        else:
            print(f"{cov_rate['line_rate']}, ", end='')
        tech_average_line[tech_name].append(cov_rate['line_rate'])
    print()

first_column = True
for tech_name, cov in tech_average_line.items():
    if first_column:
        print(f' , {str(np.mean(cov))}, ', end='')
        first_column = False
    else:
        print(f"{str(np.mean(cov))}, ", end='')
print()
print()

# first_column = True
# for tech_name, cov in tech_average_line.items():
#     if tech_name == our_key:
#         print(f"0, ", end='')
#         continue
#     statistic, p_value = stats.wilcoxon(cov, tech_average_line[our_key])
#     if first_column:
#         print(f' , {p_value:.2e}, ', end='')
#         first_column = False
#     else:
#         print(f"{p_value:.2e}, ", end='')
# print()
# print()


for project_name, tech_cov in project_rate.items():
    first_column = True
    for tech_name, cov_rate in tech_cov.items():
        if first_column:
            print(f" ,{tech_name},", end='')
            first_column = False
        else:
            print(f"{tech_name},", end='')
    break
print()

tech_average_branch = defaultdict(list)
for project_name, tech_cov in project_rate.items():
    first_column = True
    for tech_name, cov_rate in tech_cov.items():
        if first_column:
            print(f"{project_name}, {cov_rate['branch_rate']}, ", end='')
            first_column = False
        else:
            print(f"{cov_rate['branch_rate']}, ", end='')
        tech_average_branch[tech_name].append(cov_rate['branch_rate'])
    print()

first_column = True
for tech_name, cov in tech_average_branch.items():
    if first_column:
        print(f' , {str(np.mean(cov))}, ', end='')
        first_column = False
    else:
        print(f"{str(np.mean(cov))}, ", end='')
print()


# first_column = True
# for tech_name, cov in tech_average_branch.items():
#     if tech_name == our_key:
#         print(f"0, ", end='')
#         continue
#     statistic, p_value = stats.wilcoxon(cov, tech_average_branch[our_key])
#     if first_column:
#         print(f' , {p_value:.2e}, ', end='')
#         first_column = False
#     else:
#         print(f"{p_value:.2e}, ", end='')
# print()
# print()




unique_covered_regions = defaultdict()
for module_name, cov_info in all_modules_total_cov.items():
    for tech_name, tech_cov in cov_info.items():
        if tech_name in ['all_lines', 'all_branches']:
            continue
        
        if tech_name not in unique_covered_regions:
            unique_covered_regions[tech_name] = {
                "lines": set(),
                "branches": set()
            }
        
            
        exec_lines = set([str(i) + module_name for i in list(tech_cov['exec_lines'])])
        exec_branches = set([str(i) + module_name for i in list(tech_cov['exec_branches'])])

        unique_covered_regions[tech_name]["lines"].update(exec_lines)
        unique_covered_regions[tech_name]["branches"].update(exec_branches)

# venn_techs = ['pynguin_baseline', 'pynguin_all_context', 'pynguin_our']

# from matplotlib_venn import venn3

# for types in ['lines', 'branches']:
# # types = 'branches'
#     plt.clf()
#     if types == 'lines':
#         set1 = unique_covered_regions['pynguin_baseline']['lines']
#         set2 = unique_covered_regions['pynguin_all_context']['lines']
#         set3 = unique_covered_regions['pynguin_our']['lines']
#     else:
#         types == 'branches'
#         set1 = unique_covered_regions['pynguin_baseline']['branches']
#         set2 = unique_covered_regions['pynguin_all_context']['branches']
#         set3 = unique_covered_regions['pynguin_our']['branches']

#     # Define colors for each subset
#     colors = {'10': '#82e2b6', '01': '#80e2fc', '11': '#00d0cf'}

#     # Example data
#     A = set1
#     B = set2
#     C = set3

#     A_num = len(A)
#     # Draw the Venn diagram
#     venn = venn3([A_num, A_num, A_num, A_num * 0.8, A_num * 0.8, A_num * 0.8, A_num * 0.4], set_labels=('Pynguin', 'LLM', 'Our'), set_colors=('#9cd3b4', '#feebb0', '#99daf6'))

#     A_B_C = A.difference(B).difference(C)
#     B_A_C = B.difference(A).difference(C)
#     AB_C = A.intersection(B).difference(C)
#     C_B_A = C.difference(B).difference(A)
#     AC_B = A.intersection(C).difference(B)
#     BC_A = B.intersection(C).difference(A)
#     ABC = A.intersection(B).intersection(C)

#     A_B_C_label = str(len(A_B_C))
#     B_A_C_label = str(len(B_A_C))
#     AB_C_label = str(len(AB_C))
#     C_B_A_label = str(len(C_B_A))
#     AC_B_label = str(len(AC_B))
#     BC_A_label = str(len(BC_A))
#     # if types == 'branches':
#     #     ABC_label = str(len(ABC) + 469)
#     # else:
#     #     ABC_label = str(len(ABC) + 1626)
#     ABC_label = str(len(ABC))

#     regions = {
#         '100': A_B_C_label,
#         '010': B_A_C_label,
#         '001': C_B_A_label,
#         '110': AB_C_label,
#         '101': AC_B_label,
#         '011': BC_A_label,
#         '111': ABC_label
#     }

#     for key, label in regions.items():
#         if venn.get_label_by_id(key) is not None:
#             venn.get_label_by_id(key).set_text("")

#     # for text in venn.subset_labels:
#     #     text.set_text("")

#     # # Customize subset colors and sizes
#     venn.get_patch_by_id('110').set_color('#cbdd8b')
#     venn.get_patch_by_id('101').set_color('#58c5c8')
#     venn.get_patch_by_id('011').set_color('#95d1c9')
#     venn.get_patch_by_id('111').set_color('#73c8b3')
    
#     venn.get_patch_by_id('01').set_color(colors['01'])
#     venn.get_patch_by_id('11').set_color(colors['11'])

#     # Display the number of items within each subset
#     plt.text(-0.5, 0.2, A_B_C_label, fontsize=20, color='black')
#     plt.text(-0.05, 0.2, AB_C_label, fontsize=20, color='black')
#     plt.text(0.3, 0.2, B_A_C_label, fontsize=20, color='black')

#     plt.text(-0.1, -0.05, ABC_label, fontsize=20, color='black')

#     plt.text(-0.3, -0.2, AC_B_label, fontsize=20, color='black')
#     plt.text(0.15, -0.2, BC_A_label, fontsize=20, color='black')

#     plt.text(-0.1, -0.45, C_B_A_label, fontsize=20, color='black')

#     for text in plt.gca().texts:
#         text.set_fontsize(18)

#     plt.tight_layout()
#     # plt.title("The covered lines by CodaMOSA and Ours")
#     # 显示图形
#     plt.savefig(code_base + f'data/reports/res_pynguin_{types}_venn.png')