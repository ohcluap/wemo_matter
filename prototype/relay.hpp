#pragma once
#include <cstdint>

namespace wemo {
// Hardware access is deliberately absent. Real GPIO mapping remains unverified.
struct Relay {
  virtual ~Relay() = default;
  virtual bool write(bool on) = 0;
};
enum class Result { Applied, Ignored, Invalid, HardwareFailure };
class Controller {
 public:
  explicit Controller(Relay &relay) : relay_(relay) {}
  Result attribute(std::uint16_t endpoint, std::uint32_t cluster,
                   std::uint32_t attribute, const std::uint8_t *value,
                   std::uint16_t size) {
    // On/Off cluster's OnOff attribute, on our proposed outlet endpoint.
    if (endpoint != 1 || cluster != 0x0006 || attribute != 0x0000)
      return Result::Ignored;
    if (value == nullptr || size != 1 || *value > 1)
      return Result::Invalid;
    const bool requested = *value != 0;
    if (known_ && requested == on_) return Result::Applied;
    if (!relay_.write(requested)) return Result::HardwareFailure;
    on_ = requested;
    known_ = true;
    return Result::Applied;
  }
  bool known() const { return known_; }
  bool on() const { return on_; }
 private:
  Relay &relay_;
  bool known_ = false;
  bool on_ = false;
};
} // namespace wemo
