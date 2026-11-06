"""Testes dos modelos de memória e da matriz dos perfis mínimos do ACT4."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/riscv_build"))

import memory_models  # noqa: E402
from memory_models import MemoryModel  # noqa: E402
from profile_params import minimal_profiles  # noqa: E402


def test_sixteen_models_four_accepted() -> None:
    """De 16 combinações, só as que ligam a cache exatamente à memória externa passam."""
    models = memory_models.all_models()
    accepted = [m for m in models if not memory_models.problems(m, set())]
    assert len(models) == 16
    assert len(accepted) == 4
    assert all(m.icache == m.rom_external and m.dcache == m.ram_external for m in accepted)


def test_zifencei_needs_both_memories_external() -> None:
    """Um perfil com Zifencei só roda no modelo externo completo."""
    accepted = [m for m in memory_models.all_models() if not memory_models.problems(m, {"Zifencei"})]
    assert accepted == [MemoryModel(True, True, True, True)]


def test_spec_round_trip() -> None:
    """A sintaxe do --memory volta ao mesmo modelo, e uma chave que falta é recusada."""
    for model in memory_models.all_models():
        assert memory_models.parse(model.spec) == model
    with pytest.raises(ValueError):
        memory_models.parse("rom=int,ram=int")
    with pytest.raises(ValueError):
        memory_models.parse("rom=int,ram=int,icache=on,dcache=maybe")


def test_minimal_matrix_has_62_jobs() -> None:
    """Os 17 perfis mínimos dão 15 x 4 + 2 x 1 pares aceitos."""
    profiles = minimal_profiles(ROOT)
    jobs = [
        (name, m)
        for name, ext in profiles
        for m in memory_models.all_models()
        if not memory_models.problems(m, ext)
    ]
    assert len(profiles) == 17
    assert len(jobs) == 62
