import os
import ast
import astor
import pickle
from tqdm import tqdm
from collections import defaultdict
from core.base_module import Module
from core.base_function import Function, Class
from core.ast_objs import ClassDefVisitor, ClassInstantiationVisitor, FunctionDefVisitor, FunctionCallVisitor
from .find_branch_related_util import analyze_code_with_all_variables, update_functions, analyze_conditions
from data.configuration import good_modules_path, benchmark_base


def extract_classes(module_content):
    tree = ast.parse(module_content)
    class_def_visitor = ClassDefVisitor()
    class_def_visitor.visit(tree)

    classes = []
    for class_name, class_info in class_def_visitor.info.items():
        init = class_info['init']
        methods = class_info['methods']
        attributes = class_info['attr']
        comment = class_info.get('comment', None)
        content = class_info['content']
        new_class = Class(name = class_name, methods = methods, attributes = attributes, init = init, comment = comment, content = content)
        classes.append(new_class)
    return classes


def extract_functions(module_content):
    tree = ast.parse(module_content)
    function_def_visitor = FunctionDefVisitor()
    function_def_visitor.visit(tree)
    
    function_nodes = function_def_visitor.functions

    functions =  [
        Function(
            name = func_node.name,
            # parameters = [arg.arg for arg in func_node.args.args]
            signature = f"{func_node.name}({', '.join([arg.arg for arg in func_node.args.args])})",
            content = astor.to_source(func_node),
            line_range = list(range(func_node.lineno, getattr(func_node, 'end_lineno', func_node.lineno) + 1)),
            func_type = 'within_class' if class_name else 'standalone',
            belong_class = class_name
        )
        for (class_name, func_node) in function_nodes
    ] 
    
    return functions


def extract_called_functions(function_content):
    '''
    提取一个函数里面调用的其他函数
    '''
    content_tree = ast.parse(function_content)

    visitor = FunctionCallVisitor()
    visitor.visit(content_tree)
    function_calls = visitor.function_calls
    return function_calls



def extract_branch_related_called_functions(function_content):
    '''
    提取一个函数里面和分支有关的其他函数
    '''
    dependencies = analyze_code_with_all_variables(function_content)
    update_functions(dependencies)
    functions_set, variables_set = analyze_conditions(function_content)
    for name in variables_set:
        if name not in dependencies.keys():
            continue
        function_list = dependencies[name]['function']
        for funtion in function_list:
            functions_set.add(funtion)
    return functions_set


def extract_initilized_class(function_content):
    content_tree = ast.parse(function_content)

    visitor = ClassInstantiationVisitor()
    visitor.visit(content_tree)
    return visitor.instance_creations

    
def extract_imports_from_module(module_content):
    tree = ast.parse(module_content)

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
    