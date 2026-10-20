/* GPL-2.0: kernel-only fake SPI controller exercises the real patched drivers.
 * Only built for the Malta test kernel, never the physical-board image. */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/platform_device.h>
#include <linux/spi/spi.h>
#include <linux/spi/flash.h>
#include <linux/mtd/mtd.h>
#include <linux/mtd/spi-nor.h>

static unsigned int calls, forbidden, reads;
static bool fail_next_read;
static const u8 protected_status = 0x1c;
static u8 pattern(unsigned int address) { return (address ^ (address >> 8) ^ 0xa5) & 255; }

static int transfer(struct spi_master *master, struct spi_message *message) {
  struct spi_transfer *t;
  u8 command[5] = {0};
  unsigned int command_len = 0, address = 0, count = 0;
  bool first = true;
  ++calls;
  list_for_each_entry(t, &message->transfers, transfer_list) {
    if (first) {
      if (!t->tx_buf || t->len > sizeof(command)) goto bad;
      memcpy(command, t->tx_buf, t->len); command_len = t->len;
      if (command[0] == 0x03 && command_len == 4)
        address = (command[1] << 16) | (command[2] << 8) | command[3];
      else if (!((command[0] == 0x9f || command[0] == 0x05) && command_len == 1)) goto bad;
      first = false;
      if (command[0] == 0x03 && fail_next_read) {
        fail_next_read = false;
        message->status = -EIO;
        spi_finalize_current_message(master);
        return 0;
      }
    } else {
      unsigned int i;
      u8 *out = t->rx_buf;
      if (!out || t->tx_buf) goto bad;
      for (i = 0; i < t->len; ++i) {
        if (command[0] == 0x9f) {
          static const u8 id[] = {0xc2, 0x20, 0x18, 0, 0};
          out[i] = count < sizeof(id) ? id[count] : 0;
        } else if (command[0] == 0x05) out[i] = protected_status;
        else { out[i] = pattern(address++); ++reads; }
        ++count;
      }
    }
    message->actual_length += t->len;
  }
  message->status = 0;
  spi_finalize_current_message(master);
  return 0;
bad:
  ++forbidden;
  message->status = -EPERM;
  spi_finalize_current_message(master);
  return 0;
}

#define CHECK(condition, label) do { if (!(condition)) { pr_err("WEMO_FORENSIC_TEST_FAIL=%s\n", label); return -EINVAL; } pr_info("WEMO_FORENSIC_TEST_PASS=%s\n", label); } while (0)

static int __init forensic_test(void) {
  struct platform_device *parent;
  struct spi_master *master;
  struct spi_device *device;
  struct flash_platform_data data = {.name = "forensic-test", .type = "mx25l12805d"};
  struct spi_board_info info = {.modalias = "mx25l12805d", .max_speed_hz = 1000000, .chip_select = 0, .platform_data = &data};
  struct mtd_info *mtd;
  struct spi_nor *nor;
  struct erase_info erase;
  u8 buffer[32], status = 0;
  size_t length;
  unsigned int before, opcode, i;
  int result;
  parent = platform_device_register_simple("wemo-fake-spi", -1, NULL, 0);
  CHECK(!IS_ERR(parent), "fake-parent");
  master = spi_alloc_master(&parent->dev, 0);
  CHECK(master, "fake-master-allocation");
  master->bus_num = 42; master->num_chipselect = 1;
  master->transfer_one_message = transfer;
  CHECK(!spi_register_master(master), "fake-master-registration");
  device = spi_new_device(master, &info);
  CHECK(device, "fake-device-registration");
  mtd = get_mtd_device_nm("forensic-test");
  CHECK(!IS_ERR(mtd) && mtd->size == 0x1000000, "real-driver-jedec-probe");
  CHECK(!forbidden, "probe-issued-only-allowed-reads");
  nor = mtd->priv;
  CHECK(!(mtd->flags & MTD_WRITEABLE), "mtd-read-only-flag");
  length = 0;
  result = mtd_read(mtd, 0x12345, sizeof(buffer), &length, buffer);
  CHECK(!result && length == sizeof(buffer), "flash-read");
  for (i = 0; i < sizeof(buffer); ++i)
    if (buffer[i] != pattern(0x12345 + i)) { pr_err("WEMO_FORENSIC_TEST_FAIL=read-data\n"); return -EINVAL; }
  CHECK(true, "read-data-match");
  fail_next_read = true; length = 0;
  CHECK(mtd_read(mtd, 0, sizeof(buffer), &length, buffer) == -EIO && !length, "spi-read-error-propagated");
  before = calls;
  length = 0;
  CHECK(mtd_write(mtd, 0, sizeof(buffer), &length, buffer) == -EROFS && !length, "mtd-write-rejected");
  memset(&erase, 0, sizeof(erase)); erase.mtd = mtd; erase.len = mtd->erasesize;
  CHECK(mtd_erase(mtd, &erase) == -EROFS, "mtd-erase-rejected");
  CHECK(mtd->_write(mtd, 0, sizeof(buffer), &length, buffer) == -EROFS, "direct-write-callback-rejected");
  CHECK(mtd->_erase(mtd, &erase) == -EROFS, "direct-erase-callback-rejected");
  for (opcode = 0; opcode < 256; ++opcode)
    if (nor->write_reg(nor, opcode, buffer, 1, 0) != -EROFS) { pr_err("WEMO_FORENSIC_TEST_FAIL=register-write\n"); return -EINVAL; }
  CHECK(calls == before, "all-256-register-write-opcodes-blocked-before-bus");
  length = 0; nor->write(nor, 0, sizeof(buffer), &length, buffer);
  CHECK(!length && calls == before, "low-level-program-blocked");
  CHECK(nor->erase(nor, 0) == -EROFS && calls == before, "low-level-erase-blocked");
  nor->read_opcode = 0x02;
  CHECK(nor->read(nor, 0, sizeof(buffer), &length, buffer) == -EROFS && calls == before, "program-opcode-cannot-use-read-path");
  nor->read_opcode = 0x03; nor->addr_width = 4;
  CHECK(nor->read(nor, 0, sizeof(buffer), &length, buffer) == -EROFS && calls == before, "four-byte-mode-rejected");
  nor->addr_width = 3;
  for (opcode = 0; opcode < 256; ++opcode) {
    if (opcode == 0x9f || opcode == 0x05) continue;
    if (nor->read_reg(nor, opcode, buffer, 1) != -EROFS) { pr_err("WEMO_FORENSIC_TEST_FAIL=register-read-escape\n"); return -EINVAL; }
  }
  CHECK(calls == before, "non-whitelisted-register-reads-blocked");
  CHECK(!nor->read_reg(nor, 0x05, &status, 1) && status == protected_status, "protection-register-unchanged");
  CHECK(!forbidden && reads >= sizeof(buffer), "no-forbidden-spi-transactions");
  pr_info("WEMO_FORENSIC_SUITE_PASS calls=%u forbidden=%u\n", calls, forbidden);
  put_mtd_device(mtd);
  return 0;
}
late_initcall(forensic_test);
