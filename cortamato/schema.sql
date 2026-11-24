CREATE TABLE IF NOT EXISTS perfil (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS permissao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS perfil_permissao (
    perfil_id INT NOT NULL,
    permissao_id INT NOT NULL,

    PRIMARY KEY (perfil_id, permissao_id),

    CONSTRAINT fk_pp_perfil
        FOREIGN KEY (perfil_id)
        REFERENCES perfil(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_pp_permissao
        FOREIGN KEY (permissao_id)
        REFERENCES permissao(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS responsavel (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    perfil_id INT NOT NULL,
    ativo TINYINT NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_responsavel_ativo
        CHECK (ativo IN (0, 1)),

    CONSTRAINT fk_responsavel_perfil
        FOREIGN KEY (perfil_id)
        REFERENCES perfil(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS configuracao (
    chave VARCHAR(100) PRIMARY KEY,
    valor TEXT,
    descricao TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS turma (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    designacao VARCHAR(150),
    ano INT,
    dt_nome VARCHAR(150),
    dt_email VARCHAR(190)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS aluno (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero VARCHAR(50) NOT NULL,
    nome VARCHAR(150) NOT NULL,
    sexo CHAR(1) NOT NULL,
    data_nascimento DATE,
    turma_id INT,
    codigo_cartao VARCHAR(100) UNIQUE,
    ativo TINYINT NOT NULL DEFAULT 1,

    CONSTRAINT chk_aluno_sexo
        CHECK (sexo IN ('M', 'F')),

    CONSTRAINT chk_aluno_ativo
        CHECK (ativo IN (0, 1)),

    CONSTRAINT fk_aluno_turma
        FOREIGN KEY (turma_id)
        REFERENCES turma(id)
        ON DELETE SET NULL,

    UNIQUE KEY uk_aluno_numero_turma (numero, turma_id),

    INDEX idx_aluno_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS escalao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    designacao VARCHAR(100) NOT NULL,
    sexo CHAR(1) NOT NULL,
    idade_min INT NOT NULL,
    idade_max INT NOT NULL,
    apurados INT NOT NULL DEFAULT 0,
    ativo TINYINT NOT NULL DEFAULT 1,

    CONSTRAINT chk_escalao_sexo
        CHECK (sexo IN ('M', 'F')),

    CONSTRAINT chk_escalao_ativo
        CHECK (ativo IN (0, 1)),

    UNIQUE KEY uk_escalao_designacao_sexo (designacao, sexo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS prova (
    id INT AUTO_INCREMENT PRIMARY KEY,
    designacao VARCHAR(150) NOT NULL,
    fase VARCHAR(100) NOT NULL DEFAULT 'Escolar',
    data_hora DATETIME,
    distancia_m INT,
    escalao_id INT,

    CONSTRAINT fk_prova_escalao
        FOREIGN KEY (escalao_id)
        REFERENCES escalao(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS inscricao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aluno_id INT NOT NULL,
    prova_id INT,
    escalao_id INT,
    data_inscricao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    estado VARCHAR(30) NOT NULL DEFAULT 'inscrito',

    responsavel_id INT,
    observacoes TEXT,

    CONSTRAINT chk_inscricao_estado
        CHECK (
            estado IN (
                'nao_inscrito',
                'inscrito',
                'participante',
                'organizacao'
            )
        ),

    CONSTRAINT fk_inscricao_aluno
        FOREIGN KEY (aluno_id)
        REFERENCES aluno(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_inscricao_prova
        FOREIGN KEY (prova_id)
        REFERENCES prova(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_inscricao_escalao
        FOREIGN KEY (escalao_id)
        REFERENCES escalao(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_inscricao_responsavel
        FOREIGN KEY (responsavel_id)
        REFERENCES responsavel(id)
        ON DELETE SET NULL,

    UNIQUE KEY uk_inscricao_aluno (aluno_id),

    INDEX idx_inscricao_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS participacao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inscricao_id INT NOT NULL UNIQUE,
    dorsal INT NOT NULL UNIQUE,

    estado VARCHAR(30) NOT NULL DEFAULT 'entregue',

    hora_dorsal DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    registado_por INT,

    CONSTRAINT chk_participacao_estado
        CHECK (
            estado IN (
                'pendente',
                'entregue',
                'desistente',
                'desclassificado'
            )
        ),

    CONSTRAINT fk_participacao_inscricao
        FOREIGN KEY (inscricao_id)
        REFERENCES inscricao(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_participacao_responsavel
        FOREIGN KEY (registado_por)
        REFERENCES responsavel(id)
        ON DELETE SET NULL,

    INDEX idx_participacao_dorsal (dorsal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chegada (
    id INT AUTO_INCREMENT PRIMARY KEY,
    participacao_id INT NOT NULL UNIQUE,
    ordem INT NOT NULL,

    hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    metodo VARCHAR(20) NOT NULL DEFAULT 'qr',
    valida TINYINT NOT NULL DEFAULT 1,

    registado_por INT,

    CONSTRAINT chk_chegada_metodo
        CHECK (metodo IN ('qr', 'manual')),

    CONSTRAINT chk_chegada_valida
        CHECK (valida IN (0, 1)),

    CONSTRAINT fk_chegada_participacao
        FOREIGN KEY (participacao_id)
        REFERENCES participacao(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_chegada_responsavel
        FOREIGN KEY (registado_por)
        REFERENCES responsavel(id)
        ON DELETE SET NULL,

    INDEX idx_chegada_ordem (ordem)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ocorrencia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    participacao_id INT NOT NULL,

    tipo VARCHAR(30) NOT NULL,

    motivo TEXT,

    hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    registado_por INT,

    CONSTRAINT chk_ocorrencia_tipo
        CHECK (
            tipo IN (
                'desistencia',
                'desclassificacao',
                'correcao'
            )
        ),

    CONSTRAINT fk_ocorrencia_participacao
        FOREIGN KEY (participacao_id)
        REFERENCES participacao(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_ocorrencia_responsavel
        FOREIGN KEY (registado_por)
        REFERENCES responsavel(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO perfil (nome, descricao) VALUES
('Administrador', 'Acesso total: configurações, contas e todos os secretariados'),
('Secretariado de Inscrições', 'Registo, alteração e anulação de inscrições dos alunos'),
('Secretariado de Partida', 'Entrega de dorsais e listas de partida'),
('Secretariado de Meta', 'Registo de chegadas, desistências e desclassificações'),
('Resultados e Divulgação', 'Classificações, relatórios, exportações e comunicação aos DT'),
('Consulta (Direção/DT)', 'Consulta de classificações e relatórios');

INSERT IGNORE INTO permissao (codigo, descricao) VALUES
('RESPONSAVEIS_GERIR', 'Gerir responsáveis, contas e perfis'),
('PERFIS_GERIR', 'Gerir perfis e matriz de permissões'),
('CONFIG_GERIR', 'Configurar atividade, calendário, escalões e apuramentos'),
('IMPORTAR_DADOS', 'Importar turmas, diretores de turma e alunos por CSV'),
('INSCRICOES_GERIR', 'Criar, alterar e anular inscrições'),
('INSCRICOES_CONSULTAR', 'Consultar inscrições e participantes'),
('PARTIDA_GERIR', 'Secretariado de partida: dorsais e listas de partida'),
('META_GERIR', 'Secretariado de meta: chegadas e ocorrências'),
('CLASSIFICACOES_VER', 'Consultar classificações individuais e coletivas'),
('RELATORIOS_EXPORTAR', 'Gerar e exportar relatórios em PDF/CSV'),
('EMAIL_ENVIAR', 'Preparar comunicações aos diretores de turma');

INSERT IGNORE INTO perfil_permissao (perfil_id, permissao_id)
SELECT p.id, pe.id
FROM perfil p
CROSS JOIN permissao pe
WHERE p.nome = 'Administrador';

INSERT IGNORE INTO perfil_permissao (perfil_id, permissao_id)
SELECT p.id, pe.id
FROM perfil p
CROSS JOIN permissao pe
WHERE p.nome = 'Secretariado de Inscrições'
AND pe.codigo IN (
    'INSCRICOES_GERIR',
    'INSCRICOES_CONSULTAR'
);

INSERT IGNORE INTO perfil_permissao (perfil_id, permissao_id)
SELECT p.id, pe.id
FROM perfil p
CROSS JOIN permissao pe
WHERE p.nome = 'Secretariado de Partida'
AND pe.codigo IN (
    'PARTIDA_GERIR',
    'INSCRICOES_CONSULTAR'
);

INSERT IGNORE INTO perfil_permissao (perfil_id, permissao_id)
SELECT p.id, pe.id
FROM perfil p
CROSS JOIN permissao pe
WHERE p.nome = 'Secretariado de Meta'
AND pe.codigo IN (
    'META_GERIR',
    'INSCRICOES_CONSULTAR'
);

INSERT IGNORE INTO perfil_permissao (perfil_id, permissao_id)
SELECT p.id, pe.id
FROM perfil p
CROSS JOIN permissao pe
WHERE p.nome = 'Resultados e Divulgação'
AND pe.codigo IN (
    'CLASSIFICACOES_VER',
    'RELATORIOS_EXPORTAR',
    'EMAIL_ENVIAR',
    'INSCRICOES_CONSULTAR'
);

INSERT IGNORE INTO perfil_permissao (perfil_id, permissao_id)
SELECT p.id, pe.id
FROM perfil p
CROSS JOIN permissao pe
WHERE p.nome = 'Consulta (Direção/DT)'
AND pe.codigo IN (
    'CLASSIFICACOES_VER',
    'INSCRICOES_CONSULTAR'
);

INSERT IGNORE INTO configuracao (chave, valor, descricao) VALUES
('designacao_atividade', 'Corta-Mato Escolar AEPBS', 'Designação da atividade'),
('edicao', '2026/2027', 'Edição da atividade'),
('data_prova', '2026-11-27', 'Data de realização da prova'),
('hora_partida', '09:30', 'Hora da primeira partida'),
('local', 'Parque Municipal', 'Local da prova'),
('prazo_inscricoes', '2026-11-20', 'Prazo limite de inscrições'),
('ano_referencia_idades', '2026', 'Ano civil usado no cálculo da idade dos atletas'),
('dorsais_inicio', '1', 'Primeiro dorsal a atribuir'),
('apurados_por_escalao', '6', 'Nº de apurados por escalão/sexo'),
('pontos_coletiva', '4', 'Nº de melhores classificados que pontuam por equipa'),
('email_remetente', 'direcao@aepbs.pt', 'Remetente das comunicações aos DT');

INSERT IGNORE INTO escalao
(designacao, sexo, idade_min, idade_max, apurados)
VALUES
('Infantis A', 'M', 10, 11, 0),
('Infantis A', 'F', 10, 11, 0),
('Infantis B', 'M', 12, 13, 0),
('Infantis B', 'F', 12, 13, 0),
('Iniciados', 'M', 14, 15, 0),
('Iniciados', 'F', 14, 15, 0),
('Juvenis', 'M', 16, 17, 0),
('Juvenis', 'F', 16, 17, 0),
('Juniores', 'M', 18, 19, 0),
('Juniores', 'F', 18, 19, 0);
