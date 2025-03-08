import sys
sys.path.extend([".", ".."])
import json
import pickle
from tree_sitter import Parser, Language
import tree_sitter_java as tsjava

JAVA_LANGUAGE = Language(tsjava.language(), name='java')


def parse_fields_from_class_code(class_str: str, need_prefix=False):
    """
    Analyze defined fields for given class.
    :param class_str: class code in a string.
    :return: list of field dicts, for eaxmple:
            {
                "field_name": field_name,
                "field_type": field_type,
                "field_modifiers": field_modifiers,
                "declaration_text": declaration_text,
            }
    """
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_class_str = pickle.loads(pickle.dumps(class_str))
    if need_prefix:
        tmp_class_str = "public class TmpClass{\n" + class_str + "}\n"
    tree = parser.parse(bytes(tmp_class_str, "utf-8"))
    rets = []

    field_decl_query = JAVA_LANGUAGE.query(
        """
        (field_declaration 
            type: (_) @type_name 
            declarator: (variable_declarator name: (identifier)@var_name)
        ) @field_decl
        """
    )

    fields = field_decl_query.captures(tree.root_node)
    if len(fields) % 3 != 0:
        if int(len(fields) / 3) == 0:
            return []
        else:
            fields = fields[: -(len(fields) % 4)]
    num_iter = len(fields) / 3
    for i in range(int(num_iter)):
        field_name = ""
        field_type = ""
        declaration_text = ""
        for item in fields[i * 3: (i+1) * 3]:
            text = str(item[0].text, encoding="utf-8")
            if item[1] == "field_decl":
                declaration_text = text
                pass
            elif item[1] == "type_name":
                field_type = text
                pass
            elif item[1] == "var_name":
                field_name = text
                pass
            else:
                raise NotImplementedError(f"Unknown query result name {item[1]}")
        if (
                field_name != ""
                and field_type != ""
                and declaration_text != ""
        ):
            rets.append(
                {
                    "field_name": field_name,
                    "field_type": field_type,
                    "declaration_text": declaration_text,
                }
            )

    return rets


def parse_methods_from_class_node(class_str: str, need_prefix=False):
    """
    Analyze methods defined in the class.
    :param class_str:
    :return: list of collected methods. The elements are like:
                    {
                        "method_name": method_name,
                        "method_modifiers": method_modifiers,
                        "method_return_type": method_return_type,
                        "method_body": method_body,
                        "method_text": method_text,
                        "method_start_line": method start line,
                        "method_end_line": method end line
                    }
    """
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_class_str = pickle.loads(pickle.dumps(class_str))
    if need_prefix:
        tmp_class_str = "public class TmpClass{\n" + tmp_class_str + "}\n"
    tree = parser.parse(bytes(tmp_class_str, "utf-8"))
    rets = []

    method_query = JAVA_LANGUAGE.query(
        """
        (method_declaration) @method_decl
        """
    )

    methods = method_query.captures(tree.root_node)
    unique_methods = set()
    method_attr_query = JAVA_LANGUAGE.query(
        """
        (method_declaration [
            (modifiers) @modifier
            type:(_) @ret_type
            name:(identifier) @name
            body:(block) @body
            ])
        """
    )
    comment_query = JAVA_LANGUAGE.query(
        """
        (line_comment) @lc
        (block_comment) @bc
        """
    )
    for method_node, _ in methods:
        attrs = method_attr_query.captures(method_node)
        if len(attrs) % 4 != 0:
            continue
        num_iter = int(len(attrs) / 4)
        for i in range(num_iter):
            assert attrs[i * 4 + 1][1] == "ret_type"
            method_text = str(method_node.text, encoding="utf-8")
            method_return_type = str(attrs[i * 4 + 1][0].text, encoding="utf-8")
            method_name = str(attrs[i * 4 + 2][0].text, encoding="utf-8")
            method_modifiers = str(attrs[i * 4][0].text, encoding="utf-8")
            method_body = str(attrs[i * 4 + 3][0].text, encoding="utf-8")
            method_start = method_node.start_point[0]
            method_end = method_node.end_point[0]
            if method_body not in unique_methods and method_body.strip() != "":
                unique_methods.add(method_body)
                rets.append(
                    {
                        "method_name": method_name,
                        "method_modifiers": method_modifiers,
                        "method_return_type": method_return_type,
                        "method_body": method_body,
                        "method_text": method_text,
                        "method_start_line": method_start,
                        "method_end_line": method_end,
                    }
                )

    return rets


def parse_classes_from_file_node(file_code: str, strategy="generation"):
    """
    处理一下生成的代码中的inner classes
    :param file_code: 生成的code
    :return: inner classes as a list of strings.
    """
    rets = []
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tmp_file_code = pickle.loads(pickle.dumps(file_code))
    if strategy == "extend":
        tmp_file_code = "public class TmpClass {\n" + file_code
    tree = parser.parse(bytes(tmp_file_code, "utf-8"))
    class_decl_query = JAVA_LANGUAGE.query(
        """
        (class_declaration) @class_decl
        """
    )
    classes = class_decl_query.captures(tree.root_node)
    if len(classes) == 1 or len(classes) == 0:
        pass
    else:
        for class_str in classes:
            modifier_nodes = [
                str(node.text, encoding="utf-8")
                for node in class_str[0].children
                if node.type == "modifiers"
            ]
            if len(modifier_nodes) != 1 and len(modifier_nodes) != 0:
                num_modifiers = len(modifier_nodes)
                raise IndexError(
                    f"number of modifiers should be 1, but was {num_modifiers}"
                )
            else:
                if len(modifier_nodes) == 1:
                    modifier_nodes = modifier_nodes[0]
                    # 去掉public的类
                    if "public" not in modifier_nodes:
                        rets.append(str(class_str[0].text, encoding="utf-8"))
                else:
                    rets.append(str(class_str[0].text, encoding="utf-8"))

    return rets


def parse_import_stmts_from_file_code(file_code: str):
    """
    从给定的代码文件内容中提取import。为了避免噪音，需要满足两个条件：
    1. import语句必须是分号结尾
    2. import语句至多含有三个以空格区分的token

    Args:
        file_code (str): 输入的代码文件内容（最好是代码文件，其他文件中可能会被过滤掉）

    Returns:
        list: 从输入内容中提取出的import strings
    """
    rets = []
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)
    tree = parser.parse(bytes(file_code, "utf-8"))
    import_decl_query = JAVA_LANGUAGE.query(
        """
    (import_declaration) @import_decl
    """
    )
    imports = import_decl_query.captures(tree.root_node)
    for import_stmt, _ in imports:
        import_stmt = str(import_stmt.text, encoding="utf-8")
        tks = import_stmt.split()
        if import_stmt.endswith(";") and (len(tks) == 2 or len(tks) == 3):
            rets.append(import_stmt)
    return rets


def parse_method_invocation(method_code: str):
    """
    分析给定的函数中的其他函数调用情况

    Args:
        method_code (str): 给定的函数实现，通常是大模型生成的UT

    Returns:
        list<dict>: 返回一个字典的list，每个字典包含以下键值对：
            - invocation: 整体的函数调用字符串
            - invocator: 调用者的标识符，这里如果有package，也会放到一起返回
            - invoked_method_name: 被调用的方法的方法名
            - invocation_args: 被调用方法的参数列表，注意这里是带括号的实际传入参数的字符串
    """
    ret = []  # 定义一个空列表用于存储解析结果
    tmp_method_code = (
            "public class TmpClass {\n" + method_code + "}\n"
    )  # 将输入的方法代码定义到一个临时类中
    parser = Parser()  # 创建一个解析器对象
    parser.set_language(JAVA_LANGUAGE)  # 设置解析器的语言为Java
    tree = parser.parse(bytes(tmp_method_code, "utf-8"))  # 解析临时类的方法代码，生成语法树
    # 定义一个查询语句，用于匹配方法调用
    method_invocation_query = JAVA_LANGUAGE.query(
        """
    (method_invocation 
    object: (_) @object
    name: (_) @methodNname
    arguments: (_) @args
    ) @invoke
    """
    )

    invocations = method_invocation_query.captures(tree.root_node)  # 在语法树中查找所有方法调用
    if len(invocations) % 4 != 0:  # 如果调用次数不能被4整除，则跳过此次循环
        pass
    else:
        num_iter = int(len(invocations) / 4)  # 调用次数除以4得到循环次数
        for i in range(num_iter):  # 循环处理每个方法调用
            invocation_str = str(
                invocations[i * 4][0].text, encoding="utf-8"
            )  # 获取调用的字符串形式
            invocator_obj = str(
                invocations[i * 4 + 1][0].text, encoding="utf-8"
            )  # 获取调用者对象的字符串形式
            invocated_method_name = str(
                invocations[i * 4 + 2][0].text, encoding="utf-8"
            )  # 获取被调用方法的字符串形式
            invocation_args = str(
                invocations[i * 4 + 3][0].text, encoding="utf-8"
            )  # 获取调用的参数字符串形式
            ret.append(  # 将解析结果添加到列表中
                {
                    "invocation": invocation_str,  # 调用信息
                    "invocator": invocator_obj,  # 调用者对象
                    "invoked_method_name": invocated_method_name,  # 被调用方法
                    "invocation_args": invocation_args,  # 调用参数
                }
            )
        pass
    return ret  # 返回解析结果列表
