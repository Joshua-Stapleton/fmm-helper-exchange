# Source attribution

The weighted initializer and completion solvers are Andrey Perminov's linear-expressions-optimization library. This adapter calls an external, unmodified checkout pinned in UPSTREAM_PIN.json. It does not vendor that library or a compiled executable.

The small Bernoulli control function in pool_driver.cpp reproduces Reducer::getRandomSubstitutions from upstream master commit606edc0b0805f05161098e3ab3b1d1c4b867d5fe. This copied policy remains covered by the upstream MIT notice below. The experimental temperature controls and structural tester are separately labelled; they are not claimed to be the upstream default method.

MIT License

Copyright (c) 2026 Andrew Perminov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
