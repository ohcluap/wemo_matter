"""Remove sample-app diagnostic command pipe from offline source."""
from pathlib import Path
import re,subprocess
sdk=Path('/sdk')
p=sdk/'examples/lighting-app/linux/main.cpp'
s=p.read_text()
for text in ('NamedPipeCommands sChipNamedPipeCommands;', 'LightingAppCommandDelegate sLightingAppCommandDelegate;'):
    assert text in s
    s=s.replace(text,'')
for name in ('ApplicationInit','ApplicationShutdown'):
    s,n=re.subn(r'void '+name+r'\(\)\n\{.*?\n\}', 'void '+name+'() {}', s, count=1, flags=re.S)
    assert n==1
p.write_text(s)
p=sdk/'examples/lighting-app/linux/BUILD.gn'
s=subprocess.check_output(['git','-c','safe.directory=/sdk','-C','/sdk','show','HEAD:examples/lighting-app/linux/BUILD.gn'],text=True)
s=s.replace('    "LightingAppCommandDelegate.cpp",\n','')
p.write_text(s)
