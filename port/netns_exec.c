#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
int main(int argc, char **argv) {
  if (argc == 3 && strcmp(argv[1], "--hold") == 0) {
    if (unshare(CLONE_NEWNET) != 0) { perror("unshare"); return 1; }
    FILE *f=fopen(argv[2],"w"); if (!f) return 1;
    fprintf(f,"%ld\n",(long)getpid()); fclose(f);
    for (;;) pause();
  }
  if (argc >= 4 && strcmp(argv[1], "--exec") == 0) {
    char path[128]; snprintf(path,sizeof(path),"/proc/%ld/ns/net",strtol(argv[2],NULL,10));
    int fd=open(path,O_RDONLY); if(fd<0 || setns(fd,CLONE_NEWNET)!=0) { perror("setns"); return 1; }
    close(fd); execvp(argv[3],argv+3); perror("exec"); return 1;
  }
  fprintf(stderr,"Offline guest namespace helper: --hold PIDFILE or --exec PID COMMAND...\n");
  return 2;
}
