import sys
import os

sys.path.extend([".", ".."])
import subprocess
from loguru import logger
import xml.etree.ElementTree as ET

def _add_jacoco_plugin(directory): 
    pom_path = os.path.join(directory, "pom.xml")
    with open(pom_path, 'r') as f:
        pom_content = f.read()
        # 最后写回
    if not os.path.exists(pom_path):
        logger.error(f"pom.xml not found in directory: {directory}")
        return
    jacoco_dependency_content = '''
    <dependency>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>0.8.12</version>
        <scope>test</scope>
    </dependency>
    '''
    
    jacoco_plugin_content = '''
    <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>0.8.12</version>
        <executions>
            <execution>
                <id>pre-test</id>
                <goals>
                    <goal>prepare-agent</goal>
                </goals>
            </execution>
            <execution>
                <id>report</id>
                <phase>verify</phase>
                <goals>
                    <goal>report</goal>
                </goals>
            </execution>
        </executions>
    </plugin>
    '''
    jacoco_dependency = ET.fromstring(jacoco_dependency_content)
    jacoco_plugin = ET.fromstring(jacoco_plugin_content)
    
    tree = ET.parse(pom_path)
    root = tree.getroot()
    print("Root tag:", root.tag)
    namespaces = {
        'maven': 'http://maven.apache.org/POM/4.0.0'
    }
    
    # 去除命名空间前缀
    def remove_namespace(element):
        if '}' in element.tag:
            element.tag = element.tag.split('}', 1)[1]  # 去除命名空间前缀
        for child in element:
            remove_namespace(child)

    # 去除所有元素的命名空间前缀
    remove_namespace(root)
    
    # ? 会不会有项目没有dependencies的情况
    # 检查并添加 JaCoCo dependency
    dependencies = root.find('.//dependencies', namespaces)
    if dependencies is not None:
        existing_jacoco_deps = [dep for dep in dependencies.findall('dependency') if dep.find('artifactId').text == 'jacoco-maven-plugin']
    
        if not existing_jacoco_deps:
            dependencies.append(jacoco_dependency)
        else:
            # 删除现有的 JaCoCo 依赖项
            for dep in existing_jacoco_deps:
                dependencies.remove(dep)
            dependencies.append(jacoco_dependency)

    # 检查并添加 JaCoCo plugin
    profiles = root.find('.//profiles', namespaces)
    if profiles is not None:
        for profile in profiles.findall('profile'):
            build = profile.find('./build', namespaces)
            if build is not None:
                plugins = build.find('./plugins', namespaces)
                if plugins is not None:
                    existing_jacoco_plugins = [plugin for plugin in plugins.findall('plugin') if plugin.find('artifactId').text == 'jacoco-maven-plugin']
                    if not existing_jacoco_plugins:
                        plugins.append(jacoco_plugin)
                    else:
                        for plugin in existing_jacoco_plugins:
                            plugins.remove(plugin)
                        plugins.append(jacoco_plugin)

    # 写回修改后的 XML 文件
    tree.write(pom_path, encoding='utf-8', xml_declaration=True)
    return pom_path, pom_content

def run_mvn_test(args):
    directory, test_class, test_method = args
    pom_path, pom_content = _add_jacoco_plugin(directory)
    # 构建命令
    if test_class and test_method:
        mvn_command = f"mvn clean org.jacoco:jacoco-maven-plugin:prepare-agent test -Dtest={test_class}#{test_method}"
    elif test_class:
        mvn_command = f"mvn clean org.jacoco:jacoco-maven-plugin:prepare-agent test -Dtest={test_class}"
    else:
        mvn_command = f"mvn clean org.jacoco:jacoco-maven-plugin:prepare-agent test"

    jacoco_report_command = 'mvn org.jacoco:jacoco-maven-plugin:report'
    # 改变到指定目录
    os.chdir(directory)

    # 运行命令
    # javac_result = subprocess.run('javac -version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    mvn_result = subprocess.run(mvn_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _ = subprocess.run(jacoco_report_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 收集输出和错误信息
    mvn_stdout = mvn_result.stdout
    mvn_stderr = mvn_result.stderr

    # 把原始的pom.xml写回
    with open(pom_path, 'w') as f:
        f.write(pom_content)

    # 检查结果
    jacoco_report_output = os.path.join(directory, 'target/site/jacoco/jacoco.xml')
    if "BUILD SUCCESS" in mvn_stdout:
        assert os.path.exists(jacoco_report_output)
        test_result = "Passed"
    elif "BUILD FAILURE" in mvn_stdout or "Tests run:" in mvn_stdout and "Failures:" in mvn_stdout:
        if not os.path.exists(jacoco_report_output):
            test_result = "Failed Compilation"
            pass
        else:
            test_result = 'Failed Execution'
    else:
        logger.error('Unknown results of mvn test. Please check')


    return {
        "directory": directory,
        "test_class": test_class,
        "test_method": test_method,
        "result": test_result,
        "stdout": mvn_stdout,
        "stderr": mvn_stderr
    }

def run_mvn_compile(project_root):
    directory = project_root
    pom_path, pom_content = _add_jacoco_plugin(directory)
    
    mvn_command = f"mvn clean compile"
    os.chdir(project_root)
    mvn_result = subprocess.run(mvn_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    mvn_stdout = mvn_result.stdout
    mvn_stderr = mvn_result.stderr
    
    # 把原始的pom.xml写回
    with open(pom_path, 'w') as f:
        f.write(pom_content)
    
    return mvn_stdout, mvn_stderr

def run_mvn_test_no_clean(args):
    directory, test_class, test_method = args
    
    # 清空jacoco.exec和jacoco.xml文件
    jacoco_exec_path = os.path.join(directory, 'target/jacoco.exec')
    if os.path.exists(jacoco_exec_path):
        os.remove(jacoco_exec_path)
    jacoco_report_output = os.path.join(directory, 'target/site/jacoco/jacoco.xml')
    if os.path.exists(jacoco_report_output):
        os.remove(jacoco_report_output)
    
    # 构建命令 注意 这里不clean
    if test_class and test_method:
        mvn_command = f"mvn org.jacoco:jacoco-maven-plugin:prepare-agent test -Dtest={test_class}#{test_method}"
    elif test_class:
        mvn_command = f"mvn org.jacoco:jacoco-maven-plugin:prepare-agent test -Dtest={test_class}"
    else:
        mvn_command = f"mvn org.jacoco:jacoco-maven-plugin:prepare-agent test"

    jacoco_report_command = 'mvn org.jacoco:jacoco-maven-plugin:report'
    # 改变到指定目录
    os.chdir(directory)

    # 运行命令
    # javac_result = subprocess.run('javac -version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    mvn_result = subprocess.run(mvn_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _ = subprocess.run(jacoco_report_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 收集输出和错误信息
    mvn_stdout = mvn_result.stdout
    mvn_stderr = mvn_result.stderr
    
    # 检查结果
    jacoco_report_output = os.path.join(directory, 'target/site/jacoco/jacoco.xml')
    if "BUILD SUCCESS" in mvn_stdout:
        assert os.path.exists(jacoco_report_output)
        test_result = "Passed"
    elif "BUILD FAILURE" in mvn_stdout or "Tests run:" in mvn_stdout and "Failures:" in mvn_stdout:
        if not os.path.exists(jacoco_report_output):
            test_result = "Failed Compilation"
            pass
        else:
            test_result = 'Failed Execution'
    else:
        logger.error('Unknown results of mvn test. Please check')


    return {
        "directory": directory,
        "test_class": test_class,
        "test_method": test_method,
        "result": test_result,
        "stdout": mvn_stdout,
        "stderr": mvn_stderr
    }
