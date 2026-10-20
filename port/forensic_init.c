/* Identification-only PID 1. No shell, service, device writes or reboot. */
#define _GNU_SOURCE
#include <sys/mount.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>

int main(void) {
  struct utsname name;
  setvbuf(stdout, NULL, _IONBF, 0);
  if (mount("proc", "/proc", "proc", MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL)) {
    puts("WEMO_FORENSIC_INIT_FAIL=proc");
    for (;;) pause();
  }
  if (!uname(&name)) printf("WEMO_FORENSIC_KERNEL=%s %s\n", name.release, name.machine);
  puts("WEMO_FORENSIC_MTD_TABLE_BEGIN");
  char buf[512];
  int fd = open("/proc/mtd", O_RDONLY | O_CLOEXEC);
  if (fd >= 0) {
    ssize_t n;
    while ((n = read(fd, buf, sizeof(buf))) > 0) fwrite(buf, 1, n, stdout);
    close(fd);
  }
  puts("WEMO_FORENSIC_MTD_TABLE_END");
  puts("WEMO_FORENSIC_READY=identification-only; no shell or automatic reboot");
  for (;;) pause();
}
