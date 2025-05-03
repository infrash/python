genexecutable:
	cp main.py infrash
	sed  -i '1i #!/usr/bin/python\n' infrash

install: genexecutable
	sudo cp infrash /usr/bin/
	sudo chmod +x /usr/bin/infrash
	rm infrash