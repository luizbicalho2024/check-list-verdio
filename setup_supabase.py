import requests
import json
import getpass

# Este script automatiza a criação de tabelas e buckets no Supabase.
# DEVE SER EXECUTADO LOCALMENTE, NUNCA NO SERVIDOR.

# --- FUNÇÕES AUXILIARES ---

def get_headers(access_token):
    """Cria os cabeçalhos de autorização para a API de Gerenciamento."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

def execute_sql(project_ref, access_token, sql_statement, table_name):
    """Executa uma declaração SQL no projeto Supabase."""
    url = f"https://api.supabase.com/v1/projects/{project_ref}/sql"
    headers = get_headers(access_token)
    data = {"sql": sql_statement}
    
    print(f"-> Criando tabela '{table_name}'...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Lança um erro para respostas 4xx/5xx
        print(f"   ✅ Tabela '{table_name}' criada com sucesso!")
        return True
    except requests.exceptions.HTTPError as err:
        print(f"   ❌ ERRO ao criar tabela '{table_name}': {err.response.status_code}")
        print(f"      Detalhe: {err.response.json().get('message', 'Sem detalhes')}")
        return False

def create_bucket(project_ref, access_token, bucket_name):
    """Cria um bucket de armazenamento no projeto Supabase."""
    url = f"https://api.supabase.com/v1/projects/{project_ref}/storage/buckets"
    headers = get_headers(access_token)
    data = {"name": bucket_name, "public": True}
    
    print(f"-> Criando bucket '{bucket_name}'...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 409: # 409 Conflict significa que já existe
             print(f"   🟡 Bucket '{bucket_name}' já existe. Pulando.")
             return True
        response.raise_for_status()
        print(f"   ✅ Bucket '{bucket_name}' criado com sucesso!")
        return True
    except requests.exceptions.HTTPError as err:
        print(f"   ❌ ERRO ao criar bucket '{bucket_name}': {err.response.status_code}")
        print(f"      Detalhe: {err.response.json().get('message', 'Sem detalhes')}")
        return False

# --- DEFINIÇÃO DAS TABELAS (SQL) ---

SQL_USUARIOS = """
CREATE TABLE public.usuarios (
    id uuid NOT NULL PRIMARY KEY,
    created_at timestamptz(6) NOT NULL DEFAULT now(),
    nome text NULL,
    email text NULL,
    nivel_acesso text NULL,
    CONSTRAINT usuarios_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE
);
ALTER TABLE public.usuarios ENABLE ROW LEVEL SECURITY;
"""

SQL_TEMPLATES_CHECKLIST = """
CREATE TABLE public.templates_checklist (
    id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz(6) NOT NULL DEFAULT now(),
    tipo_veiculo text NOT NULL UNIQUE,
    itens jsonb NULL
);
ALTER TABLE public.templates_checklist ENABLE ROW LEVEL SECURITY;
"""

SQL_ORDENS_DE_SERVICO = """
CREATE TABLE public.ordens_de_servico (
    id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at timestamptz(6) NOT NULL DEFAULT now(),
    cliente_nome text NULL,
    cliente_endereco text NULL,
    veiculo_modelo text NULL,
    veiculo_placa text NULL,
    veiculo_tipo text NULL,
    servico_tipo text NULL,
    rastreador_tipo text NULL,
    problema_reclamado text NULL,
    tecnico_atribuido_id uuid NULL,
    tecnico_nome text NULL,
    criado_por_suporte_id uuid NULL,
    status text NULL DEFAULT 'Pendente'::text,
    rastreador_id text NULL,
    checklist_respostas jsonb NULL,
    observacoes text NULL,
    bloqueio_instalado boolean NULL,
    fotos_urls jsonb NULL,
    assinaturas_urls jsonb NULL,
    data_finalizacao timestamptz(6) NULL,
    CONSTRAINT ordens_de_servico_tecnico_atribuido_id_fkey FOREIGN KEY (tecnico_atribuido_id) REFERENCES public.usuarios(id),
    CONSTRAINT ordens_de_servico_criado_por_suporte_id_fkey FOREIGN KEY (criado_por_suporte_id) REFERENCES public.usuarios(id)
);
ALTER TABLE public.ordens_de_servico ENABLE ROW LEVEL SECURITY;
"""

# --- SCRIPT PRINCIPAL ---

def main():
    print("=====================================================")
    print("  Script de Setup do Backend - Check-List Veicular  ")
    print("=====================================================")
    print("\nEste script irá configurar as tabelas e o armazenamento no seu projeto Supabase.")
    print("\nAVISO: Você precisará do seu 'Project Ref' e de um 'Access Token' pessoal.")
    print("Seu Access Token é SECRETO. Não o compartilhe e não o salve em arquivos de projeto.\n")

    # 1. Obter credenciais do usuário
    project_ref = input("1. Cole aqui o seu 'Project Ref' do Supabase: ")
    access_token = getpass.getpass("2. Cole aqui o seu 'Access Token' pessoal (ficará oculto): ")

    if not project_ref or not access_token:
        print("\n❌ 'Project Ref' e 'Access Token' são obrigatórios. Abortando.")
        return

    print("\nIniciando configuração...\n")

    # 2. Criar Tabelas
    execute_sql(project_ref, access_token, SQL_USUARIOS, "usuarios")
    execute_sql(project_ref, access_token, SQL_TEMPLATES_CHECKLIST, "templates_checklist")
    execute_sql(project_ref, access_token, SQL_ORDENS_DE_SERVICO, "ordens_de_servico")
    
    print("\n-----------------------------------------------------\n")

    # 3. Criar Buckets de Armazenamento
    create_bucket(project_ref, access_token, "fotos_os")
    create_bucket(project_ref, access_token, "assinaturas")

    print("\n=====================================================")
    print("🎉 Configuração do backend finalizada com sucesso! �")
    print("=====================================================")
    print("\nAgora, siga o guia para criar seu primeiro usuário administrador.")

if __name__ == "__main__":
    main()
�
