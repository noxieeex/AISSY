# Safety Layer da AISSY

A AISSY nunca terá acesso irrestrito ao sistema. Toda ação com efeito passa por uma camada de segurança independente do modelo de IA, que **bloqueia por padrão** ("fail closed").

## Estado atual (Fase 1)

Implementado e testado (`aissy/safety/`, `tests/test_safety.py`):

- **Ponto único de passagem:** ferramentas do modelo e atalhos em código viram uma `Action` e só chegam ao executor depois de `SafetyLayer.run`. Sem a camada, a ação é bloqueada.
- **Allowlist (menor privilégio):** só as operações listadas em `policy.py` são permitidas (tarefas e abrir apps da lista). O que não está listado é negado.
- **Blocklist permanente:** categorias que nenhuma permissão nem confirmação libera (leitura de memória de processos, injeção de código, hooks de teclado/mouse, automação de entrada ou de jogo, overlays, captura de tela, encerrar processos, registro do Windows, formatar discos, desativar segurança, alterar permissões, comandos de shell, elevação de privilégio).
- **Alvos protegidos:** qualquer alvo ou argumento que mencione Riot, Vanguard, League of Legends ou Valorant é negado, mesmo que alguém adicione o app em `data/apps.json`.
- **Origem da ação:** `user`, `model` ou `external`. Conteúdo externo nunca autoriza nada.
- **Audit log:** cada decisão e resultado é gravado em `data/audit.log` (JSONL, só acréscimo, fora do Git). Se não for possível gravar o log, a ação é bloqueada e a camada fica bloqueada até reiniciar.
- **Parada de emergência:** `/parar` (ou dizer "parar tudo") bloqueia todas as ações; `/retomar` libera. É tratada no `main.py` antes do modelo, então não depende dele.
- **Verificação de inicialização:** se a camada não passar na autoverificação, nenhuma ação executa na sessão.
- **Testes de arquitetura:** nenhum módulo pode importar bibliotecas de hook de teclado/mouse, captura de tela ou acesso a processos; só o executor de apps inicia processos.

## Riot Vanguard

A política da Riot proíbe, entre outras coisas, automação que age pelo jogador, apps que revelam informação escondida do jogo, análise em tempo real durante a partida e leitura de memória do jogo; o Vanguard não tem lista de apps liberados.

Por isso a AISSY **não faz nada disso**, e o código impede que faça: as categorias acima estão na blocklist permanente, os alvos da Riot são protegidos e há testes que quebram se alguém importar bibliotecas desse tipo. Isso reduz muito o risco, mas **não é garantia da Riot**: para uma resposta definitiva sobre um recurso específico, consulte o suporte da Riot.

Qualquer recurso futuro que envolva atalhos globais, captura de tela, overlay ou APIs do Windows sobre outros processos exige avaliação documentada antes de ser implementado.

## Limites conhecidos

- A camada roda no mesmo processo Python que o restante da AISSY. Ela protege contra erros do modelo e prompt injection, mas não contra código malicioso com os mesmos privilégios. Isolamento forte (processo separado, usuário de baixo privilégio) está previsto para fases futuras.
- Ainda **não há** confirmação genérica (a confirmação de memória continua separada), permissões por pasta, backups, sandbox nem limites de recursos para ações.
- Comandos diretos da usuária (`/feito`, `/apagar`) e a gravação de memória ainda não passam pela camada.

- A voz neural opcional (`--voz-online`) é a única parte que usa rede: envia só o texto das respostas para gerar áudio. Não executa nada e não lê nada do sistema.
- A AISSY continua restrita ao terminal/VS Code: nenhum acesso ao desktop, a janelas ou a outros processos.

## Decisões tomadas

- `steam` não está na lista padrão de apps (pode ser adicionado em `data/apps.json`).
- O modo voz continua ligado por padrão.
- O log fica em `data/audit.log`.
- Nenhuma ação sensível (excluir, sobrescrever) pode ser proposta pelo modelo nesta fase, porque ainda não existe nenhuma.

## Próximas fases

2. Confirmation Gate genérico, preso à ação exata.
3. Processo vigia para a parada de emergência e avaliação de atalho global (checando o Vanguard).
4. Permissões por pasta, começando por leitura, com conteúdo externo tratado como dado não confiável.
5. Escrita e exclusão com backup, confirmação e reversão; sandbox e limites de recursos antes de qualquer execução de comandos.
6. Integração com projetos e jogos desenvolvidos por você, com permissão explícita para cada um.
