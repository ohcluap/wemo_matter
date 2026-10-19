/* Development OS-level WPA2 provisioning; no shell, SAVE_CONFIG, or flash API.
 * Input is two newline-terminated lines: SSID (1..32 bytes), passphrase
 * (8..63 printable ASCII bytes) or 64 hexadecimal PSK digits. Secrets never
 * appear in argv/output. Restart supplicant with wifi.conf after a crash;
 * wifi.pending is deliberately never a startup configuration.
 */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <poll.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <time.h>

static volatile sig_atomic_t cancelled;
static void cancel(int sig) { (void)sig; cancelled = 1; }
static int request(int fd, const char *cmd, char *reply, size_t capacity) {
  struct pollfd p = {fd, POLLIN, 0};
  if (send(fd, cmd, strlen(cmd), 0) < 0 || poll(&p, 1, 2000) != 1) return -1;
  ssize_t n = recv(fd, reply, capacity - 1, 0);
  if (n < 0) return -1;
  reply[n] = 0;
  return 0;
}
static int okay(int fd, const char *cmd) {
  char reply[128];
  return request(fd, cmd, reply, sizeof(reply)) == 0 && !strcmp(reply, "OK\n");
}
static int network_id(const char *s) {
  char *end;
  long n = strtol(s, &end, 10);
  return end != s && (*end == '\n' || !*end) && n >= 0 && n <= 100000 ? (int)n : -1;
}
static int status_id(const char *status) {
  const char *s = strstr(status, "\nid=");
  return s ? network_id(s + 4) : -1;
}
static int line(char *s, size_t size) {
  if (!fgets(s, size, stdin)) return 0;
  size_t n = strlen(s);
  if (!n || s[n-1] != '\n') return 0;
  s[n-1] = 0;
  return 1;
}
/* Pinned wpa_supplicant 2.11 crypto implementation linked by build script. */
int pbkdf2_sha1(const char *, const unsigned char *, size_t, int, unsigned char *, size_t);
static int derive_psk(const char *ssid, const char *passphrase, char *hex) {
  unsigned char key[32];
  int result = pbkdf2_sha1(passphrase, (const unsigned char *)ssid, strlen(ssid), 4096, key, sizeof(key));
  if (!result) for (int i = 0; i < 32; ++i) sprintf(hex + i*2, "%02x", key[i]);
  explicit_bzero(key, sizeof(key));
  return !result;
}

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "Usage: wemo-wifi-provision CONTROL_SOCKET PRIVATE_STATE_DIR TIMEOUT_SECONDS < credentials\n");
    return 2;
  }
  char *end;
  long timeout = strtol(argv[3], &end, 10);
  if (*end || timeout < 1 || timeout > 120) return 2;
  umask(077);
  signal(SIGINT, cancel); signal(SIGTERM, cancel);
  signal(SIGPIPE, SIG_IGN);
  char ssid[35], psk[67], hex[65], quoted[131], cmd[256], reply[4096];
  if (!line(ssid, sizeof(ssid)) || !line(psk, sizeof(psk)) || fgetc(stdin) != EOF) goto invalid;
  size_t sn = strlen(ssid), pn = strlen(psk);
  if (!sn || sn > 32 || pn < 8 || pn > 64) goto invalid;
  for (size_t i = 0; i < sn; ++i) {
    if ((unsigned char)ssid[i] < 32 || (unsigned char)ssid[i] == 127) goto invalid;
    sprintf(hex + i*2, "%02x", (unsigned char)ssid[i]);
  }
  for (size_t i = 0; i < pn; ++i) {
    unsigned char c = psk[i];
    if (pn == 64) { if (!isxdigit(c)) goto invalid; }
    else if (c < 32 || c > 126) goto invalid;
  }
  if (pn == 64) strcpy(quoted, psk);
  else if (!derive_psk(ssid, psk, quoted)) {
    fprintf(stderr, "PSK derivation failed\n"); return 2;
  }
  struct stat st;
  int dir = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (dir < 0 || fstat(dir, &st) || st.st_uid != geteuid() || (st.st_mode & 077)) {
    fprintf(stderr, "Private state directory required\n"); return 2;
  }
  int lock = openat(dir, "wifi.lock", O_WRONLY | O_CREAT | O_NOFOLLOW | O_NONBLOCK, 0600);
  if (lock < 0 || fstat(lock, &st) || !S_ISREG(st.st_mode) || st.st_uid != geteuid() ||
      (st.st_mode & 077) || flock(lock, LOCK_EX | LOCK_NB)) {
    fprintf(stderr, "Provisioning lock unavailable\n"); return 2;
  }
  /* Reject symlinks, permissive configs, and special files before any change. */
  if (!fstatat(dir, "wifi.conf", &st, AT_SYMLINK_NOFOLLOW)) {
    if (!S_ISREG(st.st_mode) || st.st_uid != geteuid() || (st.st_mode & 077)) return 2;
  } else if (errno != ENOENT) return 2;
  /* Stale staged credentials are never reused. Private directory + lock protects names. */
  if (unlinkat(dir, "wifi.pending", 0) && errno != ENOENT) return 2;
  int pending = openat(dir, "wifi.pending", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
  if (pending < 0) return 2;
  int staged = dprintf(pending, "# Commit only after verified association.\nctrl_interface=/tmp/wpa\nupdate_config=0\nnetwork={\n ssid=%s\n psk=%s\n key_mgmt=WPA-PSK\n proto=RSN\n}\n", hex, quoted);
  int disk_ok = staged > 0 && !fsync(pending);
  if (close(pending)) disk_ok = 0;
  if (!disk_ok) { unlinkat(dir, "wifi.pending", 0); return 2; }
  struct sockaddr_un local = {.sun_family = AF_UNIX}, remote = {.sun_family = AF_UNIX};
  snprintf(local.sun_path, sizeof(local.sun_path), "%s/wifi.control", argv[2]);
  if (strlen(argv[1]) >= sizeof(remote.sun_path) || strlen(argv[2]) + 14 >= sizeof(local.sun_path)) {
    unlinkat(dir, "wifi.pending", 0); return 2;
  }
  strcpy(remote.sun_path, argv[1]);
  unlink(local.sun_path);
  int fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0), old = -1, candidate = -1, result = 1;
  if (fd < 0 || bind(fd, (void *)&local, sizeof(local)) || connect(fd, (void *)&remote, sizeof(remote))) goto done;
  if (request(fd, "STATUS", reply, sizeof(reply))) goto done;
  old = status_id(reply);
  if (request(fd, "ADD_NETWORK", reply, sizeof(reply))) goto done;
  candidate = network_id(reply);
  if (candidate < 0) goto done;
  snprintf(cmd, sizeof(cmd), "SET_NETWORK %d ssid %s", candidate, hex);
  if (!okay(fd, cmd)) goto done;
  snprintf(cmd, sizeof(cmd), "SET_NETWORK %d psk %s", candidate, quoted);
  if (!okay(fd, cmd)) goto done;
  snprintf(cmd, sizeof(cmd), "SET_NETWORK %d key_mgmt WPA-PSK", candidate);
  if (!okay(fd, cmd)) goto done;
  snprintf(cmd, sizeof(cmd), "SET_NETWORK %d proto RSN", candidate);
  if (!okay(fd, cmd)) goto done;
  snprintf(cmd, sizeof(cmd), "SELECT_NETWORK %d", candidate);
  if (!okay(fd, cmd)) goto done;
  puts("WIFI_PROVISION_TESTING"); fflush(stdout);
  struct timespec start, now;
  if (clock_gettime(CLOCK_MONOTONIC, &start)) goto done;
  while (!cancelled) {
    if (clock_gettime(CLOCK_MONOTONIC, &now) || now.tv_sec - start.tv_sec >= timeout) break;
    if (request(fd, "STATUS", reply, sizeof(reply))) break;
    if (strstr(reply, "wpa_state=COMPLETED\n") && status_id(reply) == candidate) {
      /* Atomic replacement preserves the last committed file on failure.
       * Association proves credentials only, not DHCP, Internet, or Matter. */
      if (cancelled || renameat(dir, "wifi.pending", dir, "wifi.conf")) break;
      if (fsync(dir)) {
        fprintf(stderr, "Commit durability uncertain; restart from wifi.conf\n");
        result = 3; goto done;
      }
      result = 0; break;
    }
    sleep(1);
  }
done:
  if (result == 1 && candidate >= 0) {
    snprintf(cmd, sizeof(cmd), "REMOVE_NETWORK %d", candidate);
    int restored = okay(fd, cmd);
    if (old >= 0) {
      snprintf(cmd, sizeof(cmd), "SELECT_NETWORK %d", old);
      restored = okay(fd, cmd) && restored;
    }
    if (!restored) fprintf(stderr, "Runtime rollback unconfirmed; restart supplicant from committed config\n");
  }
  unlinkat(dir, "wifi.pending", 0);
  if (fd >= 0) close(fd);
  unlink(local.sun_path);
  close(lock); close(dir);
  explicit_bzero(psk, sizeof(psk)); explicit_bzero(quoted, sizeof(quoted)); explicit_bzero(cmd, sizeof(cmd));
  puts(result == 0 ? "WIFI_PROVISION_COMMITTED" : "WIFI_PROVISION_NOT_COMMITTED");
  return result;
invalid:
  fprintf(stderr, "Invalid credential input\n"); return 2;
}
