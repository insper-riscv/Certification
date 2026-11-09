"""Testes dos dois caminhos de geração de alvo ACT4: o do modelo de memória (referência) e o da placa."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/riscv_build"))

import memory_models  # noqa: E402
import target_gen  # noqa: E402


def test_generated_target_follows_the_memory_model(tmp_path: Path) -> None:
    """O alvo de um perfil de referência traz o config com os genéricos do modelo de memória e a variante de Zifencei."""
    model = memory_models.parse("rom=ext,ram=ext,icache=on,dcache=on")
    config = target_gen.write_generated(ROOT, tmp_path, "rv32im_zifencei", {"M", "Zifencei"}, model, 4)
    text = config.read_text()
    assert config == tmp_path / "config.yaml"
    assert 'ROM_EXTERNAL: "true"' in text and 'RAM_EXTERNAL: "true"' in text
    assert "jobs: 4" in text and "sdram_base: 0x100000" in text
    assert (tmp_path / "act/rv32im_zifencei__rom-ext_ram-ext_ic-on_dc-on/test_config.yaml").exists()
    assert (tmp_path / "act/rv32im_zifencei__rom-ext_ram-ext_ic-on_dc-on-ram/link.ld").exists()


def test_generated_target_with_internal_memories_has_no_images(tmp_path: Path) -> None:
    """Sem memória externa, o config não aponta imagens de SDRAM nem variante de RAM."""
    model = memory_models.parse("rom=int,ram=int,icache=off,dcache=off")
    text = target_gen.write_generated(ROOT, tmp_path, "rv32i", set(), model, None).read_text()
    assert 'ROM_EXTERNAL: "false"' in text and "sdram_base" not in text and "ram_tests" not in text


def test_board_target_maps_flash_and_sdram(tmp_path: Path) -> None:
    """O alvo da placa põe a FLASH em 0x1000 e a SDRAM em 0x40000000 no Sail, e o config estende o da DE0-CV."""
    config = target_gen.write_board(ROOT, tmp_path, "rv32im_zifencei", {"M", "Zifencei"}, None)
    text = config.read_text()
    assert "config.platform-de0-cv.yaml" in text and "flash_entry: 0x1200" in text and "sdram_base: 0x40000000" in text
    target = tmp_path / "act/rv32im_zifencei__board"
    regions = json.loads((target / "sail.json").read_text())["memory"]["regions"]
    main = [r for r in regions if r["attributes"]["mem_type"] == "MainMemory"]
    assert [r["base"]["value"] for r in main] == ["0x1000", "0x40000000"]
    assert (tmp_path / "act/rv32im_zifencei__board-ram/link.ld").read_text() != (target / "link.ld").read_text()


@pytest.mark.parametrize("script", ["gen_profiles.py", "gen_flash_profiles.py"])
def test_generators_import_only_existing_names(script: str) -> None:
    """Os dois geradores versionados só importam nomes que existem nos módulos que compartilham."""
    import ast

    tree = ast.parse((ROOT / "tools/riscv_build" / script).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"profile_params", "target_gen"}:
            module = __import__(node.module)
            assert all(hasattr(module, alias.name) for alias in node.names)
