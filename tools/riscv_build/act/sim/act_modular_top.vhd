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
    -- Imagem da BOOT_ROM, uma palavra de 32 bits por linha em hexadecimal.
    boot_rom_file : string  := "default.hex";
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
    has_zicsr     : boolean := false;
    has_zicntr    : boolean := false;
    has_zihpm     : boolean := false;
    has_m         : boolean := false;
    has_zmmul     : boolean := false;
    has_zifencei  : boolean := false;
    has_zicclsm   : boolean := false
  );
  port (
    -- Clock do núcleo.
    CLK            : in  std_logic;
    -- Clock do chip externo; a plataforma modular usa um só clock, então fica sem uso.
    CLK_MEM        : in  std_logic := '0';
    -- Reset, ativo em '1'.
    reset          : in  std_logic := '0';
    -- Índice da palavra do chip de RAM que a porta de depuração lê.
    DBG_WORD_ADDR  : in  std_logic_vector(23 downto 0) := (others => '0');
    -- Palavra do chip de RAM no índice de DBG_WORD_ADDR.
    DBG_WORD_DATA  : out std_logic_vector(31 downto 0);
    -- Barramento de dados da RAM interna do núcleo.
    ram_en         : out std_logic;
    ram_wren       : out std_logic;
    ram_addr       : out std_logic_vector(31 downto 0);
    ram_wdata      : out std_logic_vector(31 downto 0);
    ram_byteena    : out std_logic_vector(3 downto 0)
  );
end entity act_modular_top;

architecture structural of act_modular_top is
begin
  top_inst : entity work.modular_sim_top
    generic map (
      boot_rom_file       => boot_rom_file,
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
      has_zicclsm         => has_zicclsm
    )
    port map (
      i_clk           => CLK,
      i_rst           => reset,
      i_dbg_word_addr => DBG_WORD_ADDR,
      o_dbg_word_data => DBG_WORD_DATA,
      o_ram_en        => ram_en,
      o_ram_wren      => ram_wren,
      o_ram_addr      => ram_addr,
      o_ram_wdata     => ram_wdata,
      o_ram_byteena   => ram_byteena
    );
end architecture structural;
