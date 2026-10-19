#include <atomic>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <pthread.h>
#include <time.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <unistd.h>
std::atomic<unsigned> count{0};
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
unsigned guarded = 0;
void *worker(void *) {
  for (int i = 0; i < 1000; ++i) {
    ++count;
    assert(pthread_mutex_lock(&mutex) == 0);
    ++guarded;
    assert(pthread_mutex_unlock(&mutex) == 0);
  }
  return nullptr;
}
int main() {
  volatile double input = std::strtod("1.25", nullptr);
  assert(std::fabs(input * 2.0 - 2.5) < 0.000001);
  pthread_t thread;
  assert(pthread_create(&thread, nullptr, worker, nullptr) == 0);
  assert(pthread_join(thread, nullptr) == 0);
  assert(count == 1000 && guarded == 1000);
  timespec before{}, after{}, delay{0, 1000000};
  assert(clock_gettime(CLOCK_MONOTONIC, &before) == 0);
  assert(nanosleep(&delay, nullptr) == 0);
  assert(clock_gettime(CLOCK_MONOTONIC, &after) == 0);
  assert(after.tv_sec > before.tv_sec || (after.tv_sec == before.tv_sec && after.tv_nsec > before.tv_nsec));
  unsigned char random[32];
  assert(getrandom(random, sizeof(random), 0) == sizeof(random));
  const int fd = socket(AF_INET6, SOCK_DGRAM, 0);
  assert(fd >= 0);
  close(fd); // No bind, connect, or send. Container has no LAN interface.
  std::puts("PASS: software floating point, pthreads, mutex, atomics, monotonic clock, entropy, IPv6 socket creation");
}
