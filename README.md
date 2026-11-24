# Corta-Mato Escolar AEPBS

Sistema de informação para gestão integral do corta-mato escolar do Agrupamento de Escolas de
Padre Benjamim Salgado, desenvolvido em **Python + Flet** com **base de dados relacional MySQL**
e arquitetura **MVC**.

Modelo do enunciado: `AEPBS-CP-028-2026a`.

---

## 1. Como executar

Requisitos: **MySQL 8** (ou MariaDB 10.5+) a correr localmente ou em rede, e Python 3.10+.

```bash
pip install -r requirements.txt
```

Configure a ligação ao servidor por variáveis de ambiente (ou edite as constantes no topo de
`cortamato/models/db.py`):

| Variável                  | Omissão     | Descrição                        |
|---------------------------|-------------|----------------------------------|
| `CORTAMATO_BD_HOST`       | `localhost` | Servidor MySQL                   |
| `CORTAMATO_BD_PORTA`      | `3306`      | Porta do servidor                |
| `CORTAMATO_BD_UTILIZADOR` | `root`      | Utilizador da base de dados      |
| `CORTAMATO_BD_PASSWORD`   | (vazia)     | Palavra-passe desse utilizador   |
| `CORTAMATO_BD_NOME`       | `corta_mato`| Nome da base de dados            |

Em PowerShell:

```powershell
$env:CORTAMATO_BD_UTILIZADOR="root"
$env:CORTAMATO_BD_PASSWORD="a-tua-password"
python app.py
```

A base de dados `corta_mato` é criada automaticamente no primeiro arranque (utf8mb4), a partir de
`schema.sql`, com:

- perfis e matriz de permissões pré-configurados;
- configuração inicial da atividade;
- escalões etários por sexo;
- conta de administrador: **admin / admin123** (alterar após o primeiro acesso).

Pastas geradas em tempo de execução:

| Pasta           | Conteúdo                                        |
|-----------------|-------------------------------------------------|
| `exportacoes/`  | Relatórios gerados em PDF e CSV                 |
| `comunicacoes/` | Mensagens aos DT (`.txt` e `.eml`)              |
| `modelos_csv/`  | Modelos CSV para importação de turmas e alunos  |

A pasta `assets/` guarda os elementos gráficos da aplicação. O logótipo oficial do
Desporto Escolar está em `assets/desporto_escolar.png` e é mostrado na entrada, no menu
lateral e no painel de controlo.

A fotografia de fundo é `assets/fundo_cortamato.jpg` (também são aceites `.jpeg`/`.png` ou
`fundo.jpg`). Para usar outra imagem, basta substituir esse ficheiro por uma fotografia da
prova; a imagem é esbatida sobre o verde da marca para manter a legibilidade do texto.

---

## 2. Arquitetura MVC

```
app.py                        ponto de entrada (Flet)
cortamato/
├── schema.sql                modelo relacional + dados iniciais (script SQL)
├── models/                   MODEL
│   ├── db.py                 conexão MySQL (PyMySQL), criação da BD, esquema e conta inicial
│   ├── entidades.py          dataclasses de domínio (classificações)
│   ├── repos_acesso.py       responsáveis, perfis e permissões
│   ├── repos_cadastro.py     turmas, alunos, escalões e configurações
│   ├── repos_inscricoes.py   inscrições
│   └── repos_prova.py        participações, chegadas, ocorrências e resultados
├── controllers/              CONTROLLER
│   ├── base.py               permissões, exceções, validações comuns
│   ├── auth.py               sessão, autenticação, password
│   ├── responsaveis.py       gestão de contas e perfis
│   ├── configuracoes.py      calendário, escalões, apuramentos
│   ├── importacao.py         importação CSV de turmas/DT e alunos
│   ├── inscricoes.py         secretariado de inscrições
│   ├── partida.py            secretariado de partida (dorsais)
│   ├── meta.py               secretariado de meta (chegadas/ocorrências)
│   ├── classificacoes.py     individual, por escalão, coletiva e apurados
│   └── relatorios.py         relatórios, exportações e e-mail aos DT
├── utils/                    segurança, datas, PDF, CSV, e-mail
└── views/                    VIEW (interfaces Flet)
    ├── shell.py              menu por permissões + painel de controlo
    ├── login.py              autenticação
    ├── configuracoes.py      configuração da atividade e escalões
    ├── importacoes.py        importação CSV
    ├── inscricoes.py         inscrições
    ├── partida.py            dorsais e listas de partida
    ├── meta.py               chegadas e ocorrências
    ├── classificacoes.py     classificações e apurados
    ├── relatorios.py         relatórios e comunicação aos DT
    └── responsaveis.py       contas e matriz de permissões
```

**Regras de dependência:** `views` → `controllers` → `models` → `utils`.
Nenhuma vista executa SQL e nenhum modelo conhece a interface.

---

## 3. Fluxo do processo

```
configurações → importação de alunos e turmas → secretariado de inscrições
→ secretariado de partida → secretariado de meta → classificações → relatórios
```

Cada passo corresponde a um módulo do menu, visível apenas a quem tem permissão.

---

## 4. Perfis de acesso propostos (e justificação)

| Perfil | Permissões | Justificação |
|---|---|---|
| **Administrador** | todas | Garante a configuração do sistema, contas e correções de última hora. |
| **Secretariado de Inscrições** | gerir e consultar inscrições | Vários professores registam inscrições nas suas aulas (processo descentralizado). |
| **Secretariado de Partida** | partida + consulta | Entrega física de dorsais e validação de quem participa. |
| **Secretariado de Meta** | meta + consulta | Registo de chegadas, desistências e desclassificações no funil. |
| **Resultados e Divulgação** | classificações + relatórios + e-mail | Trata e divulga resultados e comunica aos DT. |
| **Consulta (Direção/DT)** | consultar classificações e inscrições | Acesso de leitura, sem alteração de dados. |

Princípio aplicado: **privilégio mínimo** — cada perfil só tem as permissões das tarefas que executa.

Permissões existentes: `RESPONSAVEIS_GERIR`, `PERFIS_GERIR`, `CONFIG_GERIR`, `IMPORTAR_DADOS`,
`INSCRICOES_GERIR`, `INSCRICOES_CONSULTAR`, `PARTIDA_GERIR`, `META_GERIR`,
`CLASSIFICACOES_VER`, `RELATORIOS_EXPORTAR`, `EMAIL_ENVIAR`.

A verificação é feita em **dois níveis**: o menu esconde módulos não autorizados e cada operação
de escrita nos controladores exige a permissão correspondente (decorador `@requer`).

---

## 5. Modelo de dados (resumo)

- `perfil`, `permissao`, `perfil_permissao` — controlo de acessos (N:N entre perfis e permissões).
- `responsavel` — contas de acesso, associadas a um perfil.
- `configuracao` — pares chave/valor do calendário e das regras (apuramentos, pontuação).
- `turma` — código, designação, ano e diretor de turma.
- `aluno` — número, nome, sexo, data de nascimento, turma, código do cartão.
- `escalao` — designação, sexo, intervalo de idades e nº de apurados.
- `prova` — fases/provas previstas.
- `inscricao` — aluno inscrito, escalão atribuído, estado e responsável pelo registo.
- `participacao` — dorsal entregue (1:1 com inscrição) e estado na prova.
- `chegada` — ordem de chegada, hora, método (QRCode/manual) e validade.
- `ocorrencia` — desistências, desclassificações e correções (com motivo e autor).

Estados de inscrição: `nao_inscrito`, `inscrito`, `participante`, `organizacao`.

---

## 6. Regras de negócio implementadas

1. **Escalão automático**: calculado pelo sexo e pela idade no ano de referência configurado.
2. **Dorsal único**: atribuição automática (próximo livre) ou manual, sempre validada.
3. **Ordem de chegada automática**: cada leitura gera a ordem seguinte; desfazer/corrigir
   renumera toda a lista.
4. **Dorsal repetido bloqueado**: um atleta não pode ter duas chegadas.
5. **Desistência/desclassificação**: removem a chegada e excluem o atleta das classificações.
6. **Classificação individual**: ordenada pela ordem de chegada.
7. **Classificação por escalão/sexo**: posição relativa dentro do grupo, com apurados.
8. **Classificação coletiva**: soma das melhores posições de cada turma (menor total = melhor).
9. **Anulação de inscrição** bloqueada quando já existe dorsal entregue.

---

## 7. Relatórios e exportações

Todos os relatórios podem ser pré-visualizados na aplicação e exportados em **PDF** ou **CSV**
(pasta `exportacoes/`):

1. participantes inscritos;
2. participantes por escalão;
3. listas de dorsais;
4. classificações individuais;
5. classificações coletivas;
6. listas de apurados para a fase subsequente;
7. elementos de apoio à organização;
8. estatísticas da prova.

Além disso, o módulo de relatórios prepara a **mensagem de e-mail aos diretores de turma**,
agrupada por turma e distinguindo participantes de elementos de apoio, para justificação de faltas
(guardada em `comunicacoes/` como `.txt` e `.eml`).

O gerador de PDF (`cortamato/utils/pdf.py`) foi implementado apenas com a biblioteca padrão,
evitando dependências externas.

---

## 8. Plano de testes (manual)

| # | Cenário | Passos | Resultado esperado |
|---|---|---|---|
| 1 | Autenticação válida | Login com `admin/admin123` | Entra no painel e o menu mostra todos os módulos |
| 2 | Autenticação inválida | Password errada | Mensagem de erro, sem acesso |
| 3 | Conta desativada | Desativar conta e tentar entrar | Acesso recusado com aviso |
| 4 | Controlo de permissões | Entrar com perfil de Meta | Não vê Configurações nem Responsáveis |
| 5 | Importação de turmas | Importar CSV de turmas | Turmas criadas/atualizadas; erros listados |
| 6 | Importação de alunos | Importar CSV com turma inexistente | Linha rejeitada com mensagem clara |
| 7 | Inscrição | Inscrever aluno | Estado `inscrito`, escalão atribuído automaticamente |
| 8 | Escalão inexistente | Inscrever aluno sem data de nascimento | Erro de validação, inscrição não criada |
| 9 | Dorsal automático | Entregar dorsal sem indicar número | Dorsal = próximo livre |
| 10 | Dorsal duplicado | Forçar dorsal já usado | Erro, participação não criada |
| 11 | Chegada por dorsal | Registar dorsal 1 | Ordem 1 atribuída |
| 12 | Chegada repetida | Registar outra vez o dorsal 1 | Erro, ordem não duplicada |
| 13 | Desfazer chegada | Desfazer última | Registo removido e ordens renumeradas |
| 14 | Correção de ordem | Mover chegada para a posição 1 | Lista rerordenada corretamente |
| 15 | Desistência | Registar desistência de participante com chegada | Sai das classificações |
| 16 | Classificação por escalão | Consultar escalão | Posições e apurados corretos |
| 17 | Classificação coletiva | Consultar turma com 4 classificados | Pontuação igual à soma das 4 melhores posições |
| 18 | Exportação | Exportar PDF e CSV | Ficheiros criados em `exportacoes/` e legíveis |
| 19 | Comunicação aos DT | Gerar mensagem | Alunos agrupados por turma, separados por tipo |
| 20 | Anulação bloqueada | Anular inscrição com dorsal | Erro explicativo |

---

## 9. Notas técnicas e limitações conhecidas

- **Leitura de QRCode**: a aplicação suporta o registo por código de cartão/dorsal e o registo
  manual. A integração com um leitor físico (que se comporta como teclado) funciona através do
  campo de leitura; a câmara do dispositivo não é usada diretamente.
- **Autenticação** com PBKDF2-HMAC-SHA256 (120 000 iterações, salt individual).
- **Concorrência**: MySQL em modo servidor, adequado a vários postos em simultâneo (secretariados).
  A verificação sem interface (`python verificar_sistema.py`) usa uma base de dados temporária
  `cortamato_teste`, criada e apagada a cada execução.
- O envio de e-mail é preparado localmente (`.eml`), não exigindo servidor SMTP configurado.
