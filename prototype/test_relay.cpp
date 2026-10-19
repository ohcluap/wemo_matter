#include "relay.hpp"
#include <cassert>
#include <cstdio>
struct MockRelay : wemo::Relay {
  bool fail = false;
  bool state = false;
  unsigned attempts = 0;
  bool write(bool on) override {
    ++attempts;
    if (fail) return false;
    state = on;
    return true;
  }
};
int main() {
  using wemo::Result;
  MockRelay hardware;
  wemo::Controller controller(hardware);
  std::uint8_t on = 1, off = 0, invalid = 2;
  assert(!controller.known() && hardware.attempts == 0);
  assert(controller.attribute(2, 6, 0, &on, 1) == Result::Ignored);
  assert(controller.attribute(1, 8, 0, &on, 1) == Result::Ignored);
  assert(controller.attribute(1, 6, 1, &on, 1) == Result::Ignored);
  assert(controller.attribute(1, 6, 0, nullptr, 1) == Result::Invalid);
  assert(controller.attribute(1, 6, 0, &on, 0) == Result::Invalid);
  assert(controller.attribute(1, 6, 0, &on, 2) == Result::Invalid);
  assert(controller.attribute(1, 6, 0, &invalid, 1) == Result::Invalid);
  assert(hardware.attempts == 0);
  assert(controller.attribute(1, 6, 0, &on, 1) == Result::Applied);
  assert(controller.known() && controller.on() && hardware.state);
  assert(controller.attribute(1, 6, 0, &on, 1) == Result::Applied);
  assert(hardware.attempts == 1);
  hardware.fail = true;
  assert(controller.attribute(1, 6, 0, &off, 1) == Result::HardwareFailure);
  assert(controller.on() && hardware.state);
  hardware.fail = false;
  assert(controller.attribute(1, 6, 0, &off, 1) == Result::Applied);
  assert(!controller.on() && !hardware.state);
  wemo::Controller restarted(hardware);
  assert(!restarted.known()); // No claim of persistent state or physical readback.
  std::puts("PASS: routing, input validation, on/off, idempotence, failure/retry, restart state");
}
