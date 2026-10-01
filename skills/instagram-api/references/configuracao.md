# Configurar a API oficial do Instagram (passo a passo para o usuário)

Leve o usuário por estes passos. Leva ~15 minutos e só precisa ser feito uma vez.

## A. Conta profissional
No app do Instagram: **Configurações → Tipo de conta e ferramentas → Mudar para conta profissional**
(Criador de conteúdo ou Empresa). Contas pessoais não funcionam na API.

## B. App na Meta
1. Acesse https://developers.facebook.com/apps → **Criar app**.
2. Caso de uso: **"Gerenciar mensagens e conteúdo no Instagram"** (Instagram API com login do Instagram).
3. No painel do app: **Instagram → Configuração da API com login do Instagram**.
4. Em **Funções do app → Funções**, adicione a conta do Instagram como **Testador do Instagram**,
   e no Instagram aceite o convite em *Configurações → Apps e sites → Convites de testador*
   (ou pelo site: instagram.com/accounts/manage_access).

## C. Gerar o token
1. Na seção "Gerar tokens de acesso", clique **Adicionar conta** e faça login com o Instagram.
2. Autorize as permissões:
   - `instagram_business_basic`
   - `instagram_business_content_publish` (publicar)
   - `instagram_business_manage_comments` (comentários)
   - `instagram_business_manage_messages` (DMs)
   - `instagram_business_manage_insights` (métricas)
3. Copie o token gerado (começa com `IG...`). Ele já é **de longa duração (60 dias)**.
4. Salve: `python3 scripts/ig_api.py config IG_ACCESS_TOKEN "IGAA..."`
5. Teste: `python3 scripts/ig_api.py diagnostico`

Enquanto o app está em "Desenvolvimento" ele funciona normalmente para as contas cadastradas como
testadoras — não é preciso passar pela Revisão do App para uso próprio.

## D. Repositório para hospedar mídia (GitHub)
1. Crie um repositório **público** vazio, ex.: `ig-midia` (com README para existir a branch `main`).
2. Crie um token em https://github.com/settings/personal-access-tokens → *Fine-grained* →
   acesso só a esse repositório → permissão **Contents: Read and write**.
3. Salve:
   ```bash
   python3 scripts/ig_api.py config GITHUB_TOKEN "github_pat_..."
   python3 scripts/ig_api.py config GITHUB_REPO "usuario/ig-midia"
   ```
4. Teste: `python3 scripts/ig_api.py hospedar alguma-foto.jpg` → deve devolver uma `url` que abre no navegador.

## Alternativa: Facebook Login (conta ligada a uma Página)
Se a pessoa já usa o Business Suite com Página do Facebook, dá para usar o token de Página
(não expira). Configure:
```bash
python3 scripts/ig_api.py config IG_GRAPH_HOST graph.facebook.com
python3 scripts/ig_api.py config IG_USER_ID <instagram_business_account id>
python3 scripts/ig_api.py config IG_ACCESS_TOKEN <token da página>
```
O id vem de `GET /<page-id>?fields=instagram_business_account` no Explorador da Graph API.
