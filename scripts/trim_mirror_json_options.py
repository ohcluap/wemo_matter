"""Remove JSON test-option loaders; retain default attestation and access control."""
import subprocess,re
from pathlib import Path
p=Path('/sdk/examples/platform/linux/Options.cpp')
s=subprocess.check_output(['git','-c','safe.directory=/sdk','-C','/sdk','show','HEAD:examples/platform/linux/Options.cpp'],text=True)
s,n=re.subn(r'bool ParseAccessRestrictionEntriesFromJson\(const char \* jsonString, std::vector<AccessRestrictionProvider::Entry> & entries\)\n\{.*?\n\}', 'bool ParseAccessRestrictionEntriesFromJson(const char *, std::vector<AccessRestrictionProvider::Entry> &)\n{\n    return false; // JSON CLI fixture loader omitted; runtime access control remains enabled.\n}',s,flags=re.S)
assert n==1
old='    if (gDeviceOptions.dacProviderFile.HasValue())\n    {\n        static chip::Credentials::Examples::TestHarnessDACProvider testDacProvider;\n        testDacProvider.Init(gDeviceOptions.dacProviderFile.Value().c_str());\n        gDeviceOptions.dacProvider = &testDacProvider;\n        return;\n    }\n'
assert old in s
s=s.replace(old,'')
s=s.replace('LinuxDeviceOptions::GetInstance().dacProviderFile.SetValue(aValue);', 'PrintArgError("JSON DAC fixture loading is unavailable in this compact test build\\n");\n        retval = false;')
p.write_text(s)
