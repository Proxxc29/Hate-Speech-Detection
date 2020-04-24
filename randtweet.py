from TwitterAPI import TwitterAPI
import json
def make_request():
    CONSUMERKEY="LRf0EXpyBaLkCFR9hkWImgooK"
    CONSUMERSECRET="Vesl8u1BkGLI2hWHATqFEdl6zyjmIMgElTYnH7n7NlBa2XcIg4"
    ACCESSTOKENKEY="1114550173495988224-HDXJ7gnqo91awp3gjaHYwwuZOINucP"
    ACCESSTOKENSECRET="vfLitGPn7VX3ZLcAf7uhGucGzjPSsEekxcAt8F9MvfmZN"
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
