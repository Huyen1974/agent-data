# Sử dụng image python chính thức
FROM python:3.9

# Thiết lập thư mục làm việc
WORKDIR /app

# Sao chép file yêu cầu vào container và cài đặt thư viện
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Thiết lập cổng
EXPOSE 8080

# Chạy ứng dụng Flask
CMD ["python", "backend.py"]

