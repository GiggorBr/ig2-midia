# Erros, bloqueios e boas práticas (instagram-celular)

## Mapa de erros

| Erro no JSON | O que significa | O que fazer |
|---|---|---|
| `ChallengeRequired` | Instagram quer confirmar que é você | Usuário abre o app → "Fui eu" → `login` de novo |
| `aguardando_codigo` (stderr) | Código enviado por e-mail/SMS | `echo CODIGO > ~/.ig_celular/codigo.txt` |
| `TwoFactorRequired` | Conta com 2FA | Configure `IG_TOTP_SEED` (ou desative 2FA por SMS e use app autenticador) |
| `BadPassword` | Senha errada **ou** IP bloqueado | Confira senha; use `IG_PROXY` residencial BR; ou Plano B sessionid |
| `UnknownError` "versão desatualizada" | Instagram recusou a versão do app simulada | Plano B sessionid; `pip install -U instagrapi`; ou `IG_APP_VERSION`/`IG_VERSION_CODE`/`IG_BLOKS_ID` |
| `LoginRequired` | Sessão expirou | `login` (com senha) ou novo sessionid |
| `FeedbackRequired` | **Ação bloqueada** | Parar 24–48 h. Não insistir. |
| `PleaseWaitFewMinutes` | Rate limit | Esperar 15–30 min |
| `UserNotFound` | @ errado | Conferir o usuário |
| `ClientForbiddenError` / 403 | Ação não permitida (conta privada etc.) | Pular esse alvo |

Para depurar: `IG_DEBUG=1 python3 scripts/ig_celular.py ...`

## Aquecimento de conta
- Primeira semana usando o script: só leitura (perfil, feed, inbox) + 1 post/dia.
- Depois aumente 20% por semana até os limites padrão.

## Nuvem vs. computador pessoal
- No computador da pessoa (IP residencial) o risco é bem menor.
- Em servidores/cloud (IP de datacenter), use **proxy residencial ou 4G do Brasil** em `IG_PROXY`
  e mantenha sempre o mesmo proxy para a mesma conta.

## Privacidade
- `~/.ig_celular/config.env` contém a senha e `sessao-*.json` dá acesso à conta. Nunca faça commit
  desses arquivos nem os cole em chats. Se vazar: trocar a senha do Instagram (isso invalida a sessão).
