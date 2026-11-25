import sys,glob
from loguru import logger
logger.remove()
from androguard.core.dex import DEX
pat=sys.argv[1]
for f in sorted(glob.glob('x/apk/classes*.dex')):
    d=DEX(open(f,'rb').read())
    if not any(pat.split('->')[-1] in str(s) for s in d.get_strings()): continue
    for c in d.get_classes():
        for m in c.get_methods():
            code=m.get_code()
            if not code: continue
            ins=list(code.get_bc().get_instructions())
            for k,i in enumerate(ins):
                if pat in i.get_output():
                    print('##',f,c.get_name(),m.get_name())
                    for j in ins[max(0,k-14):k+3]: print('    ',j.get_name(),j.get_output())
