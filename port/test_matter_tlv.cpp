#include <lib/core/TLV.h>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
  using namespace chip;
  using namespace chip::TLV;
  std::array<uint8_t, 64> buffer{};
  TLVWriter writer;
  writer.Init(buffer.data(), buffer.size());
  TLVType outer;
  assert(writer.StartContainer(AnonymousTag(), kTLVType_Structure, outer) == CHIP_NO_ERROR);
  assert(writer.PutBoolean(ContextTag(0), true) == CHIP_NO_ERROR);
  assert(writer.Put(ContextTag(1), uint32_t(0x12345678)) == CHIP_NO_ERROR);
  assert(writer.EndContainer(outer) == CHIP_NO_ERROR);
  assert(writer.Finalize() == CHIP_NO_ERROR);
  const uint8_t expected[] = {0x15, 0x29, 0x00, 0x26, 0x01, 0x78, 0x56, 0x34, 0x12, 0x18};
  assert(writer.GetLengthWritten() == sizeof(expected));
  assert(std::memcmp(buffer.data(), expected, sizeof(expected)) == 0);
  TLVReader reader;
  reader.Init(buffer.data(), writer.GetLengthWritten());
  assert(reader.Next() == CHIP_NO_ERROR);
  assert(reader.EnterContainer(outer) == CHIP_NO_ERROR);
  assert(reader.Next() == CHIP_NO_ERROR);
  bool on = false;
  assert(reader.GetTag() == ContextTag(0));
  assert(reader.Get(on) == CHIP_NO_ERROR && on);
  assert(reader.Next() == CHIP_NO_ERROR);
  uint32_t number = 0;
  assert(reader.Get(number) == CHIP_NO_ERROR && number == 0x12345678);
  assert(reader.Next() == CHIP_END_OF_TLV);
  assert(reader.ExitContainer(outer) == CHIP_NO_ERROR);
  // Truncation must not be silently accepted as a complete value.
  reader.Init(buffer.data() + 3, 5);
  assert(reader.Next() != CHIP_NO_ERROR);
  uint8_t tiny[1];
  writer.Init(tiny, sizeof(tiny));
  assert(writer.Put(AnonymousTag(), uint64_t(0x12345678)) == CHIP_ERROR_BUFFER_TOO_SMALL);
  std::puts("PASS: real Matter SDK TLV golden bytes, roundtrip, truncated input, output bounds");
}
