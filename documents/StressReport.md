# Stress testing report

From `stresser.py`, using the O(2n) method is killing performance at 2—5 FPS. Really fast, Python. Well, whatever.

As such, I've implemented secondary test where it only uses 1 for-loop.

Unfortunately, all of them can only reach 5 FPS. At average, it's 3 FPS ***all of them***.

CPU allocation is at 16% (Intel 17-7700HQ @ 2.8 GHz) for all of them.

Maybe Astraversa should be migrated to a better language?
