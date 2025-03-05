# Node-Red and rabbitmq  and NoSQL couchdb

In this repo developend some simple examples how to integrate Node-Red,  RabbitMQ,  NoSQL CouchDB.
The main focus aimed to learning integration Node-Red with RabbitMQ. CouchDB is used as file storage with extended functionality.

## Used tools
- [Docker RabbitMQ](https://hub.docker.com/_/rabbitmq/)
- [Docker CouchDB](https://hub.docker.com/_/couchdb)
- [odered/node-red Docker image](https://hub.docker.com/r/nodered/node-red)
- [Docker Compose](https://docs.docker.com/compose/)


## Useful links

### Rabbit MQ

- [Rabbit tutorials](https://www.rabbitmq.com/tutorials)
- [habre](https://habr.com/ru/articles/434510/)
- [@mnn-o/node-red-rabbitmq 1.0.2](https://flows.nodered.org/node/@mnn-o/node-red-rabbitmq)
- [FlowFuse: Using AMQP with Node-RED](https://flowfuse.com/node-red/protocol/amqp/)

### CouchDB

- [node-red-contrib-cloudantplus 2.0.6](https://flows.nodered.org/node/node-red-contrib-cloudantplus)
- [Apache CouchDB® 3.4.2 Documentation](https://docs.couchdb.org/en/stable/)


## Flows Deccription
 
#
### upoader.json 
Developed a simple my example with direct axchange.
The idea is from one flow uploading some file  using http and publish file binary  in queue.
The flow-consumner read binary file  from queue and store it into CouchDB as attachment. 

- publisher
<kbd><img src="doc/pic-01.png" /></kbd>
<p style="text-align: center;"><a name="pic-01">pic-01</a></p>

- consumer

<kbd><img src="doc/pic-02.png" /></kbd>
<p style="text-align: center;"><a name="pic-02">pic-02</a></p>


## Run it in docker composer

Node Red is running in container. All containers are starting  using docker-compose. The  Node-Red image is running from custom image which is described in **nodered.dockerile**. 
All necessary containers and environment variables are gathered on docker-compose file **docker-compose-nr.yaml**.

1. Change environment variables according to your configurations
Put is this variables parameters of your repository which wiil be cloned during docker build phase. In the same time it allow you enter into container and push your changes back to github repository.  Then **GIT_PSW** argument means github token which is using for https connection to github.



```yaml
  red-sender:
    # 1===
    #image: nodered/node-red
    #container_name: redsender
    build:
      context: ./
      dockerfile: nodered.dockerfile 
      args:
        GIT_USER: github username
        GIT_PSW: github token
        GIT_BRANCH: brnach name
        GIT_REPO:  githyb url without "https://"
        GIT_EMAIL: "your email"  for git config global

```

You can explicitly set up flow file which your want to run  by set up the environment variable **FLOWS**

```yaml

    environment:
      RABBITMQ_USER: "guest"
      RABBITMQ_PASSWORD: "guest"
      RABBITMQ_HOST: "rabbitmq"
      RABBITMQ_PORT: "5672"      
      COUCHDB_AUTH_TYPE: "COUCHDB_SESSION"
      COUCHDB_URL: "http://couchdb:5984"
      COUCHDB_USERNAME: "devadm"
      COUCHDB_PASSWORD: "qq" 
      FLOWS: "uploader.json"    
```

2. Build and run compose


```bash
    docker-compose -f  docker-compose-nr.yaml up --remove-orphans  --force-recreate --build -d
```

3. Stop compose

```bash

    docker-compose -f  docker-compose-nr.yaml start
```

- view log particular service
```bash
docker compose -f  docker-compose-nr.yaml  logs -f doclin-web
```


4. Start has already builded co
```

3. Store your changes in github

- Enter into **red-sender** container

```bash
    docker exec -it <container id> bash

```

- Change directory

```bash
    cd /data

```

- enter your git commands

```bash

    git status
    git add <filenamr>
    git commit -m "message"
    git push

```

## Архітектура доадтку

### FileUploader

зробелно на Node-Red. Виконує завантаження файлу та його запис в  NoSql БД як вкладеня.
База даних: ufiles
Структра документу:
```json
{
  "_id": "82d89faf9b2fdc2565848dc0ab0016d7",
  "_rev": "2-5bf1ea61d11ea7bed18e08fc1595627d",
  "name": "RFC-7701.docx",
  "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "proc_status": "new",
  "_attachments": {
    "RFC-7701.docx": {
      "content_type": "application/octet-stream",
      "revpos": 1,
      "digest": "md5-XlytfheUlCR4MXIl/Bjgvg==",
      "length": 107589,
      "stub": true
    }
  }
}

```
Пісял збереження повідомлення в БД, в RabbitMQ відправляється повідомлення в чергу в форматі:

```json
{"document_id": "82d89faf9b2fdc2565848dc0ab001517", "document_rev":"1-4019f2a0ef12eb85de598336fdd70770"}

```
де 
- "document_id відповідає ключу _id з збереженого документу під час uploading з БД ufiles:
- "document_rev" відповідає ключу _rev з збереженого документу під час uploading з БД ufiles:

В подальшому, document_id буде викоистовуватися як corelation id  для посилання на документ джерело.

### Docling Transformer

Виконує трансформацію завантаженого документу з оригіноального формату в MarkDown.

Написано на python  з використанням бібліотеки [IBM docling](https://ds4sd.github.io/docling/). [docling встанлвдюється з pypi pip install docling](https://pypi.org/project/docling/) 

Є особливість: у мене не вистачає ресурсів на комп'ютері для конвертації. Тому потрібно прийняти  якісь кроки, для того, щоб файл конвертувався та зберігся в БД і все це надійно оброблялося. Нехватка ресурсів проявляється в тому що:
- процес docling може зірватися
- втрачаэться з'єднання з rabbitMQ.

При вичитування повідомлення з черши оборбник вичитує повідмлення, по отриманих ідентифікаторах вичитує сам бінарний образ файлу з бази даних та його метадані.
Запускає конертацію, та записує результат в свою юазу даних. Пілся цього, як дані успішно збережені - підтверджує, що повідомлення з чрги оброблено (повідмлення видаляється).
Якщо на цьому етапі пропало підключення до rabbitMQ  то  обробник автоматично рестартує, потім підключається до rabbitMQ і повторно отримує це ж повідомленя. Отримавши, переверіяє по  correlation_id  наявність вже трансфомованого документа - і просто його отримує і відпрвляє далі, без повторної конертації.


```json
  "_id": "60374f833747aedc3a681434a900d6a9",
  "_rev": "2-5835a244b4678419d9908ca2e597b165",
  "name": "RFC-7701.docx",
  "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "proc_status": "MarkDownCreated",
  "converter": {
    "mdname": "RFC-7701.md",
    "dbname": "dbmd"
  },
  "_attachments": {
    "RFC-7701.docx": {
      "content_type": "application/octet-stream",
      "revpos": 1,
      "digest": "md5-XlytfheUlCR4MXIl/Bjgvg==",
      "length": 107589,
      "stub": true
    }
  }
}
```