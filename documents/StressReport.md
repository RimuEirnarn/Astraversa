# Stress testing report

From `stresser.py`, using the O(2n) method is killing performance at 2—5 FPS. Really fast, Python. Well, whatever.

As such, I've implemented secondary test where it only uses 1 for-loop.

Unfortunately, all of them can only reach 5 FPS. At average, it's 3 FPS ***all of them***.

CPU allocation is at 16% (Intel 17-7700HQ @ 2.8 GHz) for all of them.

Maybe Astraversa should be migrated to a better language?

## Report on 18/09/2026

Yesterday, Claude an I were discussing about the stress testing. Several foundings are made along the way, such as 400/200 FPS on 1000 objects, on 30/33 FPS on 10k objects, and 7/7 FPS on 50k objects. This yields uncontrollably.

... I don't know what is up but I cannot replicate 400 FPS. Pretty sure it was actually reachable, why was it gone... Maybe because I was stripping it apart? I don't remember. But hey, I won't touch it.

CFFI and Interpreted being an issue is a guarantee. But Python being hella slower than JS is a lot funnier, maybe because it's JIT?

Using Numba was a mistake. JIT testing is unreliable for now as Windows default Python 3.14.7 has no JIT, so is 3.15rc2. Someone's spitting a hoax at me.

## TL;DR

Python is slow due to CFFI and it being interpreted. 100k object draws tanks FPS down to at worst 2 FPS.