# AISSY explicada para quem pergunta (versão leiga)

## Em uma frase
A AISSY é uma assistente pessoal que roda no meu computador: eu converso com ela por voz ou texto, ela lembra de coisas que eu pedi, anota tarefas e lembretes, e só faz o que uma camada de segurança permite.

## Como ela funciona (a analogia)
Pense numa recepcionista:
- **O cérebro (o modelo de linguagem).** Um modelo de IA que roda local, pelo Ollama (`qwen2.5:7b`). Ele conversa e decide quando precisa de uma ferramenta. Roda no meu PC, não na nuvem.
- **As mãos (ferramentas / tool calling).** O modelo não faz nada sozinho. Ele "pede" uma ferramenta (anotar tarefa, ver a data, abrir um app) e o meu código executa. Isso é tool calling.
- **A memória.** Ela guarda coisas que eu peço para lembrar, num banco SQLite. Para achar a memória certa, usa dois tipos de busca juntos: por palavras e por **significado** (embeddings, modelo `bge-m3`). Embedding é transformar um texto em números de modo que frases parecidas fiquem "perto". Por isso "meu horário de estudo" acha "estudo cálculo às 19h" mesmo sem palavras iguais.
- **Os ouvidos e a boca.** Reconhecimento de fala (`faster-whisper`) e síntese de voz. Ela responde frase a frase enquanto o modelo ainda gera (streaming), para parecer mais rápida.
- **O segurança (Safety Layer).** Toda ação com efeito passa por uma camada que não depende do modelo: lista do que é permitido, lista do que é proibido, registro de tudo e um botão de parada de emergência. Na dúvida, não executa. Foi pensada também para nunca mexer em jogos nem no anti-cheat.

## Decisões e por quê (as perguntas que podem fazer)

**Por que um modelo local e não uma API?**
Privacidade (minhas conversas e memórias ficam no meu PC), custo zero e eu aprendo mais montando as peças. O provedor é trocável: já existe código para a API da OpenAI, mas não foi validado com chamadas reais.

**Por que alguns pedidos são tratados por regras e não pelo modelo?**
Modelos pequenos erram. Lembretes e abrir app são ações com efeito, então uso regras em código (previsíveis e testáveis). O modelo cuida da conversa. Também tenho uma trava que troca respostas do tipo "anotei!" quando nada foi salvo de verdade, porque o modelo às vezes afirma que fez algo que não fez.

**O que é a busca híbrida e como escolhi o limiar?**
Combina busca por palavras e por significado. Medi num conjunto de 13 perguntas com 4 casos que não deveriam achar nada, e escolhi o limiar 0.5 olhando acertos e falsos positivos. É um conjunto pequeno, então serve para decidir, não para provar.

**Onde há treino de verdade?**
O classificador de idioma. Treinei com exemplos que escrevi, separei treino e teste, e comparei com a regra antiga: 97% contra 72% no teste, 93% contra 60% num conjunto extra de frases curtas. É um modelo simples (Naive Bayes sobre trechos de letras), de propósito: dá para explicar e inspecionar. Não fiz fine-tuning de LLM.

**Por que o classificador não decide os pedidos que executam ações?**
Porque um erro estatístico não pode virar uma ação no computador. Ações ficam em regras e passam pela Safety Layer.

**Como você testa?**
Testes automáticos com `pytest` usando peças falsas (modelo falso, voz falsa), então rodam sem GPU. Para qualidade do modelo, tenho scripts de avaliação (busca de memória, persona e idioma). O que depende de áudio e Windows eu testo à mão.

## Limites (dizer sem medo, mostra maturidade)
- O modelo de 7B ainda erra às vezes (gramática, tom).
- Usuária única, sem login.
- A Safety Layer roda no mesmo processo; protege contra erros do modelo e instruções maliciosas em textos, não contra código malicioso.
- Treino: só o classificador de idioma, com poucos exemplos. Sem fine-tuning.
- Não está validado ao vivo: lembrete falado no horário, abrir app no Windows, parar/retomar (conferir antes de afirmar).
- A voz neural opcional manda o texto das respostas para um serviço online; a padrão é 100% local.

## O que NÃO dizer
- Que ela "aprende sozinha" ou "se treina": o treino é um script que eu rodo.
- Que tem fine-tuning, RAG sobre documentos ou deploy em nuvem: não tem.
- Que acessa meu computador: ela fica no terminal.
- Que a segurança é "à prova de tudo": é uma primeira fase.

## Resumo de 20 segundos (para entrevista)
"Construí uma assistente pessoal em Python que roda um modelo local. Ela usa tool calling para executar ações, memória com busca híbrida por palavras e significado, voz, e uma camada de segurança independente do modelo. Avaliei as partes com métricas, por exemplo treinei um classificador de idioma que subiu de 72% para 97% no teste, e sei dizer o que ainda não funciona."
