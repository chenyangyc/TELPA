import os
import ast
import astor
import pickle
from tqdm import tqdm
from collections import defaultdict


class ClassDefVisitor(ast.NodeVisitor):
    def __init__(self):
        self.info = defaultdict(dict)

    def visit_ClassDef(self, node):
        class_name = node.name
        
        self.info[class_name]['methods'] = set([n for n in node.body if isinstance(n, ast.FunctionDef)])
        self.info[class_name]['init'] = [astor.to_source(n) for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '__init__']
        self.info[class_name]['attr'] = [astor.to_source(n) for n in node.body if isinstance(n, ast.Assign)]
        docstring = ast.get_docstring(node)
        if docstring:
            self.info[class_name]['comment'] = docstring
        self.info[class_name]['content'] = astor.to_source(node)
        self.generic_visit(node)


class ClassInstantiationVisitor(ast.NodeVisitor):
    def __init__(self):
        self.instance_creations = set()

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr[0].isupper():  # Checking for attributes with uppercase names
            # This assumes that the object's attribute is the class name (common naming convention)
            self.instance_creations.add(node.func.attr)
        elif isinstance(node.func, ast.Name) and node.func.id[0].isupper():  # Assuming class names start with uppercase letters
            self.instance_creations.add(node.func.id)
        self.generic_visit(node)


class FunctionDefVisitor(ast.NodeVisitor):
    def __init__(self):
        self.current_class = None
        self.functions = list()

    def visit_ClassDef(self, node):
        self.current_class = node.name
        self.generic_visit(node)  # Visit methods within the class
        self.current_class = None

    def visit_FunctionDef(self, node):
        if self.current_class:
            # It's a method within the current class
            self.functions.append((self.current_class, node))
        else:
            # It's a standalone function
            self.functions.append((None, node))
        self.generic_visit(node)  # Visit any nested nodes within the function


class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self):
        # Stores function calls in the format (caller, function)
        self.function_calls = set()

    def visit_Call(self, node):
        # Check if it's a normal function call such as func()
        if isinstance(node.func, ast.Name):
            self.function_calls.add((None, node.func.id))
        # Check if it's a method call such as instance.method()
        elif isinstance(node.func, ast.Attribute):
            caller = self._get_caller(node.func.value)
            if caller != 'unittest':
                self.function_calls.add((caller, node.func.attr))
        self.generic_visit(node)
    

    def _get_caller(self, node):
        """
        Recursively retrieve the name of the variable that is calling the method.
        """
        if isinstance(node, ast.Name):
            return node.id
        return None

class ConditionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = set()  # 存储函数名，格式为 (模块名, 函数名)
        self.variables = set()  # 存储变量名

    def visit_If(self, node):
        self.extract_from_condition(node.test)
        self.generic_visit(node)

    def visit_While(self, node):
        self.extract_from_condition(node.test)
        self.generic_visit(node)

    def extract_from_condition(self, node):
        """提取条件表达式中的函数和变量"""
        if isinstance(node, ast.Call):
            self._process_call(node)
            # 递归处理函数参数中可能包含的变量或函数
            for arg in node.args:
                self.extract_from_condition(arg)
            for keyword in node.keywords:
                self.extract_from_condition(keyword.value)
        elif isinstance(node, ast.Name):
            self.variables.add(node.id)
        else:
            # 对其他类型的节点进行递归处理，以确保不遗漏任何条件部分
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.extract_from_condition(item)
                elif isinstance(value, ast.AST):
                    self.extract_from_condition(value)

    def _process_call(self, node):
        """处理函数调用，提取函数名和模块名"""
        if isinstance(node.func, ast.Name):
            # 普通函数调用，没有模块名
            self.functions.add((None, node.func.id))
        elif isinstance(node.func, ast.Attribute):
            # 属性访问，可能是模块.函数或实例.方法
            caller = self._get_caller(node.func.value)
            self.functions.add((caller, node.func.attr))

 
    def _get_caller(self, node):
        """
        Recursively retrieve the name of the variable that is calling the method.
        """
        if isinstance(node, ast.Name):
            return node.id
        return None



class CompleteAssignmentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.all_variables = set()  # 存储所有遇到的变量
        self.dependencies = {}

    def visit_Assign(self, node):
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        self.all_variables.update(targets)

        value = node.value
        right_side_variables = set()
        right_side_functions = set()

        self.extract_from_value(value, right_side_variables, right_side_functions)

        for target in targets:
            if target not in self.dependencies:
                self.dependencies[target] = {'function': [], 'identifier': []}
            self.dependencies[target]['function'].extend(list(right_side_functions))
            self.dependencies[target]['identifier'].extend(list(right_side_variables - set(targets)))
        
        self.generic_visit(node)

    def extract_from_value(self, node, variables, functions):
        if isinstance(node, ast.Name):
            variables.add(node.id)
            self.all_variables.add(node.id)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                caller = self._get_caller(node.func.value)
                function_name = node.func.attr
                functions.add((caller, function_name))
            elif isinstance(node.func, ast.Name):
                functions.add((None, node.func.id))
            for arg in node.args:
                self.extract_from_value(arg, variables, functions)
            for keyword in node.keywords:
                self.extract_from_value(keyword.value, variables, functions)
        elif isinstance(node, ast.BinOp):
            self.extract_from_value(node.left, variables, functions)
            self.extract_from_value(node.right, variables, functions)
        else:
            for field, value in ast.iter_fields(node):
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            self.extract_from_value(item, variables, functions)
                elif isinstance(value, ast.AST):
                    self.extract_from_value(value, variables, functions)

    def _get_caller(self, node):
        """
        Recursively retrieve the name of the variable that is calling the method.
        """
        if isinstance(node, ast.Name):
            return node.id
        return None


# class MethodSignatureExtractor(ast.NodeVisitor):
#     def __init__(self):
#         self.method_signatures = set()
#         self.current_class = None

#     def visit_ClassDef(self, node):
#         self.current_class = node.name
#         for item in node.body:
#             if isinstance(item, ast.FunctionDef):
#                 self.visit_FunctionDef(item)

#     def visit_AsyncFunctionDef(self, node):
#         # Async function definitions (Python 3.5+)
#         method_name = node.name
#         parameters = [arg.arg for arg in node.args.args]
#         signature = f"{self.current_class}.{method_name}({', '.join(parameters)})"
#         self.method_signatures.add(signature)

#     def visit_FunctionDef(self, node):
#         # Regular function definitions
#         method_name = node.name
#         parameters = [arg.arg for arg in node.args.args]
#         if self.current_class:
#             # Class method
#             signature = f"{self.current_class}.{method_name}({', '.join(parameters)})"
#         else:
#             # Standalone function
#             signature = f"{method_name}({', '.join(parameters)})"
#         self.method_signatures.add(signature)

#     def get_method_signatures(self):
#         return self.method_signatures