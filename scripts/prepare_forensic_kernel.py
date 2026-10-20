#!/usr/bin/env python3
"""Prepare an isolated, fail-closed forensic driver fork; no live device access."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'sources/linux-3.18.27-forensic'
if not source.exists():
    shutil.copytree(ROOT / 'sources/linux-3.18.27-wemo', source)


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected source geometry; refusing an ambiguous patch: ' + old[:65])
    return text.replace(old, new)


# Recreate changed files from the original vendor-patched tree on each run.
original = ROOT / 'sources/linux-3.18.27-wemo'
driver_path = 'drivers/mtd/devices/m25p80.c'
s = (original / driver_path).read_text()
def insert_after_open(s, function, guard):
    start = s.index(function)
    position = s.index('{', start) + 1
    return s[:position] + '\n#ifdef CONFIG_WEMO_FORENSIC_RO\n' + guard + '\n#endif\n' + s[position:]

s = insert_after_open(s, 'static int m25p80_read_reg(', ' if (!((code == 0x9f && len == 5) || (code == 0x05 && len == 1))) return -EROFS;')
s = insert_after_open(s, 'static int m25p80_write_reg(', ' return -EROFS;')
s = insert_after_open(s, 'static void m25p80_write(', ' *retlen = 0; return;')
s = insert_after_open(s, 'static int m25p80_erase(', ' return -EROFS;')
s = insert_after_open(s, 'static void m25p80_chunked_write(', ' *_retlen = 0; return;')
s = insert_after_open(s, 'static int m25p80_read(', ' if (nor->read_opcode != 0x03 || nor->addr_width != 3 || nor->read_dummy ||\n     from < 0 || from > nor->mtd->size || len > nor->mtd->size - from) return -EROFS;')
s = replace(s, '\tspi_sync(spi, &m);\n\n\t*retlen = m.actual_length - m25p_cmdsz(nor) - dummy;', '''\tret = spi_sync(spi, &m);
 if (ret) return ret;
 if (m.actual_length < m25p_cmdsz(nor) + dummy ||
     m.actual_length > m25p_cmdsz(nor) + dummy + len) return -EIO;
\t*retlen = m.actual_length - m25p_cmdsz(nor) - dummy;''')
blocked = '''
#ifdef CONFIG_WEMO_FORENSIC_RO
static int forensic_mtd_write(struct mtd_info *mtd, loff_t to, size_t len, size_t *retlen, const u_char *buf)
{ *retlen = 0; return -EROFS; }
static int forensic_mtd_erase(struct mtd_info *mtd, struct erase_info *instr)
{ return -EROFS; }
#endif
'''
s = replace(s, 'static int m25p_probe(struct spi_device *spi)', blocked + '\nstatic int m25p_probe(struct spi_device *spi)')
s = replace(s, '\tppdata.of_node = spi->dev.of_node;', '''#ifdef CONFIG_WEMO_FORENSIC_RO
 flash->mtd.flags &= ~MTD_WRITEABLE;
 flash->mtd._write = forensic_mtd_write;
 flash->mtd._erase = forensic_mtd_erase;
 flash->mtd._lock = NULL;
 flash->mtd._unlock = NULL;
 nor->write = m25p80_write;
#endif
\tppdata.of_node = spi->dev.of_node;''')
(source / driver_path).write_text(s)
nor_path = 'drivers/mtd/spi-nor/spi-nor.c'
s = (original / nor_path).read_text()
s = replace(s, '\tmutex_init(&nor->lock);', '''#ifdef CONFIG_WEMO_FORENSIC_RO
 /* No mode changes, non-3-byte devices, quad configuration or status writes. */
 if (info->addr_width > 3 || (u64)info->sector_size * info->n_sectors > 0x1000000)
  return -EOPNOTSUPP;
 mode = SPI_NOR_NORMAL;
#endif
\tmutex_init(&nor->lock);''')
s = replace(s, '\t\twrite_enable(nor);\n\t\twrite_sr(nor, 0);', '''#ifndef CONFIG_WEMO_FORENSIC_RO
\t\twrite_enable(nor);
\t\twrite_sr(nor, 0);
#endif''')
s = replace(s, '\t/* Quad/Dual-read mode takes precedence over fast/normal */', '''#ifdef CONFIG_WEMO_FORENSIC_RO
 nor->flash_read = SPI_NOR_NORMAL;
#endif
\t/* Quad/Dual-read mode takes precedence over fast/normal */''')
(source / nor_path).write_text(s)
config_path = 'drivers/mtd/Kconfig'
s = (original / config_path).read_text()
s = replace(s, 'if MTD\n', '''if MTD

config WEMO_FORENSIC_RO
 bool "Strict read-only m25p80 forensic driver"
 depends on MTD_M25P80=y && MTD_SPI_NOR=y

config WEMO_FORENSIC_TEST
 bool "Fake SPI controller for offline forensic tests only"
 depends on WEMO_FORENSIC_RO && MIPS_MALTA
''')
(source / config_path).write_text(s)
make_path = 'drivers/mtd/Makefile'
(source / make_path).write_text((original / make_path).read_text() + '\nobj-$(CONFIG_WEMO_FORENSIC_TEST) += wemo_forensic_test.o\n')
shutil.copyfile(ROOT / 'port/forensic_spi_test.c', source / 'drivers/mtd/wemo_forensic_test.c')
make_path = 'arch/mips/ralink/Makefile'
s = replace((original / make_path).read_text(),
            'obj-y := prom.o of.o reset.o clk.o timer.o',
            'obj-y := prom.o of.o reset.o clk.o\nifneq ($(CONFIG_WEMO_FORENSIC_RO),y)\nobj-y += timer.o\nendif')
(source / make_path).write_text(s)
gpio_path = 'drivers/gpio/gpiolib-of.c'
s = replace((original / gpio_path).read_text(),
            'static struct of_device_id gpio_export_ids[] = {',
            '#ifndef CONFIG_WEMO_FORENSIC_RO\nstatic struct of_device_id gpio_export_ids[] = {')
(source / gpio_path).write_text(s + '\n#endif /* !CONFIG_WEMO_FORENSIC_RO: no DT GPIO export driver */\n')
print('Prepared isolated forensic source; normal Matter/vendor source trees unchanged')
