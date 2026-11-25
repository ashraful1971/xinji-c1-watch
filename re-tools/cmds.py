from loguru import logger
logger.remove()
from androguard.core.dex import DEX
d=DEX(open('x/apk/classes7.dex','rb').read())
for c in d.get_classes():
    if c.get_name()=='Lcom/szfission/wear/sdk/parse/CMDHelper;':
        for m in c.get_methods():
            code=m.get_code()
            if not code or not m.get_name().startswith(('get','send')): continue
            strs=[i.get_output().split(', ',1)[1] for i in code.get_bc().get_instructions() if i.get_name().startswith('const-string')]
            print(m.get_name(),m.get_descriptor(),strs)
