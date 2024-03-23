

def select_examples(target_function, all_programs):
    selected_examples = list()
    line_range = target_function.line_range

    chosen_covered_lines = set()
    # find the test with highest cov rate
    for single_case in all_programs:
        executed_lines = single_case.coverage['exec']
        
        function_executed_lines = executed_lines.intersection(line_range)
        function_executed_rate = len(function_executed_lines) / len(line_range)
        
        single_case.set_single_func_cov_lines(function_executed_lines)
        single_case.set_single_func_cov_rate(function_executed_rate)

    # 按cov从大到小排序
    sorted_by_cov = sorted(all_programs, key=lambda x: x.single_func_cov_rate)

    for single_case in all_programs:
        if len(selected_examples) > 5:
            break
        if len(single_case.single_func_cov_lines - chosen_covered_lines) > 0:
            selected_examples.append(single_case)
            chosen_covered_lines = chosen_covered_lines.union(single_case.single_func_cov_lines)
    
    return selected_examples
   