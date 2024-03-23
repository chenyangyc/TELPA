from .base_item import Item


class Function(Item):
    def __init__(self, name, signature, content, line_range, func_type, belong_class, called_functions=None, instance_creation=None, \
                 direct_program=None):
        super().__init__()
        self.name = name
        self.signature = signature
        self.content = content
        self.line_range = line_range
        self.func_type = func_type
        self.belong_class = belong_class
        
        self.is_target = False
        
        self.branch_related_called_functions = set()
        
        self.called_functions = called_functions if called_functions is not None else set()
        self.called_chains = list()
        
        self.callee_functions = set()
        self.callee_chains = list()
        self.used_callee_chains = list()
        self.using_callee_chains = list()
        # 已经用过的
        # 下次可选的
        
        self.instance_creation = instance_creation if instance_creation is not None else set()
        
        self.direct_programs = direct_program if direct_program is not None else list()
        
        self.new_programs = list()
        self.covered_lines = set()
        # self.coverer_tests = coverer_tests if coverer_tests is not None else []
    
    
    def add_branch_related_called_functions(self, func_call):
        self.branch_related_called_functions.add(func_call)
        
    def add_called_function(self, func_call):
        self.called_functions.add(func_call)
    
    def add_callee_function(self, callee_func):
        self.callee_functions.add(callee_func)
    
    def add_called_chain(self, called_chain):
        self.called_chains.append(called_chain)
        
    def add_callee_chain(self, callee_chain):
        self.callee_chains.append(callee_chain)
        
    def add_instance_creation(self, instance_creation):
        self.instance_creation.add(instance_creation)
    
    def set_target(self):
        self.is_target = True
    
    def add_direct_program(self, direct_program):
        self.direct_programs.append(direct_program)
    
    def add_new_program(self, new_program):
        self.new_programs.append(new_program)
    
    
    def get_covered_lines(self):
        return self.covered_lines
    
    def add_covered_lines(self, new_line):
        self.covered_lines = self.covered_lines.union(new_line)
    
        

class Class():
    def __init__(self, name, methods, attributes, init, comment, content):
        self.name = name
        self.methods = methods
        self.attributes = attributes
        self.init = init
        self.comment = comment
        self.content = content

    