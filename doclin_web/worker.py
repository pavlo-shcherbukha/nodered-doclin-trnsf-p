import os
import time
import json
import sys
import logging
import pika
import io
import docling

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem

from ibmcloudant.cloudant_v1 import CloudantV1
from ibmcloudant import CouchDbSessionAuthenticator
from doclin_web.couchdb import CouchDB
import doclin_web.shjsonformatter

logger = logging.getLogger(__name__)
img_gray = None
img_prop = None

apploglevel = os.environ.get("LOGLEVEL")
if apploglevel is None:
    logger.setLevel(logging.DEBUG)
elif apploglevel == 'DEBUG':
    logger.setLevel(logging.DEBUG)
elif apploglevel == 'INFO':
    logger.setLevel(logging.INFO)
elif apploglevel == 'WARNING':
    logger.setLevel(logging.WARNING)
elif apploglevel == 'ERROR':
    logger.setLevel(logging.ERROR)
elif apploglevel == 'CRITICAL':
    logger.setLevel(logging.CRITICAL)
else:
    logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(doclin_web.shjsonformatter.JSONFormatter())
logger.addHandler(handler)

logger.debug("debug message")

def read_image(file_path):
    with open(file_path, "rb") as file:
        image_bytes = file.read()
    return image_bytes

def save_modified_image(file_path, modified_bytes):
    with open(file_path, "wb") as file:
        file.write(modified_bytes)

def db_read_image(db, docref):
    """
        виконую обробку вкладення через doclin
    """
    presult = {"ok": False, "msg": ""}
    dbdoc = db.readDocument(docref.get("document_id"))
    logger.debug("DB documnet" + json.dumps(dbdoc))
    if dbdoc["proc_status"] != "new":
        presult["ok"] = False
        presult["msg"] = "Document already processed!"
        return presult

    logger.debug("читаю вклаження")
    binimg = db.readAttachment(docref.get("document_id"), dbdoc["name"])
    logger.debug("db attachment  прочитано" + dbdoc["name"])
    presult["ok"] = True
    presult["msg"] = ""
    presult["blob"] = binimg
    presult["name"] = dbdoc["name"]
    presult["mime_type"] = dbdoc["name"]
    presult["metadata"] = dbdoc
    return presult

def converting(filedata):
    """
        doclin transformation
    """
    logger.debug("getting buffer")
    buff = io.BytesIO(filedata["blob"])
    logger.debug("making source")
    source = DocumentStream(name=filedata["name"], stream=buff)
    logger.debug("Create Converter")
    converter = DocumentConverter()
    try:
        logger.debug("converting")
        result = converter.convert(source)
        logger.debug("Converted !!!!!")
        logger.debug("DONE!!!")
        return result.document
    except Exception as e:
        logger.error("error converting!!!" + str(e))


def mdfilename(fname):
    dotpos=fname.rfind(".")
    fnamemd=fname + ".md"
    if dotpos>0:
        ext=fname[dotpos:]
        fnamemd=fname.replace(ext, ".md")
    return fnamemd

def pil_image_to_byte_array(image):
  imgByteArr = io.BytesIO()
  image.save(imgByteArr, format=image.format)
  imgByteArr = imgByteArr.getvalue()
  return imgByteArr  



def connect_to_rabbitmq():
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", 5672))
    logger.debug("Підключаюся до Rabbit MQ")

    credentials = pika.PlainCredentials(username=user, password=password)
    parameters = pika.ConnectionParameters(host=host, port=port, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    return connection

def main():
    while True:
        try:
            connection = connect_to_rabbitmq()
            channel = connection.channel()

            logger.debug("Налаштовую черги")
            q_name_in = "test_queue"
            q_name_out = "test_dbwrt"
            logger.debug("Налаштовую канал для читання повідомтлень")
            channel.queue_declare(queue=q_name_in, durable=True)

            logger.debug("Налаштовую канал для публікації повідомтлень")
            channel.queue_declare(queue=q_name_out, durable=True)

            logger.debug("Підключаю базу даних")
            couchd = CouchDB(__name__)
            dblist = couchd.checkDataBases()
            logger.debug(f"Database lists: {dblist}")

            logger.debug("Connection to RabbitMQ established successfully.")
            def callback(ch, method, properties, body):
                """
                    Обробка отриманого повідомлення
                """
                logger.debug(f"Received message: ====================================================================================")
                logger.debug(f"Received message: {properties}")
                logger.debug(f" app-id {properties.app_id}")
                logger.debug(f" custom headers: {properties.headers}")
                logger.debug(f"Received message: ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                
                logger.debug(f"Recieved body.....::::: {body}") 
                msgo = json.loads(body)
                logger.debug("Перевіряю наявність документа в БД dbmd")
                isdocument=couchd.isMarkDownExists(msgo.get("document_id"))
                if isdocument["ok"]:
                    logger.debug(f"Документ {msgo.get('document_id')} вже оброблений")
                    logger.debug("Установка delivery_tag)")    
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    ch.basic_publish(   exchange='doclin_repl', 
                                        routing_key='converter', 
                                        body=json.dumps({"document_id": msgo.get('document_id'),"dbname": "dbmd", "mdname": mdname, "status": "MarkDownCreated"}), 
                                        properties=pika.BasicProperties(
                                            content_encoding="utf-8",
                                            content_type="application/json",
                                            headers={"document_id": msgo.get('document_id'), "dbname": "dbmd"},
                                            delivery_mode=2,
                                            correlation_id=msgo.get('document_id'),
                                            app_id= "docling_weber")
                    )                    
                    logger.debug(f"====Повідомлення обрелене успішно! docid={ msgo.get('document_id') }====")                    
                else:
                    logger.debug(f"Документ {msgo.get('document_id')} не оброблений")    
                    logger.debug("Читаю запис з БД")
                    filedata = db_read_image(couchd, msgo)
                    mdname = mdfilename(filedata["name"])
                    doclingdoc=converting(filedata)
                    logger.debug("Writing to markdown")
                    mdstrings = doclingdoc.export_to_markdown()
                    logger.debug("Writing to markdown - OK")
            
                    #mdstrings="# TEST STRING \n NEW STRING \n"
                    logger.debug("Storing markdoun to DB")
                    mddoc=couchd.addMarkDownDocumet( msgo.get('document_id'), mdname)
                    addr = couchd.addMarkDownAttachment(mddoc.get("id"), mdname, mdstrings)
                    logger.debug("Writed to DB: " + json.dumps(addr))
                    logger.debug("Processing document images and tables")
                    table_counter = 0
                    picture_counter = 0
                    for element, _level in doclingdoc.iterate_items():
                        if isinstance(element, TableItem):
                            table_counter += 1
                        if isinstance(element, PictureItem):
                            picture_counter += 1
                            element_image_filename = mdname + f"-picture-{picture_counter}.png"
                            logger.debug("Processing image", element_image_filename)
                            pilimage = element.get_image(doclingdoc)
                            b=pil_image_to_byte_array(pilimage)
                            imagemeta={"filename": element_image_filename, "filedsc": "Picture", "correlation_id":  msgo.get('document_id'), "contenttype": "iamge/png"}
                            logger.debug(f"save image to db: {element_image_filename}")
                            imgdoc=couchd.saveImage( b, imagemeta)
                            logger.debug(f"save image to db - result: {json.dumps(imgdoc)}")

                    logger.debug("Processing document images and tables-OK")
                    logger.debug("Установка delivery_tag)")    
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                   

                    ch.basic_publish(   exchange='doclin_repl', 
                                        routing_key='converter', 
                                        body=json.dumps({"document_id": msgo.get('document_id'),"dbname": "dbmd", "mdname": mdname, "status": "MarkDownCreated"}), 
                                        properties=pika.BasicProperties(
                                            content_encoding="utf-8",
                                            content_type="application/json",
                                            headers={"document_id": msgo.get('document_id'), "dbname": "dbmd"},
                                            delivery_mode=2,
                                            correlation_id=msgo.get('document_id'),
                                            app_id= "docling_weber")
                    )








                    logger.debug(f"====Повідомлення обрелене успішно! docid={addr['id']}====")

            # Declare the exchange
            logger.debug(f"Declare the exchange")
            exchange_name = 'doclin_trnsf'
            channel.exchange_declare(exchange=exchange_name, exchange_type='direct', durable=True)

            # Declare the queue
            logger.debug(f"Declare the queue")
            queue_name = 'uploader'
            channel.queue_declare(queue=queue_name, durable=True)

            logger.debug(f"Bind the queue to the exchange")
            routing_key = 'uploader'
            channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)

            logger.debug(f"Setting up message consumption from queue")
            channel.basic_consume(queue=queue_name, on_message_callback=callback)

            logger.debug(f"======Очікю повідомлення з черги=====")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.debug(f"Failed to establish connection to RabbitMQ: {e}")
            time.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.debug(f"An error occurred: {e}")
            sys.exit(1)

