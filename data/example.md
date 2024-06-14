## Overview of the prompting process

Our prompting process is two-stage. In the first stage, the LLM is insturcuted to summarize the intent of the target method with the given context, which is collected through the program analysis.

```markdown
### User Message
There is a python function '{target method name}'. The context of the function is ```{entire bodies of methods collected through forward and backward analysis and associated class declarations and constructors}```"
What is the functionality of the function? Do not write any unit tests in your response.

### Response

```

Then in the second stage, the LLM is provided with the counter-examples and instructed to generate new different tests:

```markdown
### User Message
{stage1 prompt}

### Response
{stage1 response}

### User Message
The test programs below are designed to test the function '{target method name}'. They can cover different part of the function. The contents of the test programs are ```{counter-examples}```.
Please help me generate new test programs that cover different scenarios or edge cases. 

### Response

```

## Example

For example, given a target method `is_public_family`, a simplified version of the module (named `parser`) hosting it is like this:

```python
<other code>

def is_magic(name: str) -> bool:
    """Check magic name."""
    name = name.rsplit(".", maxsplit=1)[-1]
    return name[:2] == name[-2:] == "__"


def is_public_family(name: str) -> bool:
    """Check the name is come from public modules or not."""
    for n in name.split("."):
        # Magic name
        if is_magic(n):
            continue
        # Local or private name
        if n.startswith("_"):
            return False
    return True

@dataclass
class Parser:
    """AST parser.

    Usage:
    >>> p = Parser()
    >>> with open("pkg_path", 'r') as f:
    >>>     p.parse('pkg_name', f.read())
    >>> s = p.compile()

    Or create with parameters:
    >>> p = Parser.new(link=True, level=1)
    """

    link: bool = True
    b_level: int = 1
    toc: bool = False
    level: dict[str, int] = field(default_factory=dict)
    doc: dict[str, str] = field(default_factory=dict)
    docstring: dict[str, str] = field(default_factory=dict)
    imp: dict[str, set[str]] = field(default_factory=dict)
    root: dict[str, str] = field(default_factory=dict)
    alias: dict[str, str] = field(default_factory=dict)
    const: dict[str, str] = field(default_factory=dict)
    _Self = TypeVar("_Self", bound="Parser")

		<other code in the class>
		
    def is_public(self, s: str) -> bool:
        """Check the name is public style or listed in `__all__`."""
        if s in self.imp:
            for ch in chain(self.doc.keys(), self.const.keys()):
                if ch.startswith(s + ".") and is_public_family(ch):
                    break
            else:
                return False
        all_l = self.imp[self.root[s]]
        if all_l:
            return s == self.root[s] or bool({s, parent(s)} & all_l)
        else:
            return is_public_family(s)

```

One of the sequences that can enter the target method collected through backward analysis is `is_public -> is_public_family`. And the method collected through forward analysis is `is_magic`.

Therefore, we first construct the stage1 prompt. The prompt includes all entire bodies of the collected methods and the declarations and constructors of the associated classes.

````markdown
There is a python function is_public_family in module 'parser'. A simplified version of this module is
```
def is_magic(name: str) -> bool:
    """Check magic name."""
    name = name.rsplit(".", maxsplit=1)[-1]
    return name[:2] == name[-2:] == "__"


def is_public_family(name: str) -> bool:
    """Check the name is come from public modules or not."""
    for n in name.split("."):
        # Magic name
        if is_magic(n):
            continue
        # Local or private name
        if n.startswith("_"):
            return False
    return True

@dataclass
class Parser:
    """AST parser.

    Usage:
    >>> p = Parser()
    >>> with open("pkg_path", 'r') as f:
    >>>     p.parse('pkg_name', f.read())
    >>> s = p.compile()

    Or create with parameters:
    >>> p = Parser.new(link=True, level=1)
    """

    link: bool = True
    b_level: int = 1
    toc: bool = False
    level: dict[str, int] = field(default_factory=dict)
    doc: dict[str, str] = field(default_factory=dict)
    docstring: dict[str, str] = field(default_factory=dict)
    imp: dict[str, set[str]] = field(default_factory=dict)
    root: dict[str, str] = field(default_factory=dict)
    alias: dict[str, str] = field(default_factory=dict)
    const: dict[str, str] = field(default_factory=dict)
    _Self = TypeVar("_Self", bound="Parser")

    def is_public(self, s: str) -> bool:
        """Check the name is public style or listed in `__all__`."""
        if s in self.imp:
            for ch in chain(self.doc.keys(), self.const.keys()):
                if ch.startswith(s + ".") and is_public_family(ch):
                    break
            else:
                return False
        all_l = self.imp[self.root[s]]
        if all_l:
            return s == self.root[s] or bool({s, parent(s)} & all_l)
        else:
            return is_public_family(s)

```
What is the functionality of is_public_family? Do not write any unit tests in your response.
````

Then we construct stage2 prompt according to the counter-examples:

````markdown
The test programs below are designed to test the function 'is_public_family' through the call chain is_public->is_public_family. They can cover different part of the function. The contents of the test programs are:
```
from apimd.parser import Parser
import unittest
import timeout_decorator
import sys
import os

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test0(self):
    		parser0 = Parser()
        self.assertTrue(parser0.is_public('module.Class'))

if __name__ == "__main__":
    unittest.main()
``` 
```
from apimd.parser import Parser
import unittest
import timeout_decorator
import sys
import os

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test0(self):
    		parser0 = Parser()
        self.assertFalse(parser0.is_public('_module.Class'))

if __name__ == "__main__":
    unittest.main()
```
Please generate new test programs that cover different scenarios or edge cases. The code should be self-contained and complete.
````

