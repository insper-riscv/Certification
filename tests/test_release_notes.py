"""Testes da montagem do release: título, tag, notas, logs e as recusas."""

import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools/riscv_build"))

import release_notes

INT = "rom=int,ram=int,icache=off,dcache=off"
EXT = "rom=ext,ram=ext,icache=on,dcache=on"
COMMIT = "e7b9a78869f5839836037e764d4700d71879590b"


def _write(results: Path, profile: str, memory: str, elfs: list[str], verdict: str = "PASS", commit: str = COMMIT) -> None:
    """Grava a pasta de um job com o seu result.json e um log."""
    slug = "rom-int_ram-int_ic-off_dc-off" if memory == INT else "rom-ext_ram-ext_ic-on_dc-on"
    folder = results / f"act4-result-{profile}-{slug}"
    folder.mkdir(parents=True)
    data = {
        "schema": 1,
        "profile": profile,
        "memory": memory,
        "slug": slug,
        "extensions": ["I", "M"],
        "act4_commit": commit,
        "results": {elf: verdict for elf in elfs},
    }
    (folder / "result.json").write_text(json.dumps(data))
    (folder / "latest.log").write_text("=== Summary ===\n")


def _args(results: Path, out: Path, *extra: str) -> list[str]:
    """Monta a linha de comando de um release automático."""
    return [
        "--results", str(results), "--out", str(out), "--mode", "auto", "--kind", "matrix",
        "--cert-commit", "0123456789abcdef0123456789abcdef01234567", "--riscv-commit", "cf2b634527096c8191ba8fd83494a948fb51ec65",
        "--datetime", "2026-11-06T14:03:09Z", "--run-url", "https://github.com/insper-riscv/Certification/actions/runs/1", *extra,
    ]


@pytest.fixture
def results(tmp_path: Path) -> Path:
    """Um run que passou: as duas bases e três módulos."""
    base = tmp_path / "results"
    _write(base, "rv32i", INT, ["rv32i/I/I-add-00", "rv32i/I/I-sub-00"])
    _write(base, "rv32im", INT, ["rv32i/I/I-add-00", "rv32i/M/M-mul-00", "rv32i/Zmmul/Zmmul-mul-00"])
    _write(base, "rv32im", EXT, ["rv32i/I/I-add-00", "rv32i/M/M-mul-00", "rv32i/Zmmul/Zmmul-mul-00"])
    _write(base, "rv32e", INT, ["rv32e/E/E-add-00"])
    return base


def test_auto_release_files(results: Path, tmp_path: Path) -> None:
    """O release automático escreve o título da combinação, a tag e os logs por perfil."""
    out = tmp_path / "out"
    assert release_notes.main(_args(results, out)) == 0
    assert (out / "title.txt").read_text() == "RV32 I/E M, Zmmul\n"
    assert (out / "tag.txt").read_text() == "cert-20261106-140309-0123456\n"
    attached = (out / "attachments.txt").read_text().split()
    assert [Path(p).name for p in attached] == ["logs-rv32e.tar.gz", "logs-rv32i.tar.gz", "logs-rv32im.tar.gz"]
    with tarfile.open(attached[2]) as tar:
        names = sorted(tar.getnames())
    assert "rv32im/rom-ext_ram-ext_ic-on_dc-on/latest.log" in names
    assert "rv32im/rom-int_ram-int_ic-off_dc-off/result.json" in names


def test_notes_count_elfs_from_the_results(results: Path, tmp_path: Path) -> None:
    """As notas contam ELFs distintos e execuções por módulo, e descrevem a memória de cada job."""
    out = tmp_path / "out"
    release_notes.main(_args(results, out, "--reused-from", "https://github.com/insper-riscv/Certification/actions/runs/0"))
    notes = (out / "notes.md").read_text()
    assert "| I | I | 2 | 4 |" in notes
    assert "| I | M | 1 | 2 |" in notes
    assert "| E | E | 1 | 1 |" in notes
    assert "| Total | | 5 | 9 |" in notes
    assert "| `rv32im` | externa (chip de FLASH) | externa (chip de RAM) | ligada | ligada | D | 3 |" in notes
    assert "| `rv32i` | interna | interna | desligada | desligada | A | 2 |" in notes
    assert COMMIT in notes
    assert "cf2b634527096c8191ba8fd83494a948fb51ec65" in notes
    assert "Resultado reaproveitado do run" in notes
    assert "—" not in notes


def test_only_the_base_that_passed_is_in_the_title(tmp_path: Path) -> None:
    """Sem nenhum perfil E, o título cita só a base I."""
    base = tmp_path / "results"
    _write(base, "rv32i", INT, ["rv32i/I/I-add-00", "rv32i/Zicntr/Zicntr-x-00"])
    out = tmp_path / "out"
    assert release_notes.main(_args(base, out)) == 0
    assert (out / "title.txt").read_text() == "RV32 I Zicntr\n"


def test_modules_follow_the_canonical_order() -> None:
    """Os módulos saem na ordem canônica, os desconhecidos no fim."""
    assert release_notes.order_modules({"Zihpm", "Zbb", "M", "Zicond", "Zicsr", "Zimop"}) == ["M", "Zicsr", "Zihpm", "Zimop", "Zicond", "Zbb"]


def test_manual_titles(results: Path, tmp_path: Path) -> None:
    """O modo manual põe dia e hora no título, com a matriz ou o perfil."""
    args = _args(results, tmp_path / "a")
    args[args.index("auto")] = "manual"
    assert release_notes.main(args) == 0
    assert (tmp_path / "a/title.txt").read_text() == "2026-11-06 14:03 UTC, matriz\n"
    one = tmp_path / "one"
    _write(one, "rv32i_zimop", EXT, ["rv32i/Zimop/Zimop-x-00"])
    args = _args(one, tmp_path / "b")
    args[args.index("auto")] = "manual"
    args[args.index("matrix")] = "profile"
    assert release_notes.main(args) == 0
    assert (tmp_path / "b/title.txt").read_text() == "2026-11-06 14:03 UTC, perfil rv32i_zimop\n"
    assert "Notas" not in (tmp_path / "b/notes.md").read_text()


def test_a_failed_elf_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Um ELF em FAIL recusa o release e não deixa arquivo algum."""
    base = tmp_path / "results"
    _write(base, "rv32i", INT, ["rv32i/I/I-add-00"])
    _write(base, "rv32im", INT, ["rv32i/M/M-mul-00"], verdict="FAIL")
    out = tmp_path / "out"
    assert release_notes.main(_args(base, out)) == 1
    assert "did not pass" in capsys.readouterr().err
    assert not out.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["results"]


def test_missing_job_of_the_matrix_is_refused(results: Path, tmp_path: Path) -> None:
    """Se um par planejado não tem resultado, não há release."""
    matrix = json.dumps([{"profile": "rv32i", "slug": "rom-int_ram-int_ic-off_dc-off"}, {"profile": "rv32i_zimop", "slug": "rom-int_ram-int_ic-off_dc-off"}])
    assert release_notes.main(_args(results, tmp_path / "out", "--matrix", matrix)) == 1
    assert not (tmp_path / "out").exists()


def test_jobs_with_different_act4_commits_are_refused(tmp_path: Path) -> None:
    """A imagem atualizada no meio do run deixa os jobs com commits diferentes do ACT4."""
    base = tmp_path / "results"
    _write(base, "rv32i", INT, ["rv32i/I/I-add-00"])
    _write(base, "rv32im", INT, ["rv32i/M/M-mul-00"], commit="a" * 40)
    assert release_notes.main(_args(base, tmp_path / "out")) == 1


def test_empty_results_are_refused(tmp_path: Path) -> None:
    """Um job sem veredito por ELF não vira release."""
    base = tmp_path / "results"
    _write(base, "rv32i", INT, [])
    assert release_notes.main(_args(base, tmp_path / "out")) == 1
    assert release_notes.main(_args(tmp_path / "nothing", tmp_path / "out2")) == 1


def test_arguments_are_validated(results: Path, tmp_path: Path) -> None:
    """Hash, link e data fora do formato são recusados antes de qualquer leitura."""
    for bad in (("--act4-commit", "zz"), ("--reused-from", "javascript:alert(1)"), ("--run-url", "http://x")):
        args = _args(results, tmp_path / "out")
        if bad[0] == "--run-url":
            args[args.index("--run-url") + 1] = bad[1]
        else:
            args += list(bad)
        with pytest.raises(SystemExit):
            release_notes.main(args)
    args = _args(results, tmp_path / "out")
    args[args.index("--datetime") + 1] = "yesterday"
    with pytest.raises(SystemExit):
        release_notes.main(args)


def test_attachment_over_the_limit_is_refused(results: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Um anexo com 2 GiB ou mais recusa o release."""
    monkeypatch.setattr(release_notes, "MAX_ATTACHMENT", 10)
    assert release_notes.main(_args(results, tmp_path / "out")) == 1
    assert not (tmp_path / "out").exists()
