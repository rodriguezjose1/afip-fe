build
pyinstaller --onefile --add-data ".env_test;." main.py

test getcae
python main.py getcae 4 6 15

test verify
python main.py verify 4 6 6

test getcae exe
.\main.exe getcae 4 6 150

test verify exe
.\main.exe verify 4 6 6
