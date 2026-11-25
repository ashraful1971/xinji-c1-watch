import sys
from loguru import logger
logger.remove()
from androguard.core.dex import DEX
d=DEX(open('x/apk/classes7.dex','rb').read())
want=sys.argv[1]; meths=sys.argv[2:]
for c in d.get_classes():
    if c.get_name()==want:
        for m in c.get_methods():
            if m.get_name() in meths:
                print('=====',m.get_name(),m.get_descriptor())
                code=m.get_code()
                ins=code.get_bc().get_instructions()
                n=0
                off=0
                for i in ins:
                    print('  %04x'%off,i.get_name(),i.get_output()); off+=i.get_length()//2; n+=1
                print('  [count',n,'insns_size',code.insns_size,']')
