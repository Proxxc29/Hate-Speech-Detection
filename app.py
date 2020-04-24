from flask import Flask,render_template,request,g
import warnings
warnings.filterwarnings("ignore")
import pickle
import numpy as np
import pandas as pd
from sklearn.externals import joblib
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.feature_selection import SelectFromModel
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.stem.porter import *
import string
import re
import classifier
import randtweet as rt
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as VS
from textstat.textstat import *

stopwords=stopwords = nltk.corpus.stopwords.words("english")

other_exclusions = ["#ff", "ff", "rt"]
stopwords.extend(other_exclusions)

sentiment_analyzer = VS()

stemmer = PorterStemmer()
def preprocess(text_string):
    """
    Accepts a text string and replaces:
    1) urls with URLHERE
    2) lots of whitespace with one instance
    3) mentions with MENTIONHERE

    This allows us to get standardized counts of urls and mentions
    Without caring about specific people mentioned
    """
    space_pattern = '\s+'
    giant_url_regex = ('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
        '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    mention_regex = '@[\w\-]+'
    parsed_text = re.sub(space_pattern,' ', str(text_string))
    parsed_text = re.sub(giant_url_regex, 'URLHERE', parsed_text)
    parsed_text = re.sub(mention_regex, 'MENTIONHERE', parsed_text)
    #parsed_text = parsed_text.code("utf-8", errors='ignore')
    return parsed_text

def tokenize(tweet):
    """Removes punctuation & excess whitespace, sets to lowercase,
    and stems tweets. Returns a list of stemmed tokens."""
    tweet = " ".join(re.split("[^a-zA-Z]*", tweet.lower())).strip()
    #tokens = re.split("[^a-zA-Z]*", tweet.lower())
    tokens = [stemmer.stem(t) for t in tweet.split()]
    return tokens

def basic_tokenize(tweet):
    """Same as tokenize but without the stemming"""
    tweet = " ".join(re.split("[^a-zA-Z.,!?]*", tweet.lower())).strip()
    #print tweet
    return tweet

def get_pos_tags(tweets):
    """Takes a list of strings (tweets) and
    returns a list of strings of (POS tags).
    """
    tweet_tags = []
    #for t in tweets:
    tokens = basic_tokenize(preprocess(tweets))
    tags = nltk.pos_tag(tokens)
    tag_list = [x[1] for x in tags]
    #for i in range(0, len(tokens)):
    tag_str = " ".join(tag_list)
    tweet_tags.append(tag_str)
    return tweet_tags

def count_twitter_objs(text_string):
    """
    Accepts a text string and replaces:
    1) urls with URLHERE
    2) lots of whitespace with one instance
    3) mentions with MENTIONHERE
    4) hashtags with HASHTAGHERE

    This allows us to get standardized counts of urls and mentions
    Without caring about specific people mentioned.

    Returns counts of urls, mentions, and hashtags.
    """
    space_pattern = '\s+'
    giant_url_regex = ('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
        '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    mention_regex = '@[\w\-]+'
    hashtag_regex = '#[\w\-]+'
    parsed_text = re.sub(space_pattern, ' ', text_string)
    parsed_text = re.sub(giant_url_regex, 'URLHERE', parsed_text)
    parsed_text = re.sub(mention_regex, 'MENTIONHERE', parsed_text)
    parsed_text = re.sub(hashtag_regex, 'HASHTAGHERE', parsed_text)
    return(parsed_text.count('URLHERE'),parsed_text.count('MENTIONHERE'),parsed_text.count('HASHTAGHERE'))

def other_features_(tweet):
    """This function takes a string and returns a list of features.
    These include Sentiment scores, Text and Readability scores,
    as well as Twitter specific features.

    This is modified to only include those features in the final
    model."""

    sentiment = sentiment_analyzer.polarity_scores(tweet)

    words = preprocess(tweet) #Get text only

    syllables = textstat.syllable_count(words) #count syllables in words
    num_chars = sum(len(w) for w in words) #num chars in words
    num_chars_total = len(tweet)
    num_terms = len(tweet.split())
    num_words = len(words.split())
    avg_syl = round(float((syllables+0.001))/float(num_words+0.001),4)
    num_unique_terms = len(set(words.split()))

    ###Modified FK grade, where avg words per sentence is just num words/1
    FKRA = round(float(0.39 * float(num_words)/1.0) + float(11.8 * avg_syl) - 15.59,1)
    ##Modified FRE score, where sentence fixed to 1
    FRE = round(206.835 - 1.015*(float(num_words)/1.0) - (84.6*float(avg_syl)),2)

    twitter_objs = count_twitter_objs(tweet) #Count #, @, and http://
    features = [FKRA, FRE, syllables, num_chars, num_chars_total, num_terms, num_words,
                num_unique_terms, sentiment['compound'],
                twitter_objs[2], twitter_objs[1],]
    #features = pandas.DataFrame(features)
    return features

def get_oth_features(tweets):
    """Takes a list of tweets, generates features for
    each tweet, and returns a numpy array of tweet x features"""
    feats=[]
    for t in tweets:
        feats.append(other_features_(t))
    return np.array(feats)


def transform_inputs(tweets, tf_vectorizer, idf_vector, pos_vectorizer):
    """
    This function takes a list of tweets, along with used to
    transform the tweets into the format accepted by the model.

    Each tweet is decomposed into
    (a) An array of TF-IDF scores for a set of n-grams in the tweet.
    (b) An array of POS tag sequences in the tweet.
    (c) An array of features including sentiment, vocab, and readability.

    Returns a pandas dataframe where each row is the set of features
    for a tweet. The features are a subset selected using a Logistic
    Regression with L1-regularization on the training data.

    """
    tf_array = tf_vectorizer.fit_transform(tweets).toarray()
    tfidf_array = tf_array*idf_vector
    print ("Built TF-IDF array")
    #print tweets
    pos_tags = get_pos_tags(tweets)
    #print get_pos_tags(tweets)
    pos_array = pos_vectorizer.fit_transform(pos_tags).toarray()
    print ("Built POS array")
    #print pos_vectorizer.fit_transform(pos_tags).toarray()
    oth_array = get_oth_features(tweets)
    print ("Built other feature array")
    #print get_oth_features(tweets)
    M = np.concatenate([tfidf_array, pos_array, oth_array],axis=1)
    return pd.DataFrame(M)

def predictions(X, model):
    """
    This function calls the predict function on
    the trained model to generated a predicted y
    value for each observation.
    """
    y_preds = model.predict(X)
    return y_preds

def class_to_name(class_label):
    """
    This function can be used to map a numeric
    feature name to a particular class.
    """
    if class_label == 0:
        return "Hate speech"
    elif class_label == 1:
        return "Offensive language"
    elif class_label == 2:
        return "Neither"
    else:
        return "No label"

def get_tweets_predictions(tweets, perform_prints=True):
    fixed_tweets = []
    #for i, t_orig in enumerate(tweets):
    s = tweets
    try:
        s = s.encode("latin1")
    except:
        try:
            s = s.encode("utf-8")
        except:
            pass
    if type(s) != unicode:
        fixed_tweets.append(unicode(s, errors="ignore"))
    else:
        fixed_tweets.append(s)
    #print fixed_tweets
    print tweets
    #assert len(tweets) == len(fixed_tweets), "shouldn't remove any tweets"
    tweets = fixed_tweets
    print (len(tweets), " tweets to classify")

    print ("Loading trained classifier... ")
    model = joblib.load('final_model.pkl')

    print ("Loading other information...")
    tf_vectorizer = joblib.load('final_tfidf.pkl')
    idf_vector = joblib.load('final_idf.pkl')
    pos_vectorizer = joblib.load('final_pos.pkl')
    #Load ngram dict
    #Load pos dictionary
    #Load function to transform data

    print ("Transforming inputs...")
    X = transform_inputs(tweets, tf_vectorizer, idf_vector, pos_vectorizer)

    print ("Running classification model...")
    predicted_class = predictions(X, model)

    return predicted_class	

app=Flask(__name__)

@app.route('/')
def index():
	return render_template('demoForm.html')


@app.route('/', methods=['POST','GET'])
def getValue():
        stopwords=stopwords = nltk.corpus.stopwords.words("english")

        other_exclusions = ["#ff", "ff", "rt"]
        stopwords.extend(other_exclusions)

        sentiment_analyzer = VS()

        stemmer = PorterStemmer()
        def preprocess(text_string):
            """
            Accepts a text string and replaces:
            1) urls with URLHERE
            2) lots of whitespace with one instance
            3) mentions with MENTIONHERE

            This allows us to get standardized counts of urls and mentions
            Without caring about specific people mentioned
            """
            space_pattern = '\s+'
            giant_url_regex = ('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
                '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            mention_regex = '@[\w\-]+'
            parsed_text = re.sub(space_pattern,' ', str(text_string))
            parsed_text = re.sub(giant_url_regex, 'URLHERE', parsed_text)
            parsed_text = re.sub(mention_regex, 'MENTIONHERE', parsed_text)
            #parsed_text = parsed_text.code("utf-8", errors='ignore')
            return parsed_text

        def tokenize(tweet):
            """Removes punctuation & excess whitespace, sets to lowercase,
            and stems tweets. Returns a list of stemmed tokens."""
            tweet = " ".join(re.split("[^a-zA-Z]*", tweet.lower())).strip()
            #tokens = re.split("[^a-zA-Z]*", tweet.lower())
            tokens = [stemmer.stem(t) for t in tweet.split()]
            return tokens

        def basic_tokenize(tweet):
            """Same as tokenize but without the stemming"""
            tweet = " ".join(re.split("[^a-zA-Z.,!?]*", tweet.lower())).strip()
            #print tweet
            return tweet

        def get_pos_tags(tweets):
            """Takes a list of strings (tweets) and
            returns a list of strings of (POS tags).
            """
            tweet_tags = []
            #for t in tweets:
            tokens = basic_tokenize(preprocess(tweets))
            tags = nltk.pos_tag(tokens)
            tag_list = [x[1] for x in tags]
            #for i in range(0, len(tokens)):
            tag_str = " ".join(tag_list)
            tweet_tags.append(tag_str)
            return tweet_tags

        def count_twitter_objs(text_string):
            """
            Accepts a text string and replaces:
            1) urls with URLHERE
            2) lots of whitespace with one instance
            3) mentions with MENTIONHERE
            4) hashtags with HASHTAGHERE

            This allows us to get standardized counts of urls and mentions
            Without caring about specific people mentioned.

            Returns counts of urls, mentions, and hashtags.
            """
            space_pattern = '\s+'
            giant_url_regex = ('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
                '[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            mention_regex = '@[\w\-]+'
            hashtag_regex = '#[\w\-]+'
            parsed_text = re.sub(space_pattern, ' ', text_string)
            parsed_text = re.sub(giant_url_regex, 'URLHERE', parsed_text)
            parsed_text = re.sub(mention_regex, 'MENTIONHERE', parsed_text)
            parsed_text = re.sub(hashtag_regex, 'HASHTAGHERE', parsed_text)
            return(parsed_text.count('URLHERE'),parsed_text.count('MENTIONHERE'),parsed_text.count('HASHTAGHERE'))

        def other_features_(tweet):
            """This function takes a string and returns a list of features.
            These include Sentiment scores, Text and Readability scores,
            as well as Twitter specific features.

            This is modified to only include those features in the final
            model."""

            sentiment = sentiment_analyzer.polarity_scores(tweet)

            words = preprocess(tweet) #Get text only

            syllables = textstat.syllable_count(words) #count syllables in words
            num_chars = sum(len(w) for w in words) #num chars in words
            num_chars_total = len(tweet)
            num_terms = len(tweet.split())
            num_words = len(words.split())
            avg_syl = round(float((syllables+0.001))/float(num_words+0.001),4)
            num_unique_terms = len(set(words.split()))

            ###Modified FK grade, where avg words per sentence is just num words/1
            FKRA = round(float(0.39 * float(num_words)/1.0) + float(11.8 * avg_syl) - 15.59,1)
            ##Modified FRE score, where sentence fixed to 1
            FRE = round(206.835 - 1.015*(float(num_words)/1.0) - (84.6*float(avg_syl)),2)

            twitter_objs = count_twitter_objs(tweet) #Count #, @, and http://
            features = [FKRA, FRE, syllables, num_chars, num_chars_total, num_terms, num_words,
                        num_unique_terms, sentiment['compound'],
                        twitter_objs[2], twitter_objs[1],]
            #features = pandas.DataFrame(features)
            return features

        def get_oth_features(tweets):
            """Takes a list of tweets, generates features for
            each tweet, and returns a numpy array of tweet x features"""
            feats=[]
            for t in tweets:
                feats.append(other_features_(t))
            return np.array(feats)


        def transform_inputs(tweets, tf_vectorizer, idf_vector, pos_vectorizer):
            """
            This function takes a list of tweets, along with used to
            transform the tweets into the format accepted by the model.

            Each tweet is decomposed into
            (a) An array of TF-IDF scores for a set of n-grams in the tweet.
            (b) An array of POS tag sequences in the tweet.
            (c) An array of features including sentiment, vocab, and readability.

            Returns a pandas dataframe where each row is the set of features
            for a tweet. The features are a subset selected using a Logistic
            Regression with L1-regularization on the training data.

            """
            tf_array = tf_vectorizer.fit_transform(tweets).toarray()
            tfidf_array = tf_array*idf_vector
            print ("Built TF-IDF array")
            #print tweets
            pos_tags = get_pos_tags(tweets)
            #print get_pos_tags(tweets)
            pos_array = pos_vectorizer.fit_transform(pos_tags).toarray()
            print ("Built POS array")
            #print pos_vectorizer.fit_transform(pos_tags).toarray()
            oth_array = get_oth_features(tweets)
            print ("Built other feature array")
            #print get_oth_features(tweets)
            M = np.concatenate([tfidf_array, pos_array, oth_array],axis=1)
            return pd.DataFrame(M)

        def predictions(X, model):
            """
            This function calls the predict function on
            the trained model to generated a predicted y
            value for each observation.
            """
            y_preds = model.predict(X)
            return y_preds

        def class_to_name(class_label):
            """
            This function can be used to map a numeric
            feature name to a particular class.
            """
            if class_label == 0:
                return "Hate speech"
            elif class_label == 1:
                return "Offensive language"
            elif class_label == 2:
                return "Neither"
            else:
                return "No label"

        def get_tweets_predictions(tweets, perform_prints=True):
            fixed_tweets = []
            #for i, t_orig in enumerate(tweets):
            s = tweets
            try:
                s = s.encode("latin1")
            except:
                try:
                    s = s.encode("utf-8")
                except:
                    pass
            if type(s) != unicode:
                fixed_tweets.append(unicode(s, errors="ignore"))
            else:
                fixed_tweets.append(s)
            #print fixed_tweets
            print tweets
            #assert len(tweets) == len(fixed_tweets), "shouldn't remove any tweets"
            tweets = fixed_tweets
            print (len(tweets), " tweets to classify")

            print ("Loading trained classifier... ")
            model = joblib.load('final_model.pkl')

            print ("Loading other information...")
            tf_vectorizer = joblib.load('final_tfidf.pkl')
            idf_vector = joblib.load('final_idf.pkl')
            pos_vectorizer = joblib.load('final_pos.pkl')
            #Load ngram dict
            #Load pos dictionary
            #Load function to transform data

            print ("Transforming inputs...")
            X = transform_inputs(tweets, tf_vectorizer, idf_vector, pos_vectorizer)

            print ("Running classification model...")
            predicted_class = predictions(X, model)

            return predicted_class	

        def initial(comt):
                print ("Loading data to classify...")
            #Tweets obtained here: https://github.com/sashaperigo/Trump-Tweets
                
                trump_tweets = comt
                trump_predictions = get_tweets_predictions(trump_tweets)

                print ("Printing predicted values: ")
            #for i,t in enumerate(trump_tweets):
                #print t
                ans = class_to_name(trump_predictions)
                print(ans)
                return ans
        if request.form['submit_but'] == 'predict':	
            comt = request.form['comt']
            my_prediction=initial(comt)
            return render_template('demoForm.html',val=comt,res = my_prediction)
        if request.form['submit_but'] == 'twitter':
            tweet2classify = rt.randtweet().encode('utf-8')
            #print(tweet2classify)
            try:
                tweet2classify = tweet2classify.encode("latin1")
            except:
                try:
                    tweet2classify = tweet2classify.encode("utf-8")
                except:
                    pass
            if type(tweet2classify) != unicode:
                tweet2classify=unicode(tweet2classify, errors="ignore")
            else:
                tweet2classify=tweet2classify
            my_prediction=initial(tweet2classify)
            return render_template('demoForm.html',val=tweet2classify,res = my_prediction)
            

	
if __name__ == '__main__':
	app.run(debug=True)
        #getValue()
	
	
@app.route('/result', methods=['POST','GET'])	
def dispresult():
	#return render_template('demoForm.html',val=comt,res=res_val)
    render_template('demoForm.html',res = my_prediction)
        
