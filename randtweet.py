from TwitterAPI import TwitterAPI
import json
def make_request():
    CONSUMERKEY="your consumer_key"
    CONSUMERSECRET="your consumer_secret"
    ACCESSTOKENKEY="your access_token_key"
    ACCESSTOKENSECRET="your access_token_secret"
    api =  TwitterAPI(CONSUMERKEY,CONSUMERSECRET,ACCESSTOKENKEY,ACCESSTOKENSECRET)
    r = api.request('statuses/filter', {'locations':'-87.9,41.6,-87.5,42.0'})
    return r 
#decoded = r.encode('utf-8')
#print r
#print r.json()
##for key in r.keys():
##    print key
##for item in r:
##    print(item.keys)
##    if i>1:
##        break
##    print item
##    i = i+1
##    
def randtweet():
    r = make_request()
    for item in r:
        rand_tweet =item['text']
        break
    #print rand_tweet
    return rand_tweet
if __name__ == '__main__':
    print(randtweet())
