# Date: 20250612
docker build -t db-app:test . 
docker run -it -p 8501:8501 -v ${PWD}/app:/app --name db-app-01 db-app:test bash