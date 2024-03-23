from .base_item import Item


class Module(Item):
    def __init__(self, name, content, module_dir, module_path, functions=None, classes=None):
        super().__init__()
        self.name = name
        self.content = content
        self.module_dir = module_dir
        self.module_path = module_path
        self.functions = functions if functions is not None else []
        self.classes = classes if classes is not None else []
        self.total_line_num = 0
    
    def add_function(self, new_func):
        self.functions.append(new_func)
    
    def add_class(self, new_class):
        self.classes.append(new_class)
        
    def set_total_line_num(self, total_line_num):
        self.total_line_num = total_line_num