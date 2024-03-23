from itertools import groupby
from io import StringIO
import ast
import astor
from core.ast_objs import FunctionDefVisitor
import re


def construct_all_context(target_function, module_content):
    target_content = target_function.content
    prev_context = module_content.split(target_content)[0] + '\n\n' + target_content
    return prev_context


def construct_context_no_forward(target_function, name_2_class, chosen_chain=None):
    # TODO: called_functions / branch_related_called_functions
    # chosen_called_functions = target_function.called_functions
    chosen_called_functions = set()
    
    if chosen_chain is None:
        chosen_calee_functions = set()
    else:
        chosen_calee_functions = set(chosen_chain)
    
    chosen_context_functions = chosen_called_functions.union(chosen_calee_functions)
    chosen_context_functions = chosen_context_functions.union({target_function})
    all_classes = set([i.belong_class for i in chosen_context_functions])
    
    # 对对象列表按照属性 belong_class 进行排序
    sorted_functions = sorted(chosen_context_functions, key=lambda obj: (obj.belong_class is None, obj.belong_class))

    # 使用 groupby 进行分组
    grouped_functions = {key: list(group) for key, group in groupby(sorted_functions, key=lambda obj: obj.belong_class)}

    # 输出结果
    all_content = []
    for belong_class, functions in grouped_functions.items():
        class_content = ''
        class_content = StringIO(class_content)

        if belong_class is not None:
            class_obj = name_2_class[belong_class]
            
            class_declare = class_obj.content.split('\n')[0]
            class_init = class_obj.init[0] if class_obj.init else None


            class_content.write(class_declare.strip())
            class_content.write('\n')
            if class_init is not None:
                for i in class_init.split('\n'):
                    if i.strip() == '':
                        continue
                    class_content.write('    ' + i)
                    class_content.write('\n')
                    
            class_content.write('\n')

        for func in functions:
            func_content = func.content
            for i in func_content.split('\n'):
                if i.strip() == '':
                    continue
                class_content.write('    ' + i)
                class_content.write('\n')
            class_content.write('\n')
            pass
        all_content.append(class_content.getvalue())
        class_content.close()
    final_context = '\n'.join(all_content)
    return final_context



def construct_context(target_function, name_2_class, chosen_chain=None):
    # TODO: called_functions / branch_related_called_functions
    # chosen_called_functions = target_function.called_functions
    chosen_called_functions = target_function.branch_related_called_functions
    
    if chosen_chain is None:
        chosen_calee_functions = set()
    else:
        chosen_calee_functions = set(chosen_chain)
    
    chosen_context_functions = chosen_called_functions.union(chosen_calee_functions)
    chosen_context_functions = chosen_context_functions.union({target_function})
    all_classes = set([i.belong_class for i in chosen_context_functions])
    
    # 对对象列表按照属性 belong_class 进行排序
    sorted_functions = sorted(chosen_context_functions, key=lambda obj: (obj.belong_class is None, obj.belong_class))

    # 使用 groupby 进行分组
    grouped_functions = {key: list(group) for key, group in groupby(sorted_functions, key=lambda obj: obj.belong_class)}

    # 输出结果
    all_content = []
    for belong_class, functions in grouped_functions.items():
        class_content = ''
        class_content = StringIO(class_content)

        if belong_class is not None:
            class_obj = name_2_class[belong_class]
            
            class_declare = class_obj.content.split('\n')[0]
            class_init = class_obj.init[0] if class_obj.init else None


            class_content.write(class_declare.strip())
            class_content.write('\n')
            if class_init is not None:
                for i in class_init.split('\n'):
                    if i.strip() == '':
                        continue
                    class_content.write('    ' + i)
                    class_content.write('\n')
                    
            class_content.write('\n')

        for func in functions:
            func_content = func.content
            for i in func_content.split('\n'):
                if i.strip() == '':
                    continue
                class_content.write('    ' + i)
                class_content.write('\n')
            class_content.write('\n')
            pass
        all_content.append(class_content.getvalue())
        class_content.close()
    final_context = '\n'.join(all_content)
    return final_context

        
def construct_call_chain_info(chosen_chain):
    chain_func_names = [single_func.name for single_func in chosen_chain if single_func.name != '__init__']
    return '->'.join(chain_func_names)
    

def construct_summarize_function_prompt(target_function, module_name, context):
    func_name = target_function.name
    prompt = (
        f"There is a python function '{func_name}' in module {module_name}. "
        f"A simplified version of this module is \n```\n{context}\n```\n"
        # f"The information of the function is \n```\n{context}\n```\n"
        f"What is the functionality of the function? Do not write any unit tests in your response. "
    )
    return prompt


def construct_prompt_from_direct_program(target_function, test_programs):
    func_name = target_function.name

    test_program_info = '\n'.join([f'```\n{test_program.content.strip()}\n```' for test_program in test_programs])
    
    if len(test_programs) > 1:
        prompt = (
            f"The test programs below is designed to test the function '{func_name}'. They can cover different part of the function. "
            f"The contents of the test programs are \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. Do not modify the import statements. "
            # f"Your code format should be consistent with the provided test programs. " 
        )
    else:
        prompt = (
            f"The test program below is designed to test the function '{func_name}' and can only cover part of it. "
            f"The content of the test program is \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. Do not modify the import statements. "
            # f"Your code format should be consistent with the provided test programs. " 
        )

    return prompt
    

def construct_prompt_from_calee_program(target_function, test_programs, chosen_chain):
    func_name = target_function.name
    test_program_info = '\n'.join([f'```\n{test_program.content.strip()}\n```' for test_program in test_programs])
    
    # TODO: 建立更好的 call chain 的信息
    call_chain_info = construct_call_chain_info(chosen_chain)
    
    if len(test_programs) > 1:
        prompt = (
            f"The test programs below can cover different part of the function '{func_name}' through the call chain {call_chain_info}. "
            f"The contents of the test programs are \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. Do not modify the import statements. "
            # f"Your code format should be consistent with the provided test programs. " 
        )
    else:
        prompt = (
            f"The test program below is designed to test the function '{func_name}' through the call chain {call_chain_info}. "
            f"The content of the test program is \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. Do not modify the import statements. "
            # f"Your code format should be consistent with the provided test programs. " 
        )
    return prompt
    


def construct_summarize_function_prompt_new(target_function, module_name, context):
    func_name = target_function.name
    prompt = (
        f"There is a python function '{func_name}' in file {module_name.split('.')[-1]}. "
        f"A simplified version of this file is \n```\n{context}\n```\n"
        # f"The information of the function is \n```\n{context}\n```\n"
        f"What is the functionality of the function? Do not write any unit tests in your response. "
    )
    return prompt



def construct_context_new(target_function, name_2_class, chosen_chain=None):
    # TODO: called_functions / branch_related_called_functions
    # chosen_called_functions = target_function.called_functions
    chosen_called_functions = target_function.branch_related_called_functions
    
    if chosen_chain is None:
        chosen_calee_functions = set()
    else:
        chosen_calee_functions = set(chosen_chain)
    
    chosen_context_functions = chosen_called_functions.union(chosen_calee_functions)
    chosen_context_functions = chosen_context_functions.union({target_function})
    all_classes = set([i.belong_class for i in chosen_context_functions])
    
    # 对对象列表按照属性 belong_class 进行排序
    sorted_functions = sorted(chosen_context_functions, key=lambda obj: (obj.belong_class is None, obj.belong_class))

    # 使用 groupby 进行分组
    grouped_functions = {key: list(group) for key, group in groupby(sorted_functions, key=lambda obj: obj.belong_class)}

    # 输出结果
    final_classes = []
    all_content = []
    for belong_class, functions in grouped_functions.items():
        class_content = ''
        class_content = StringIO(class_content)

        if belong_class is not None:
            final_classes.append(belong_class)
            class_obj = name_2_class[belong_class]
            
            class_declare = class_obj.content.split('\n')[0]
            class_init = class_obj.init[0] if class_obj.init else None


            class_content.write(class_declare.strip())
            class_content.write('\n')
            if class_init is not None:
                for i in class_init.split('\n'):
                    if i.strip() == '':
                        continue
                    class_content.write('    ' + i)
                    class_content.write('\n')
                    
            class_content.write('\n')

        for func in functions:
            func_content = func.content
            for i in func_content.split('\n'):
                if i.strip() == '':
                    continue
                class_content.write('    ' + i)
                class_content.write('\n')
            class_content.write('\n')
            pass
        all_content.append(class_content.getvalue())
        class_content.close()
    final_context = '\n'.join(all_content)
    return final_context, final_classes


def construct_prompt_from_direct_program_new(target_function, test_programs, imports):
    func_name = target_function.name

    test_program_info = '\n'.join([f'```\n{test_program.content.strip()}\n```' for test_program in test_programs])
    
    if len(test_programs) > 1:
        prompt = (
            f"The test programs below is designed to test the function '{func_name}'. They can cover different part of the function. "
            f"The contents of the test programs are \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. "
            f"The import statements of the test class are \n```\n{imports}\n```\n "
            # f"Your code format should be consistent with the provided test programs. " 
        )
    else:
        prompt = (
            f"The test program below is designed to test the function '{func_name}' and can only cover part of it. "
            f"The content of the test program is \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. "
            f"The import statements of the test class are \n```\n{imports}\n```\n "
            # f"Your code format should be consistent with the provided test programs. " 
        )

    return prompt
    

def construct_prompt_from_calee_program_new(target_function, test_programs, chosen_chain, imports):
    func_name = target_function.name
    test_program_info = '\n'.join([f'```\n{test_program.content.strip()}\n```' for test_program in test_programs])
    
    # TODO: 建立更好的 call chain 的信息
    call_chain_info = construct_call_chain_info(chosen_chain)
    
    if len(test_programs) > 1:
        prompt = (
            f"The test programs below can cover different part of the function '{func_name}' through the call chain {call_chain_info}. "
            f"The contents of the test programs are \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. "
            f"The import statements of the test class are \n```\n{imports}\n```\n "
            # f"Your code format should be consistent with the provided test programs. " 
        )
    else:
        prompt = (
            f"The test program below is designed to test the function '{func_name}' through the call chain {call_chain_info}. "
            f"The content of the test program is \n{test_program_info}\n"
            f"Please generate new test programs that cover different scenarios or edge cases. "
            f"The code should be self-contained and complete. Do not add new classes and interfaces. "
            f"The import statements of the test class are \n```\n{imports}\n```\n "
            # f"Your code format should be consistent with the provided test programs. " 
        )
    return prompt
    

def construct_prompt_from_scratch(target_function, imports):
    func_name = target_function.name
    prompt = (
        f"Please write some test cases for {func_name} in unittest that can cover different scenarios and edge cases. "
        f"The code should be self-contained and complete. "
        f"The import statements of the test class are \n```\n{imports}\n```\n "
    )
    return prompt
    

def extract_functions_for_llm(content):
    tree = ast.parse(content)
    function_def_visitor = FunctionDefVisitor()
    function_def_visitor.visit(tree)
    
    function_nodes = function_def_visitor.functions

    functions =  [astor.to_source(func_node) for (class_name, func_node) in function_nodes] 
    
    return functions


def extract_imports_for_llm(llm_output):
    tree = ast.parse(llm_output)

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            content = astor.to_source(node).strip()
            if 'import collections as collections_abc' not in content:
                imports.add(content)
        elif isinstance(node, ast.ImportFrom):
            content = astor.to_source(node).strip()
            if 'import collections as collections_abc' not in content:
                imports.add(content)

    return list(imports)
    
    
def reindent_model_output(model_output):
    pattern = r"```python(.*?)```"

    # Find and extract the code snippet
    code_snippet = re.findall(pattern, model_output, re.DOTALL)[0]

    functions = extract_functions_for_llm(code_snippet)
    return code_snippet, functions 


    # model_output = model_output.split('def test_case')
    # functions = set()
    # count = 0
    # for i in model_output[1:]:
    #     codestr = StringIO(i)
    #     lines = codestr.readlines()
    #     func_lines = [l for l in lines if not any(i in l for i in ['assert', 'Assert', '```'])]
        
    #     single_function = 'def test_case' + ''.join(func_lines)
        
    #     pattern = r"def test_case_(.*?)\("
    #     origin_id = re.findall(pattern, single_function, re.DOTALL)[0]
    #     origin_name = f"def test_case_{origin_id}"
    #     new_name = f"def test_case_{count}"
    #     single_function = single_function.replace(origin_name, new_name)
        
    #     functions.add(single_function)
    #     count += 1
    # return functions


def invoke_llm(prompt, chat_bot, add_to_history):
    response = chat_bot.chat(prompt, add_to_history)
    return response

def invoke_llm_cache(chat_bot, stage1_prompt, stage1_response=None, stage2_prompt=None):
    response = chat_bot.chat_cache(stage1_prompt, stage1_response, stage2_prompt)
    return response
                
                

