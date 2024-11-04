import psycopg2
from psycopg2 import sql

# Kết nối đến cơ sở dữ liệu PostgreSQL
def connect_to_postgresql():
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="Webhub_SecurePass_2024!",
            host="127.0.0.1",
            port="5432",
            database="postgres"
        )
        return connection
    except Exception as error:
        print("Lỗi khi kết nối đến PostgreSQL:", error)
        return None

# Hàm cập nhật thông tin
def update_data():
    connection = connect_to_postgresql()
    if connection is None:
        return
    
    try:
        cursor = connection.cursor()
        query = sql.SQL("UPDATE service_account_info SET created_at = NOW() WHERE id = %s")
        cursor.execute(query, (1,))  # Thay đổi giá trị ID tuỳ theo yêu cầu
        
        connection.commit()
        print("Cập nhật dữ liệu thành công!")
    
    except Exception as error:
        print("Lỗi khi cập nhật dữ liệu:", error)
    
    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    update_data()

