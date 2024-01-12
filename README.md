# consulta_efornecedores

Este é um projeto RPA que automatiza a verificação do valor do frete emitido.
O RPA roda a cada hora consultando a base de dados interna (Tabela: tg99all) e consulta os n° conhecimento retornados no site efornecedores, para a usina Usiminas.
Caso encontre diferença entre o valor liberado pela usina e o valor emitido no CTE, é enviado uma notificação por e-mail.


### 📋 Pré-requisitos

* Python 3.11
* Docker e docker-compose
* Selenium Hub
* Botcity

### 🔧 Instalação

```
git clone https://github.com/expfig/consulta_efornecedores.git
```
```
poetry install 
```
```
poetry run python bot.py
```


## 🛠️ Construído com

* [Docker](https://docs.docker.com/) - Gerenciador de Containers
* [Selenium](https://github.com/SeleniumHQ/docker-selenium) - O framework web usado
* [Poetry](https://python-poetry.org/docs/) - Gerenciador de Dependência
* [Python 3.11](https://docs.python.org/3.11/) - Linguagem usada

 

## ✒️ Autores

* *Desenvolvedor principal* - [JoaoAnacleto](https://github.com/JoaoAnacletoFIG)
