# Feiras PT

Calendário de feiras tradicionais e gastronómicas em Portugal (continente, Madeira e Açores), em dois ficheiros .ics: <https://machado65.github.io/feiras-pt/feiras.ics> em português e <https://machado65.github.io/feiras-pt/fairs.ics> em inglês. O repositório é público e muitos dos utilizadores são estrangeiros, por isso a versão inglesa conta tanto como a portuguesa. O dono subscreve a versão portuguesa no Google Calendar. Uma routine do Claude na cloud revê o calendário no dia 1 de cada mês.

## Como funciona

- `feiras.json` é a única fonte de verdade. A routine só mexe neste ficheiro.
- `gerar_ics.py` valida o JSON e gera `_site/feiras.ics` (português) e `_site/fairs.ics` (inglês). Usa só a biblioteca padrão.
  - `python3 gerar_ics.py --listar` mostra as feiras por data.
  - `python3 gerar_ics.py --formatar` valida, ordena e normaliza o JSON e gera os dois .ics.
- `.github/workflows/publicar.yml` corre em cada push para `main`: valida, gera e publica no GitHub Pages.
- `.github/workflows/integrar.yml` corre quando um ramo `claude/*` recebe um push (é para onde a routine faz push). Se o ramo só mudar `feiras.json` e o ficheiro for válido, junta as alterações no `main` num único commit do github-actions (o Claude nunca aparece como autor no `main`), apaga o ramo e dispara a publicação. Se mudar outros ficheiros, falha e não junta nada.
- O Google Calendar e as outras apps voltam a ler os .ics sozinhas (pode demorar até um dia).

## O que entra

O dono quer feiras tradicionais e de gastronomia, de todo o país por igual:

- feiras e mercados medievais ou de época;
- feiras e festivais gastronómicos e de produtos regionais (fumeiro, queijo, castanha, chocolate, doçaria conventual, marisco, porco, mel, pão...);
- feiras e festas do vinho;
- feiras anuais históricas (Feira de São Mateus, Feira de Março, Feiras Novas, Feira dos Santos, Feira Nacional do Cavalo...);
- feiras de artesanato de referência;
- mercados e vilas de Natal de referência.

Uma feira é "interessante" quando é conhecida a nível nacional ou regional, já tem várias edições, dura pelo menos um fim de semana (ou é um dia muito marcante) e tem datas publicadas por uma fonte credível. Prefere qualidade a quantidade: o alvo é ter 4 a 10 feiras por mês.

Não entram:

- mercados semanais ou mensais regulares (Feira da Ladra, feira semanal de Barcelos);
- arraiais, festas populares e romarias sem uma feira a sério;
- feiras profissionais (B2B) e salões comerciais (automóvel, imobiliário, noivos);
- feiras do livro, de tecnologia, gaming ou emprego (o dono não as quer neste calendário);
- eventos fora de Portugal.

## Formato de feiras.json

```json
{
  "feiras": [
    {
      "id": "feira-do-fumeiro-vinhais-2027",
      "nome": "Feira do Fumeiro de Vinhais",
      "nome_en": "Vinhais Smoked Meats Fair",
      "categoria": "gastronomia",
      "inicio": "2027-02-04",
      "fim": "2027-02-07",
      "confirmado": false,
      "cidade": "Vinhais",
      "distrito": "Bragança",
      "descricao": "Uma ou duas frases factuais em português de Portugal.",
      "descricao_en": "The same in British English.",
      "nota": "Datas estimadas: em 2025 foi de 6 a 9 e em 2026 de 5 a 8 de fevereiro.",
      "nota_en": "Estimated: 6–9 February in 2025 and 5–8 February in 2026.",
      "url": "https://www.cm-vinhais.pt/",
      "fonte": "https://onde-confirmaste-as-datas",
      "atualizado": "2026-11-08"
    }
  ]
}
```

- `id`: minúsculas sem acentos, números e hífenes, a acabar no ano de `inicio`. **Nunca mudes o id de uma entrada que já existe**: é o UID do evento no calendário, e mudá-lo cria um duplicado no telemóvel do dono. Se as datas mudarem, mudam-se as datas e mantém-se o id.
- Uma entrada por edição. A edição do ano seguinte é uma entrada nova, com id novo.
- `categoria`: `medieval`, `gastronomia`, `vinho`, `natal`, `artesanato` ou `tradicional`.
- `inicio` e `fim` são inclusivos (AAAA-MM-DD).
- `confirmado: true` só quando as datas desta edição foram publicadas pela organização ou pela câmara, ou por imprensa ou agenda que as cite. Datas deduzidas de anos anteriores levam `confirmado: false` e uma `nota` a explicar de onde vêm (o validador obriga).
- `local` (opcional): recinto ou zona. `cidade`: localidade ou concelho. `distrito`: distrito, ou `Madeira` ou `Açores`.
- `url`: a melhor página para o visitante (organização ou câmara). `fonte`: a página onde confirmaste as datas (pode ser a mesma).
- `nota` (opcional nas confirmadas): informação prática curta.
- `nome_en`, `descricao_en` e `nota_en` são a versão inglesa (inglês britânico) e são obrigatórios; `nota_en` existe sempre que existir `nota`. Traduz os nomes descritivos (Feira do Queijo → Cheese Fair) e mantém os nomes próprios (Wonderland Lisboa, Feiras Novas, Perlim). Explica em poucas palavras os termos locais, por exemplo "água-pé (young wine)". O calendário inglês mostra também o nome português.
- `estado: "cancelada"` quando uma edição é cancelada. Mantém a entrada; o calendário mostra-a como cancelada.
- `atualizado`: põe a data de hoje sempre que mudares uma entrada, e só nesse caso.

## Atualização mensal

Este é o procedimento da routine, que corre no dia 1 de cada mês. Segue-o do princípio ao fim.

1. Corre `python3 gerar_ics.py --listar` para ver o estado atual.
2. **Confirmar.** Para cada entrada com `confirmado: false` que comece nos próximos 6 meses, procura as datas oficiais. Se as encontrares, corrige as datas, põe `confirmado: true`, atualiza `fonte` e `atualizado` e apaga a `nota` (ou troca-a por informação prática).
3. **Rever as próximas.** Para as entradas que comecem nas próximas 6 semanas, procura adiamentos, mudanças de datas ou cancelamentos.
4. **Procurar novas** para os próximos 12 meses:
   - Percorre a lista de referência abaixo. Se uma feira anual não tiver entrada para a próxima edição e essa edição começar nos próximos 12 meses, cria-a. Usa datas oficiais se já existirem; se não, estima-as a partir da última edição (mesmo dia da semana) com `confirmado: false`.
   - Não fiques pela lista de referência. Para cada um dos próximos 3 meses, pesquisa feiras gastronómicas, de vinho e medievais (e mercados de Natal, na época) em todas as regiões: Minho, Trás-os-Montes, Beiras, Centro, Lisboa, Alentejo, Algarve, Madeira e Açores. Por exemplo: "feiras gastronómicas dezembro 2026", "feira do fumeiro janeiro 2027", "mercado de Natal 2026 Braga", "feira do queijo fevereiro 2027". As feiras destes 3 meses são as que mais importam, porque na revisão seguinte algumas já terão começado.
   - Antes de criar uma entrada, confirma que ainda não existe (procura pelo nome e pela cidade).
5. **Limpar.** Apaga as entradas que terminaram há mais de 12 meses.
6. Corre `python3 gerar_ics.py --formatar`. Tem de terminar sem erros; se der erros, corrige-os.
7. Se `feiras.json` mudou, faz commit só desse ficheiro com uma mensagem como `Feiras: +3 novas, 2 confirmadas, 1 cancelada` e faz push para o ramo em que estás (nunca para o `main`). Se nada mudou, não faças commit.
8. Acaba com um resumo em português de Portugal: o que adicionaste, confirmaste, alteraste ou removeste, cada um com a fonte. Diz também o que procuraste e não conseguiste confirmar.

Regras:

- Não inventes datas. Uma data estimada leva sempre `confirmado: false` e uma nota.
- Não mexas noutros ficheiros. Se achares que o código, os workflows ou este documento precisam de mudar, diz isso no resumo.
- Escreve os campos em português de Portugal e os campos `_en` em inglês britânico, sem emojis. O resumo final é em português de Portugal.
- Os commits não levam `Co-Authored-By` nem menções ao Claude: o dono é o único autor do projeto.

## Fontes úteis

- Sites das câmaras (`cm-<concelho>.pt`, por exemplo cm-vinhais.pt, cm-montalegre.pt, cm-borba.pt). Muitas publicam a agenda ou o regulamento da feira em PDF.
- viralagenda.com (por distrito e concelho, nas categorias "markets-fairs" e "gastronomy"), e-konomista.pt (guias mensais de feiras medievais, castanha e Natal), agroportal.pt (feiras agrícolas e de fumeiro), turismodocentro.pt, visitalentejo.pt, visitlisboa.com, portosecreto.co, lisboasecreta.co, nit.pt, timeout.pt, postal.pt e sulinformacao.pt (Algarve), visitmadeira.com, visitazores.com.
- essenciadovinho.com tem as datas das edições do Essência do Vinho em Lisboa, na Madeira e no Porto. A imprensa regional (noticiasdevilareal.sapo.pt, odigital.sapo.pt, radiocampanario.com, linhasdeelvas.pt) costuma anunciar as datas das feiras do interior antes das agendas.
- visitportugal.com bloqueia pedidos automáticos (desafio "Anubis"). Usa os excertos que aparecem nos resultados da pesquisa em vez de abrir as páginas.
- Na cloud, o WebFetch pode não chegar a muitos sites (câmaras, viralagenda, e-konomista). Quando falhar, usa os excertos da pesquisa e diz no resumo que as datas vêm daí.

## Lista de referência

Feiras anuais a acompanhar. A lista não é fechada: acrescenta ao calendário outras que cumpram os critérios.

| Feira | Local | Altura habitual |
| --- | --- | --- |
| Festa das Chouriças | Querença (Loulé) | 3.º fim de semana de janeiro |
| Feira do Fumeiro e Presunto do Barroso | Montalegre | fim de janeiro, quinta a domingo |
| Feira Gastronómica do Porco | Boticas | janeiro |
| Feira do Fumeiro de Vinhais | Vinhais | início de fevereiro, quinta a domingo |
| Festival do Butelo e das Casulas | Bragança | à volta do Carnaval |
| Feiras do queijo Serra da Estrela | Celorico da Beira, Oliveira do Hospital, Seia, Fornos de Algodres | fevereiro a março |
| Feira do Queijo do Alentejo | Serpa | fevereiro ou março |
| Essência do Vinho | Porto (Palácio da Bolsa) | fim de fevereiro |
| Festival Internacional de Chocolate | Óbidos | março, fins de semana |
| Feira do Porco Alentejano | Ourique | março |
| Feira dos Enchidos Tradicionais | Monchique | março |
| Feira de Março | Aveiro | 25 de março a fim de abril |
| Ovibeja | Beja | fim de abril ou início de maio |
| Festival Islâmico | Mértola | maio dos anos ímpares |
| Feira Nacional de Agricultura | Santarém (CNEMA) | início de junho |
| Feira de São João | Évora | 23 de junho a início de julho |
| FIA Lisboa – Feira Internacional de Artesanato | Lisboa (FIL) | fim de junho a início de julho |
| Feira do Alvarinho | Monção | início de julho |
| Festival Medieval | Elvas | início de julho |
| Mercado Medieval | Óbidos | segunda quinzena de julho |
| Feira de Sant'Iago | Setúbal | fim de julho a início de agosto |
| Feira Nacional de Artesanato | Vila do Conde | fim de julho a agosto |
| FIARTIL – Feira de Artesanato do Estoril | Cascais | julho a agosto |
| Viagem Medieval em Terra de Santa Maria | Santa Maria da Feira | fim de julho a início de agosto |
| Festival da Sardinha | Portimão | início de agosto |
| Feira Medieval de Silves | Silves | agosto, até dia 15 |
| Festival do Marisco | Olhão | 10 a 15 de agosto |
| Festival do Bacalhau | Ílhavo | agosto |
| Feira de São Mateus | Viseu | agosto a setembro |
| Dias Medievais | Castro Marim | fim de agosto |
| Festa do Vinho Madeira | Funchal | fim de agosto a meados de setembro |
| Feira do Vinho do Dão | Nelas | início de setembro |
| Festa das Vindimas | Palmela | início de setembro |
| Feiras Novas | Ponte de Lima | setembro |
| Feira da Luz | Lisboa (Carnide) | setembro |
| Feira de Santa Iria | Faro | outubro |
| Festival Nacional de Gastronomia | Santarém | fim de outubro a início de novembro |
| Rural Castanea – Festa da Castanha | Vinhais | fim de outubro |
| Feira dos Santos | Chaves | fim de outubro a 1 de novembro |
| Feira Nacional do Cavalo | Golegã | novembro, à volta do São Martinho |
| Festa da Vinha e do Vinho | Borba | novembro, à volta do São Martinho |
| Festa do Castanheiro – Feira da Castanha | Marvão | novembro |
| Feira do Mel e da Castanha | Lousã | novembro |
| Mostra Internacional de Doces & Licores Conventuais | Alcobaça | novembro |
| Mercados e vilas de Natal (Wonderland Lisboa, Óbidos Vila Natal, Perlim, Águeda é Natal, mercado de Natal do Porto) | vários | fim de novembro a início de janeiro |
