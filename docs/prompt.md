preciso fazer uma aplicação em python para melhorar o processo de assinatura de folha de ponto na UnDF (Universidade do Distrito Federal). A folha de ponto é para os docentes, servidores e técnicos administrativos.
Basicamente, o sistema deve usar um padrão de folha de ponto, buscar o nome do servidor, cargo, função, UA (unidade administativa), exercício, matrícula, padrão (ainda vou conferir o que é) e carga horária.

----------------------------
requisitos do professor: UC: Estágio Empresarial 1 Prof.: Alexandre Natã Vicente
Sistema de Gestão de Folhas de Ponto — DIGEP
1 Problema
A Diretoria de Gestão de Pessoas (DIGEP) é responsável pelo gerenciamento das folhas
de ponto dos professores e servidores da instituição. Mensalmente, a unidade precisa digitalizar
e arquivar centenas de folhas de ponto, gerando um volume significativo de documentos que
precisam ser organizados e armazenados de forma adequada.
Além do arquivamento, existe uma necessidade específica relacionada aos professores que
acumulam cargo. Nesses casos, a folha de ponto deve ser encaminhada ao e-mail pessoal do
respectivo professor, para que ele possa anexá-la ao processo administrativo correspondente.
Atualmente, esse fluxo envolve uma quantidade significativa de trabalho manual e exige
que os documentos sejam posteriormente localizados quando há necessidade de consulta.
Dessa forma, há necessidade de uma solução que facilite a digitalização, identificação,
organização e arquivamento das folhas de ponto, bem como o encaminhamento das folhas aos
servidores que acumulam cargo.
O sistema deverá, portanto, contribuir para a redução do trabalho manual da DIGEP,
facilitar o tratamento mensal das folhas de ponto e permitir que os documentos arquivados
sejam localizados de maneira rápida e organizada sempre que houver necessidade de consulta
futura.
O problema central da DIGEP tem três etapas:
Receber/digitalizar centenas de folhas mensalmente;
Distribuir automaticamente determinadas folhas, especialmente para servidores que
acumulam cargo;
Arquivar e localizar rapidamente qualquer folha posteriormente.
2 Objetivo
Digitalizar e organizar o fluxo mensal das folhas de ponto dos servidores e docentes da
UnDF, permitindo:
• cadastro/importação dos servidores;
• associação da folha de ponto ao servidor e ao período;
• armazenamento do documento digitalizado;
• consulta posterior;
• identificação de servidores que acumulam cargo;
• envio automático da folha ao e-mail pessoal desses servidores;
• controle do que já foi digitalizado, enviado e arquivado.
UC: Estágio Empresarial 1 Prof.: Alexandre Natã Vicente
3 Requisitos do MVP
Automatizar o recebimento, identificação, arquivamento e distribuição das folhas de ponto
da DIGEP, utilizando OCR para extrair os dados dos documentos e associá-los
automaticamente aos respectivos servidores e competências.
UC: Estágio Empresarial 1 Prof.: Alexandre Natã Vicente
Funcionalidade MVP
Cadastro/importação de servidores
Cadastro de matrícula/identificação funcional
Registro de e-mail pessoal
Indicação de acumulação de cargo
Cadastro da competência (mês/ano)
Upload da folha digitalizada
Associação folha ↔ servidor ↔ competência
Armazenamento do PDF/imagem
Consulta por servidor
Consulta por competência
Download da folha
Busca por nome/matrícula
Identificação de folhas de acumuladores
Envio da folha ao e-mail pessoal
Registro de que o envio foi realizado
Controle de erro no envio
Controle de acesso
Histórico/auditoria básica
• RF01 — Cadastro de servidores
O sistema deverá permitir importar e manter os dados necessários dos servidores para
identificação e distribuição das folhas de ponto.
• RF02 — Upload em lote
O sistema deverá permitir o envio simultâneo de múltiplas folhas de ponto digitalizadas.
• RF03 — OCR
UC: Estágio Empresarial 1 Prof.: Alexandre Natã Vicente
O sistema deverá processar os documentos utilizando tecnologia OCR para extração das
informações relevantes da folha de ponto.
• RF04 — Extração de dados
O sistema deverá identificar, quando disponíveis, informações como matrícula, nome do
servidor e competência da folha.
• RF05 — Identificação automática
O sistema deverá utilizar os dados extraídos para identificar automaticamente o servidor
correspondente.
• RF06 — Arquivamento
O sistema deverá armazenar a folha associada ao servidor e à respectiva competência.
• RF07 — Consulta
O sistema deverá permitir localizar folhas arquivadas por servidor, matrícula e competência.
• RF08 — Visualização e download
O sistema deverá permitir visualizar e baixar folhas arquivadas.
• RF09 — Identificação de acumuladores
O sistema deverá identificar servidores que possuam acumulação de cargo.
• RF10 — Envio de folhas
O sistema deverá permitir o envio da folha de ponto do servidor acumulador para seu e-mail
pessoal cadastrado.
• RF11 — Controle de envio
O sistema deverá informar o estado do envio, incluindo pelo menos:
o pendente;
o enviado;
o erro.
• RF12 — Rastreamento
O sistema deve registrar data, destinatário e resultado do envio.

------------------------------------------------------------

tem na raiz do sistema: um docx que é a folha de ponto, e o excel é a base que serveria pra preencher - subindo na aplicação, identificando os campos, e alterando os campos no docx.

aplicação precisa ser em python, ja tem o 3.14 instalado

Agora temos que captar as informações, quaisquer duvidas agora vc deve me perguntar antes de planejar a implementação. A interface pode ser dentro do proprio pyhton e deve ser capaz de gerar um .exe so pra pessoa executar e facilitar a pessoa leiga a iniciar a aplicação. 
