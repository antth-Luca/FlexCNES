# FlexCNES v0.2.0

Preenche as Fichas 20/21 (PDF) e a planilha mensal "ALTERAÇÕES CNES" (xlsx).
Python + CustomTkinter + SQLite. Tema Sistema/Claro/Escuro.

## Executar
    pip install -r requirements.txt
    python main.py

## Novidades da 0.2.0
- **Administrador:** o 1º usuário criado é o administrador. Ele cadastra, edita (nome, login, ativo/desativado)
  e redefine a senha de usuários comuns (menu **Conta ▸ Administração**). A senha definida pelo administrador é
  temporária: o usuário é obrigado a trocá-la no próximo acesso.
- **Minha senha:** qualquer usuário troca a própria senha informando a atual (**Conta ▸ Alterar minha senha**).
- **Lupa:** o código do CBO (Ficha 21) tem uma lupa antes do campo: busca por código ou descrição e preenche os dois. Os campos de município (nascimento e residência) ficaram menores e têm um botão de lupa ao lado
  que preenche o IBGE e a UF pela base CNES.
- **Local do banco:** padrão em `%APPDATA%\FlexCNES_Preenchimento`. O administrador pode apontar outra pasta,
  inclusive de rede (`\\servidor\compartilhamento\FlexCNES`), em **Conta ▸ Administração ▸ Banco de dados**.
  Cada computador guarda essa escolha no seu próprio `config.json`.
  - No 1º acesso de um computador novo, use **Usar banco de dados existente (rede)…** para ligar-se ao banco já criado.
  - O acesso é verificado ao abrir o programa (com opções se falhar), a cada 30 s (faixa vermelha + aviso) e ao salvar.
  - Bancos da v0.1 são migrados sozinhos; o primeiro usuário existente vira administrador.

## Atenção ao usar rede
O SQLite em pasta de rede funciona para poucos usuários simultâneos. Evite sincronizadores (OneDrive/Dropbox)
na pasta do banco e faça cópias de segurança da pasta com frequência. A base CNES importada continua local.

## Gerar EXE (no Windows, com o venv ativo)
    pip install -r requirements.txt pyinstaller
    python -m PyInstaller --onefile --windowed --name FlexCNES --icon assets/icon.ico --collect-all customtkinter --add-data "assets;assets" main.py

## Testes
    python tests/test_core.py
    python tests/smoke_gui.py      # usa um Tkinter simulado; não substitui um teste visual no Windows
