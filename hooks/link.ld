/* SPDX-License-Identifier: GPL-3.0-or-later. LBPP Randomizer (see README.md). */
/* The randomizer's code and data, loaded in the cave after the game's .bss (elf.py CAVE_VA).
   Game functions and globals are absolute symbols from game.ld. Everything, .bss included,
   goes into one blob, so the loader gives it zeroed memory. */
INCLUDE game.ld
ENTRY(hook_prize_bubble_load)
SEED_ADDRESS = seed;
SECTIONS
{
  . = 0x08c0ee00;
  .rando : {
    KEEP(*(.text.hooks))
    *(.text .text.*)
    *(.rodata .rodata.* .sdata .sdata.* .data .data.*)
    *(.sbss .sbss.* .bss .bss.* COMMON)
    . = ALIGN(16);
  }
  /DISCARD/ : { *(.comment) *(.MIPS.abiflags) *(.reginfo) *(.pdr) *(.gnu.attributes) *(.mdebug.*) }
}
