# TP Entrevistas

Teleprompter local para entrevistas, em inglês ou português. Funciona de dois jeitos:

- **✨ Gerar respostas com IA.** Você diz a sua área ou cola a descrição da vaga, e a IA prepara cards com as perguntas mais prováveis. Durante a entrevista, você cola a pergunta ou um print dela, e a resposta aparece na tela em cerca de 3 segundos.
- **📄 Usar o seu texto pronto.** Você cola o texto ou anexa um `.docx`, `.txt` ou `.md`, e ele vira o roteiro na tela. Títulos dividem o texto em vários cards.

Foi pensado para quem conhece o assunto, mas quer apoio para não travar nem enrolar, principalmente numa segunda língua.

*English: a local AI teleprompter for job interviews in English or Portuguese. Generate answer cards from your resume and the job description, get live answers from a pasted question or screenshot, or load your own script (.docx/.txt/.md). Runs on your Claude subscription through Claude Code.*

## Destaques

- **Usa a sua assinatura do Claude.** O servidor chama o [Claude Code](https://claude.com/claude-code), então o plano Pro ou Max basta. Não precisa de chave de API e não há custo por uso.
- **Lê um print da pergunta.** Aperte Cmd+V com a imagem e ele lê a pergunta, mesmo quando a plataforma não deixa copiar o texto.
- **Respostas com cara de gente falando.** As frases têm o tamanho do seu nível de idioma e usam só fatos que você informou. Um filtro barra os vícios de IA ("não só X, mas Y", jargões, travessões).
- **Modo compacto para a câmera.** O texto fica numa coluna estreita logo abaixo da webcam, com rolagem automática, para os olhos quase não se mexerem.
- **Sem dependências.** É um arquivo Python que só usa a biblioteca padrão, mais uma página HTML.

## Requisitos

- macOS. O `start.sh`, que abre a janela no topo da tela, só funciona no macOS. O servidor roda em qualquer sistema com Python e Claude Code.
- Python 3.9 ou mais novo.
- [Claude Code](https://claude.com/claude-code) instalado e com login na sua conta (`claude auth login`).
- Google Chrome (opcional, para a janela sem barra de endereço).

## Como usar

```bash
git clone https://github.com/o-bom-redator/TP_Entrevistas.git
cd TP_Entrevistas
./start.sh
```

O `start.sh` liga o servidor e abre a janela. Outra opção é rodar `python3 server.py` e abrir http://localhost:8765.

Na primeira vez, aparece a tela de configuração:

1. Escolha o **idioma das respostas** (inglês ou português), o seu **nível de inglês** e a **duração** de cada resposta.
2. Escolha o caminho:
   - **Gerar respostas com IA:** em "Sobre você", cole o currículo ou anexe o arquivo; em "Vaga ou área", cole a vaga ou só escreva a área. Depois clique em **Gerar cards e começar**, ou em **Começar sem cards** para usar só as respostas ao vivo.
   - **Usar meu texto pronto:** cole o texto ou anexe o arquivo. Linhas `## Título` ou títulos do Word dividem o texto em cards.
3. Para mudar alguma coisa depois, clique em **⚙**.

Tudo o que você configura fica salvo na pasta `data/`, que não vai para o Git. Seus dados ficam só no seu computador e no Claude.

## Atalhos

| Ação | Como |
|---|---|
| Resposta a partir de um print | Cmd+Ctrl+Shift+4 (copia a área selecionada), clique no teleprompter e aperte Cmd+V |
| Resposta a partir de texto | Cole a pergunta no campo e aperte Enter |
| Abrir um card pronto | Digite 1 ou 2 palavras da pergunta |
| Ligar/desligar a rolagem | Espaço |
| Velocidade da rolagem | ↑ / ↓ |
| Tamanho da fonte | A− / A+ |
| Modo compacto | C |
| Voltar ao campo de busca | Esc |

O seletor de modelo alterna entre o **Sonnet** (padrão, segue melhor os seus fatos) e o **Haiku** (um pouco mais rápido).

## Dicas para olhar para a câmera

- Deixe a janela o mais perto possível da webcam. `./start.sh 600 220` define a largura e a altura. Ocultar a barra de menus do macOS faz a janela subir uns 3 cm.
- Sente um pouco mais longe e aumente a fonte. Quanto mais longe, menos o movimento dos olhos aparece.
- Use a rolagem automática, para a linha que você lê ficar sempre no mesmo lugar.
- Use o texto como guia: leia uma frase, olhe para a câmera e fale.

## Uso responsável

Use para treinar, ensaiar e em situações em que consultar anotações é permitido. Muitas plataformas de entrevista e de avaliação proíbem respostas com roteiro ou com IA, então confira as regras antes. E confira cada fato gerado antes de falar.

## Problemas comuns

- **`[ERROR] … OAuth access token has expired`**: rode `claude auth login`.
- **Primeira resposta lenta**: o servidor já ignora os seus servidores MCP, hooks e plugins. Se continuar lento, rode `claude -p oi` uma vez no terminal.
- **A janela não abre no lugar certo**: o `start.sh` usa um perfil separado do Chrome (`~/.ai-teleprompter-chrome`) para que o tamanho e a posição sejam respeitados.

## Licença

MIT
