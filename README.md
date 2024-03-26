# TELPA (TEst generation via Llm and Program Analysis)

Welcome to the homepage of **TELPA**! This the implementation of our research "LLM-based Testing for Hard-to-Cover Branches via Program-Analysis-Enhanced Prompting".



## Introduction

Automatic test generation plays a critical role in software quality assurance. While the recent advances in Search-Based Software Testing (SBST) and Large Language Models (LLMs) have shown promise in generating useful tests, these techniques still struggle to cover certain branches. Reaching these hard-to-cover branches usually requires constructing complex objects and resolving intricate inter-procedural dependencies in branch conditions, which poses significant challenges for existing techniques. 
In this work, we propose TELPA, a novel technique aimed at addressing these challenges. 
Its key insight lies in extracting real usage scenarios of the target method under test to learn how to construct complex objects and extracting methods entailing inter-procedural dependencies with hard-to-cover branches to learn the semantics of branch constraints. 
To enhance efficiency and effectiveness, TELPA identifies a set of ineffective tests as counter-examples for LLMs and employs a feedback-based process to iteratively refine these counter-examples.
Then, TELPA integrates program analysis results and counter-examples into the prompt, guiding LLMs to gain deeper understandings of the semantics of the target method and generate diverse tests that can reach the hard-to-cover branches.

<img src="figures/overview.pdf" alt="overview" style="zoom:80%;" />

<p align="center">Figure 1: Overview of TELPA</p>



## Example of prompt construction

Our prompting process is two-stage. In the first stage, the LLM is insturcuted to summarize the functionality of the target method with a given spcific context, which is constructed with the method-invocation analysis results:

```
### User Message
There is a python function ‘{target method}’. The context of the function is ```{methods in the method-invocation sequence and all associated methods}```"
What is the functionality of the function? Do not write any unit tests in your response.

### Response
```

Then in the second stage, the LLM is provided with the counter-examples and instructed to generate new different tests:

```
### User Message
There is a python function ‘{target method}’. The information of the function is ```{methods in the method-invocation sequence and all associated methods}```"
What is the functionality of the function? Do not write any unit tests in your response.

### Response
<stage1 response>

### User Message
The test programs below are designed to test the function '{target method}'. They can cover different part of the function. The contents of the test programs are {counter-examples}
Please help me generate new test programs that cover different scenarios or edge cases. 

### Response
```





## Getting Started!

### Data preparation

TELPA is currently evaluated on a benchmark consisting of 486 modules. And TELPA leverages existing test cases generated in preceding test generation process as counter-examples.

Therefore, you need to first download the [benchmark and the existing test cases](https://drive.google.com/file/d/1iqcAFyMMgggtjmONpyuFmg1-6gBq8y_W/view?usp=drive_link), which have been compressed into one zip file.

Then unzip the zip file, you will get three folders: 

- benchmark: the open-source projects
- existing_test_cases: existing test cases
- existing_report: the report information of existing test cases (mapped through file name)

Put these folders under  `data`  folder.

That is, you should have the following folders after this step `./data/benchmark`, `./data/existing_test_cases`, and `./data/existing_report`



### Test generation

>Note that we leveraged [fastchat](https://github.com/lm-sys/FastChat/tree/main) to run the LLM locally. Therefore, you have to fisrt deploy a LLM in a fastchat way. Assume that the LLM is deployed in a url like **'http:host_ip:port/v1'**

Run `starter.py` to start the generation process. `starter.py` accepts three arguments:

- the path to the existing test cases
- the part of the modules you want to run
- the url on which the LLM is deployed

For example, run the command below:

```shell
python starter.py /path/to/TELPA/data/xxx part1, http:host_ip:port/v1
```

Then the generation process will begin, and the generated tests and the corresponding report information will be stored under the `data` folder.



### File Structure

`core` stores the definitions of all the objects used in the artifacts.

`utils` stores utils functions, such as the files used for parsing the AST, etc.

`data` stores the configuration file and the execution results.

`run` is the entry script of the artifacts.
