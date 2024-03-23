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



## Getting Started



## File Structure