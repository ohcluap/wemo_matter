#pragma once
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>

namespace WemoRelay {
// No path means the existing in-memory simulator. Sysfs is independently gated;
// no pin export or direction change is performed by this backend.
inline bool Apply(bool on) {
    const char * path = std::getenv("WEMO_RELAY_VALUE_PATH");
    if (path == nullptr || path[0] == '\0') return true;
    const bool simulatedFile = std::strcmp(path, "/tmp/wemo-relay/value") == 0;
    const char * enabled = std::getenv("WEMO_RELAY_ENABLE_SYSFS");
    const bool verifiedSysfs = std::strcmp(path, "/sys/class/gpio/gpio19/value") == 0 &&
        enabled != nullptr && std::strcmp(enabled, "1") == 0 &&
        access("/etc/wemo-matter/verified-gpio19", R_OK) == 0;
    if (!simulatedFile && !verifiedSysfs) return false;
    const int fd = open(path, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return false;
    const char value = on ? '1' : '0';
    const bool written = write(fd, &value, 1) == 1;
    close(fd);
    if (!written) return false;
    const int readFd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (readFd < 0) return false;
    char readback = 0;
    const bool verified = read(readFd, &readback, 1) == 1 && readback == value;
    close(readFd);
    return verified;
}
} // namespace WemoRelay
