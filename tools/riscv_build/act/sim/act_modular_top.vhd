-- =============================================================================
-- Topo de simulação do ACT4: a plataforma modular com os nomes de porta dos testbenches
--
-- Envolve o modular_sim_top do Insper-RISC-V e dá a ele as portas que os testbenches desta
-- pasta (test_act.py e test_act_sdram.py) observam. Com rom_external e ram_external falsos é o
-- modelo integrated, e o testbench vê o barramento da RAM do núcleo; com os dois verdadeiros é o
-- modelo external, em que a ROM e a RAM ficam atrás das caches e o testbench lê o tohost do chip
-- de RAM pela porta de depuração. Os tamanhos são os da plataforma: ROM e RAM de 1 MB e caches de
-- 4 kbit.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;

entity act_modular_top is
  generic (
    -- Imagem da BOOT_MEMORY, uma palavra de 32 bits por linha em hexadecimal.
    boot_memory_file : string  := "default.hex";
    -- Imagem da ROM, a partir do endereço 0.
    rom_file      : string  := "default.hex";
    -- Imagem da RAM, a partir da sua base.
    ram_file      : string  := "";
    -- A ROM fica atrás da cache de instruções.
    rom_external  : boolean := false;
    -- A RAM fica atrás da cache de dados.
    ram_external  : boolean := false;
    -- Bordas até a primeira palavra do chip de FLASH.
    flash_first_latency : natural := 24;
    -- Bordas entre as palavras seguintes da mesma linha do chip de FLASH.
    flash_next_latency  : natural := 4;
    -- Bordas entre o pedido e a conclusão de um acesso ao chip de RAM.
    ext_ram_latency     : natural := 8;
    -- Extensões do perfil.
    -- RV32E (16 registradores) no lugar do RV32I.
    has_e         : boolean := false;
    -- Inclui a extensão Zicsr.
    has_zicsr     : boolean := false;
    -- Inclui a extensão Zicntr.
    has_zicntr    : boolean := false;
    -- Inclui a extensão Zihpm.
    has_zihpm     : boolean := false;
    -- Inclui a extensão M completa.
    has_m         : boolean := false;
    -- Inclui a extensão Zmmul.
    has_zmmul     : boolean := false;
    -- Inclui a extensão Zifencei.
    has_zifencei  : boolean := false;
    -- Inclui a extensão Zicclsm.
    has_zicclsm   : boolean := false;
    -- Inclui a extensão Zimop.
    has_zimop     : boolean := false;
    -- Inclui a extensão Zicond.
    has_zicond    : boolean := false;
    -- Inclui as dicas ntl.* da extensão Zihintntl.
    has_zihintntl : boolean := false;
    -- Inclui a dica pause da extensão Zihintpause.
    has_zihintpause : boolean := false
  );
  port (
    -- Clock do núcleo.
    i_clk            : in  std_logic;
    -- Clock do chip externo; a plataforma modular usa um só clock, então fica sem uso.
    i_clk_mem        : in  std_logic := '0';
    -- Reset, ativo em '1'.
    i_rst            : in  std_logic := '0';
    -- Índice da palavra do chip de RAM que a porta de depuração lê.
    i_dbg_word_addr  : in  std_logic_vector(23 downto 0) := (others => '0');
    -- Palavra do chip de RAM no índice de i_dbg_word_addr.
    o_dbg_word_data  : out std_logic_vector(31 downto 0);
    -- Acesso à RAM interna do núcleo.
    o_ram_en         : out std_logic;
    -- Habilita a escrita na RAM.
    o_ram_wren       : out std_logic;
    -- Endereço do acesso à RAM.
    o_ram_addr       : out std_logic_vector(31 downto 0);
    -- Dado a escrever na RAM.
    o_ram_wdata      : out std_logic_vector(31 downto 0);
    -- Habilitação de bytes da escrita na RAM.
    o_ram_byteena    : out std_logic_vector(3 downto 0)
  );
end entity act_modular_top;

architecture structural of act_modular_top is
begin
  u_top : entity work.modular_sim_top
    generic map (
      boot_memory_file       => boot_memory_file,
      rom_file            => rom_file,
      ram_file            => ram_file,
      rom_external        => rom_external,
      ram_external        => ram_external,
      flash_first_latency => flash_first_latency,
      flash_next_latency  => flash_next_latency,
      ext_ram_latency     => ext_ram_latency,
      has_e               => has_e,
      has_zicsr           => has_zicsr,
      has_zicntr          => has_zicntr,
      has_zihpm           => has_zihpm,
      has_m               => has_m,
      has_zmmul           => has_zmmul,
      has_zifencei        => has_zifencei,
      has_zicclsm         => has_zicclsm,
      has_zimop           => has_zimop,
      has_zicond          => has_zicond,
      has_zihintntl       => has_zihintntl,
      has_zihintpause     => has_zihintpause
    )
    port map (
      i_clk           => i_clk,
      i_rst           => i_rst,
      i_dbg_word_addr => i_dbg_word_addr,
      o_dbg_word_data => o_dbg_word_data,
      o_ram_en        => o_ram_en,
      o_ram_wren      => o_ram_wren,
      o_ram_addr      => o_ram_addr,
      o_ram_wdata     => o_ram_wdata,
      o_ram_byteena   => o_ram_byteena
    );
end architecture structural;
