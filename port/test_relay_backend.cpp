#include "RelayBackend.h"
#include <cassert>
#include <cstdio>
#include <sys/stat.h>
int main() {
  unsetenv("WEMO_RELAY_VALUE_PATH");
  assert(WemoRelay::Apply(false));
  mkdir("/tmp/wemo-relay",0700);
  FILE * f=fopen("/tmp/wemo-relay/value","w"); assert(f); fputs("0",f); fclose(f);
  setenv("WEMO_RELAY_VALUE_PATH","/tmp/wemo-relay/value",1);
  assert(WemoRelay::Apply(true)); assert(WemoRelay::Apply(false));
  unlink("/tmp/wemo-relay/value"); assert(!WemoRelay::Apply(true));
  symlink("/etc/passwd","/tmp/wemo-relay/value"); assert(!WemoRelay::Apply(true));
  setenv("WEMO_RELAY_VALUE_PATH","/sys/class/gpio/gpio19/value",1);
  assert(!WemoRelay::Apply(true));
  setenv("WEMO_RELAY_VALUE_PATH","/etc/passwd",1); assert(!WemoRelay::Apply(true));
  puts("PASS: value-file relay, missing-file/symlink rejection and disabled physical path");
}
