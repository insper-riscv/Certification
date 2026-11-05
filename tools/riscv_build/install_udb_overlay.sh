#!/bin/sh
# Instala no UDB do ACT4 a extensão E (RV32E), que o UDB publicado não declara, como o overlay "rv32e".
# Uso, da raiz do repositório e antes do `certify` de um perfil rv32e*: sh tools/riscv_build/install_udb_overlay.sh
set -eu
gem_dir=$(ls -d /opt/act-bundle/ruby/*/gems/udb-*)
target="$gem_dir/.data/spec/custom/isa/rv32e"
mkdir -p "$target"
cp -r tools/riscv_build/act/udb-overlay/. "$target/"
