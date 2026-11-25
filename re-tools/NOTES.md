APK analysis helpers (androguard 4.x in a `uv venv`; paths inside the scripts point at extracted dex under x/apk/).
- cmds.py    : lists every CMDHelper method with its AT command string (classes7.dex)
- callers.py : `callers.py 'Class;->method'` finds call sites across all classes*.dex (prints context)
- cls2.py    : `cls2.py 'Lpkg/Class;' method...` dumps disassembly of methods
Setup: unzip the .xapk, unzip classes*.dex from com.linwear.top.apk into x/apk/, `uv venv av && uv pip install --python av/bin/python androguard`.
