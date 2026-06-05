---
orphan: true
---

<!--
THIS FILE IS GENERATED - DO NOT EDIT BY HAND!
Run `just docs` or `python scripts/document_rules.py` to regenerate this file.
-->

(rule-use-collections-abc)=

# use-collections-abc

<p class="rule-metadata">
  <span>Collection: <code>fixit-extra</code></span>
  <span>Autofix: Yes</span>
  <span>Python: `>= 3.3`</span>
</p>

Require collection ABCs to be imported from collections.abc.

## Message

ABCs must be imported from collections.abc


## Valid examples

```python
from collections.abc import Container
```
```python
from collections.abc import Container, Hashable
```
```python
from collections.abc import (Container, Hashable)
```
```python
from collections import defaultdict
```
```python
from collections import abc
```
```python
import collections
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```python
import collections.abc
```
```python
import collections.abc.Container
```
```python
class MyTest(collections.Something):
    def test(self):
        pass
```
```python
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping
```
```python
try:
    from collections.abc import Mapping, Container
except ImportError:
    from collections import Mapping, Container
```
```python
try:
    from collections.abc import Mapping, Container
except ImportError:
    def fallback_import():
        from collections import Mapping, Container
```
```python
try:
    from collections.abc import Mapping, Container
except Exception:
    exit()
```
```python
try:
    from collections import defaultdict
except Exception:
    exit()
```
```{raw} html
</details>
```

## Invalid examples

```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from collections import Container
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections.abc import Container
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from collections import Container, Hashable
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections.abc import Container, Hashable
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
from collections import (Container, Hashable)
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections.abc import (Container, Hashable)
```
```{raw} html
</div>
```
```{raw} html
<details class="rule-extra-examples"><summary>Show more</summary>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
import collections.Container
```
<p class="rule-example-label">Suggested fix</p>

```python
import collections.abc.Container
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
import collections.Container as cont
```
<p class="rule-example-label">Suggested fix</p>

```python
import collections.abc.Container as cont
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from collections import defaultdict, Container
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections import defaultdict
from collections.abc import Container
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from collections import defaultdict
from collections import Container
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections import defaultdict
from collections.abc import Container
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example rule-invalid-example-separated">
```
```python
from collections import defaultdict, Container
from collections import OrderedDict, Mapping
```
<p class="rule-example-label">Suggested fix</p>

```python
from collections import defaultdict
from collections.abc import Container
from collections import OrderedDict
from collections.abc import Mapping
```
```{raw} html
</div>
```
```{raw} html
<div class="rule-invalid-example">
```
```python
class MyTest(collections.Container):
    def test(self):
        pass
```
<p class="rule-example-label">Suggested fix</p>

```python
class MyTest(collections.abc.Container):
    def test(self):
        pass
```
```{raw} html
</div>
```
```{raw} html
</details>
```
