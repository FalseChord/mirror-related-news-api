import os
from google.cloud import pubsub_v1
import json
import ConfigParser
import time
import datetime
# for pubsub mode
from ExtractTFIDF import *
from GetFeatureVectors import *
from BuildIndexTreeV2 import *
from FeedToRedisV2 import * 
import logging

logging.basicConfig(filename='pubsub.log',level=logging.DEBUG)

def ProcessStreamingData():
    ExtractTFIDF(mode='pubsub')
    fv,id_list = GetFeatureVectors(mode="pubsub")
    BuildIndexTree(fv,id_list,mode="pubsub")
    FeedToRedis(mode="pubsub")
    print("DONE!")

def GenerateStreamingJson(stream_jsons,dest_dir="streaming-data/"):
    time_stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = "streaming-"+time_stamp                  
    f = open(dest_dir+output_filename,'w')
    output_dict = dict()
    output_dict['_items']=stream_jsons

    print("total:"+str(len(stream_jsons)))
    output_json = json.dumps(output_dict)
    f.write(output_json)
    print("output file:"+dest_dir+output_filename)
    f.close()

def GetPubSubStreaming(dest_dir="streaming-data/"):
    print("[START] Getting Pubsub Streaming...")
    # read the config for redis connection
    config = ConfigParser.ConfigParser()
    config.read('related-news-engine.conf')
    credential = config.get('PUBSUB','GOOGLE_APPLICATION_CREDENTIALS')
    project_id = config.get('PUBSUB','PROJECT_ID')
    topic_id = config.get('PUBSUB','TOPIC_ID')
    sub_id = config.get('PUBSUB','SUB_ID')

    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential

    project_path = 'projects/'+project_id
    topic_path = project_path+'/topics/'+topic_id
    subscription_path = project_path+'/subscriptions/'+sub_id
    full_subscription_path = topic_path+'/subscriptions/'+sub_id
   

    print('subscription_path:'+subscription_path)
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()    
    
    existing_subscriber=False
    for subinfo in subscriber.list_subscriptions(project_path):
        if subscription_path==subinfo.name:
            existing_subscriber=True
            break

    if existing_subscriber==False:
        subscriber.create_subscription(subscription_path,topic_path)
   
    slice_stream_jsons=[]

    # define the callback function
    def callback(message):
        json_dict = json.loads(message.data)
        if '_id' in json_dict:
            #print(json_dict['_id']) 
            # this is for defug, will remove later"
            import datetime
            logging.info("pubsub,"+str(datetime.now())+","+str(json_dict['_id']))
            ########################################
            slice_stream_jsons.append(json_dict)
        message.ack()
    # subscriber
    subscriber.subscribe(subscription_path,callback)

    # what will we do when describing

    while True:
        time.sleep(10)
        if slice_stream_jsons!=[]:
            ### for debug
            import datetime
            for x in slice_stream_jsons:
                logging.info("while,"+str(datetime.now())+","+str(x['_id']))

            ###############
            print("Ready to output:"+str(len(slice_stream_jsons)))
            GenerateStreamingJson(slice_stream_jsons,dest_dir)
            ProcessStreamingData()
            slice_stream_jsons=[]
            print("Clean the queue!")
        print("I'm sleep!")

if __name__=="__main__":
    GetPubSubStreaming()
