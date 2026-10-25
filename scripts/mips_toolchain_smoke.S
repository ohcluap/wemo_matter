/* Offline toolchain/emulator smoke test only. Not a Matter application. */
.set noreorder
.text
.globl _start
_start:
    li $v0, 4001
    li $a0, 0
    syscall
