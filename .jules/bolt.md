## 2024-05-24 - Optimizing `in` checks
**Learning:** Using a tuple instead of a list for `in` checks or iterations inside comprehensions/generator expressions is faster because Python compiler optimizes literal tuples into constants, avoiding the cost of instantiating a new list object on each evaluation.
**Action:** When writing or optimizing code that iterates over a static collection of items inside a function, always prefer tuples or global sets over inline lists to minimize runtime overhead.
