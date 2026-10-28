![FlexCNES logo](https://github.com/antth-Luca/FlexCNES/blob/v0.1.0/repo-icon.png)

# App FlexCNES — Assistente para preenchimento das fichas e planilha CNES

Aplicativo desktop (Python + CustomTkinter + SQLite), com tema Sistema/Claro/Escuro que coleta os dados e preenche:
- **Ficha 20** (Cadastro de Profissional) e **Ficha 21** (Continuação, até 3 vínculos por página; várias páginas se preciso) — em PDF, sobre os modelos originais. Pode-se gerar só a 20, só a 21 ou as duas.
- **Planilha "ALTERAÇÕES CNES"** — acrescenta/atualiza a aba do mês (inclusão, exclusão, outras alterações).

## Executar
    pip install -r requirements.txt
    python main.py
(Tkinter vem com o Python do Windows/macOS; no Linux: `sudo apt install python3-tk`.)

## Como funciona
1. **Primeiro acesso**: cria usuário e senha (mín. 8 caracteres; PBKDF2-SHA256 com salt). Depois, só usuário logado preenche documentos.
2. **Estabelecimento**: cadastrado uma vez (CNES, nome fantasia, município...), editável depois e reutilizado.
3. **Base CNES (opcional)**: menu para importar o ZIP do DATASUS; com ela, basta digitar o CNES para preencher o estabelecimento, e municípios/CBO são pesquisáveis.
4. Histórico dos registros, edição e regeração.
5. A planilha sai em .xlsx; se o **LibreOffice** estiver instalado, também é convertida para .xls.

Dados ficam em SQLite na pasta do usuário. Testes: `python tests/test_core.py` e `python tests/smoke_gui.py`.

## Gerar EXE (no Windows)
    pip install -r requirements.txt pyinstaller
    pyinstaller --onefile --windowed --name FlexCNES --icon assets/icon.ico --collect-all customtkinter --add-data "assets;assets" main.py
Resultado: `dist/FlexCNES.exe`. O tema escolhido fica em `config.json` na pasta de dados.
