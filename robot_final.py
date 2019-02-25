#准备：

import string
from rasa_nlu.model import Interpreter
import json
import re
import random
import spacy
from iexfinance import get_historical_data
from datetime import datetime
from iexfinance import Stock


#rasa
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config

trainer = Trainer(config.load("config_spacy.yml"))
training_data = load_data('training_data.json')

print(training_data)
interpreter = trainer.train(training_data)

import requests  #通过request获取信息/API
url = "http://api.github.com/search/repositories?q=language:python&sort=stars"
r = requests.get(url)
response_dict = r.json()
repo_dicts = response_dict ["items"]


# Define the states
INIT = 0
START_SEARCH = 1
SEARCH = 2
SEARCH_TOTAL = 3
SEARCH_TOP = 4
SEARCH_NAME = 5
SEARCH_OWNER = 6
SEARCH_URL = 7
SEARCH_STARS = 8
STOCK_PRICE = 9
STOCK_DATA = 10

#初始化参数ß
messages = ["0"]
states = [INIT]
message = messages[-1]
deny_ents = []

#实体识别
def get_entity(message):
    nlp = spacy.load("en_core_web_md")
    doc=nlp(message)
    if doc.ents == ():
        return None

    else:
        return  doc.ents[0].text


rules = {
    'i like (.*)': ['What would it mean if you got {0}', 'Why do you want {0}', "What's stopping you from getting {0}"],
    'do you remember (.*)': ['Did you think I would forget {0}',
                             "Why haven't you been able to forget {0}",
                             'What do you mean about {0}',
                             'Yes .. and?'],
    'do you think (.*)': ['If {0}? Absolutely.',
                          'Of course! No doubt about that.'],
    'if (.*)': ["Do you really think it's likely that {0}",
                'Do you wish that {0}',
                'What do you think about {0}',
                'Really--if {0}'],
    'do you like (.*)': ["perhaps..I've never thought about that. Do you like it?",
                         'Um, I would say: yes! No doubt about that.',
                         "What are you talking about? How could I like {0}"]
}

#random.choice answer
responses = {

    'greet': ['Hello you! :)'],
    'thankyou' : ['you are very welcome',"no problem","my pleasure."],
    'goodbye': ['goodbye for now','byebye!'],
    'name':["{0}? That's a good name","hi! {0}"],

}

answer = ["what you are looking for is: {0}.","{0} is what I've found","The repository you want named: {}"]


def match_rule(rules, message):    #phras：替换式回答里面需要保留的部分
    response, phrase = "default", None
    message = message.lower()
    # Iterate over the rules dictionary
    for pattern, responses in rules.items():
        # Create a match object
        match = re.search(pattern, message)
        if match is not None:
            # Choose a random response
            response = random.choice(responses)
            if '{0}' in response:
                phrase = match.group(1)
        if match is None:
            return response, phrase
    Response_identify = 1
    return response, phrase


#人称替换  Define replace_pronouns()
def replace_pronouns(message):
    message = message.lower()
    if 'me' in message:
        # Replace 'me' with 'you'
        return re.sub("me","you",message)
    if 'my' in message:
        # Replace 'my' with 'your'
        return re.sub("my","your",message)
    if 'your' in message:
        # Replace 'your' with 'my'
        return re.sub("your","my",message)
    if 'you' in message:
        # Replace 'you' with 'me'
        return re.sub("you","I",message)
    return message

def chitchat_response(message):
    # Call match_rule()
    response, phrase = match_rule(rules, message)
    # Return none is response is "default"
    if response == "default":
        return None
    if '{0}' in response:
        # Replace the pronouns of phrase
        phrase = replace_pronouns(phrase)
        # Calculate the response
        response = response.format(phrase)
        return response

#意图识别(解析message)
def interpret(message):
    interpreter = Interpreter.load("./models/current/nlu")
    result = interpreter.parse(message)
    #print(json.dumps(result, indent=2))
    intent = result['intent']['name']
    #print(intent)
    return str(intent)


def tell_joke():
    request = json.loads(requests.get('https://api.chucknorris.io/jokes/random').text)  # make an api call
    joke = request['value']  # extract a joke from returned json response
    return joke


#获取github实时python库的数量
def find_python_total_count():
    return "There are {0} repositories of Python on Github. I can show you statistic chart of them If you want .".format(response_dict["total_count"])


#查询最受欢迎的item
def find_top_item():
    return "The most popular repository is: {0}.".format(repo_dicts[0]['name'])

#通过name查询detail
def find_information_name(message):
    i=0
    pattern = re.compile(r'#(.*?)#')
    match = re.search(pattern, message)
    if match is None:
        return "Sorry, no repository is eligible."
    if match is not None:
        name = match.group(1)
        while i < 30:
            if repo_dicts[i]["name"] == str(name):
                return "Details - Name: {}, Owner: {}, Stars: {}, Repository: {} Created: {}, Updated: {}, Destription: {} (＾－＾)".format(repo_dicts[i]['name'],repo_dicts[i]["owner"]["login"],repo_dicts[i]["stargazers_count"],repo_dicts[i]["html_url"],repo_dicts[i]["created_at"],repo_dicts[i]["updated_at"],repo_dicts[i]["description"])
            else: i+=1
    return "Sorry, no repository is eligible"

#通过owner获得project名字
def get_item_owner(message):
    pattern = re.compile(r'-(.*?)-')   #从message 中提取owner
    i = 0
    match = re.search(pattern, message)
    if match is None:
        return "Sorry, no repository is eligible.",None
    if match is not None:
        owner = match.group(1)
    while i < 30:
        if str(owner) == repo_dicts[i]["owner"]["login"]:
            return  random.choice(answer).format(repo_dicts[i]['name']),i
        else:
            i+=1
    return "Sorry, no repository is eligible",None



#通过url获得project名字
def get_item_url(message):
    str(message)
    pattern =re.compile(r'[a-zA-z]+://[^\s]*')
    i = 0
    match = re.search(pattern, message)
    if match is None:
        return "Sorry, no repository is eligible.",None
    if match is not None:
        url = match.group(0)
        while i < 30:
            if str(url) == str(repo_dicts[i]["html_url"]):
                return random.choice(answer).format(repo_dicts[i]['name']),i
            else:
                if i == 29:
                    return "Sorry, no repository is eligible",None
                else:
                    i+=1


def get_item_star(message):
    stars = re.sub("\D", "",message)
    i = 0
    while i < 30:
        if str(repo_dicts[i]["stargazers_count"]) == stars:
            return random.choice(answer).format(repo_dicts[i]["name"]),i
        else:
            i+=1
            if i ==29:
                return "Sorry, no repository is eligible",None


def random_item():
    ran = list(range(0,29))
    i = random.sample(ran, 1)[0]
    return "information - Name: {}, Owner: {}, Stars: {}, Repository: {} Created: {}, Updated: {}, Destription: {} (＾－＾)".format(repo_dicts[i]['name'],repo_dicts[i]["owner"]["login"],repo_dicts[i]["stargazers_count"],repo_dicts[i]["html_url"],repo_dicts[i]["created_at"],repo_dicts[i]["updated_at"],repo_dicts[i]["description"])



def other_infor(msg):
    if msg is None:
        return "Sorry, I can't find any information."
    else:
        i = int(msg)
        return "information - Name: {}, Owner: {}, Stars: {}, Repository: {} Created: {}, Updated: {}, Destription: {} (＾－＾)".format(repo_dicts[i]['name'],repo_dicts[i]["owner"]["login"],repo_dicts[i]["stargazers_count"],repo_dicts[i]["html_url"],repo_dicts[i]["created_at"],repo_dicts[i]["updated_at"],repo_dicts[i]["description"])




#股票查询_price
def get_price(message):
    nlp = spacy.load("en_core_web_md")
    doc = nlp(message)

    if doc.ents == ():
        #ent = None
        return "sorry, I can't find any information."

    else:
        ent = doc.ents[0].text
        price = Stock(ent)
        price.get_open()
        price.get_price()

        batch = Stock([ent])
        return "The price of {} is {}. ".format(ent, batch.get_price())


def get_data(message):
    nlp = spacy.load("en_core_web_md")
    doc=nlp(message)
    if doc.ents == ():
        #ent = None
        return "sorry, I can't find any information."

    else:
        ent=doc.ents[0].text
        start = datetime(2019, 1, 13)
        end = datetime(2019, 1, 17)
        df = get_historical_data(ent, start=start, end=end, output_format='pandas')
        return df.head()


# Define the policy rules
policy_rules = {
    (INIT, "function_ask"): (SEARCH, "I can help you to check information of python on Github and provide you with any Real-Time stock information\nDo you want to search now?"),
    (INIT, "greet"): (INIT,random.choice(responses['greet'])),
    (INIT, "name"): (INIT,random.choice(responses['name']).format(get_entity(message))),
    (SEARCH, "deny"): (SEARCH, "Ok. Just tell me if you want ＾－＾"),
    (SEARCH, "affirm"): (START_SEARCH, "Okay!\nPlease tell me what you want.\n--By the way, if you want to search by NAME, remenber using # # to highlight it. \nif you want to search by owner,please using - - to highlight the owner's name :)"),

    (START_SEARCH, "joke"): (START_SEARCH, tell_joke()),
    (START_SEARCH, "get_random"): (START_SEARCH, random_item()),
    (START_SEARCH, "get"): (START_SEARCH, "Hope to help you next time :)"),
    (START_SEARCH, "thankyou"): (START_SEARCH, "That's OK!"),
    (START_SEARCH, "deny"): (START_SEARCH, "OK. Always happy to help you!"),

    (START_SEARCH, "find_python_total_count"): (SEARCH_TOTAL, find_python_total_count()),
    (SEARCH_TOTAL, "deny"): (START_SEARCH, "OK. Always happy to help you!"),
    (SEARCH_TOTAL, "affirm"): (START_SEARCH, "There is the chart: AxesImage(80,52.8;496x369.6)"),
    (SEARCH_TOTAL, "find_information_name"): (SEARCH_NAME, find_information_name(message)),
    (SEARCH_TOTAL, "get_random"): (START_SEARCH, random_item()),
    (SEARCH_TOTAL, "joke"): (START_SEARCH, tell_joke()),

    (START_SEARCH, "find_top_item"): (SEARCH_TOP, find_top_item()),
    (SEARCH_TOP, "thankyou"): (START_SEARCH, "No problem!"),
    (SEARCH_TOP, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you next time :)"),
    (SEARCH_TOP, "get_random"): (START_SEARCH, random_item()),
    (SEARCH_TOP, "joke"): (START_SEARCH, tell_joke()),
    (SEARCH_TOP, "otherinfor"):(START_SEARCH,other_infor(0)),

    (START_SEARCH, "find_information_name"): (SEARCH_NAME,find_information_name(message)),
    (SEARCH_NAME, "find_information_name"): (START_SEARCH,find_information_name(message)),
    (SEARCH_NAME, "get"): (START_SEARCH, "Always happy to help you!"),
    (SEARCH_NAME, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you again :)"),
    (SEARCH_NAME, "get_random"): (START_SEARCH, random_item()),
    (SEARCH_NAME, "thankyou"): (START_SEARCH, "My pleaseure."),
    (SEARCH_NAME, "get_item_owner"): (SEARCH_OWNER, get_item_owner(message)[0]),
    (SEARCH_NAME, "get_item_url"): (SEARCH_URL, get_item_url(message)[0]),
    (SEARCH_NAME, "get_item_star"): (SEARCH_STARS, get_item_star(message)[0]),

    (START_SEARCH, "get_item_owner"): (SEARCH_OWNER, get_item_owner(message)[0]),
    (SEARCH_OWNER, "get"): (START_SEARCH, "Always happy to help you!"),
    (SEARCH_OWNER, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you next time :)"),
    (SEARCH_OWNER, "get_item_url"): (SEARCH_URL, get_item_url(message)[0]),
    (SEARCH_OWNER, "thankyou"): (START_SEARCH, "My pleaseure."),
    (SEARCH_OWNER, "get_item_owner"): (START_SEARCH, get_item_owner(message)[0]),
    (SEARCH_OWNER, "get_item_star"): (SEARCH_STARS, get_item_star(message)[0]),
    (SEARCH_OWNER, "find_information_name"): (START_SEARCH,find_information_name(message)),
    (SEARCH_OWNER, "otherinfor"):(START_SEARCH,other_infor(get_item_owner(message)[1])),

    (START_SEARCH, "get_item_url"): (SEARCH_URL, get_item_url(message)[0]),
    (SEARCH_URL, "get_item_url"): (START_SEARCH, get_item_url(message)[0]),
    (SEARCH_URL, "get"): (START_SEARCH, "Always happy to help you!"),
    (SEARCH_URL, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you again :)"),
    (SEARCH_URL, "find_top_item"): (START_SEARCH, find_top_item()),
    (SEARCH_URL, "get_item_star"): (SEARCH_STARS, get_item_star(message)[0]),
    (SEARCH_URL, "thankyou"): (START_SEARCH, "You are welcome."),
    (SEARCH_URL, "get_stock_history_data"): (START_SEARCH, get_price(message)),
    (SEARCH_URL, "get_item_owner"): (SEARCH_OWNER, get_item_owner(message)[0]),
    (SEARCH_URL, "find_information_name"): (START_SEARCH,find_information_name(message)),
    (SEARCH_URL, "otherinfor"):(START_SEARCH,other_infor(get_item_url(message)[1])),

    (START_SEARCH, "get_item_star"): (SEARCH_STARS, get_item_star(message)[0]),
    (SEARCH_STARS, "get_item_star"): (START_SEARCH, get_item_star(message)[0]),
    (SEARCH_STARS, "get"): (START_SEARCH, "Always happy to help you!"),
    (SEARCH_STARS, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you next time :)"),
    (SEARCH_STARS, "get_item_owner"): (SEARCH_OWNER, get_item_owner(message)[0]),
    (SEARCH_STARS, "get_item_url"): (SEARCH_URL, get_item_star(message)[0]),
    (SEARCH_STARS, "thankyou"): (START_SEARCH, "No problem!"),
    (SEARCH_STARS, "find_information_name"): (START_SEARCH,find_information_name(message)),
    (SEARCH_STARS, "otherinfor"):(START_SEARCH,other_infor(get_item_star(message)[1])),


    (START_SEARCH, "get_stock_price"): (STOCK_PRICE, get_price(message)),
    (STOCK_PRICE, "get_stock_history_data"): (START_SEARCH, get_data(message)),
    (STOCK_PRICE, "get"): (START_SEARCH, "Hope to help you again!"),
    (STOCK_PRICE, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you next time :)"),
    (STOCK_PRICE, "thankyou"): (START_SEARCH, "No problem!"),


    (START_SEARCH, "get_stock_history_data"): (STOCK_DATA, get_data(message)),
    (STOCK_DATA, "get"): (START_SEARCH, "Hope to help you again!"),
    (STOCK_DATA, "deny"): (START_SEARCH, "Sorry, I can't find other relative information. Hope to help you next time :)"),
    (STOCK_DATA, "thankyou"): (START_SEARCH, "No problem!")
}

def send_message(state, message):
    print("USER : {}".format(message))
    response = chitchat_response(message)
    if response is not None:
        print("BOT : {}".format(response))
        states.append(state)
        return response

    intent = interpret(message)


    #根据意图将相应message内容及时替换进policy_rules
    if intent == "get_stock_price":
        policy_rules[(START_SEARCH, "get_stock_price")] = (STOCK_PRICE, get_price(message))

    elif intent == "name":
        policy_rules[(INIT, "name")] = (INIT,random.choice(responses['name']).format(get_entity(message)))

    elif intent == "get_stock_history_data":
        policy_rules[(STOCK_PRICE, "get_stock_history_data")] = (START_SEARCH, get_data(message))
        policy_rules[(START_SEARCH, "get_stock_history_data")] = (STOCK_DATA, get_data(message))
        policy_rules[(SEARCH_URL, "get_stock_history_data")] = (STOCK_DATA, get_data(message))

    elif intent == "find_information_name":
        policy_rules[(SEARCH_TOTAL, "find_information_name")] = (START_SEARCH, find_information_name(message))
        policy_rules[(START_SEARCH, "find_information_name")] = (SEARCH_NAME, find_information_name(message))
        policy_rules[(SEARCH_STARS, "find_information_name")] = (START_SEARCH, find_information_name(message))
        policy_rules[(SEARCH_URL, "find_information_name")] = (START_SEARCH,find_information_name(message))
        policy_rules[(SEARCH_OWNER, "find_information_name")] = (START_SEARCH,find_information_name(message))
        policy_rules[(SEARCH_NAME, "find_information_name")] = (START_SEARCH,find_information_name(message))

    elif intent == "get_item_owner":
        policy_rules[(START_SEARCH, "get_item_owner")] = (SEARCH_OWNER, get_item_owner(message)[0])
        policy_rules[(SEARCH_STARS, "get_item_owner")] = (SEARCH_OWNER, get_item_owner(message)[0])
        policy_rules[(SEARCH_URL, "get_item_owner")] = (SEARCH_OWNER, get_item_owner(message)[0])
        policy_rules[(SEARCH_OWNER, "get_item_owner")] = (SEARCH_OWNER, get_item_owner(message)[0])
        policy_rules[(SEARCH_NAME, "get_item_owner")] = (SEARCH_OWNER, get_item_owner(message)[0])
        policy_rules[(SEARCH_OWNER, "otherinfor")] = (START_SEARCH,other_infor(get_item_owner(message)[1]))


    elif intent == "get_item_url":
        policy_rules[(START_SEARCH, "get_item_url")] = (SEARCH_URL, get_item_url(message)[0])
        policy_rules[(SEARCH_STARS, "get_item_url")] = (SEARCH_URL, get_item_star(message)[0])
        policy_rules[ (SEARCH_URL, "get_item_url")] = (START_SEARCH, get_item_url(message)[0])
        policy_rules[(SEARCH_OWNER, "get_item_url")] = (SEARCH_URL, get_item_url(message)[0])
        policy_rules[(SEARCH_NAME, "get_item_url")] = (SEARCH_URL, get_item_url(message)[0])
        policy_rules[(SEARCH_URL, "otherinfor")] = (START_SEARCH,other_infor(get_item_url(message)[1]))

    elif intent == "get_item_star":
        policy_rules[(START_SEARCH, "get_item_star")] = (SEARCH_STARS, get_item_star(message)[0])
        policy_rules[(SEARCH_STARS, "get_item_star")] = (START_SEARCH, get_item_star(message)[0])
        policy_rules[(SEARCH_URL, "get_item_star")] = (SEARCH_STARS, get_item_star(message)[0])
        policy_rules[(SEARCH_OWNER, "get_item_star")] = (SEARCH_STARS, get_item_star(message)[0])
        policy_rules[(SEARCH_NAME, "get_item_star")] = (SEARCH_STARS, get_item_star(message)[0])
        policy_rules[(SEARCH_STARS, "otherinfor")] = (START_SEARCH,other_infor(get_item_star(message)[1]))





    # Calculate the new_state, response, and pending_state
    new_state, response = policy_rules[(state, intent)]
    print("BOT : {}".format(response))
    states.append(new_state)
    return response

from wxpy import *
bot = Bot(cache_path = True)  #
myFriend = bot.friends("keep going") #确定接收消息的对象


@bot.register(chats= None, msg_types=None, except_self=True) #注册消息处理方法：自动回复
def forward_message(message):
    state = states[-1]
    print(states)
    print(state)
    messages.append(message.text)
    print(messages[-1])
    answer = send_message(state,messages[-1])
    return answer

embed()