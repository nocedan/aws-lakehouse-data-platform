# Arquitetura VPC — Data Lake Pipeline

## Visão Geral

Pipeline de dados composto por RDS Postgres (fonte), Glue ETL (processamento), S3 (Data Lake em formato Iceberg), e Redshift Serverless (Analytics/BI), todos dentro de uma VPC na região `us-east-2`.

---

## Estrutura da VPC

| Atributo | Valor |
|---|---|
| VPC ID | `vpc-061faf1ae5ffd07b3` |
| CIDR | `172.31.0.0/16` |
| Região | `us-east-2` |

### Subnets

| AZ | Subnet ID | Tipo |
|---|---|---|
| us-east-2a | `subnet-0542dc5c734d3e97f` | Privada |
| us-east-2a | `subnet-07a282d1f8cbfd440` | Pública |
| us-east-2b | `subnet-03f92c672f0727bea` | Pública |
| us-east-2b | `subnet-0fbc9b3a2be8e48ff` | Privada |
| us-east-2c | `subnet-052a6c82291ba9566` | Pública |
| us-east-2c | `subnet-085468e52285240bb` | Privada |

---

## Componentes de Rede

### Route Tables

**Tabela Pública**
- Subnets: `subnet-07a...`, `subnet-03f9...`, `subnet-52a...`
- Rotas: `0.0.0.0/0 → igw-0bcb787c55450d784`

**Tabela Privada**
- Subnets: `subnet-0542...`, `subnet-0fbc...`, `subnet-0854...`
- Rotas:
  - `0.0.0.0/0 → NAT Gateway`
  - `pl-XXXXXXXX (S3) → S3 Gateway Endpoint` *(gratuito, evita custo de transferência pelo NAT)*

### Gateways

| Recurso | Função |
|---|---|
| Internet Gateway `igw-0bcb787c55450d784` | Saída para internet nas subnets públicas |
| NAT Gateway (na subnet pública) | Saída para internet das subnets privadas |
| S3 Gateway Endpoint | Acesso direto ao S3 sem custo de transferência via NAT |

> **Por que manter o S3 Gateway Endpoint?** Ele é gratuito e impede que o tráfego de dados do Data Lake (potencialmente alto volume) passe pelo NAT Gateway, evitando custo de transferência.

---

## Serviços e Posicionamento

### RDS Postgres
- **Subnets:** Privadas
- **Motivo:** Sem exposição pública; acessado apenas pelo Glue via Security Group

### AWS Glue ETL
- **Subnets:** Privadas
- **Motivo:** O Glue exige subnet com rota para NAT Gateway ou S3 Endpoint — subnets públicas com IGW não são aceitas pelo validador do Glue
- **Acesso ao S3:** Via S3 Gateway Endpoint (rota na tabela privada)
- **Demais serviços AWS** (STS, Secrets Manager, CloudWatch): Via NAT Gateway

### S3 — Data Lake (Iceberg)
- Serviço gerenciado, fora da VPC
- Acessado pelo Glue via S3 Gateway Endpoint

### Redshift Serverless
- **Subnets:** Públicas
- **Acesso externo:** Via IAM Authentication a partir de PCs locais
- **Segurança:** Security Group restrito ao IP ou faixa de IPs corporativos autorizados

---

## Diagrama

```
Internet / PC Local
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  VPC 172.31.0.0/16                                        │
│                                                           │
│  ┌─────────────── Subnets Públicas ───────────────────┐  │
│  │                                                     │  │
│  │   NAT Gateway ◄──── (saída das subnets privadas)   │  │
│  │                                                     │  │
│  │   Redshift Serverless (acesso IAM externo)          │  │
│  │                                                     │  │
│  └──────────────────────┬──────────────────────────────┘  │
│                         │ IGW                             │
│  ┌─────────────── Subnets Privadas ───────────────────┐  │
│  │                                                     │  │
│  │   AWS Glue ETL Jobs ──────────────────────────┐    │  │
│  │                                               │    │  │
│  │   RDS Postgres (fonte)                        │    │  │
│  │                                               ▼    │  │
│  └───────────────────────────────────────────────┼────┘  │
│                                                   │       │
│                              S3 Gateway Endpoint  │       │
└───────────────────────────────────────────────────┼───────┘
                                                    │
                                                    ▼
                                              S3 — Data Lake
                                              (Iceberg Tables)
```

---

## Segurança — Security Groups

| Serviço | Regra de entrada |
|---|---|
| RDS Postgres | Porta 5432 — apenas do SG do Glue |
| Glue | Sem entrada; saída irrestrita |
| Redshift Serverless | Porta 5439 — apenas dos IPs autorizados |