"""Os modelos de memória e de cache do topo modular de simulação, e quais combinações ele aceita.

A escolha tem quatro eixos independentes na sintaxe do `--memory` do riscv-tools: a ROM e a RAM dentro
(`int`) ou fora (`ext`) do chip, e a existência da cache de instruções (`icache`) e da de dados (`dcache`).
Os quatro eixos dão 16 combinações. O topo `modular_sim_top` do Insper-RISC-V só monta a cache de
instruções dentro do ramo da ROM externa e a de dados dentro do ramo da RAM externa, e não tem genérico
`HAS_ICACHE` nem `HAS_DCACHE`, então aceita as 4 combinações em que cada cache existe exatamente quando a
sua memória é externa.
"""

from dataclasses import dataclass
from itertools import product

# Os valores que cada chave do `--memory` aceita aqui; os tamanhos das caches ficam nos genéricos do topo.
_LOCATION = {"int": False, "ext": True}
_SWITCH = {"on": True, "off": False}


@dataclass(frozen=True)
class MemoryModel:
    """Uma combinação de memórias e caches da plataforma modular.

    Parameters
    ----------
    rom_external : bool
        A ROM fica fora do chip, no chip de FLASH simulado.
    ram_external : bool
        A RAM fica fora do chip, no chip de RAM simulado.
    icache : bool
        Existe a cache de instruções.
    dcache : bool
        Existe a cache de dados.
    """

    rom_external: bool
    ram_external: bool
    icache: bool
    dcache: bool

    @property
    def spec(self) -> str:
        """Escreve a combinação na sintaxe do `--memory` do riscv-tools.

        Returns
        -------
        str
            Por exemplo `rom=ext,ram=int,icache=on,dcache=off`.
        """
        return (
            f"rom={'ext' if self.rom_external else 'int'},"
            f"ram={'ext' if self.ram_external else 'int'},"
            f"icache={'on' if self.icache else 'off'},"
            f"dcache={'on' if self.dcache else 'off'}"
        )

    @property
    def architecture(self) -> str | None:
        """Dá o nome da arquitetura de memória coerente, ou None se a combinação não é uma delas.

        Returns
        -------
        str or None
            `A` (ROM e RAM internas), `B` (RAM externa com cache de dados), `C` (ROM externa com cache de
            instruções) ou `D` (as duas externas com as duas caches), os mesmos nomes dos modelos
            `integrated`, `external-data`, `external-instruction` e `external` do topo modular.
        """
        if self.icache != self.rom_external or self.dcache != self.ram_external:
            return None
        return {(False, False): "A", (False, True): "B", (True, False): "C", (True, True): "D"}[
            (self.rom_external, self.ram_external)
        ]

    @property
    def slug(self) -> str:
        """Dá um nome curto, seguro para nome de arquivo, à combinação.

        Returns
        -------
        str
            Por exemplo `rom-ext_ram-int_ic-on_dc-off`.
        """
        return (
            f"rom-{'ext' if self.rom_external else 'int'}"
            f"_ram-{'ext' if self.ram_external else 'int'}"
            f"_ic-{'on' if self.icache else 'off'}"
            f"_dc-{'on' if self.dcache else 'off'}"
        )


def parse(text: str) -> MemoryModel:
    """Lê uma combinação na sintaxe do `--memory` do riscv-tools; as quatro chaves são obrigatórias.

    Parameters
    ----------
    text : str
        Lista de `chave=valor` separada por vírgulas, com `rom` e `ram` (`int` ou `ext`) e `icache` e
        `dcache` (`on` ou `off`).

    Returns
    -------
    MemoryModel
        A combinação lida.

    Raises
    ------
    ValueError
        Se uma chave falta, se repete, é desconhecida ou tem valor fora da lista.
    """
    found: dict[str, bool] = {}
    for pair in text.split(","):
        key, sign, value = pair.strip().partition("=")
        table = _LOCATION if key in ("rom", "ram") else _SWITCH
        if not sign or key not in ("rom", "ram", "icache", "dcache") or key in found or value not in table:
            raise ValueError(f"--memory: '{pair}' is not valid (rom/ram=int|ext, icache/dcache=on|off, each once)")
        found[key] = table[value]
    if len(found) != 4:
        raise ValueError("--memory needs the four keys rom, ram, icache and dcache")
    return MemoryModel(found["rom"], found["ram"], found["icache"], found["dcache"])


def all_models() -> list[MemoryModel]:
    """Lista as 16 combinações, na ordem em que a ROM varia mais devagar e a cache de dados mais depressa.

    Returns
    -------
    list of MemoryModel
        As 16 combinações.
    """
    return [MemoryModel(*bits) for bits in product((False, True), repeat=4)]


def problems(model: MemoryModel, extensions: set[str]) -> list[str]:
    """Diz por que o topo modular não aceita a combinação para o perfil, ou devolve a lista vazia.

    Parameters
    ----------
    model : MemoryModel
        A combinação de memórias e caches.
    extensions : set of str
        As extensões do perfil.

    Returns
    -------
    list of str
        Uma razão por regra violada; vazia quando a combinação elabora e o perfil a certifica.
    """
    found: list[str] = []
    for name, external, cache in (("ROM", model.rom_external, model.icache), ("RAM", model.ram_external, model.dcache)):
        letter = "i" if name == "ROM" else "d"
        if cache and not external:
            found.append(
                f"the {letter}cache cannot sit over an internal {name}: modular_sim_top instantiates it only for "
                f"an external {name} and has no HAS_{letter.upper()}CACHE generic"
            )
        if external and not cache:
            found.append(
                f"an external {name} always sits behind the {letter}cache: the {'FLASH' if name == 'ROM' else 'RAM'} "
                f"chip speaks the line protocol of the cache, and the top has no generic to leave it out"
            )
    if "Zifencei" in extensions and not (model.rom_external and model.ram_external):
        found.append(
            "Zifencei-fence.i-00 rewrites its own code, so its body runs from the RAM: the fetch must reach the RAM "
            "through the instruction cache, which needs both memories external"
        )
    return found
