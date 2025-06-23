import sqlite3
import datetime

# Nome do arquivo do banco de dados
DB_NAME = 'farmtech_data.db'

def create_connection():
    """Cria uma conexão com o banco de dados SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        # print(f"Conexão com SQLite DB versão {sqlite3.sqlite_version} bem-sucedida.")
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
    return conn

def create_table(conn):
    """Cria a tabela de leituras_sensores se ela não existir."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leituras_sensores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                fosforo INTEGER,
                potassio INTEGER,
                ph_ldr_raw INTEGER,
                ph_estimado REAL,
                umidade REAL,
                estado_bomba INTEGER
            );
        """)
        conn.commit()
        # print("Tabela 'leituras_sensores' verificada/criada com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao criar tabela: {e}")

def insert_data(conn):
    """Insere dados na tabela leituras_sensores."""
    print("\n--- Inserir Novos Dados ---")
    print("Por favor, insira os dados da leitura do sensor.")
    print("Você pode copiar do Monitor Serial do Wokwi ou inserir manually.")

    try:
        # Coleta de dados do usuário
        # Tenta obter o timestamp atual como padrão, mas permite entrada manual
        default_timestamp = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
        timestamp_str = input(f"Timestamp (formato YYYY-MM-DD HH:MM:SS, padrão: {default_timestamp}): ")
        if not timestamp_str:
            timestamp_str = default_timestamp
        
        # Validação simples de formato (pode ser melhorada)
        try:
            datetime.datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
        except ValueError:
            print("Formato de timestamp inválido. Usando o timestamp atual.")
            timestamp_str = default_timestamp

        fosforo = int(input("Fósforo (0=Ausente, 1=Presente): "))
        potassio = int(input("Potássio (0=Ausente, 1=Presente): "))
        ph_ldr_raw = int(input("Valor bruto do LDR (pH): "))
        ph_estimado = float(input("Valor de pH Estimado: "))
        umidade = float(input("Umidade do Solo (%): "))
        estado_bomba = int(input("Estado da Bomba (0=Desligada, 1=Ligada): "))

        # Confirmação
        print("\nDados a serem inseridos:")
        print(f"  Timestamp: {timestamp_str}")
        print(f"  Fósforo: {fosforo}")
        print(f"  Potássio: {potassio}")
        print(f"  LDR Raw: {ph_ldr_raw}")
        print(f"  pH Estimado: {ph_estimado}")
        print(f"  Umidade: {umidade}%")
        print(f"  Estado Bomba: {'Ligada' if estado_bomba == 1 else 'Desligada'}")
        
        confirm = input("\nConfirmar inserção? (s/n): ").strip().lower()
        if confirm != 's':
            print("Inserção cancelada.")
            return

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leituras_sensores (timestamp, fosforo, potassio, ph_ldr_raw, ph_estimado, umidade, estado_bomba)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp_str, fosforo, potassio, ph_ldr_raw, ph_estimado, umidade, estado_bomba))
        conn.commit()
        print(f"Dados inseridos com sucesso! ID do registro: {cursor.lastrowid}")

    except ValueError:
        print("Erro: Entrada inválida. Certifique-se de que os números são inseridos corretamente.")
    except sqlite3.Error as e:
        print(f"Erro ao inserir dados: {e}")


def read_data(conn):
    """Lê e exibe todos os dados da tabela leituras_sensores."""
    print("\n--- Visualizar Dados Armazenados ---")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leituras_sensores ORDER BY timestamp DESC")
        rows = cursor.fetchall()

        if not rows:
            print("Nenhum dado encontrado no banco de dados.")
            return

        print("\nID | Timestamp           | P | K | LDR Raw | pH Est. | Umidade | Bomba")
        print("---|---------------------|---|---|---------|---------|---------|-------")
        for row in rows:
            # row: (id, timestamp, fosforo, potassio, ph_ldr_raw, ph_estimado, umidade, estado_bomba)
            bomba_status = "Ligada" if row[7] == 1 else "Desl."
            print(f"{row[0]:<2} | {row[1]:<19} | {row[2]:<1} | {row[3]:<1} | {row[4]:<7} | {row[5]:<7.2f} | {row[6]:<7.1f}% | {bomba_status:<6}")
    
    except sqlite3.Error as e:
        print(f"Erro ao ler dados: {e}")

def update_data(conn):
    """Atualiza um registro existente na tabela."""
    print("\n--- Atualizar Dados ---")
    read_data(conn) # Mostra os dados para o usuário escolher qual atualizar
    
    try:
        record_id = int(input("Digite o ID do registro que deseja atualizar: "))
        
        # Verificar se o registro existe
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leituras_sensores WHERE id = ?", (record_id,))
        record = cursor.fetchone()
        if not record:
            print(f"Registro com ID {record_id} não encontrado.")
            return

        print(f"\nAtualizando registro ID: {record_id}")
        print("Deixe o campo em branco para manter o valor atual.")

        # Coleta novos dados, mantendo os antigos se nada for digitado
        timestamp_str = input(f"Novo Timestamp (atual: {record[1]}): ") or record[1]
        fosforo_str = input(f"Novo Fósforo (0/1, atual: {record[2]}): ")
        fosforo = int(fosforo_str) if fosforo_str else record[2]
        
        potassio_str = input(f"Novo Potássio (0/1, atual: {record[3]}): ")
        potassio = int(potassio_str) if potassio_str else record[3]

        ph_ldr_raw_str = input(f"Novo LDR Raw (atual: {record[4]}): ")
        ph_ldr_raw = int(ph_ldr_raw_str) if ph_ldr_raw_str else record[4]

        ph_estimado_str = input(f"Novo pH Estimado (atual: {record[5]}): ")
        ph_estimado = float(ph_estimado_str) if ph_estimado_str else record[5]

        umidade_str = input(f"Nova Umidade (atual: {record[6]}): ")
        umidade = float(umidade_str) if umidade_str else record[6]

        estado_bomba_str = input(f"Novo Estado da Bomba (0/1, atual: {record[7]}): ")
        estado_bomba = int(estado_bomba_str) if estado_bomba_str else record[7]

        cursor.execute("""
            UPDATE leituras_sensores
            SET timestamp = ?, fosforo = ?, potassio = ?, ph_ldr_raw = ?, ph_estimado = ?, umidade = ?, estado_bomba = ?
            WHERE id = ?
        """, (timestamp_str, fosforo, potassio, ph_ldr_raw, ph_estimado, umidade, estado_bomba, record_id))
        conn.commit()
        print(f"Registro ID {record_id} atualizado com sucesso.")

    except ValueError:
        print("Erro: Entrada inválida. Certifique-se de que os números são inseridos corretamente.")
    except sqlite3.Error as e:
        print(f"Erro ao atualizar dados: {e}")

def delete_data(conn):
    """Deleta um registro da tabela."""
    print("\n--- Deletar Dados ---")
    read_data(conn) # Mostra os dados para o usuário escolher qual deletar

    try:
        record_id = int(input("Digite o ID do registro que deseja deletar: "))

        # Verificar se o registro existe
        cursor_check = conn.cursor()
        cursor_check.execute("SELECT 1 FROM leituras_sensores WHERE id = ?", (record_id,))
        if not cursor_check.fetchone():
            print(f"Registro com ID {record_id} não encontrado.")
            return

        confirm = input(f"Tem certeza que deseja deletar o registro ID {record_id}? (s/n): ").strip().lower()
        if confirm == 's':
            cursor = conn.cursor()
            cursor.execute("DELETE FROM leituras_sensores WHERE id = ?", (record_id,))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"Registro ID {record_id} deletado com sucesso.")
            else:
                print(f"Nenhum registro encontrado com ID {record_id} para deletar (talvez já tenha sido removido).")
        else:
            print("Deleção cancelada.")

    except ValueError:
        print("Erro: ID inválido. Deve ser um número.")
    except sqlite3.Error as e:
        print(f"Erro ao deletar dados: {e}")

def main_menu(conn):
    """Exibe o menu principal e gerencia a interação do usuário."""
    while True:
        print("\n--- FarmTech Solutions - Gerenciador de Dados de Sensores (Simulado) ---")
        print("1. Inserir dados da leitura do sensor")
        print("2. Visualizar todos os dados")
        print("3. Atualizar dados de uma leitura")
        print("4. Deletar dados de uma leitura")
        print("5. Sair")

        choice = input("Escolha uma opção (1-5): ")

        if choice == '1':
            insert_data(conn)
        elif choice == '2':
            read_data(conn)
        elif choice == '3':
            update_data(conn)
        elif choice == '4':
            delete_data(conn)
        elif choice == '5':
            print("Saindo do programa.")
            break
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == '__main__':
    conn = create_connection()
    if conn:
        create_table(conn) # Garante que a tabela exista
        main_menu(conn)
        conn.close()
        # print("Conexão com o banco de dados fechada.")