"""Disassemble selected MIPS ELF functions offline; never execute the input.

Requires capstone 5.0.6 and pyelftools 0.32. GOT annotations are static symbol
references, not proof that a call is reachable. Addresses belong to this input
ELF, not the user's firmware. Output is intended for manual control-flow review.
"""
import argparse
import hashlib
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile


def inspect(path, functions):
    output = [f'Input: {path.name}', f'SHA256: {hashlib.sha256(path.read_bytes()).hexdigest()}']
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        if elf.elfclass != 32 or not elf.little_endian or elf['e_machine'] != 'EM_MIPS':
            raise ValueError('Expected little-endian MIPS32 ELF')
        symbols = list(elf.get_section_by_name('.dynsym').iter_symbols())
        tags = {t.entry.d_tag: t.entry.get('d_val', t.entry.get('d_ptr'))
                for t in elf.get_section_by_name('.dynamic').iter_tags()}
        gp = struct.unpack('<6I', elf.get_section_by_name('.reginfo').data())[-1]
        got = elf.get_section_by_name('.got')
        words = struct.unpack('<' + 'I' * (got.data_size // 4), got.data())
        local, first = tags['DT_MIPS_LOCAL_GOTNO'], tags['DT_MIPS_GOTSYM']

        def read_address(address, size):
            for segment in elf.iter_segments():
                if (segment['p_type'] == 'PT_LOAD' and segment['p_vaddr'] <= address
                        and address + size <= segment['p_vaddr'] + segment['p_filesz']):
                    stream.seek(segment['p_offset'] + address - segment['p_vaddr'])
                    return stream.read(size)
            raise ValueError('Requested function outside file-backed load segments')

        disassembler = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
        for name in functions:
            matches = [s for s in symbols if s.name == name and s['st_size'] > 0 and s['st_info']['type'] == 'STT_FUNC']
            if len(matches) != 1:
                raise ValueError(f'Expected one defined function: {name}')
            symbol = matches[0]
            output.append(f'\nFUNCTION {name} address={symbol["st_value"]:#x} size={symbol["st_size"]}')
            for instruction in disassembler.disasm(
                    read_address(symbol['st_value'], symbol['st_size']), symbol['st_value']):
                annotation = ''
                if instruction.mnemonic == 'lw' and '($gp)' in instruction.op_str:
                    offset = int(instruction.op_str.split(', ')[1].split('(')[0], 0)
                    relative = gp + offset - got['sh_addr']
                    index = relative // 4
                    if relative % 4 == 0 and 0 <= index < len(words):
                        value = symbols[first + index - local].name if index >= local else hex(words[index])
                        annotation = ' ; GOT ' + value
                output.append(f'{instruction.address:08x}: {instruction.mnemonic} {instruction.op_str}{annotation}')
        rodata = elf.get_section_by_name('.rodata')
        if rodata:
            output.append('\nRODATA STRINGS (addresses, not execution evidence)')
            offset = 0
            for data in rodata.data().split(b'\0'):
                if len(data) >= 4 and all(32 <= b < 127 or b in (9, 10, 13) for b in data):
                    output.append(f'{rodata["sh_addr"] + offset:08x}: {data.decode("ascii")!r}')
                offset += len(data) + 1
    return '\n'.join(output) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('functions', nargs='+')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = inspect(args.input, args.functions)
    with args.output.open('x', encoding='utf-8') as destination:
        destination.write(result)
